from api.security import fetch_dependabot_alerts
from api.commits import fetch_recent_commits
from metrics.security_metrics import (
    open_security_alerts,
    average_remediation_time_days,
    signed_commits_percentage,
    protected_branches_count,
    protected_branches_status,
)
from reports.csv_writer import ensure_dir, write_key_value_csv
from reports.csv_writer import write_time_series_csv


def run_security_metrics(client, owner, repo):
    print("\n SECURITY & COMPLIANCE METRICS")

    # Dependabot alerts
    alerts = fetch_dependabot_alerts(client, owner, repo)
    open_alerts = open_security_alerts(alerts)
    avg_fix_time = average_remediation_time_days(alerts)

    print("Open security alerts:", open_alerts)
    print("Avg remediation time (days):", avg_fix_time)

    # Signed commits
    commits = fetch_recent_commits(client, owner, repo, since_days=90)
    signed_pct = signed_commits_percentage(commits)

    print("Signed commits (%):", signed_pct)

    # Protected branches
    branches = client.get(f"/repos/{owner}/{repo}/branches")
    protected_count = protected_branches_count(client, owner, repo, branches)
    branch_status = protected_branches_status(client, owner, repo, branches, max_branches=30)

    print("Protected branches:", protected_count)


    # CSV
    ensure_dir("reports")

    write_key_value_csv(
        "reports/security_compliance_metrics.csv",
        {
            "open_security_alerts": open_alerts,
            "avg_remediation_time_days": avg_fix_time,
            "signed_commits_percentage": signed_pct,
            "protected_branches": protected_count
        }
    )

    # Detailed CSVs for PDF
    # Dependabot alert details (up to 30)
    alert_rows = []
    for a in (alerts or [])[:30]:
        pkg = (
            a.get("security_vulnerability", {})
            .get("package", {})
            .get("name")
        ) or (
            a.get("dependency", {})
            .get("package", {})
            .get("name")
        ) or ""
        severity = (
            a.get("security_advisory", {})
            .get("severity")
        ) or ""
        alert_rows.append([
            a.get("number", ""),
            severity,
            pkg,
            a.get("created_at", ""),
            a.get("fixed_at", ""),
            a.get("state", ""),
        ])

    write_time_series_csv(
        "reports/security_alerts_sample.csv",
        alert_rows,
        headers=["alert_number", "severity", "package", "created_at", "fixed_at", "state"],
    )

    # Signed commit sample (up to 30)
    commit_rows = []
    for c in (commits or [])[:30]:
        commit_rows.append([
            c.get("sha", "")[:10],
            c.get("commit", {}).get("author", {}).get("date", ""),
            c.get("commit", {}).get("author", {}).get("name", ""),
            bool(c.get("commit", {}).get("verification", {}).get("verified")),
        ])

    write_time_series_csv(
        "reports/signed_commits_sample.csv",
        commit_rows,
        headers=["sha", "date", "author", "verified"],
    )

    # Branch protection sample (up to 30)
    branch_rows = [[r["branch"], r["protected"]] for r in branch_status]
    write_time_series_csv(
        "reports/branch_protection_sample.csv",
        branch_rows,
        headers=["branch", "protected"],
    )

    print("✅Security & compliance CSV generated")
