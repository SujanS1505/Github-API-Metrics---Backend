from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Mapping, Optional, Sequence

from ...adapters.github.github_client import GitHubClient, default_client
from ..time_utils import parse_github_datetime


_PR_COUNT_QUERY = """
query ($q: String!) {
  search(query: $q, type: ISSUE, first: 1) {
    issueCount
  }
}
"""

_REOPEN_SCAN_QUERY = """
query ($q: String!, $cursor: String) {
  search(query: $q, type: ISSUE, first: 50, after: $cursor) {
    nodes {
      ... on PullRequest {
        number
        title
        url
        state
        updatedAt
        closedAt
        author { login }
        timelineItems(itemTypes: REOPENED_EVENT, first: 50) {
          nodes {
            ... on ReopenedEvent {
              createdAt
            }
          }
        }
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
"""


@dataclass(frozen=True)
class ReopenedPullRequest:
    number: int
    title: str
    url: str
    author: str
    reopened_at: str
    updated_at: str
    closed_at: str


def _repo_qualifier(client: GitHubClient) -> str:
    return f"repo:{client.owner}/{client.repo}"


def _count_closed_prs(*, client: GitHubClient, since_date: str) -> int:
    q = f"{_repo_qualifier(client)} is:pr is:closed closed:>={since_date}"
    payload = client.graphql(_PR_COUNT_QUERY, {"q": q})
    return int(payload["data"]["search"]["issueCount"])


def _to_reopened_pr(pr: Mapping[str, Any], *, reopened_at: str) -> ReopenedPullRequest:
    return ReopenedPullRequest(
        number=int(pr.get("number") or 0),
        title=str(pr.get("title") or ""),
        url=str(pr.get("url") or ""),
        author=str(((pr.get("author") or {}) or {}).get("login") or ""),
        reopened_at=reopened_at,
        updated_at=str(pr.get("updatedAt") or ""),
        closed_at=str(pr.get("closedAt") or ""),
    )


def pr_reopen_rate_summary(
    *,
    days: int = 90,
    max_prs_scanned: int = 500,
    max_reopened_prs: int = 500,
) -> Dict[str, object]:
    """Reopen rate of PRs in the last N days.

    Definition:
    - "Reopened PR" means a PR that has at least one `ReopenedEvent` with
      `createdAt` within the window.

    Implementation notes:
    - GitHub search does not expose a first-class `reopened:` qualifier, so we:
      1) search for PRs updated in the window
      2) inspect timeline `REOPENED_EVENT`s and filter by the window.

    Because we scan a bounded number of PRs (`max_prs_scanned`), this is best
    treated as an estimate when repositories have very high PR churn.
    """

    client = default_client()
    since_dt = datetime.now(UTC) - timedelta(days=days)
    since_date = since_dt.date().isoformat()

    closed_prs = _count_closed_prs(client=client, since_date=since_date)

    # Search candidates by updates; reopen implies update, so this is a good superset.
    q = f"{_repo_qualifier(client)} is:pr updated:>={since_date} sort:updated-desc"

    cursor: Optional[str] = None
    scanned = 0
    reopen_events = 0
    reopened_prs: List[ReopenedPullRequest] = []

    while True:
        payload = client.graphql(_REOPEN_SCAN_QUERY, {"q": q, "cursor": cursor})
        conn = payload["data"]["search"]
        nodes: Sequence[Optional[Mapping[str, Any]]] = conn.get("nodes") or []

        for pr in nodes:
            if not pr:
                continue

            scanned += 1
            timeline = (pr.get("timelineItems") or {}).get("nodes") or []

            in_window: List[str] = []
            for ev in timeline:
                if not ev:
                    continue
                created_at = str(ev.get("createdAt") or "")
                if not created_at:
                    continue
                try:
                    if parse_github_datetime(created_at) >= since_dt:
                        in_window.append(created_at)
                except Exception:
                    continue

            if in_window:
                reopen_events += len(in_window)
                most_recent = max(in_window)
                reopened_prs.append(_to_reopened_pr(pr, reopened_at=most_recent))

                if len(reopened_prs) >= max_reopened_prs:
                    break

            if scanned >= max_prs_scanned:
                break

        if len(reopened_prs) >= max_reopened_prs or scanned >= max_prs_scanned:
            break

        if not conn["pageInfo"]["hasNextPage"]:
            break

        cursor = conn["pageInfo"]["endCursor"]

    reopened_count = len(reopened_prs)
    reopen_rate = (reopened_count / closed_prs) if closed_prs else None

    reopened_prs.sort(key=lambda r: r.reopened_at, reverse=True)

    return {
        "days": days,
        "since_date": since_date,
        "closed_prs": closed_prs,
        "prs_scanned": scanned,
        "reopened_prs": reopened_count,
        "reopen_events": reopen_events,
        "reopen_rate": reopen_rate,
        "reopened_prs_details": reopened_prs,
    }
