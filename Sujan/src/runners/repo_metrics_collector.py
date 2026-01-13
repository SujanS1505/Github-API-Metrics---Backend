from datetime import datetime

from api.commits import fetch_commit_details, fetch_recent_commits
from api.issues import fetch_all_issues
from api.security import fetch_dependabot_alerts
from metrics.code_quality_metrics import (
    calculate_code_churn,
    find_hotspot_files,
    find_stale_files,
    test_to_code_ratio,
)
from metrics.issue_backlog_metrics import (
    average_resolution_time_days,
    bug_vs_feature_ratio,
    issues_created_vs_closed_per_sprint,
    open_closed_ratio,
)
from metrics.security_metrics import (
    average_remediation_time,
    protected_branches_count,
    signed_commits_percentage,
)


def collect_repo_metrics(client, owner, repo):
    # -------- Issues --------
    # PDF mode should finish quickly even for huge repos.
    issues = fetch_all_issues(client, owner, repo, max_pages=10)

    issue_metrics = {
        "open_closed": open_closed_ratio(issues),
        "avg_resolution_days": average_resolution_time_days(issues),
        "bug_feature": bug_vs_feature_ratio(issues),
        "sprint_throughput": issues_created_vs_closed_per_sprint(issues),
    }

    # -------- Code Quality --------

    # Fetch recent commits (lightweight)
    commits = fetch_recent_commits(client, owner, repo, since_days=90)

    # Fetch commit details (files changed) + last-touched timestamps per file
    commit_details = []
    commit_dates = {}

    for commit in commits:
        sha = commit["sha"]
        detail = fetch_commit_details(client, owner, repo, sha)
        if not detail:
            continue

        commit_details.append(detail)

        try:
            commit_time = datetime.strptime(
                detail["commit"]["author"]["date"],
                "%Y-%m-%dT%H:%M:%SZ",
            )
        except Exception:
            continue

        for file in detail.get("files", []):
            commit_dates[file.get("filename")] = commit_time

    churn, commit_count = calculate_code_churn(commit_details)
    hotspots = find_hotspot_files(churn, commit_count)
    test_ratio = test_to_code_ratio(churn.keys())
    stale_files = find_stale_files(commit_dates)

    code_quality_metrics = {
        "code_churn": churn,
        "hotspots": hotspots,
        "test_to_code_ratio": test_ratio,
        "stale_files": stale_files,
    }

    # -------- Security --------
    alerts = fetch_dependabot_alerts(client, owner, repo)
    branches = client.get(f"/repos/{owner}/{repo}/branches")

    security_metrics = {
        "open_alerts": len(alerts),
        "avg_remediation_days": average_remediation_time(alerts),
        "signed_commits_pct": signed_commits_percentage(commits),
        "protected_branches": protected_branches_count(client, owner, repo, branches),
    }

    return {
        "issues": issue_metrics,
        "code_quality": code_quality_metrics,
        "security": security_metrics,
    }
