from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import DefaultDict, Dict, Iterable, List, Optional, Tuple

from ...adapters.github.github_client import default_client
from ..time_utils import parse_github_datetime

SEARCH_MERGED_PRS_QUERY = """
query ($q: String!, $cursor: String) {
    search(query: $q, type: ISSUE, first: 100, after: $cursor) {
        nodes {
            ... on PullRequest {
                number
                title
                url
                createdAt
                mergedAt
                baseRefName
                headRefName
                author { login }
            }
        }
        pageInfo {
            hasNextPage
            endCursor
        }
    }
}
"""


def fetch_merged_pull_requests(
    *,
    days: int = 90,
    max_prs: int = 2000,
) -> List[dict]:
    """Fetch merged PRs for the last N days.

    Uses GraphQL search with a merged date filter.
    """

    client = default_client()
    since = datetime.now(UTC) - timedelta(days=days)
    since_date = since.date().isoformat()
    query = f"repo:{client.owner}/{client.repo} is:pr is:merged merged:>={since_date} sort:updated-desc"

    prs: List[dict] = []
    cursor: Optional[str] = None

    while True:
        payload = client.graphql(
            SEARCH_MERGED_PRS_QUERY,
            {
                "q": query,
                "cursor": cursor,
            },
        )

        conn = payload["data"]["search"]
        nodes = conn.get("nodes") or []

        for pr in nodes:
            if not pr:
                continue

            merged_at_raw = pr.get("mergedAt")
            if not merged_at_raw:
                continue

            created_at_raw = pr.get("createdAt")
            if not created_at_raw:
                continue

            merged_at = parse_github_datetime(merged_at_raw)
            if merged_at < since:
                continue

            prs.append(
                {
                    "number": pr.get("number"),
                    "title": pr.get("title") or "",
                    "url": pr.get("url") or "",
                    "created_at": created_at_raw,
                    "merged_at": merged_at_raw,
                    "author": (pr.get("author") or {}).get("login") or "",
                    "base": pr.get("baseRefName") or "",
                    "head": pr.get("headRefName") or "",
                }
            )

            if len(prs) >= max_prs:
                break

        if len(prs) >= max_prs:
            break

        if not conn["pageInfo"]["hasNextPage"]:
            break

        cursor = conn["pageInfo"]["endCursor"]

    return prs


def merges_per_day_week_month(
    merged_prs: Iterable[dict],
) -> Tuple[DefaultDict[str, int], DefaultDict[str, int], DefaultDict[str, int]]:
    per_day: DefaultDict[str, int] = defaultdict(int)
    per_week: DefaultDict[str, int] = defaultdict(int)
    per_month: DefaultDict[str, int] = defaultdict(int)

    for pr in merged_prs:
        d = parse_github_datetime(pr["merged_at"])
        per_day[d.strftime("%Y-%m-%d")] += 1
        per_week[f"{d.year}-W{d.isocalendar()[1]}"] += 1
        per_month[d.strftime("%Y-%m")] += 1

    return per_day, per_week, per_month


def average_time_between_merges_hours(merged_prs: Iterable[dict]) -> Optional[float]:
    times: List[datetime] = []
    for pr in merged_prs:
        times.append(parse_github_datetime(pr["merged_at"]))

    if len(times) < 2:
        return None

    times.sort()
    total_diff_seconds = 0.0
    for i in range(1, len(times)):
        total_diff_seconds += (times[i] - times[i - 1]).total_seconds()

    return (total_diff_seconds / (len(times) - 1)) / 3600.0


def merge_frequency_summary(*, merged_prs: List[dict], days: int) -> Dict[str, object]:
    total = len(merged_prs)
    per_day = total / days if days else 0.0
    per_week = total / (days / 7) if days else 0.0

    return {
        "merged_prs": total,
        "merges_per_day": per_day,
        "merges_per_week": per_week,
        "avg_time_between_merges_hours": average_time_between_merges_hours(merged_prs),
    }
