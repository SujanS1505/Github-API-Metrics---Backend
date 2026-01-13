from reports.pdf_report_generator import generate_pdf_report


def run_pdf_report():
    csv_files = {
        "Issue Summary Metrics": "reports/issue_summary_metrics.csv",
        "Issue Sprint Throughput": "reports/issue_sprint_throughput.csv",
        "Code Quality Metrics": "reports/code_quality_summary.csv",
        "Security & Compliance Metrics": "reports/security_compliance_metrics.csv",
    }

    output_pdf = "reports/github_metrics_report.pdf"
    generate_pdf_report(csv_files, output_pdf)

    print(f"\n📄 PDF report generated: {output_pdf}")
