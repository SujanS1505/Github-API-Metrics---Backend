from datetime import datetime, timezone

from api.issues import fetch_all_issues, fetch_issue_events
from metrics.issue_backlog_metrics import (
    open_closed_ratio,
    average_resolution_time_days,
    bug_vs_feature_ratio,
    issues_created_vs_closed_per_sprint
)
from reports.csv_writer import (
    ensure_dir,
    write_key_value_csv,
    write_time_series_csv
)


def run_issue_metrics(client, owner, repo, max_pages=None):
    # Fetch issues
    if max_pages is None:
        issues = fetch_all_issues(client, owner, repo)
    else:
        issues = fetch_all_issues(client, owner, repo, max_pages=max_pages)

    print(f"\nTotal issues fetched: {len(issues)}")

    if issues:
        print("\nSample issue:")
        for k, v in issues[0].items():
            print(f"{k}: {v}")
    else:
        print("No issues found in this repository.")

    print("\n📊 ISSUE ANALYTICS")

    # ---- Metrics ----
    ratio = open_closed_ratio(issues)
    avg_time = average_resolution_time_days(issues)
    bug_feature = bug_vs_feature_ratio(issues)
    sprint = issues_created_vs_closed_per_sprint(issues)

    # Reopen rate (sampled from most recent issues)
    recent_by_created = sorted(
        [i for i in issues if i.get("created_at")],
        key=lambda x: x["created_at"],
        reverse=True,
    )
    reopen_sample = recent_by_created[: min(30, len(recent_by_created))]

    reopen_rows = []
    reopened_issue_count = 0
    for issue in reopen_sample:
        number = issue.get("number")
        if not number:
            continue

        events = fetch_issue_events(client, owner, repo, number, max_pages=1)
        reopened_events = [e for e in events if e.get("event") == "reopened"]
        reopened_count = len(reopened_events)
        if reopened_count > 0:
            reopened_issue_count += 1

        last_reopened_at = reopened_events[-1].get("created_at", "") if reopened_events else ""
        reopen_rows.append([
            number,
            issue.get("state", ""),
            reopened_count,
            last_reopened_at or "",
            issue.get("created_at").strftime("%Y-%m-%d") if issue.get("created_at") else "",
            issue.get("closed_at").strftime("%Y-%m-%d") if issue.get("closed_at") else "",
            "; ".join(issue.get("labels", [])[:8]),
        ])

    reopen_rate = round((reopened_issue_count / len(reopen_rows)) * 100, 2) if reopen_rows else 0

    print("Open issues:", ratio["open_issues"])
    print("Closed issues:", ratio["closed_issues"])
    print("Open/Closed ratio:", ratio["open_closed_ratio"])
    print("Avg resolution time (days):", avg_time)
    print("Bug issues:", bug_feature["bug_issues"])
    print("Feature issues:", bug_feature["feature_issues"])
    print("Bug/Feature ratio:", bug_feature["bug_feature_ratio"])
    print("Issue reopen rate (%):", reopen_rate)

    print("\nIssues per sprint:")
    print("Created:")
    for k, v in sprint["created"].items():
        print(f"Sprint {k}: Created {v} issues")

    print("Closed:")
    for k, v in sprint["closed"].items():
        print(f"Sprint {k}: Closed {v} issues")

    # ---- CSV Generation ----
    REPORT_DIR = "reports"
    ensure_dir(REPORT_DIR)

    summary_metrics = {
        "open_issues": ratio["open_issues"],
        "closed_issues": ratio["closed_issues"],
        "open_closed_ratio": ratio["open_closed_ratio"],
        "avg_resolution_time_days": avg_time,
        "bug_issues": bug_feature["bug_issues"],
        "feature_issues": bug_feature["feature_issues"],
        "bug_feature_ratio": bug_feature["bug_feature_ratio"],
        "issue_reopen_rate_pct": reopen_rate,
        "issue_reopen_sample_size": len(reopen_rows),
    }

    write_key_value_csv(
        f"{REPORT_DIR}/issue_summary_metrics.csv",
        summary_metrics
    )

    sprint_rows = []
    for sprint_date in sorted(
        set(sprint["created"]) | set(sprint["closed"])
    ):
        sprint_rows.append([
            sprint_date,
            sprint["created"].get(sprint_date, 0),
            sprint["closed"].get(sprint_date, 0)
        ])

    write_time_series_csv(
        f"{REPORT_DIR}/issue_sprint_throughput.csv",
        sprint_rows,
        headers=["sprint_start_date", "issues_created", "issues_closed"]
    )

    # Detailed CSVs (20-30 rows each)
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    open_issues = [i for i in issues if i.get("state") == "open" and i.get("created_at")]
    open_issues_sorted = sorted(open_issues, key=lambda x: x["created_at"])  # oldest first
    open_rows = []
    for i in open_issues_sorted[:30]:
        age_days = (now - i["created_at"]).days
        open_rows.append([
            i.get("number"),
            i.get("title", "")[:120],
            i["created_at"].strftime("%Y-%m-%d"),
            age_days,
            i.get("comments", 0),
            i.get("author", ""),
            "; ".join(i.get("labels", [])[:8]),
        ])

    write_time_series_csv(
        f"{REPORT_DIR}/issues_open_sample.csv",
        open_rows,
        headers=["issue_number", "title", "created_at", "age_days", "comments", "author", "labels"],
    )

    closed_issues = [
        i for i in issues
        if i.get("state") == "closed" and i.get("created_at") and i.get("closed_at")
    ]
    closed_by_resolution = sorted(
        closed_issues,
        key=lambda x: (x["closed_at"] - x["created_at"]).days,
        reverse=True,
    )
    resolution_rows = []
    for i in closed_by_resolution[:30]:
        resolution_days = (i["closed_at"] - i["created_at"]).days
        resolution_rows.append([
            i.get("number"),
            i.get("title", "")[:120],
            i["created_at"].strftime("%Y-%m-%d"),
            i["closed_at"].strftime("%Y-%m-%d"),
            resolution_days,
            i.get("author", ""),
            "; ".join(i.get("labels", [])[:8]),
        ])

    write_time_series_csv(
        f"{REPORT_DIR}/issue_resolution_sample.csv",
        resolution_rows,
        headers=["issue_number", "title", "created_at", "closed_at", "resolution_days", "author", "labels"],
    )

    write_time_series_csv(
        f"{REPORT_DIR}/issue_reopen_sample.csv",
        reopen_rows,
        headers=[
            "issue_number",
            "state",
            "reopen_count",
            "last_reopened_at",
            "created_at",
            "closed_at",
            "labels",
        ],
    )

    print("\n✅ Issue CSV reports generated")
