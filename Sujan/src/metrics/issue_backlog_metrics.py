from collections import Counter
from datetime import datetime, timedelta


def open_closed_ratio(issues):
    open_issues = sum(1 for i in issues if i.get("state") == "open")
    closed_issues = sum(1 for i in issues if i.get("state") == "closed")

    total = open_issues + closed_issues
    ratio = round(open_issues / total, 2) if total else 0

    return {
        "open_issues": open_issues,
        "closed_issues": closed_issues,
        "open_closed_ratio": ratio,
    }


def average_resolution_time_days(issues):
    durations = []

    for issue in issues:
        if issue.get("state") == "closed" and issue.get("closed_at") and issue.get("created_at"):
            delta = issue["closed_at"] - issue["created_at"]
            durations.append(delta.total_seconds() / 86400)

    if not durations:
        return 0

    return round(sum(durations) / len(durations), 2)


def bug_vs_feature_ratio(issues):
    bug = 0
    feature = 0

    bug_tokens = ("bug", "kind:bug", "type:bug")
    feature_tokens = (
        "feature",
        "enhancement",
        "kind:feature",
        "type:feature",
        "type:enhancement",
    )

    for issue in issues:
        labels = [str(l).lower() for l in issue.get("labels", [])]

        is_bug = any(any(tok in label for tok in bug_tokens) for label in labels)
        is_feature = any(any(tok in label for tok in feature_tokens) for label in labels)

        if is_bug:
            bug += 1
        elif is_feature:
            feature += 1

    ratio = round(bug / feature, 2) if feature else None

    return {
        "bug_issues": bug,
        "feature_issues": feature,
        "bug_feature_ratio": ratio,
    }


def issues_created_vs_closed_per_sprint(issues, sprint_start_date=None, sprint_days=14):
    """Counts issues created/closed per sprint window.

    Sprints are fixed-size buckets of `sprint_days` starting from `sprint_start_date`.
    If sprint_start_date is None, uses the earliest created_at in the provided issues.
    """

    if not issues:
        return {"created": {}, "closed": {}}

    if sprint_start_date is None:
        valid_dates = [i.get("created_at") for i in issues if i.get("created_at")]
        if not valid_dates:
            return {"created": {}, "closed": {}}
        sprint_start_date = min(valid_dates)

    created = Counter()
    closed = Counter()

    for issue in issues:
        created_at = issue.get("created_at")
        if not created_at:
            continue

        days_since_start = (created_at - sprint_start_date).days
        sprint_index = days_since_start // sprint_days
        sprint_start = sprint_start_date + timedelta(days=sprint_index * sprint_days)
        created[sprint_start.date()] += 1

        closed_at = issue.get("closed_at")
        if closed_at:
            days_since_start_closed = (closed_at - sprint_start_date).days
            sprint_index_closed = days_since_start_closed // sprint_days
            sprint_start_closed = sprint_start_date + timedelta(days=sprint_index_closed * sprint_days)
            closed[sprint_start_closed.date()] += 1

    return {"created": dict(created), "closed": dict(closed)}
