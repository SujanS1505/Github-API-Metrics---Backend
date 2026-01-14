from api.repo_metadata import fetch_repo_metadata
from reports.pdf_report_generator import generate_repo_pdf_from_csv
from runners.code_quality_runner import run_code_quality_metrics
from runners.issue_metrics_runner import run_issue_metrics
from runners.security_metrics_runner import run_security_metrics


def run_pdf_report(client, owner, repo):
    repo_meta = fetch_repo_metadata(client, owner, repo)

    # Generate/refresh CSVs first (PDF reads these for full detail).
    # Keep issue fetch bounded for huge repos while still producing useful trends.
    run_issue_metrics(client, owner, repo, max_pages=20)
    run_code_quality_metrics(client, owner, repo)
    run_security_metrics(client, owner, repo)

    output_pdf = f"reports/{owner}_{repo}_metrics_report.pdf"
    generate_repo_pdf_from_csv(repo_meta, report_dir="reports", output_pdf=output_pdf, top_n=100)

    print(f"\n📄 Repo-specific PDF generated: {output_pdf}")
