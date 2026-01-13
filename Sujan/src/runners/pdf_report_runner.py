from api.repo_metadata import fetch_repo_metadata
from runners.repo_metrics_collector import collect_repo_metrics
from reports.pdf_report_generator import generate_repo_pdf


def run_pdf_report(client, owner, repo):
    repo_meta = fetch_repo_metadata(client, owner, repo)
    metrics = collect_repo_metrics(client, owner, repo)

    output_pdf = f"reports/{owner}_{repo}_metrics_report.pdf"
    generate_repo_pdf(repo_meta, metrics, output_pdf)

    print(f"\n📄 Repo-specific PDF generated: {output_pdf}")
