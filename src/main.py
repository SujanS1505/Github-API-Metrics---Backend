import argparse
from github_client import GitHubClient
from api.issues import fetch_all_issues
from metrics.issue_backlog_metrics import (
    issues_created_vs_closed_by_year,
    open_closed_ratio,
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


    print("\n📊 ISSUE ANALYTICS")

    ratio = open_closed_ratio(issues)
    print("Open issues:", ratio["open_issues"])
    print("Closed issues:", ratio["closed_issues"])
    print("Open/Closed ratio:", ratio["open_closed_ratio"])

    avg_time = average_resolution_time_days(issues)
    print("Avg resolution time (days):", avg_time)

    bug_feature = bug_vs_feature_ratio(issues)
    print("Bug issues:", bug_feature["bug_issues"])
    print("Feature issues:", bug_feature["feature_issues"])
    print("Bug/Feature ratio:", bug_feature["bug_feature_ratio"])



    sprint = issues_created_vs_closed_per_sprint(issues)
    print("\nIssues per sprint:")
    print("Created:")

    for k, v in sprint["created"].items():
        print(f"Sprint {k}: Created {v} issues")

    print("Closed:")

    for k, v in sprint["closed"].items():
        print(f"Sprint {k}: Closed {v} issues")



if __name__ == "__main__":
    main()
