from __future__ import annotations

from datetime import datetime, timedelta

from ...adapters.github.github_client import default_client


def get_active_contributors(days: int = 90, per_page: int = 100) -> int:
    print(f"[INFO] Calculating active contributors for last {days} days")

    client = default_client()
    contributors: set[str] = set()
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
                contributors.add(commit["author"]["login"])
            else:
                contributors.add(commit["commit"]["author"]["email"])

        print(f"[INFO] Page {page} processed | Active contributors so far: {len(contributors)}")
        page += 1

    print("[INFO] Active contributor calculation completed")
    return len(contributors)
