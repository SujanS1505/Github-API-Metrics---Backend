from __future__ import annotations

from datetime import datetime, timedelta
from typing import Tuple

from ...adapters.github.github_client import default_client


def lines_added_vs_deleted(
    *,
    days: int = 90,
    max_commits: int = 200,
    per_page: int = 100,
) -> Tuple[int, int]:
    print(f"[INFO] Calculating lines added vs deleted for last {days} days")

    client = default_client()
    total_additions = 0
    total_deletions = 0
    page = 1
    processed_commits = 0
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
            sha = commit["sha"]

            detail = client.rest_get(
                f"/repos/{client.owner}/{client.repo}/commits/{sha}",
                params=None,
            )
            stats = detail.get("stats", {})

            additions = int(stats.get("additions", 0) or 0)
            deletions = int(stats.get("deletions", 0) or 0)

            total_additions += additions
            total_deletions += deletions
            processed_commits += 1

            print(
                f"[INFO] Commit {processed_commits} | +{additions} / -{deletions} | "
                f"Totals: +{total_additions} / -{total_deletions}"
            )

            if processed_commits >= max_commits:
                print("[WARN] Max commit processing limit reached")
                break

        if processed_commits >= max_commits:
            break

        page += 1

    print("[INFO] Code churn calculation completed")
    return total_additions, total_deletions
