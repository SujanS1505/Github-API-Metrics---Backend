from datetime import datetime, timedelta

GITHUB_DATETIME_FMT = "%Y-%m-%dT%H:%M:%SZ"


def open_security_alerts(alerts):
    return len(alerts)


def average_remediation_time_days(alerts):
    durations = []

    for alert in alerts:
        if alert.get("fixed_at"):
            created = datetime.strptime(alert["created_at"], GITHUB_DATETIME_FMT)
            fixed = datetime.strptime(alert["fixed_at"], GITHUB_DATETIME_FMT)
            durations.append((fixed - created).total_seconds() / 86400)

    if not durations:
        return None

    return round(sum(durations) / len(durations), 2)


def signed_commits_percentage(commits):
    signed = 0
    total = len(commits)

    for c in commits:
        if c.get("commit", {}).get("verification", {}).get("verified"):
            signed += 1

    if total == 0:
        return 0

    return round((signed / total) * 100, 2)


def protected_branches_count(client, owner, repo, branches):
    protected = 0

    for b in branches:
        name = b["name"]
        try:
            protection = client.get(
                f"/repos/{owner}/{repo}/branches/{name}/protection"
            )
            if protection:
                protected += 1
        except Exception:
            continue

    return protected


def protected_branches_status(client, owner, repo, branches, max_branches=30):
    """Return a list of {branch, protected} for PDF details."""
    rows = []
    if not branches:
        return rows

    for b in branches[:max_branches]:
        name = b.get("name")
        if not name:
            continue

        protected = False
        try:
            protection = client.get(
                f"/repos/{owner}/{repo}/branches/{name}/protection"
            )
            protected = bool(protection)
        except Exception:
            protected = False

        rows.append({"branch": name, "protected": protected})

    return rows


from datetime import datetime


def average_remediation_time(alerts):
    """
    Calculate average remediation time (in days) for fixed Dependabot alerts.
    Returns None if no fixed alerts exist.
    """
    durations = []

    for alert in alerts:
        created = alert.get("created_at")
        fixed = alert.get("fixed_at")

        if created and fixed:
            created_dt = datetime.strptime(created, GITHUB_DATETIME_FMT)
            fixed_dt = datetime.strptime(fixed, GITHUB_DATETIME_FMT)
            durations.append((fixed_dt - created_dt).days)

    if not durations:
        return None

    return round(sum(durations) / len(durations), 2)
