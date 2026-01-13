from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import DefaultDict, Dict, Iterable, List, Tuple

from ...adapters.github.github_client import default_client
from ..time_utils import parse_github_datetime


def fetch_commits(*, days: int | None = None, per_page: int = 100) -> List[dict]:
    """Fetch commits from the repo.

    If days is None, fetches entire history (can be large).
    If days is set, fetches commits since now-days.
    """

    client = default_client()

    params: Dict[str, str] = {}
    if days is not None:
        since = (datetime.utcnow() - timedelta(days=days)).isoformat() + "Z"
        params["since"] = since
        print(f"[INFO] Fetching commits since {since}")
    else:
        print("[INFO] Fetching ALL commits (since filter removed)")

    commits: List[dict] = []
    page = 1

    while True:
        data = client.rest_get(
            f"/repos/{client.owner}/{client.repo}/commits",
            params={**params, "per_page": per_page, "page": page},
        )
        if not data:
            print("[INFO] No more commits returned by API")
            break

        commits.extend(data)
        print(f"[INFO] Page {page} fetched | Total commits fetched so far: {len(commits)}")
        page += 1

    print(f"[INFO] Finished fetching commits | Total fetched: {len(commits)}")
    return commits


def commits_per_day_week_month(
    commits: Iterable[dict],
) -> Tuple[DefaultDict[str, int], DefaultDict[str, int], DefaultDict[str, int]]:
    print("[INFO] Aggregating commits per day / week / month")

    per_day: DefaultDict[str, int] = defaultdict(int)
    per_week: DefaultDict[str, int] = defaultdict(int)
    per_month: DefaultDict[str, int] = defaultdict(int)

    for c in commits:
        d = parse_github_datetime(c["commit"]["author"]["date"])
        per_day[d.strftime("%Y-%m-%d")] += 1
        per_week[f"{d.year}-W{d.isocalendar()[1]}"] += 1
        per_month[d.strftime("%Y-%m")] += 1

    print("[INFO] Aggregation completed")
    return per_day, per_week, per_month
