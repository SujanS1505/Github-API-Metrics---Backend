from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER
from datetime import datetime, timezone

from reports.csv_reader import read_csv_as_dicts, read_key_value_csv


BRAND_BLUE = colors.HexColor("#1F3A5F")
LIGHT_ROW = colors.HexColor("#F5F7FB")
TEXT_GREY = colors.HexColor("#4B5563")


def simple_table(rows, *, col_widths=None, font_size=9, header_font_size=9):
    table = Table(rows, repeatRows=1, colWidths=col_widths)
    style_cmds = [
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 1), (-1, -1), font_size),
        ("FONTSIZE", (0, 0), (-1, 0), header_font_size),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]

    # Alternate row background for readability
    for r in range(1, len(rows)):
        if r % 2 == 0:
            style_cmds.append(("BACKGROUND", (0, r), (-1, r), LIGHT_ROW))

    table.setStyle(TableStyle(style_cmds))
    return table


def _build_styles():
    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            name="CoverTitle",
            parent=styles["Title"],
            fontSize=26,
            leading=30,
            alignment=TA_CENTER,
            textColor=BRAND_BLUE,
        )
    )

    styles.add(
        ParagraphStyle(
            name="CoverSubtitle",
            parent=styles["BodyText"],
            fontSize=11,
            leading=14,
            alignment=TA_CENTER,
            textColor=TEXT_GREY,
        )
    )

    styles.add(
        ParagraphStyle(
            name="SectionHeading",
            parent=styles["Heading2"],
            textColor=BRAND_BLUE,
            spaceBefore=10,
            spaceAfter=6,
        )
    )

    styles.add(
        ParagraphStyle(
            name="SubHeading",
            parent=styles["Heading3"],
            textColor=BRAND_BLUE,
            spaceBefore=8,
            spaceAfter=4,
        )
    )

    styles.add(
        ParagraphStyle(
            name="BodySmall",
            parent=styles["BodyText"],
            fontSize=9,
            leading=11,
            textColor=TEXT_GREY,
        )
    )

    return styles


def _cover_kpi_table(issue_summary, cq_summary, sec_summary):
    def v(d, k, default="N/A"):
        val = d.get(k)
        return str(val) if val not in (None, "") else default

    rows = [
        ["KPI", "Value", "KPI", "Value"],
        ["Open issues", v(issue_summary, "open_issues"), "Closed issues", v(issue_summary, "closed_issues")],
        ["Open/closed ratio", v(issue_summary, "open_closed_ratio"), "Avg resolution (days)", v(issue_summary, "avg_resolution_time_days")],
        ["Bug/feature ratio", v(issue_summary, "bug_feature_ratio"), "Reopen rate (%)", v(issue_summary, "issue_reopen_rate_pct")],
        ["Files analyzed", v(cq_summary, "files_analyzed"), "Test-to-code ratio", v(cq_summary, "test_to_code_ratio")],
        ["Hotspot files", v(cq_summary, "hotspot_files"), "Stale files", v(cq_summary, "stale_files")],
        ["Open security alerts", v(sec_summary, "open_security_alerts"), "Signed commits (%)", v(sec_summary, "signed_commits_percentage")],
        ["Protected branches", v(sec_summary, "protected_branches"), "Avg remediation (days)", v(sec_summary, "avg_remediation_time_days")],
    ]

    return simple_table(rows, col_widths=[155, 90, 155, 90], font_size=8, header_font_size=9)


def _add_cover_page(elements, styles, repo_meta, report_dir):
    issue_summary = read_key_value_csv(f"{report_dir}/issue_summary_metrics.csv")
    cq_summary = read_key_value_csv(f"{report_dir}/code_quality_summary.csv")
    sec_summary = read_key_value_csv(f"{report_dir}/security_compliance_metrics.csv")

    elements.append(Spacer(1, 0.6 * inch))
    elements.append(Paragraph("GitHub Repository Metrics Report", styles["CoverTitle"]))
    elements.append(Spacer(1, 0.15 * inch))
    elements.append(Paragraph(repo_meta["full_name"], styles["CoverSubtitle"]))
    elements.append(Paragraph(f"Stars: {repo_meta['stars']}", styles["CoverSubtitle"]))
    elements.append(Paragraph(
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        styles["CoverSubtitle"],
    ))
    elements.append(Spacer(1, 0.35 * inch))

    elements.append(Paragraph("KPI Summary", styles["SectionHeading"]))
    elements.append(_cover_kpi_table(issue_summary, cq_summary, sec_summary))

    elements.append(Spacer(1, 0.25 * inch))
    elements.append(Paragraph(
        "Collection notes: issues are fetched with a page cap in PDF mode; commits are sampled from the last ~90 days; hotspot/stale detection uses the thresholds in code.",
        styles["BodySmall"],
    ))


def _pretty_metric_name(key: str) -> str:
    return (
        key.replace("_", " ")
        .replace("pct", "%")
        .strip()
        .title()
    )


def _to_number(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return value

    s = str(value).strip()
    if s == "":
        return None

    try:
        if "." in s:
            return float(s)
        return int(s)
    except ValueError:
        try:
            return float(s)
        except ValueError:
            return None


def _key_value_rows(metrics: dict):
    rows = [["Metric", "Value"]]
    for key, value in metrics.items():
        display_value = value
        if display_value in (None, ""):
            display_value = "N/A"
        rows.append([_pretty_metric_name(key), str(display_value)])
    return rows


def _top_n(rows, key, n=25):
    def sort_key(r):
        return _to_number(r.get(key)) or 0

    return sorted(rows, key=sort_key, reverse=True)[:n]


def generate_repo_pdf(repo_meta, metrics, output_pdf):
    styles = _build_styles()
    doc = SimpleDocTemplate(
        output_pdf,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=54,
        bottomMargin=42,
        title=repo_meta.get("full_name", "GitHub Repository Metrics"),
    )
    elements = []

    # -------- Header --------
    elements.append(Paragraph("GitHub Repository Metrics Report", styles["CoverTitle"]))
    elements.append(Spacer(1, 10))

    elements.append(Paragraph(
        f"""
        <b>Repository:</b> {repo_meta['full_name']}<br/>
        <b>Stars:</b> {repo_meta['stars']}<br/>
        <b>Generated:</b> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}
        """,
        styles["BodySmall"]
    ))
    elements.append(Spacer(1, 20))

    # -------- Issue Metrics --------
    elements.append(Paragraph("Issue & Backlog Metrics", styles["SectionHeading"]))
    issue_rows = [
        ["Metric", "Value"],
        ["Open Issues", metrics["issues"]["open_closed"]["open_issues"]],
        ["Closed Issues", metrics["issues"]["open_closed"]["closed_issues"]],
        ["Avg Resolution Time (days)", metrics["issues"]["avg_resolution_days"]],
        ["Bug / Feature Ratio", metrics["issues"]["bug_feature"]["bug_feature_ratio"]],
    ]
    elements.append(simple_table(issue_rows))
    elements.append(Spacer(1, 20))

    # -------- Code Quality --------
    elements.append(Paragraph("Code Quality & Maintenance", styles["SectionHeading"]))
    cq_rows = [
        ["Metric", "Value"],
        ["Test-to-Code Ratio", metrics["code_quality"]["test_to_code_ratio"]],
        ["Hotspot Files", len(metrics["code_quality"]["hotspots"])],
        ["Stale Files", len(metrics["code_quality"]["stale_files"])],
    ]
    elements.append(simple_table(cq_rows))
    elements.append(Spacer(1, 20))

    # -------- Security --------
    elements.append(Paragraph("Security & Compliance", styles["SectionHeading"]))
    sec_rows = [
        ["Metric", "Value"],
        ["Open Dependabot Alerts", metrics["security"]["open_alerts"]],
        ["Avg Remediation Time (days)", metrics["security"]["avg_remediation_days"]],
        ["Signed Commits (%)", metrics["security"]["signed_commits_pct"]],
        ["Protected Branches", metrics["security"]["protected_branches"]],
    ]
    elements.append(simple_table(sec_rows))

    def _draw_header_footer(canvas, doc_):
        canvas.saveState()
        width, height = A4

        header_y = height - 0.5 * inch
        canvas.setFont("Helvetica-Bold", 9)
        canvas.setFillColor(BRAND_BLUE)
        canvas.drawString(doc_.leftMargin, header_y, "GitHub Metrics")
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(TEXT_GREY)
        canvas.drawRightString(width - doc_.rightMargin, header_y, repo_meta.get("full_name", ""))
        canvas.setStrokeColor(colors.HexColor("#CBD5E1"))
        canvas.setLineWidth(0.6)
        canvas.line(doc_.leftMargin, header_y - 6, width - doc_.rightMargin, header_y - 6)

        footer_y = 0.35 * inch
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(TEXT_GREY)
        canvas.drawString(doc_.leftMargin, footer_y, f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d')} UTC")
        canvas.drawRightString(width - doc_.rightMargin, footer_y, f"Page {canvas.getPageNumber()}")
        canvas.restoreState()

    doc.build(elements, onFirstPage=_draw_header_footer, onLaterPages=_draw_header_footer)


def _add_header(elements, styles, repo_meta):
    elements.append(Paragraph("Repository Overview", styles["SectionHeading"]))
    elements.append(
        Paragraph(
            f"""
            <b>Repository:</b> {repo_meta['full_name']}<br/>
            <b>Stars:</b> {repo_meta['stars']}<br/>
            <b>Generated:</b> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}
            """,
            styles["BodySmall"],
        )
    )
    elements.append(Spacer(1, 16))


def _add_issues_section(elements, styles, report_dir, sprint_max_rows=100):
    issue_summary_path = f"{report_dir}/issue_summary_metrics.csv"
    issue_summary = read_key_value_csv(issue_summary_path)

    elements.append(Paragraph("Issue & Backlog Metrics", styles["SectionHeading"]))
    elements.append(simple_table(_key_value_rows(issue_summary)))
    elements.append(Spacer(1, 10))

    # Metric metadata (definitions + calculation notes)
    elements.append(Paragraph("Metric metadata", styles["SubHeading"]))
    elements.append(Paragraph(
        "Open vs Closed Issues Ratio (Backlog health): open / (open + closed)",
        styles["BodySmall"],
    ))
    elements.append(Paragraph(
        "Average Issue Resolution Time (Delivery efficiency): average days from created_at to closed_at for closed issues.",
        styles["BodySmall"],
    ))
    elements.append(Paragraph(
        "Issue Reopen Rate (Requirement clarity): % of sampled recent issues with at least one 'reopened' event (Issues Events API).",
        styles["BodySmall"],
    ))
    elements.append(Paragraph(
        "Bug vs Feature Ratio (Product stability): bug-labeled issues / feature-labeled issues (supports labels like 'kind:bug').",
        styles["BodySmall"],
    ))
    elements.append(Paragraph(
        "Issues Created vs Closed per Sprint (Throughput consistency): counts grouped by 14-day sprints starting at earliest created_at in the fetched set.",
        styles["BodySmall"],
    ))

    open_issues = _to_number(issue_summary.get("open_issues")) or 0
    closed_issues = _to_number(issue_summary.get("closed_issues")) or 0
    total_issues = open_issues + closed_issues
    elements.append(
        Paragraph(
            f"<b>Total Issues (open + closed):</b> {total_issues}",
            styles["BodySmall"],
        )
    )

    # Detailed: Open issues sample (20-30 rows)
    open_sample_path = f"{report_dir}/issues_open_sample.csv"
    open_rows = read_csv_as_dicts(open_sample_path)
    if open_rows:
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("Open Issues (Oldest sample)", styles["SubHeading"]))
        table_rows = [["#", "Title", "Created", "Age (days)", "Comments", "Author"]]
        for r in open_rows[:30]:
            table_rows.append([
                r.get("issue_number", ""),
                Paragraph(str(r.get("title", "")), styles["BodySmall"]),
                r.get("created_at", ""),
                r.get("age_days", ""),
                r.get("comments", ""),
                r.get("author", ""),
            ])
        elements.append(simple_table(
            table_rows,
            col_widths=[35, 260, 60, 55, 45, 65],
            font_size=7,
            header_font_size=8,
        ))

    # Detailed: Resolution time sample (20-30 rows)
    resolution_path = f"{report_dir}/issue_resolution_sample.csv"
    resolution_rows = read_csv_as_dicts(resolution_path)
    if resolution_rows:
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("Issue Resolution Time (Longest sample)", styles["SubHeading"]))
        table_rows = [["#", "Title", "Created", "Closed", "Resolution (days)"]]
        for r in resolution_rows[:30]:
            table_rows.append([
                r.get("issue_number", ""),
                Paragraph(str(r.get("title", "")), styles["BodySmall"]),
                r.get("created_at", ""),
                r.get("closed_at", ""),
                r.get("resolution_days", ""),
            ])
        elements.append(simple_table(
            table_rows,
            col_widths=[35, 300, 60, 60, 65],
            font_size=7,
            header_font_size=8,
        ))

    # Detailed: Reopen rate sample (20-30 rows)
    reopen_path = f"{report_dir}/issue_reopen_sample.csv"
    reopen_rows = read_csv_as_dicts(reopen_path)
    if reopen_rows:
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("Issue Reopen Rate (Recent sample)", styles["SubHeading"]))
        table_rows = [["#", "State", "Reopens", "Last Reopened"]]
        for r in reopen_rows[:30]:
            table_rows.append([
                r.get("issue_number", ""),
                r.get("state", ""),
                r.get("reopen_count", ""),
                r.get("last_reopened_at", ""),
            ])
        elements.append(simple_table(
            table_rows,
            col_widths=[60, 70, 55, 250],
            font_size=8,
            header_font_size=9,
        ))

    throughput_path = f"{report_dir}/issue_sprint_throughput.csv"
    throughput_rows = read_csv_as_dicts(throughput_path)
    if not throughput_rows:
        return

    elements.append(Spacer(1, 12))
    elements.append(Paragraph("Issue Throughput by Sprint", styles["SubHeading"]))

    created_total = sum((_to_number(r.get("issues_created")) or 0) for r in throughput_rows)
    closed_total = sum((_to_number(r.get("issues_closed")) or 0) for r in throughput_rows)
    elements.append(
        Paragraph(
            f"<b>Total Created:</b> {created_total} &nbsp;&nbsp; <b>Total Closed:</b> {closed_total}",
            styles["BodySmall"],
        )
    )

    recent = throughput_rows[-min(len(throughput_rows), sprint_max_rows):]
    table_rows = [["Sprint Start", "Created", "Closed"]]
    for r in recent:
        table_rows.append(
            [
                r.get("sprint_start_date", ""),
                str(r.get("issues_created", "")),
                str(r.get("issues_closed", "")),
            ]
        )
    elements.append(
        simple_table(
            table_rows,
            col_widths=[140, 90, 90],
            font_size=8,
            header_font_size=9,
        )
    )
    elements.append(
        Paragraph(
            f"Showing last {len(recent)} sprints. Full history is in {throughput_path}.",
            styles["BodySmall"],
        )
    )


def _add_code_quality_section(elements, styles, report_dir, top_n):
    cq_summary_path = f"{report_dir}/code_quality_summary.csv"
    cq_summary = read_key_value_csv(cq_summary_path)
    elements.append(Paragraph("Code Quality & Maintenance", styles["SectionHeading"]))
    elements.append(simple_table(_key_value_rows(cq_summary)))
    elements.append(Spacer(1, 12))

    churn_path = f"{report_dir}/code_churn_by_file.csv"
    churn_rows = read_csv_as_dicts(churn_path)
    if churn_rows:
        churn_values = [(_to_number(r.get("code_churn")) or 0) for r in churn_rows]
        total_churn = sum(churn_values)
        avg_churn = round(total_churn / len(churn_values), 2) if churn_values else 0
        elements.append(Paragraph("Code Churn", styles["SubHeading"]))
        elements.append(
            Paragraph(
                f"<b>Total churn:</b> {total_churn} &nbsp;&nbsp; <b>Avg churn/file:</b> {avg_churn}",
                styles["BodySmall"],
            )
        )

        top_churn = _top_n(churn_rows, "code_churn", n=top_n)
        churn_table = [["File", "Churn", "Commits"]]
        for r in top_churn:
            churn_table.append([
                Paragraph(str(r.get("file_path", "")), styles["BodySmall"]),
                str(r.get("code_churn", "")),
                str(r.get("commit_count", "")),
            ])
        elements.append(simple_table(
            churn_table,
            col_widths=[340, 55, 55],
            font_size=7,
            header_font_size=8,
        ))
        elements.append(
            Paragraph(
                f"Top {len(top_churn)} files by churn. Full listing is in {churn_path}.",
                styles["BodySmall"],
            )
        )

    hotspots_path = f"{report_dir}/hotspot_files.csv"
    hotspot_rows = read_csv_as_dicts(hotspots_path)
    elements.append(Spacer(1, 14))
    elements.append(Paragraph("Hotspot Files", styles["SubHeading"]))
    if hotspot_rows:
        top_hotspots = _top_n(hotspot_rows, "code_churn", n=top_n)
        hs_table = [["File", "Churn", "Commits"]]
        for r in top_hotspots:
            hs_table.append([
                Paragraph(str(r.get("file_path", "")), styles["BodySmall"]),
                str(r.get("code_churn", "")),
                str(r.get("commit_count", "")),
            ])
        elements.append(simple_table(
            hs_table,
            col_widths=[340, 55, 55],
            font_size=7,
            header_font_size=8,
        ))
    else:
        elements.append(Paragraph("No hotspot files found (per current thresholds).", styles["BodySmall"]))

    # Stale files details (20-30 rows)
    stale_path = f"{report_dir}/stale_files.csv"
    stale_rows = read_csv_as_dicts(stale_path)
    if stale_rows:
        elements.append(Spacer(1, 14))
        elements.append(Paragraph("Stale Files (No recent commits)", styles["SubHeading"]))
        table_rows = [["File", "Last Commit"]]
        for r in stale_rows[:30]:
            table_rows.append([
                Paragraph(str(r.get("file_path", "")), styles["BodySmall"]),
                r.get("last_commit_date", ""),
            ])
        elements.append(simple_table(
            table_rows,
            col_widths=[420, 90],
            font_size=7,
            header_font_size=8,
        ))


def _add_security_section(elements, styles, report_dir):
    sec_summary_path = f"{report_dir}/security_compliance_metrics.csv"
    sec_summary = read_key_value_csv(sec_summary_path)
    elements.append(Paragraph("Security & Compliance", styles["SectionHeading"]))
    elements.append(simple_table(_key_value_rows(sec_summary)))
    if _to_number(sec_summary.get("open_security_alerts")) == 0:
        elements.append(Spacer(1, 8))
        elements.append(
            Paragraph(
                "Note: Dependabot Alerts may be inaccessible for some repos/tokens; in that case the CSV will show 0 alerts.",
                styles["BodySmall"],
            )
        )

    # Metric metadata
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("Metric metadata", styles["SubHeading"]))
    elements.append(Paragraph(
        "Open security alerts (Dependabot): count of open alerts returned by the Dependabot Alerts API.",
        styles["BodySmall"],
    ))
    elements.append(Paragraph(
        "Time to remediate vulnerabilities: average days between created_at and fixed_at for fixed alerts (if available).",
        styles["BodySmall"],
    ))
    elements.append(Paragraph(
        "Signed commits percentage: % of recent commits whose verification.verified == true.",
        styles["BodySmall"],
    ))
    elements.append(Paragraph(
        "Protected branches count: number of branches where the branch protection endpoint returns data.",
        styles["BodySmall"],
    ))

    # Detailed: Dependabot alerts sample (20-30 rows)
    alerts_path = f"{report_dir}/security_alerts_sample.csv"
    alert_rows = read_csv_as_dicts(alerts_path)
    if alert_rows:
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("Dependabot Alerts (Sample)", styles["SubHeading"]))
        table_rows = [["#", "Severity", "Package", "Created", "Fixed", "State"]]
        for r in alert_rows[:30]:
            table_rows.append([
                r.get("alert_number", ""),
                r.get("severity", ""),
                Paragraph(str(r.get("package", "")), styles["BodySmall"]),
                r.get("created_at", ""),
                r.get("fixed_at", ""),
                r.get("state", ""),
            ])
        elements.append(simple_table(
            table_rows,
            col_widths=[40, 55, 190, 80, 80, 55],
            font_size=7,
            header_font_size=8,
        ))

    # Detailed: Signed commits sample (20-30 rows)
    signed_path = f"{report_dir}/signed_commits_sample.csv"
    signed_rows = read_csv_as_dicts(signed_path)
    if signed_rows:
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("Signed Commits (Sample)", styles["SubHeading"]))
        table_rows = [["SHA", "Date", "Author", "Verified"]]
        for r in signed_rows[:30]:
            table_rows.append([
                r.get("sha", ""),
                r.get("date", ""),
                Paragraph(str(r.get("author", "")), styles["BodySmall"]),
                r.get("verified", ""),
            ])
        elements.append(simple_table(
            table_rows,
            col_widths=[60, 170, 220, 60],
            font_size=7,
            header_font_size=8,
        ))

    # Detailed: Branch protection sample (20-30 rows)
    bp_path = f"{report_dir}/branch_protection_sample.csv"
    bp_rows = read_csv_as_dicts(bp_path)
    if bp_rows:
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("Branch Protection (Sample)", styles["SubHeading"]))
        table_rows = [["Branch", "Protected"]]
        for r in bp_rows[:30]:
            table_rows.append([
                Paragraph(str(r.get("branch", "")), styles["BodySmall"]),
                r.get("protected", ""),
            ])
        elements.append(simple_table(
            table_rows,
            col_widths=[420, 90],
            font_size=7,
            header_font_size=8,
        ))


def generate_repo_pdf_from_csv(repo_meta, report_dir, output_pdf, top_n=25):
    """Generate a PDF from the CSV reports produced by the runners."""
    styles = _build_styles()
    doc = SimpleDocTemplate(
        output_pdf,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=54,
        bottomMargin=42,
        title=repo_meta.get("full_name", "GitHub Repository Metrics"),
    )
    elements = []

    _add_cover_page(elements, styles, repo_meta, report_dir)
    elements.append(PageBreak())

    _add_header(elements, styles, repo_meta)
    _add_issues_section(elements, styles, report_dir, sprint_max_rows=100)

    elements.append(PageBreak())
    _add_code_quality_section(elements, styles, report_dir, top_n=top_n)

    elements.append(PageBreak())
    _add_security_section(elements, styles, report_dir)

    def _draw_header_footer(canvas, doc_):
        canvas.saveState()
        width, height = A4

        header_y = height - 0.5 * inch
        canvas.setFont("Helvetica-Bold", 9)
        canvas.setFillColor(BRAND_BLUE)
        canvas.drawString(doc_.leftMargin, header_y, "GitHub Metrics")
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(TEXT_GREY)
        canvas.drawRightString(width - doc_.rightMargin, header_y, repo_meta.get("full_name", ""))
        canvas.setStrokeColor(colors.HexColor("#CBD5E1"))
        canvas.setLineWidth(0.6)
        canvas.line(doc_.leftMargin, header_y - 6, width - doc_.rightMargin, header_y - 6)

        footer_y = 0.35 * inch
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(TEXT_GREY)
        canvas.drawString(doc_.leftMargin, footer_y, f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d')} UTC")
        canvas.drawRightString(width - doc_.rightMargin, footer_y, f"Page {canvas.getPageNumber()}")
        canvas.restoreState()

    doc.build(elements, onFirstPage=_draw_header_footer, onLaterPages=_draw_header_footer)
