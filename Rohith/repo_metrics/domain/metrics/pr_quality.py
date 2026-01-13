from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from statistics import mean, median
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from ...adapters.github.github_client import GitHubClient, default_client
from ..time_utils import parse_github_datetime


_PR_SEARCH_QUERY = """
query ($q: String!, $cursor: String) {
  search(query: $q, type: ISSUE, first: 50, after: $cursor) {
    nodes {
      ... on PullRequest {
        number
        title
        url
        state
        isDraft
        createdAt
        updatedAt
        closedAt
        mergedAt
        additions
        deletions
        changedFiles
        author { login }
        comments { totalCount }
        reviewThreads { totalCount }
        reviews(first: 50) {
          totalCount
          nodes {
            author { login }
            state
            submittedAt
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
class PullRequestQualityRow:
    number: int
    url: str
    title: str
    author: str
    is_draft: bool
    created_at: str
    ready_for_review_at: str
    merged_at: str
    closed_at: str
    additions: int
    deletions: int
    loc_changed: int
    changed_files: int
    reviewers_count: int
    approvals_count: int
    first_review_at: str
    review_turnaround_hours: Optional[float]
    issue_comments: int
    review_threads: int
    total_comments: int


def _repo_qualifier(client: GitHubClient) -> str:
    return f"repo:{client.owner}/{client.repo}"


def _safe_int(v: Any) -> int:
    try:
        return int(v)
    except Exception:
        return 0


def _hours_between(start_iso: str, end_iso: str) -> Optional[float]:
    if not start_iso or not end_iso:
        return None
    try:
        start = parse_github_datetime(start_iso)
        end = parse_github_datetime(end_iso)
        delta = end - start
        return delta.total_seconds() / 3600.0
    except Exception:
        return None


def _distinct_reviewers(reviews: Sequence[Mapping[str, Any]], *, pr_author: str) -> Tuple[int, int, str, Optional[float]]:
    reviewers: set[str] = set()
    approvals_by_reviewer: set[str] = set()
    first_review_at: Optional[str] = None

    for r in reviews:
        author = str(((r.get("author") or {}) or {}).get("login") or "")
        if not author or author == pr_author:
            continue

        submitted_at = str(r.get("submittedAt") or "")
        state = str(r.get("state") or "")

        reviewers.add(author)
        if state == "APPROVED":
            approvals_by_reviewer.add(author)

        if submitted_at:
            if first_review_at is None or submitted_at < first_review_at:
                first_review_at = submitted_at

    return len(reviewers), len(approvals_by_reviewer), first_review_at or "", None


def pr_quality_summary(*, days: int = 90, max_prs: int = 500) -> Dict[str, object]:
    """Compute PR quality metrics for PRs created in the last N days."""

    client = default_client()
    since_dt = datetime.now(UTC) - timedelta(days=days)
    since_date = since_dt.date().isoformat()

    q = f"{_repo_qualifier(client)} is:pr created:>={since_date} sort:created-desc"

    cursor: Optional[str] = None
    rows: List[PullRequestQualityRow] = []
    scanned = 0

    while True:
        payload = client.graphql(_PR_SEARCH_QUERY, {"q": q, "cursor": cursor})
        conn = payload["data"]["search"]
        nodes: Sequence[Optional[Mapping[str, Any]]] = conn.get("nodes") or []

        for pr in nodes:
            if not pr:
                continue

            scanned += 1
            if scanned > max_prs:
                break

            author = str(((pr.get("author") or {}) or {}).get("login") or "")
            is_draft = bool(pr.get("isDraft"))

            created_at = str(pr.get("createdAt") or "")
            ready_at = created_at
            merged_at = str(pr.get("mergedAt") or "")
            closed_at = str(pr.get("closedAt") or "")

            additions = _safe_int(pr.get("additions"))
            deletions = _safe_int(pr.get("deletions"))
            loc_changed = additions + deletions
            changed_files = _safe_int(pr.get("changedFiles"))

            issue_comments = _safe_int(((pr.get("comments") or {}) or {}).get("totalCount"))
            review_threads = _safe_int(((pr.get("reviewThreads") or {}) or {}).get("totalCount"))
            total_comments = issue_comments + review_threads

            reviews_conn = (pr.get("reviews") or {}) or {}
            reviews_nodes: Sequence[Optional[Mapping[str, Any]]] = reviews_conn.get("nodes") or []
            reviews: List[Mapping[str, Any]] = [r for r in reviews_nodes if r]

            reviewers_count, approvals_count, first_review_at, _ = _distinct_reviewers(reviews, pr_author=author)
            turnaround_hours = _hours_between(ready_at, first_review_at) if first_review_at else None

            rows.append(
                PullRequestQualityRow(
                    number=_safe_int(pr.get("number")),
                    url=str(pr.get("url") or ""),
                    title=str(pr.get("title") or ""),
                    author=author,
                    is_draft=is_draft,
                    created_at=created_at,
                    ready_for_review_at=ready_at,
                    merged_at=merged_at,
                    closed_at=closed_at,
                    additions=additions,
                    deletions=deletions,
                    loc_changed=loc_changed,
                    changed_files=changed_files,
                    reviewers_count=reviewers_count,
                    approvals_count=approvals_count,
                    first_review_at=first_review_at,
                    review_turnaround_hours=turnaround_hours,
                    issue_comments=issue_comments,
                    review_threads=review_threads,
                    total_comments=total_comments,
                )
            )

        if scanned > max_prs:
            break

        if not conn["pageInfo"]["hasNextPage"]:
            break

        cursor = conn["pageInfo"]["endCursor"]

    non_draft = [r for r in rows if not r.is_draft]

    turnaround_vals = [r.review_turnaround_hours for r in non_draft if isinstance(r.review_turnaround_hours, (int, float))]
    reviewers_vals = [r.reviewers_count for r in non_draft]
    loc_vals = [r.loc_changed for r in non_draft]
    comments_vals = [r.total_comments for r in non_draft]

    merged_non_draft = [r for r in non_draft if r.merged_at]
    merged_with_approval = [r for r in merged_non_draft if r.approvals_count >= 1]

    approval_rate = (len(merged_with_approval) / len(merged_non_draft)) if merged_non_draft else None

    def _safe_mean(vals: Sequence[float]) -> Optional[float]:
        try:
            return float(mean(vals)) if vals else None
        except Exception:
            return None

    def _safe_median(vals: Sequence[float]) -> Optional[float]:
        try:
            return float(median(vals)) if vals else None
        except Exception:
            return None

    largest_by_loc = sorted(non_draft, key=lambda r: r.loc_changed, reverse=True)
    slowest_turnaround = sorted(
        [r for r in non_draft if isinstance(r.review_turnaround_hours, (int, float))],
        key=lambda r: float(r.review_turnaround_hours or 0.0),
        reverse=True,
    )

    return {
        "days": days,
        "since_date": since_date,
        "prs_scanned": scanned,
        "prs_count": len(rows),
        "non_draft_prs_count": len(non_draft),
        "review_turnaround_avg_hours": _safe_mean([float(v) for v in turnaround_vals]),
        "review_turnaround_median_hours": _safe_median([float(v) for v in turnaround_vals]),
        "avg_reviewers_per_pr": _safe_mean([float(v) for v in reviewers_vals]),
        "median_reviewers_per_pr": _safe_median([float(v) for v in reviewers_vals]),
        "avg_pr_loc_changed": _safe_mean([float(v) for v in loc_vals]),
        "median_pr_loc_changed": _safe_median([float(v) for v in loc_vals]),
        "avg_pr_total_comments": _safe_mean([float(v) for v in comments_vals]),
        "median_pr_total_comments": _safe_median([float(v) for v in comments_vals]),
        "approval_rate": approval_rate,
        "merged_prs_count": len(merged_non_draft),
        "merged_prs_with_approval": len(merged_with_approval),
        "details": rows,
        "largest_prs": largest_by_loc[:25],
        "slowest_review_turnaround": slowest_turnaround[:25],
    }
