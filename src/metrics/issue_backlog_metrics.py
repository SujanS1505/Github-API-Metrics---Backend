from datetime import timedelta
from collections import defaultdict


def open_vs_closed_ratio(issues):
    open_count = sum(1 for i in issues if i["state"] == "open")
    closed_count = sum(1 for i in issues if i["state"] == "closed")

    total = open_count + closed_count
    if total == 0:
        return 0.0

    return round(open_count / total, 2)


def average_resolution_time_days(issues):
    durations = []

    for issue in issues:
        if issue["state"] == "closed" and issue["created_at"] and issue["closed_at"]:
            durations.append(issue["closed_at"] - issue["created_at"])

    if not durations:
        return None

    avg_duration = sum(durations, timedelta()) / len(durations)
    return round(avg_duration.total_seconds() / 86400, 2)


def bug_vs_feature_ratio(issues):
    bug = 0
    feature = 0

    for issue in issues:
        labels = [l.lower() for l in issue["labels"]]

        if any("bug" in l for l in labels):
            bug += 1
        elif any(k in l for k in ["feature", "enhancement"] for l in labels):
            feature += 1

    if feature == 0:
        return None

    return round(bug / feature, 2)


def issues_created_vs_closed_per_sprint(issues, sprint_days=14):
    """
    Groups issues by sprint window and counts created vs closed
    """
    buckets = defaultdict(lambda: {"created": 0, "closed": 0})

    for issue in issues:
        created_bucket = issue["created_at"].date() - timedelta(
            days=issue["created_at"].date().toordinal() % sprint_days
        )
        buckets[created_bucket]["created"] += 1

        if issue["closed_at"]:
            closed_bucket = issue["closed_at"].date() - timedelta(
                days=issue["closed_at"].date().toordinal() % sprint_days
            )
            buckets[closed_bucket]["closed"] += 1

    return buckets
