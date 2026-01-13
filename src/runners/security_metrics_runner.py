from api.security import fetch_dependabot_alerts
from api.commits import fetch_recent_commits
from metrics.security_metrics import (
    open_security_alerts,
    average_remediation_time_days,
    signed_commits_percentage,
    protected_branches_count
)
from reports.csv_writer import ensure_dir, write_key_value_csv


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

    print("✅Security & compliance CSV generated")
