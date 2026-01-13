from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from ...adapters.github.github_client import default_client


def calculate_bus_factor(
    *,
    days: int = 90,
    threshold_percent: float = 50,
    per_page: int = 100,
) -> Tuple[Optional[int], Optional[float]]:
    print(f"[INFO] Calculating bus factor (approx.) for last {days} days")

    client = default_client()
    author_commits: Dict[str, int] = defaultdict(int)
    page = 1
    since = (datetime.utcnow() - timedelta(days=days)).isoformat() + "Z"

    while True:
        commits = client.rest_get(
            f"/repos/{client.owner}/{client.repo}/commits",
            params={"per_page": per_page, "page": page, "since": since},
        )
        if not commits:
            print("[INFO] No more commits returned by API")
            break

        for commit in commits:
            if commit.get("author"):
                author = commit["author"]["login"]
            else:
                author = commit["commit"]["author"]["email"]
            author_commits[author] += 1

        print(f"[INFO] Page {page} processed | Unique contributors so far: {len(author_commits)}")
        page += 1

    total_commits = sum(author_commits.values())
    if total_commits == 0:
        print("[WARN] No commits found for bus factor calculation")
        return None, None

    sorted_authors = sorted(author_commits.items(), key=lambda x: x[1], reverse=True)

    cumulative_commits = 0
    bus_factor = 0
    ownership_percent: float = 0.0

    for author, count in sorted_authors:
        cumulative_commits += count
        bus_factor += 1
        ownership_percent = (cumulative_commits / total_commits) * 100

        print(
            f"[INFO] Adding contributor '{author}' | Cumulative ownership: {ownership_percent:.2f}%"
        )

        if ownership_percent >= threshold_percent:
            break

    print("[INFO] Bus factor calculation completed")
    return bus_factor, ownership_percent


def calculate_bus_factor_details(
    *,
    days: int = 90,
    threshold_percent: float = 50,
    per_page: int = 100,
) -> Dict[str, object]:
    """Return bus factor plus the exact contributor list used.

    Output keys:
    - days, threshold_percent
    - total_commits
    - bus_factor
    - ownership_percent
    - contributors: list[dict] sorted by commits desc, with cumulative ownership
      and a boolean `in_bus_factor` for the authors included until threshold.
    """

    print(f"[INFO] Calculating bus factor DETAILS for last {days} days")

    client = default_client()
    author_commits: Dict[str, int] = defaultdict(int)
    page = 1
    since = (datetime.utcnow() - timedelta(days=days)).isoformat() + "Z"

    while True:
        commits = client.rest_get(
            f"/repos/{client.owner}/{client.repo}/commits",
            params={"per_page": per_page, "page": page, "since": since},
        )
        if not commits:
            break

        for commit in commits:
            if commit.get("author"):
                author = commit["author"]["login"]
            else:
                author = commit["commit"]["author"]["email"]
            author_commits[author] += 1

        page += 1

    total_commits = sum(author_commits.values())
    if total_commits == 0:
        return {
            "days": days,
            "threshold_percent": threshold_percent,
            "total_commits": 0,
            "bus_factor": None,
            "ownership_percent": None,
            "contributors": [],
        }

    sorted_authors = sorted(author_commits.items(), key=lambda x: x[1], reverse=True)

    cumulative_commits = 0
    bus_factor = 0
    ownership_percent: float = 0.0
    contributors: List[Dict[str, object]] = []

    for author, count in sorted_authors:
        cumulative_commits += count
        cumulative_percent = (cumulative_commits / total_commits) * 100
        percent = (count / total_commits) * 100

        in_bus_factor = False
        if ownership_percent < threshold_percent:
            bus_factor += 1
            in_bus_factor = True
            ownership_percent = cumulative_percent

        contributors.append(
            {
                "author": author,
                "commits": count,
                "ownership_percent": percent,
                "cumulative_ownership_percent": cumulative_percent,
                "in_bus_factor": in_bus_factor,
            }
        )

    return {
        "days": days,
        "threshold_percent": threshold_percent,
        "total_commits": total_commits,
        "bus_factor": bus_factor,
        "ownership_percent": ownership_percent,
        "contributors": contributors,
    }
