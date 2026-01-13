import argparse
from github_client import GitHubClient
from runners.issue_metrics_runner import run_issue_metrics
from runners.code_quality_runner import run_code_quality_metrics
from runners.security_metrics_runner import run_security_metrics


def main():
    parser = argparse.ArgumentParser(description="GitHub Metrics Backend")
    parser.add_argument(
        "--repo",
        required=True,
        help="Repository in owner/repo format (e.g. apache/airflow)"
    )
    parser.add_argument(
        "--mode",
        required=True,
        choices=["issues", "code-quality","security", "all", "pdf"],
        help="Which metrics to run"
    )


    args = parser.parse_args()
    owner, repo = args.repo.split("/")

    client = GitHubClient()

    # Repo verification
    repo_data = client.get(f"/repos/{owner}/{repo}")
    print("Repository:", repo_data["full_name"])
    print("Stars:", repo_data["stargazers_count"])

    rate = client.get("/rate_limit")
    print("Remaining requests:", rate["rate"]["remaining"])

    if args.mode in ("issues", "all"):
        run_issue_metrics(client, owner, repo)

    if args.mode in ("code-quality", "all"):
        run_code_quality_metrics(client, owner, repo)

    if args.mode in ("security", "all"):
        run_security_metrics(client, owner, repo)

    if args.mode == "pdf":
        from runners.pdf_report_runner import run_pdf_report
        run_pdf_report()



if __name__ == "__main__":
    main()