from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import DefaultDict, Dict

from ...adapters.github.github_client import default_client


def commit_frequency_by_author(days: int = 90, per_page: int = 100) -> Dict[str, int]:
    print(f"[INFO] Calculating commit frequency by author for last {days} days")

    client = default_client()
    author_commits: DefaultDict[str, int] = defaultdict(int)
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
            if commit.get("author"):
                author = commit["author"]["login"]
            else:
                author = commit["commit"]["author"]["email"]
            author_commits[author] += 1

        print(f"[INFO] Page {page} processed | Unique authors so far: {len(author_commits)}")
        page += 1

    print("[INFO] Commit frequency by author calculation completed")
    return dict(author_commits)
