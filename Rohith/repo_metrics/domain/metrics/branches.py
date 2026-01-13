from __future__ import annotations

from typing import List, Optional

from ...adapters.github.github_client import default_client


def get_branch_count(per_page: int = 100) -> int:
    """Return the total number of branches in the repository.

    Interpreted as a proxy for parallel development complexity.
    """

    client = default_client()
    count = 0

    for _ in client.rest_get_paginated(
        f"/repos/{client.owner}/{client.repo}/branches",
        params=None,
        per_page=per_page,
    ):
        count += 1

    return count


def list_branches(per_page: int = 100, limit: Optional[int] = None) -> List[dict]:
    """List branches with basic details.

    Returns items with keys: name, protected, sha.
    """

    client = default_client()
    branches: List[dict] = []

    for b in client.rest_get_paginated(
        f"/repos/{client.owner}/{client.repo}/branches",
        params=None,
        per_page=per_page,
    ):
        branches.append(
            {
                "name": b.get("name"),
                "protected": bool(b.get("protected")),
                "sha": (b.get("commit") or {}).get("sha"),
            }
        )
        if limit is not None and len(branches) >= limit:
            break

    return branches
