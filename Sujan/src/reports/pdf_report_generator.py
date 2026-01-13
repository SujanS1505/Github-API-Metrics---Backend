from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from datetime import datetime


def simple_table(rows):
    table = Table(rows, repeatRows=1)
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F3A5F")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
    ]))
    return table


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
        <b>Generated:</b> {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
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
