from __future__ import annotations

from datetime import datetime


def parse_github_datetime(date_str: str) -> datetime:
    """Parse GitHub ISO timestamps like '2026-01-12T10:11:12Z' to aware datetime."""
    # GitHub uses 'Z' for UTC. datetime.fromisoformat expects '+00:00'.
    if date_str.endswith("Z"):
        date_str = date_str[:-1] + "+00:00"
    return datetime.fromisoformat(date_str)
