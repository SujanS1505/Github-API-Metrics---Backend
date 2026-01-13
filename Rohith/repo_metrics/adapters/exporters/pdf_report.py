from __future__ import annotations

from datetime import datetime
from typing import Dict, Iterable, List, Mapping, Optional, Sequence
import re
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    SimpleDocTemplate,
    Spacer,
    Paragraph,
    Table,
    TableStyle,
    PageBreakIfNotEmpty,
    HRFlowable,
    KeepTogether,
)


def _fmt(value: object) -> str:
    if value is None:
        return "N/A"
    return str(value)


def _short_date(value: object) -> str:
    """Shorten GitHub ISO timestamps to a compact date/time.

    Prefer YYYY-MM-DD, and if a time is present keep up to minutes.
    """

    s = _fmt(value)
    if len(s) >= 16 and "T" in s:
        return s[:16]
    if len(s) >= 10:
        return s[:10]
    return s


_COLOR_TEXT = colors.HexColor("#111827")
_COLOR_MUTED = colors.HexColor("#6B7280")
_COLOR_GRID = colors.HexColor("#CBD5E1")  # slate-300 (softer than #E5E7EB)
_COLOR_ROW_ALT = colors.HexColor("#F9FAFB")
_COLOR_HEADER_BG = colors.HexColor("#111827")
_COLOR_HEADER_FG = colors.white


def _draw_header_footer(*, canvas: Canvas, doc: SimpleDocTemplate, owner: str, repo: str, generated_at_utc: datetime) -> None:
    canvas.saveState()

    width, height = doc.pagesize
    left = doc.leftMargin
    right = width - doc.rightMargin
    top = height - doc.topMargin + 0.35 * inch
    bottom = doc.bottomMargin - 0.45 * inch

    canvas.setStrokeColor(_COLOR_GRID)
    canvas.setLineWidth(0.7)
    canvas.line(left, top - 0.18 * inch, right, top - 0.18 * inch)
    canvas.line(left, bottom + 0.25 * inch, right, bottom + 0.25 * inch)

    canvas.setFillColor(_COLOR_TEXT)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(left, top, f"Repository Activity Report")

    canvas.setFillColor(_COLOR_MUTED)
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(right, top, f"{owner}/{repo} • Generated {generated_at_utc.strftime('%Y-%m-%d %H:%M UTC')}")

    canvas.setFillColor(_COLOR_MUTED)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(left, bottom, f"{owner}/{repo}")
    canvas.drawRightString(right, bottom, f"Page {doc.page}")

    canvas.restoreState()


def _styled_table(
    data: Sequence[Sequence[object]],
    *,
    col_widths: Sequence[float] | None = None,
    header_bg: colors.Color = _COLOR_HEADER_BG,
    header_fg: colors.Color = _COLOR_HEADER_FG,
    numeric_cols_right: Sequence[int] = (),
    repeat_rows: int = 1,
) -> Table:
    t = Table(data, colWidths=col_widths, repeatRows=repeat_rows)

    style_cmds: list[tuple] = [
        ("BACKGROUND", (0, 0), (-1, 0), header_bg),
        ("TEXTCOLOR", (0, 0), (-1, 0), header_fg),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("LEADING", (0, 1), (-1, -1), 10),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _COLOR_ROW_ALT]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        # More whitespace; feels less cramped.
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, 0), 6),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        # Elegant borders: outer box + subtle row separators (no harsh full grid).
        ("BOX", (0, 0), (-1, -1), 0.6, _COLOR_GRID),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, _COLOR_GRID),
        ("LINEBELOW", (0, 1), (-1, -1), 0.25, _COLOR_GRID),
    ]

    for col in numeric_cols_right:
        style_cmds.append(("ALIGN", (col, 1), (col, -1), "RIGHT"))
        style_cmds.append(("ALIGN", (col, 0), (col, 0), "RIGHT"))

    t.setStyle(TableStyle(style_cmds))
    return t


def _widths_from_fracs(total_width: float, fracs: Sequence[float]) -> List[float]:
    """Convert fractional column widths to absolute widths.

    This keeps tables aligned to the available page width and prevents overflow.
    """

    if not fracs:
        return []
    s = float(sum(fracs))
    if s <= 0:
        raise ValueError("Column fractions must sum to > 0")
    widths = [total_width * (float(f) / s) for f in fracs]
    widths[-1] = total_width - sum(widths[:-1])
    return widths


def _add_section(
    story: List[object],
    title: str,
    *,
    h2_style: ParagraphStyle,
    new_page: bool,
) -> None:
    if new_page:
        # Avoid creating a blank page when the previous flowable already
        # consumed the page exactly and Platypus has implicitly advanced.
        story.append(PageBreakIfNotEmpty())
    story.append(Paragraph(title, h2_style))
    story.append(HRFlowable(width="100%", thickness=0.6, color=_COLOR_GRID, spaceBefore=2, spaceAfter=10))
    story.append(Spacer(1, 4))


def _remove_header_only_pages(*, pdf_path: str, owner: str, repo: str) -> None:
    """Remove pages that contain only the header/footer.

    ReportLab/Platypus can occasionally emit an "empty" page between explicit
    page breaks. Because we always draw a header/footer, these pages aren't
    technically empty, but they look blank to the reader.
    """

    try:
        from pypdf import PdfReader, PdfWriter  # type: ignore[import-not-found]
    except Exception:
        return

    path = Path(pdf_path)
    if not path.exists():
        return

    reader = PdfReader(str(path))
    writer = PdfWriter()

    owner_repo = f"{owner}/{repo}".strip()
    generated_re = re.compile(r"Generated\s+\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}\s+UTC", re.IGNORECASE)
    page_re = re.compile(r"Page\s+\d+", re.IGNORECASE)

    def is_header_only(page) -> bool:
        text = (page.extract_text() or "").strip()
        if not text:
            return True
        # Normalize and remove known header/footer strings.
        compact = re.sub(r"\s+", " ", text)
        compact = compact.replace("Repository Activity Report", "")
        if owner_repo:
            compact = compact.replace(owner_repo, "")
        compact = generated_re.sub("", compact)
        compact = page_re.sub("", compact)
        # Some PDFs include odd control characters in extracted text.
        compact = re.sub(r"[\x00-\x1F\x7F]+", "", compact)
        compact = re.sub(r"[\s\|•\-]+", " ", compact).strip()
        # Check if the remaining text is minimal (< 20 chars) - likely just artifacts
        return len(compact) < 20

    removed_any = False
    for page in reader.pages:
        if is_header_only(page):
            removed_any = True
            continue
        writer.add_page(page)

    if not removed_any:
        return

    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("wb") as f:
        writer.write(f)
    tmp_path.replace(path)


def write_repository_activity_pdf(
    *,
    output_path: str,
    owner: str,
    repo: str,
    days: int,
    generated_at_utc: datetime,
    summary_rows: Sequence[Sequence[object]],
    bus_factor_details: Mapping[str, object],
    author_frequency: Mapping[str, int],
    per_day: Mapping[str, int],
    per_week: Mapping[str, int],
    per_month: Mapping[str, int],
    branches: Optional[Sequence[Mapping[str, object]]] = None,
    merge_summary: Optional[Mapping[str, object]] = None,
    merged_prs: Optional[Sequence[Mapping[str, object]]] = None,
    merges_per_day: Optional[Mapping[str, int]] = None,
    merges_per_week: Optional[Mapping[str, int]] = None,
    merges_per_month: Optional[Mapping[str, int]] = None,
    pr_lead_time_summary: Optional[Mapping[str, object]] = None,
    pr_efficiency_summary: Optional[Mapping[str, object]] = None,
    closed_not_merged_prs: Optional[Sequence[Mapping[str, object]]] = None,
    pr_reopen_rate_summary: Optional[Mapping[str, object]] = None,
    pr_quality_summary: Optional[Mapping[str, object]] = None,
    top_authors_limit: int = 25,
) -> None:
    """Generate a clean PDF report from computed metrics.

    This intentionally avoids HTML->PDF converters (hard on Windows). ReportLab is
    pure-Python and stable.
    """

    doc = SimpleDocTemplate(
        output_path,
        pagesize=LETTER,
        # More whitespace for a cleaner, less cramped feel.
        leftMargin=0.85 * inch,
        rightMargin=0.85 * inch,
        topMargin=1.10 * inch,
        bottomMargin=1.00 * inch,
        title=f"Repository Activity Report - {owner}/{repo}",
        author="GitHub Repo Metrics",
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "Title",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=27,
        textColor=_COLOR_TEXT,
        spaceAfter=8,
    )

    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=11,
        leading=15,
        textColor=_COLOR_MUTED,
        spaceAfter=14,
    )

    h2 = ParagraphStyle(
        "H2",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=_COLOR_TEXT,
        spaceBefore=18,
        spaceAfter=8,
    )

    body = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=_COLOR_TEXT,
        spaceAfter=6,
    )

    table_cell = ParagraphStyle(
        "TableCell",
        parent=body,
        fontSize=8,
        leading=10,
    )

    story: List[object] = []

    page_width = float(doc.width)

    story.append(Paragraph(f"Repository Activity Report", title_style))
    story.append(
        Paragraph(
            f"<b>Repo:</b> {owner}/{repo} &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>Window:</b> last {days} days &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>Generated (UTC):</b> {generated_at_utc.strftime('%Y-%m-%d %H:%M:%S')}",
            subtitle_style,
        )
    )

    # Summary table
    _add_section(story, "Summary", h2_style=h2, new_page=False)
    summary_data = [["Metric", "Value", "Notes"]]
    for metric_name, metric_value, notes in summary_rows:
        summary_data.append(
            [
                Paragraph(escape(str(metric_name)), table_cell),
                Paragraph(escape(_fmt(metric_value)), table_cell),
                Paragraph(escape(_fmt(notes)), table_cell),
            ]
        )

    summary_table = _styled_table(
        summary_data,
        col_widths=_widths_from_fracs(page_width, [0.44, 0.16, 0.40]),
        numeric_cols_right=(1,),
    )
    story.append(summary_table)
    story.append(Spacer(1, 14))

    # Merge frequency
    if merge_summary is not None:
        _add_section(story, "Merge Frequency (Integration Cadence)", h2_style=h2, new_page=True)
        story.append(
            Paragraph(
                f"Merged PRs in window: <b>{_fmt(merge_summary.get('merged_prs'))}</b><br/>"
                f"Avg merges/week: <b>{_fmt(round(float(merge_summary.get('merges_per_week', 0.0)), 2))}</b><br/>"
                f"Avg hours between merges: <b>{_fmt(round(float(merge_summary.get('avg_time_between_merges_hours')), 2) if isinstance(merge_summary.get('avg_time_between_merges_hours'), (int, float)) else merge_summary.get('avg_time_between_merges_hours'))}</b>",
                body,
            )
        )
        try:
            merged_prs_count = int(merge_summary.get("merged_prs") or 0)
        except Exception:
            merged_prs_count = 0
        if merged_prs_count == 0:
            story.append(
                Paragraph(
                    "<i>Note:</i> No merged pull requests were found in this window. "
                    "Some repositories (e.g., GitHub mirrors) integrate changes via direct pushes or merge commits "
                    "outside GitHub PR workflows, so PR-based merge metrics can legitimately be 0/N/A.",
                    subtitle_style,
                )
            )
        story.append(Spacer(1, 12))

        if merged_prs:
            story.append(Paragraph("Recent merged pull requests", body))
            story.append(Spacer(1, 6))
            pr_rows = list(merged_prs)[:25]
            pr_table_data: List[List[object]] = [["#", "Created at", "Merged at", "Lead (days)", "Author", "Title"]]
            for pr in pr_rows:
                created_at_raw = str(pr.get("created_at", ""))
                merged_at_raw = str(pr.get("merged_at", ""))
                created_at = created_at_raw[:10] if len(created_at_raw) >= 10 else created_at_raw
                merged_at = merged_at_raw[:10] if len(merged_at_raw) >= 10 else merged_at_raw
                lead_days = ""
                try:
                    from ...domain.metrics.pr_lead_time import pr_merge_lead_time_hours

                    lt_hours = pr_merge_lead_time_hours(pr)
                    lead_days = f"{(lt_hours / 24.0):.2f}" if isinstance(lt_hours, (int, float)) else ""
                except Exception:
                    lead_days = ""

                author = str(pr.get("author", ""))
                title = str(pr.get("title", ""))[:240]

                pr_table_data.append(
                    [
                        Paragraph(escape(str(pr.get("number", ""))), table_cell),
                        Paragraph(escape(created_at), table_cell),
                        Paragraph(escape(merged_at), table_cell),
                        Paragraph(escape(lead_days), table_cell),
                        Paragraph(escape(author), table_cell),
                        Paragraph(escape(title), table_cell),
                    ]
                )

            pr_table = _styled_table(
                pr_table_data,
                # Keep this within the printable width (was overflowing previously).
                col_widths=_widths_from_fracs(page_width, [0.07, 0.13, 0.13, 0.10, 0.14, 0.43]),
                numeric_cols_right=(0, 3),
            )
            story.append(pr_table)
            story.append(Spacer(1, 14))

        if pr_lead_time_summary is not None:
            _add_section(story, "Lead Time for Change (PR merge time)", h2_style=h2, new_page=True)

            def _fmt_hours(v: object) -> str:
                if isinstance(v, (int, float)):
                    return f"{v:.2f}"
                return _fmt(v)

            story.append(
                Paragraph(
                    f"Samples: <b>{_fmt(pr_lead_time_summary.get('count'))}</b><br/>"
                    f"Average lead time (hours): <b>{_fmt_hours(pr_lead_time_summary.get('avg_hours'))}</b><br/>"
                    f"Median lead time (hours): <b>{_fmt_hours(pr_lead_time_summary.get('median_hours'))}</b><br/>"
                    f"P75 lead time (hours): <b>{_fmt_hours(pr_lead_time_summary.get('p75_hours'))}</b><br/>"
                    f"P90 lead time (hours): <b>{_fmt_hours(pr_lead_time_summary.get('p90_hours'))}</b>",
                    body,
                )
            )
            try:
                lt_count = int(pr_lead_time_summary.get("count") or 0)
            except Exception:
                lt_count = 0
            if lt_count == 0:
                story.append(
                    Paragraph(
                        "<i>Note:</i> Lead time is computed from PR created→merged timestamps. "
                        "With zero merged PR samples in the window, lead time is reported as N/A.",
                        subtitle_style,
                    )
                )
            story.append(Spacer(1, 12))

        if pr_efficiency_summary is not None:
            _add_section(story, "PRs Merged vs Closed (Development Efficiency)", h2_style=h2, new_page=True)

            closed_prs = pr_efficiency_summary.get("closed_prs")
            merged_prs_count = pr_efficiency_summary.get("merged_prs")
            closed_not_merged = pr_efficiency_summary.get("closed_not_merged_prs")
            merge_rate = pr_efficiency_summary.get("merge_rate")
            merge_rate_pct = (
                f"{(float(merge_rate) * 100.0):.2f}%" if isinstance(merge_rate, (int, float)) else _fmt(merge_rate)
            )

            story.append(
                Paragraph(
                    f"Closed PRs (window): <b>{_fmt(closed_prs)}</b><br/>"
                    f"Merged PRs (window): <b>{_fmt(merged_prs_count)}</b><br/>"
                    f"Closed without merge: <b>{_fmt(closed_not_merged)}</b><br/>"
                    f"Merge rate (merged/closed): <b>{merge_rate_pct}</b>",
                    body,
                )
            )
            try:
                closed_count = int(closed_prs or 0)
            except Exception:
                closed_count = 0
            if closed_count == 0:
                story.append(
                    Paragraph(
                        "<i>Note:</i> No closed pull requests were found in this window, so merge rate is N/A. "
                        "If you expected PR activity, double-check `OWNER`/`REPO` and the `DAYS` window.",
                        subtitle_style,
                    )
                )
            story.append(Spacer(1, 10))

            if closed_not_merged_prs:
                story.append(Paragraph("Recently closed without merge (sample)", body))
                story.append(Spacer(1, 6))
                rows = list(closed_not_merged_prs)[:25]
                tdata: List[List[object]] = [["#", "Closed at", "Author", "Title"]]
                for pr in rows:
                    pr_num = escape(str(pr.get("number", "")))
                    closed_at = escape(_short_date(pr.get("closed_at", "")))
                    author = escape(str(pr.get("author", "")))
                    title = escape(str(pr.get("title", ""))[:240])
                    tdata.append(
                        [
                            Paragraph(pr_num, table_cell),
                            Paragraph(closed_at, table_cell),
                            Paragraph(author, table_cell),
                            Paragraph(title, table_cell),
                        ]
                    )

                t = _styled_table(
                    tdata,
                    col_widths=_widths_from_fracs(page_width, [0.10, 0.18, 0.18, 0.54]),
                    numeric_cols_right=(0,),
                )
                story.append(t)
                story.append(Spacer(1, 14))

        if pr_reopen_rate_summary is not None:
            _add_section(story, "PR Reopen Rate (Review Quality Signal)", h2_style=h2, new_page=True)

            closed_prs = pr_reopen_rate_summary.get("closed_prs")
            reopened_prs = pr_reopen_rate_summary.get("reopened_prs")
            reopen_events = pr_reopen_rate_summary.get("reopen_events")
            scanned_prs = pr_reopen_rate_summary.get("prs_scanned")
            reopen_rate = pr_reopen_rate_summary.get("reopen_rate")
            reopen_rate_pct = (
                f"{(float(reopen_rate) * 100.0):.2f}%" if isinstance(reopen_rate, (int, float)) else _fmt(reopen_rate)
            )

            story.append(
                Paragraph(
                    f"Closed PRs (window): <b>{_fmt(closed_prs)}</b><br/>"
                    f"Reopened PRs (window): <b>{_fmt(reopened_prs)}</b><br/>"
                    f"Reopen events (window): <b>{_fmt(reopen_events)}</b><br/>"
                    f"Reopen rate (reopened/closed): <b>{reopen_rate_pct}</b><br/>"
                    f"Scanned PRs (recently updated): <b>{_fmt(scanned_prs)}</b>",
                    body,
                )
            )

            story.append(
                Paragraph(
                    "<i>Note:</i> GitHub search does not provide a direct reopen-date qualifier for PRs. "
                    "This metric is computed by scanning recently-updated PRs and checking their reopen events. "
                    f"If your repository has very high PR churn, you may need to increase the scan limit.",
                    subtitle_style,
                )
            )
            story.append(Spacer(1, 10))

            details = pr_reopen_rate_summary.get("reopened_prs_details") or []
            if details:
                story.append(Paragraph("Most recently reopened PRs (sample)", body))
                story.append(Spacer(1, 6))

                rows = list(details)[:25]
                tdata: List[List[object]] = [["#", "Reopened at", "Author", "Title"]]
                for pr in rows:
                    pr_num = escape(str(getattr(pr, "number", "")))
                    reopened_at = escape(_short_date(getattr(pr, "reopened_at", "")))
                    author = escape(str(getattr(pr, "author", "")))
                    title = escape(str(getattr(pr, "title", ""))[:240])
                    tdata.append(
                        [
                            Paragraph(pr_num, table_cell),
                            Paragraph(reopened_at, table_cell),
                            Paragraph(author, table_cell),
                            Paragraph(title, table_cell),
                        ]
                    )

                t = _styled_table(
                    tdata,
                    col_widths=_widths_from_fracs(page_width, [0.10, 0.20, 0.18, 0.52]),
                    numeric_cols_right=(0,),
                )
                story.append(t)
                story.append(Spacer(1, 14))

        if pr_quality_summary is not None:
            _add_section(story, "PR Quality Metrics", h2_style=h2, new_page=True)

            def _fmt_hours(v: object) -> str:
                if isinstance(v, (int, float)):
                    return f"{v:.2f}"
                return _fmt(v)

            approval_rate = pr_quality_summary.get("approval_rate")
            approval_rate_pct = (
                f"{(float(approval_rate) * 100.0):.2f}%" if isinstance(approval_rate, (int, float)) else _fmt(approval_rate)
            )

            summary_table = _styled_table(
                [
                    ["Metric", "Value"],
                    ["PRs scanned", _fmt(pr_quality_summary.get("prs_scanned"))],
                    ["Non-draft PRs", _fmt(pr_quality_summary.get("non_draft_prs_count"))],
                    ["Avg review turnaround (hrs)", _fmt_hours(pr_quality_summary.get("review_turnaround_avg_hours"))],
                    ["Median review turnaround (hrs)", _fmt_hours(pr_quality_summary.get("review_turnaround_median_hours"))],
                    ["Avg reviewers / PR", _fmt_hours(pr_quality_summary.get("avg_reviewers_per_pr"))],
                    ["Median reviewers / PR", _fmt_hours(pr_quality_summary.get("median_reviewers_per_pr"))],
                    ["Avg PR size (LOC changed)", _fmt_hours(pr_quality_summary.get("avg_pr_loc_changed"))],
                    ["Median PR size (LOC changed)", _fmt_hours(pr_quality_summary.get("median_pr_loc_changed"))],
                    ["Avg total comments / PR", _fmt_hours(pr_quality_summary.get("avg_pr_total_comments"))],
                    ["Approval rate", approval_rate_pct],
                ],
                col_widths=_widths_from_fracs(page_width, [0.64, 0.36]),
                numeric_cols_right=(1,),
            )
            story.append(summary_table)
            story.append(Spacer(1, 12))

            story.append(
                Paragraph(
                    "<i>Definitions:</i> Review turnaround is created → first non-author review. "
                    "PR size is additions + deletions. Total comments uses issue comments + review thread count (proxy for inline review discussion).",
                    subtitle_style,
                )
            )
            story.append(Spacer(1, 10))

            largest = pr_quality_summary.get("largest_prs") or []
            slowest = pr_quality_summary.get("slowest_review_turnaround") or []

            if largest:
                story.append(Paragraph("Largest PRs (LOC changed) – sample", body))
                story.append(Spacer(1, 6))
                rows = list(largest)[:10]
                tdata: List[List[object]] = [["#", "LOC", "Author", "Title"]]
                for pr in rows:
                    tdata.append(
                        [
                            Paragraph(escape(str(getattr(pr, "number", ""))), table_cell),
                            Paragraph(escape(str(getattr(pr, "loc_changed", ""))), table_cell),
                            Paragraph(escape(str(getattr(pr, "author", ""))), table_cell),
                            Paragraph(escape(str(getattr(pr, "title", ""))[:240]), table_cell),
                        ]
                    )
                t = _styled_table(
                    tdata,
                    col_widths=_widths_from_fracs(page_width, [0.10, 0.12, 0.18, 0.60]),
                    numeric_cols_right=(0, 1),
                )
                story.append(t)
                story.append(Spacer(1, 12))

            if slowest:
                story.append(Paragraph("Slowest first-review turnaround (hours) – sample", body))
                story.append(Spacer(1, 6))
                rows = list(slowest)[:10]
                tdata = [["#", "Hrs", "Author", "Title"]]
                for pr in rows:
                    hrs = getattr(pr, "review_turnaround_hours", None)
                    hrs_s = f"{float(hrs):.2f}" if isinstance(hrs, (int, float)) else "N/A"
                    tdata.append(
                        [
                            Paragraph(escape(str(getattr(pr, "number", ""))), table_cell),
                            Paragraph(escape(hrs_s), table_cell),
                            Paragraph(escape(str(getattr(pr, "author", ""))), table_cell),
                            Paragraph(escape(str(getattr(pr, "title", ""))[:240]), table_cell),
                        ]
                    )
                t = _styled_table(
                    tdata,
                    col_widths=_widths_from_fracs(page_width, [0.10, 0.12, 0.18, 0.60]),
                    numeric_cols_right=(0, 1),
                )
                story.append(t)
                story.append(Spacer(1, 14))

        if merges_per_day is not None and merges_per_week is not None and merges_per_month is not None:
            story.append(Paragraph("Merge volume (recent buckets)", body))
            story.append(Spacer(1, 6))

            def tail_items(mapping: Mapping[str, int], n: int) -> List[List[str]]:
                keys = sorted(mapping.keys())
                keys = keys[-n:]
                return [[k, str(mapping[k])] for k in keys]

            thirds = _widths_from_fracs(page_width, [1, 1, 1])
            col_w = thirds[0]

            md = _styled_table(
                [["Day", "Merges"]] + tail_items(merges_per_day, 14),
                col_widths=_widths_from_fracs(col_w, [0.70, 0.30]),
                numeric_cols_right=(1,),
            )
            mw = _styled_table(
                [["Week", "Merges"]] + tail_items(merges_per_week, 12),
                col_widths=_widths_from_fracs(col_w, [0.70, 0.30]),
                numeric_cols_right=(1,),
            )
            mm = _styled_table(
                [["Month", "Merges"]] + tail_items(merges_per_month, 12),
                col_widths=_widths_from_fracs(col_w, [0.70, 0.30]),
                numeric_cols_right=(1,),
            )

            buckets = Table([[md, mw, mm]], colWidths=thirds)
            buckets.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                        ("TOPPADDING", (0, 0), (-1, -1), 0),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ]
                )
            )
            story.append(KeepTogether([buckets]))
            story.append(Spacer(1, 14))

    # Branch list
    if branches:
        _add_section(story, "Branches", h2_style=h2, new_page=True)
        story.append(Paragraph("Branch list (truncated to first 50).", body))
        story.append(Spacer(1, 6))

        branch_rows = list(branches)[:50]
        branch_data: List[List[object]] = [["Branch", "Protected", "Head SHA"]]
        for b in branch_rows:
            branch_data.append(
                [
                    str(b.get("name", "")),
                    "YES" if b.get("protected") else "NO",
                    str(b.get("sha", ""))[:12],
                ]
            )

        branch_table = _styled_table(branch_data, col_widths=_widths_from_fracs(page_width, [0.50, 0.14, 0.36]))
        story.append(branch_table)
        story.append(Spacer(1, 14))

    # Bus factor details
    _add_section(story, "Bus Factor (Contributor Concentration)", h2_style=h2, new_page=True)

    bf = bus_factor_details.get("bus_factor")
    bf_own = bus_factor_details.get("ownership_percent")
    bf_total = bus_factor_details.get("total_commits")
    bf_threshold = bus_factor_details.get("threshold_percent")

    story.append(
        Paragraph(
            f"Total commits in window: <b>{_fmt(bf_total)}</b><br/>"
            f"Threshold: <b>{_fmt(bf_threshold)}%</b><br/>"
            f"Bus factor: <b>{_fmt(bf)}</b> (contributors required to reach the threshold)<br/>"
            f"Cumulative ownership at cutoff: <b>{_fmt(round(bf_own, 2) if isinstance(bf_own, (int, float)) else bf_own)}%</b>",
            body,
        )
    )
    story.append(Spacer(1, 10))

    contributors: Iterable[dict] = bus_factor_details.get("contributors", [])  # type: ignore[assignment]
    bf_table_data = [["Author", "Commits", "Own %", "Cumulative %", "In bus factor"]]
    for row in contributors:
        bf_table_data.append(
            [
                str(row["author"]),
                str(row["commits"]),
                f"{row['ownership_percent']:.2f}",
                f"{row['cumulative_ownership_percent']:.2f}",
                "YES" if row["in_bus_factor"] else "NO",
            ]
        )

    bf_table = _styled_table(
        bf_table_data,
        col_widths=_widths_from_fracs(page_width, [0.40, 0.12, 0.12, 0.18, 0.18]),
        numeric_cols_right=(1, 2, 3),
    )

    bf_table_style: list[tuple] = []

    # Highlight rows that are in the bus factor cutoff.
    for i, row in enumerate(contributors, start=1):
        if row.get("in_bus_factor"):
            bf_table_style.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#ECFEFF")))
            bf_table_style.append(("TEXTCOLOR", (0, i), (-1, i), colors.HexColor("#0E7490")))

    if bf_table_style:
        bf_table.setStyle(TableStyle(bf_table_style))
    story.append(bf_table)

    # Author frequency
    _add_section(story, f"Top Authors (by commits, last {days} days)", h2_style=h2, new_page=True)
    top_authors = sorted(author_frequency.items(), key=lambda x: x[1], reverse=True)[:top_authors_limit]
    author_table_data = [["Author", "Commits"]] + [[a, str(c)] for a, c in top_authors]

    author_table = _styled_table(
        author_table_data,
        col_widths=_widths_from_fracs(page_width, [0.76, 0.24]),
        numeric_cols_right=(1,),
    )
    story.append(author_table)
    story.append(Spacer(1, 14))

    # Time distribution summary (small tables)
    _add_section(story, "Commit Volume (by day / week / month)", h2_style=h2, new_page=True)
    story.append(Paragraph("For compactness, this section shows the most recent buckets.", body))
    story.append(Spacer(1, 8))

    def tail_items(mapping: Mapping[str, int], n: int) -> List[List[str]]:
        keys = sorted(mapping.keys())
        keys = keys[-n:]
        return [[k, str(mapping[k])] for k in keys]

    thirds = _widths_from_fracs(page_width, [1, 1, 1])
    col_w = thirds[0]

    day_table = _styled_table(
        [["Day", "Commits"]] + tail_items(per_day, 14),
        col_widths=_widths_from_fracs(col_w, [0.70, 0.30]),
        numeric_cols_right=(1,),
    )
    week_table = _styled_table(
        [["Week", "Commits"]] + tail_items(per_week, 12),
        col_widths=_widths_from_fracs(col_w, [0.70, 0.30]),
        numeric_cols_right=(1,),
    )
    month_table = _styled_table(
        [["Month", "Commits"]] + tail_items(per_month, 12),
        col_widths=_widths_from_fracs(col_w, [0.70, 0.30]),
        numeric_cols_right=(1,),
    )

    buckets = Table([[day_table, week_table, month_table]], colWidths=thirds)
    buckets.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.append(KeepTogether([buckets]))

    doc.build(
        story,
        onFirstPage=lambda c, d: _draw_header_footer(canvas=c, doc=d, owner=owner, repo=repo, generated_at_utc=generated_at_utc),
        onLaterPages=lambda c, d: _draw_header_footer(canvas=c, doc=d, owner=owner, repo=repo, generated_at_utc=generated_at_utc),
    )

    _remove_header_only_pages(pdf_path=output_path, owner=owner, repo=repo)
