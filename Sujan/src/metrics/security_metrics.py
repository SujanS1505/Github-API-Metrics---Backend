from datetime import datetime, timedelta


def open_security_alerts(alerts):
    return len(alerts)


def average_remediation_time_days(alerts):
    durations = []

    for alert in alerts:
        if alert.get("fixed_at"):
            created = datetime.strptime(alert["created_at"], "%Y-%m-%dT%H:%M:%SZ")
            fixed = datetime.strptime(alert["fixed_at"], "%Y-%m-%dT%H:%M:%SZ")
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
            created_dt = datetime.strptime(created, "%Y-%m-%dT%H:%M:%SZ")
            fixed_dt = datetime.strptime(fixed, "%Y-%m-%dT%H:%M:%SZ")
            durations.append((fixed_dt - created_dt).days)

    if not durations:
        return None

    return round(sum(durations) / len(durations), 2)
