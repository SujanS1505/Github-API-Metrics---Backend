from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Dict, List, Optional

from ...adapters.github.github_client import default_client


_PR_COUNT_QUERY = """
query ($q: String!) {
  search(query: $q, type: ISSUE, first: 1) {
    issueCount
  }
}
"""

_CLOSED_NOT_MERGED_QUERY = """
query ($q: String!, $cursor: String) {
  search(query: $q, type: ISSUE, first: 100, after: $cursor) {
    nodes {
      ... on PullRequest {
        number
        title
        url
        createdAt
        closedAt
        mergedAt
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


def pr_merged_vs_closed_summary(*, days: int = 90) -> Dict[str, object]:
    """PRs merged vs closed in the last N days.

    Closed includes both merged and unmerged PRs.

    Returns a dict suitable for CSV/PDF reporting.
    """

    client = default_client()
    since = (datetime.now(UTC) - timedelta(days=days)).date().isoformat()

    repo = f"repo:{client.owner}/{client.repo}"

    closed_q = f"{repo} is:pr is:closed closed:>={since}"
    merged_q = f"{repo} is:pr is:merged merged:>={since}"

    closed_payload = client.graphql(_PR_COUNT_QUERY, {"q": closed_q})
    merged_payload = client.graphql(_PR_COUNT_QUERY, {"q": merged_q})

    closed_count = int(closed_payload["data"]["search"]["issueCount"])
    merged_count = int(merged_payload["data"]["search"]["issueCount"])

    not_merged_count = max(0, closed_count - merged_count)

    merge_rate = (merged_count / closed_count) if closed_count else None

    return {
        "closed_prs": closed_count,
        "merged_prs": merged_count,
        "closed_not_merged_prs": not_merged_count,
        "merge_rate": merge_rate,
        "since_date": since,
        "days": days,
    }


def fetch_closed_not_merged_prs(*, days: int = 90, max_prs: int = 500) -> List[dict]:
    """Fetch recently closed PRs that were not merged in the last N days."""

    client = default_client()
    since = (datetime.now(UTC) - timedelta(days=days)).date().isoformat()
    repo = f"repo:{client.owner}/{client.repo}"

    # -is:merged is supported by GitHub search.
    query = f"{repo} is:pr is:closed -is:merged closed:>={since} sort:updated-desc"

    out: List[dict] = []
    cursor: Optional[str] = None

    while True:
        payload = client.graphql(
            _CLOSED_NOT_MERGED_QUERY,
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

            out.append(
                {
                    "number": pr.get("number"),
                    "title": pr.get("title") or "",
                    "url": pr.get("url") or "",
                    "author": (pr.get("author") or {}).get("login") or "",
                    "created_at": pr.get("createdAt") or "",
                    "closed_at": pr.get("closedAt") or "",
                    "merged_at": pr.get("mergedAt") or "",
                }
            )

            if len(out) >= max_prs:
                return out

        if not conn["pageInfo"]["hasNextPage"]:
            return out

        cursor = conn["pageInfo"]["endCursor"]
