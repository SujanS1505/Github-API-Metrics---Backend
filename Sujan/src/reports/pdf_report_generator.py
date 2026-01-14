from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from datetime import datetime, timezone

from reports.csv_reader import read_csv_as_dicts, read_key_value_csv


def simple_table(rows, *, col_widths=None, font_size=9, header_font_size=9):
    table = Table(rows, repeatRows=1, colWidths=col_widths)
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F3A5F")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 1), (-1, -1), font_size),
        ("FONTSIZE", (0, 0), (-1, 0), header_font_size),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return table


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
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(output_pdf, pagesize=A4)
    elements = []

    # -------- Header --------
    elements.append(Paragraph("GitHub Repository Metrics Report", styles["Title"]))
    elements.append(Spacer(1, 10))

    elements.append(Paragraph(
        f"""
        <b>Repository:</b> {repo_meta['full_name']}<br/>
        <b>Stars:</b> {repo_meta['stars']}<br/>
        <b>Generated:</b> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}
        """,
        styles["Normal"]
    ))
    elements.append(Spacer(1, 20))

    # -------- Issue Metrics --------
    elements.append(Paragraph("Issue & Backlog Metrics", styles["Heading2"]))
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
    elements.append(Paragraph("Code Quality & Maintenance", styles["Heading2"]))
    cq_rows = [
        ["Metric", "Value"],
        ["Test-to-Code Ratio", metrics["code_quality"]["test_to_code_ratio"]],
        ["Hotspot Files", len(metrics["code_quality"]["hotspots"])],
        ["Stale Files", len(metrics["code_quality"]["stale_files"])],
    ]
    elements.append(simple_table(cq_rows))
    elements.append(Spacer(1, 20))

    # -------- Security --------
    elements.append(Paragraph("Security & Compliance", styles["Heading2"]))
    sec_rows = [
        ["Metric", "Value"],
        ["Open Dependabot Alerts", metrics["security"]["open_alerts"]],
        ["Avg Remediation Time (days)", metrics["security"]["avg_remediation_days"]],
        ["Signed Commits (%)", metrics["security"]["signed_commits_pct"]],
        ["Protected Branches", metrics["security"]["protected_branches"]],
    ]
    elements.append(simple_table(sec_rows))

    doc.build(elements)


def _add_header(elements, styles, repo_meta):
    elements.append(Paragraph("GitHub Repository Metrics Report", styles["Title"]))
    elements.append(Spacer(1, 10))
    elements.append(
        Paragraph(
            f"""
            <b>Repository:</b> {repo_meta['full_name']}<br/>
            <b>Stars:</b> {repo_meta['stars']}<br/>
            <b>Generated:</b> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}
            """,
            styles["Normal"],
        )
    )
    elements.append(Spacer(1, 16))


def _add_issues_section(elements, styles, report_dir, sprint_max_rows=100):
    issue_summary_path = f"{report_dir}/issue_summary_metrics.csv"
    issue_summary = read_key_value_csv(issue_summary_path)

    elements.append(Paragraph("Issue & Backlog Metrics", styles["Heading2"]))
    elements.append(simple_table(_key_value_rows(issue_summary)))
    elements.append(Spacer(1, 10))

    # Metric metadata (definitions + calculation notes)
    elements.append(Paragraph("Metric metadata", styles["Heading3"]))
    elements.append(Paragraph(
        "Open vs Closed Issues Ratio (Backlog health): open / (open + closed)",
        styles["BodyText"],
    ))
    elements.append(Paragraph(
        "Average Issue Resolution Time (Delivery efficiency): average days from created_at to closed_at for closed issues.",
        styles["BodyText"],
    ))
    elements.append(Paragraph(
        "Issue Reopen Rate (Requirement clarity): % of sampled recent issues with at least one 'reopened' event (Issues Events API).",
        styles["BodyText"],
    ))
    elements.append(Paragraph(
        "Bug vs Feature Ratio (Product stability): bug-labeled issues / feature-labeled issues (supports labels like 'kind:bug').",
        styles["BodyText"],
    ))
    elements.append(Paragraph(
        "Issues Created vs Closed per Sprint (Throughput consistency): counts grouped by 14-day sprints starting at earliest created_at in the fetched set.",
        styles["BodyText"],
    ))

    open_issues = _to_number(issue_summary.get("open_issues")) or 0
    closed_issues = _to_number(issue_summary.get("closed_issues")) or 0
    total_issues = open_issues + closed_issues
    elements.append(
        Paragraph(
            f"<b>Total Issues (open + closed):</b> {total_issues}",
            styles["Normal"],
        )
    )

    # Detailed: Open issues sample (20-30 rows)
    open_sample_path = f"{report_dir}/issues_open_sample.csv"
    open_rows = read_csv_as_dicts(open_sample_path)
    if open_rows:
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("Open Issues (Oldest sample)", styles["Heading3"]))
        table_rows = [["#", "Title", "Created", "Age (days)", "Comments", "Author"]]
        for r in open_rows[:30]:
            table_rows.append([
                r.get("issue_number", ""),
                Paragraph(str(r.get("title", "")), styles["BodyText"]),
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
        elements.append(Paragraph("Issue Resolution Time (Longest sample)", styles["Heading3"]))
        table_rows = [["#", "Title", "Created", "Closed", "Resolution (days)"]]
        for r in resolution_rows[:30]:
            table_rows.append([
                r.get("issue_number", ""),
                Paragraph(str(r.get("title", "")), styles["BodyText"]),
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
        elements.append(Paragraph("Issue Reopen Rate (Recent sample)", styles["Heading3"]))
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
    elements.append(Paragraph("Issue Throughput by Sprint", styles["Heading3"]))

    created_total = sum((_to_number(r.get("issues_created")) or 0) for r in throughput_rows)
    closed_total = sum((_to_number(r.get("issues_closed")) or 0) for r in throughput_rows)
    elements.append(
        Paragraph(
            f"<b>Total Created:</b> {created_total} &nbsp;&nbsp; <b>Total Closed:</b> {closed_total}",
            styles["Normal"],
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
            styles["Normal"],
        )
    )


def _add_code_quality_section(elements, styles, report_dir, top_n):
    cq_summary_path = f"{report_dir}/code_quality_summary.csv"
    cq_summary = read_key_value_csv(cq_summary_path)
    elements.append(Paragraph("Code Quality & Maintenance", styles["Heading2"]))
    elements.append(simple_table(_key_value_rows(cq_summary)))
    elements.append(Spacer(1, 12))

    churn_path = f"{report_dir}/code_churn_by_file.csv"
    churn_rows = read_csv_as_dicts(churn_path)
    if churn_rows:
        churn_values = [(_to_number(r.get("code_churn")) or 0) for r in churn_rows]
        total_churn = sum(churn_values)
        avg_churn = round(total_churn / len(churn_values), 2) if churn_values else 0
        elements.append(Paragraph("Code Churn", styles["Heading3"]))
        elements.append(
            Paragraph(
                f"<b>Total churn:</b> {total_churn} &nbsp;&nbsp; <b>Avg churn/file:</b> {avg_churn}",
                styles["Normal"],
            )
        )

        top_churn = _top_n(churn_rows, "code_churn", n=top_n)
        churn_table = [["File", "Churn", "Commits"]]
        for r in top_churn:
            churn_table.append([
                Paragraph(str(r.get("file_path", "")), styles["BodyText"]),
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
                styles["Normal"],
            )
        )

    hotspots_path = f"{report_dir}/hotspot_files.csv"
    hotspot_rows = read_csv_as_dicts(hotspots_path)
    elements.append(Spacer(1, 14))
    elements.append(Paragraph("Hotspot Files", styles["Heading3"]))
    if hotspot_rows:
        top_hotspots = _top_n(hotspot_rows, "code_churn", n=top_n)
        hs_table = [["File", "Churn", "Commits"]]
        for r in top_hotspots:
            hs_table.append([
                Paragraph(str(r.get("file_path", "")), styles["BodyText"]),
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
        elements.append(Paragraph("No hotspot files found (per current thresholds).", styles["Normal"]))

    # Stale files details (20-30 rows)
    stale_path = f"{report_dir}/stale_files.csv"
    stale_rows = read_csv_as_dicts(stale_path)
    if stale_rows:
        elements.append(Spacer(1, 14))
        elements.append(Paragraph("Stale Files (No recent commits)", styles["Heading3"]))
        table_rows = [["File", "Last Commit"]]
        for r in stale_rows[:30]:
            table_rows.append([
                Paragraph(str(r.get("file_path", "")), styles["BodyText"]),
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
    elements.append(Paragraph("Security & Compliance", styles["Heading2"]))
    elements.append(simple_table(_key_value_rows(sec_summary)))
    if _to_number(sec_summary.get("open_security_alerts")) == 0:
        elements.append(Spacer(1, 8))
        elements.append(
            Paragraph(
                "Note: Dependabot Alerts may be inaccessible for some repos/tokens; in that case the CSV will show 0 alerts.",
                styles["Normal"],
            )
        )

    # Metric metadata
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("Metric metadata", styles["Heading3"]))
    elements.append(Paragraph(
        "Open security alerts (Dependabot): count of open alerts returned by the Dependabot Alerts API.",
        styles["BodyText"],
    ))
    elements.append(Paragraph(
        "Time to remediate vulnerabilities: average days between created_at and fixed_at for fixed alerts (if available).",
        styles["BodyText"],
    ))
    elements.append(Paragraph(
        "Signed commits percentage: % of recent commits whose verification.verified == true.",
        styles["BodyText"],
    ))
    elements.append(Paragraph(
        "Protected branches count: number of branches where the branch protection endpoint returns data.",
        styles["BodyText"],
    ))

    # Detailed: Dependabot alerts sample (20-30 rows)
    alerts_path = f"{report_dir}/security_alerts_sample.csv"
    alert_rows = read_csv_as_dicts(alerts_path)
    if alert_rows:
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("Dependabot Alerts (Sample)", styles["Heading3"]))
        table_rows = [["#", "Severity", "Package", "Created", "Fixed", "State"]]
        for r in alert_rows[:30]:
            table_rows.append([
                r.get("alert_number", ""),
                r.get("severity", ""),
                Paragraph(str(r.get("package", "")), styles["BodyText"]),
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
        elements.append(Paragraph("Signed Commits (Sample)", styles["Heading3"]))
        table_rows = [["SHA", "Date", "Author", "Verified"]]
        for r in signed_rows[:30]:
            table_rows.append([
                r.get("sha", ""),
                r.get("date", ""),
                Paragraph(str(r.get("author", "")), styles["BodyText"]),
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
        elements.append(Paragraph("Branch Protection (Sample)", styles["Heading3"]))
        table_rows = [["Branch", "Protected"]]
        for r in bp_rows[:30]:
            table_rows.append([
                Paragraph(str(r.get("branch", "")), styles["BodyText"]),
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
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(output_pdf, pagesize=A4)
    elements = []

    _add_header(elements, styles, repo_meta)
    _add_issues_section(elements, styles, report_dir, sprint_max_rows=100)

    elements.append(PageBreak())
    _add_code_quality_section(elements, styles, report_dir, top_n=top_n)

    elements.append(PageBreak())
    _add_security_section(elements, styles, report_dir)

    doc.build(elements)
