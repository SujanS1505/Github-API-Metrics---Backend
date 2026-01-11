import argparse
from github_client import GitHubClient
from api.issues import fetch_all_issues
from metrics.issue_backlog_metrics import (
    open_vs_closed_ratio,
    average_resolution_time_days,
    bug_vs_feature_ratio,
    issues_created_vs_closed_per_sprint
)



def main():
    parser = argparse.ArgumentParser(description="GitHub Metrics Backend")
    parser.add_argument(
        "--repo",
        required=True,
        help="Repository in owner/repo format (e.g. apache/spark)"
    )
    args = parser.parse_args()

    owner, repo = args.repo.split("/")
    client = GitHubClient()

    # Verify repository
    repo_data = client.get(f"/repos/{owner}/{repo}")
    print("Repository:", repo_data["full_name"])
    print("Stars:", repo_data["stargazers_count"])

    # Rate limit check
    rate = client.get("/rate_limit")
    print("Remaining requests:", rate["rate"]["remaining"])

    # Fetch issues
    issues = fetch_all_issues(client, owner, repo)

    print(f"\nTotal issues fetched: {len(issues)}")

    if issues:
        print("\nSample issue:")
        for k, v in issues[0].items():
            print(f"{k}: {v}")
    else:
        print("No issues found in this repository.")


    ratio = open_vs_closed_ratio(issues)
    avg_resolution = average_resolution_time_days(issues)
    bug_feature = bug_vs_feature_ratio(issues)
    throughput = issues_created_vs_closed_per_sprint(issues)

    print("\n--- Issue & Backlog Metrics ---")
    print("Open vs Closed Ratio:", ratio)
    print("Average Resolution Time (days):", avg_resolution)
    print("Bug vs Feature Ratio:", bug_feature)

    print("\nIssues Created vs Closed per Sprint (sample):")
    for sprint, data in list(throughput.items())[:3]:
        print(sprint, data)


if __name__ == "__main__":
    main()
