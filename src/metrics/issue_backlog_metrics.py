from datetime import datetime, timedelta
from collections import Counter


def open_closed_ratio(issues):
    open_issues = sum(1 for i in issues if i["state"] == "open")
    closed_issues = sum(1 for i in issues if i["state"] == "closed")

    total = open_issues + closed_issues
    ratio = round(open_issues / total, 2) if total else 0

    return {
        "open_issues": open_issues,
        "closed_issues": closed_issues,
        "open_closed_ratio": ratio
    }


def average_resolution_time_days(issues):
    durations = []

    for issue in issues:
        if issue["state"] == "closed" and issue["closed_at"]:
            delta = issue["closed_at"] - issue["created_at"]
            durations.append(delta.total_seconds() / 86400)

    if not durations:
        return 0

    return round(sum(durations) / len(durations), 2)


def bug_vs_feature_ratio(issues):
    bug = 0
    feature = 0

    for issue in issues:
        labels = [l.lower() for l in issue["labels"]]
        if "bug" in labels:
            bug += 1
        elif "feature" in labels or "enhancement" in labels:
            feature += 1

    ratio = round(bug / feature, 2) if feature else None

    return {
        "bug_issues": bug,
        "feature_issues": feature,
        "bug_feature_ratio": ratio
    }


def issues_created_vs_closed_by_year(issues):
    created = Counter()
    closed = Counter()

    for issue in issues:
        created[issue["created_at"].year] += 1
        if issue["closed_at"]:
            closed[issue["closed_at"].year] += 1

    return {
        "created": dict(created),
        "closed": dict(closed)
    }


def issues_created_vs_closed_per_sprint(
    issues,
    sprint_start_date=None,
    sprint_days=14
):
    """
    Calculates number of issues created and closed per sprint.
    """

    if sprint_start_date is None:
        sprint_start_date = min(i["created_at"] for i in issues if i["created_at"])

    created = Counter()
    closed = Counter()

    for issue in issues:
        # CREATED
        days_since_start = (issue["created_at"] - sprint_start_date).days
        sprint_index = days_since_start // sprint_days
        sprint_start = sprint_start_date + timedelta(days=sprint_index * sprint_days)
        created[sprint_start.date()] += 1

        # CLOSED
        if issue["closed_at"]:
            days_since_start_closed = (issue["closed_at"] - sprint_start_date).days
            sprint_index_closed = days_since_start_closed // sprint_days
            sprint_start_closed = sprint_start_date + timedelta(
                days=sprint_index_closed * sprint_days
            )
            closed[sprint_start_closed.date()] += 1

    return {
        "created": dict(created),
        "closed": dict(closed)
    }