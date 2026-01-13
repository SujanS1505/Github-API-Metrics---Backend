from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional

from ...adapters.github.github_client import default_client
from ..time_utils import parse_github_datetime


def average_time_between_commits(days: int = 90, per_page: int = 100) -> Optional[float]:
    print(f"[INFO] Calculating average time between commits for last {days} days")

    client = default_client()
    commit_times: List[datetime] = []
    page = 1
    since = (datetime.utcnow() - timedelta(days=days)).isoformat() + "Z"

    while True:
        data = client.rest_get(
            f"/repos/{client.owner}/{client.repo}/commits",
            params={"per_page": per_page, "page": page, "since": since},
        )
        if not data:
            print("[INFO] No more commits returned by API")
            break

        for commit in data:
            commit_times.append(parse_github_datetime(commit["commit"]["author"]["date"]))

        print(f"[INFO] Page {page} processed | Total commits collected: {len(commit_times)}")
        page += 1

    if len(commit_times) < 2:
        print("[WARN] Not enough commits to calculate cadence")
        return None

    commit_times.sort()

    total_diff_seconds = 0.0
    for i in range(1, len(commit_times)):
        total_diff_seconds += (commit_times[i] - commit_times[i - 1]).total_seconds()

    avg_seconds = total_diff_seconds / (len(commit_times) - 1)
    avg_hours = avg_seconds / 3600.0

    print("[INFO] Average time between commits calculated successfully")
    return avg_hours
