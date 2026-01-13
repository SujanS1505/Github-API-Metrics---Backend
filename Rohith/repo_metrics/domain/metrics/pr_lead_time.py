from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, List, Mapping, Optional

from ..time_utils import parse_github_datetime


@dataclass(frozen=True)
class LeadTimeStats:
    count: int
    avg_hours: Optional[float]
    median_hours: Optional[float]
    p75_hours: Optional[float]
    p90_hours: Optional[float]
    min_hours: Optional[float]
    max_hours: Optional[float]


def _percentile(values_sorted: List[float], p: float) -> Optional[float]:
    """Compute percentile using linear interpolation (similar to numpy's default).

    p is in [0, 100].
    """

    if not values_sorted:
        return None

    if p <= 0:
        return values_sorted[0]
    if p >= 100:
        return values_sorted[-1]

    n = len(values_sorted)
    if n == 1:
        return values_sorted[0]

    rank = (p / 100.0) * (n - 1)
    low = int(math.floor(rank))
    high = int(math.ceil(rank))
    if low == high:
        return values_sorted[low]

    weight = rank - low
    return (values_sorted[low] * (1.0 - weight)) + (values_sorted[high] * weight)


def pr_merge_lead_time_hours(pr: Mapping[str, object]) -> Optional[float]:
    created_raw = pr.get("created_at")
    merged_raw = pr.get("merged_at")
    if not isinstance(created_raw, str) or not isinstance(merged_raw, str):
        return None

    created_at = parse_github_datetime(created_raw)
    merged_at = parse_github_datetime(merged_raw)
    diff = merged_at - created_at
    return diff.total_seconds() / 3600.0


def pr_merge_lead_time_summary(merged_prs: Iterable[Mapping[str, object]]) -> dict:
    values: List[float] = []
    for pr in merged_prs:
        lt = pr_merge_lead_time_hours(pr)
        if lt is None:
            continue
        if lt < 0:
            continue
        values.append(lt)

    values.sort()

    if not values:
        stats = LeadTimeStats(
            count=0,
            avg_hours=None,
            median_hours=None,
            p75_hours=None,
            p90_hours=None,
            min_hours=None,
            max_hours=None,
        )
    else:
        count = len(values)
        avg = sum(values) / count
        median = _percentile(values, 50.0)
        p75 = _percentile(values, 75.0)
        p90 = _percentile(values, 90.0)
        stats = LeadTimeStats(
            count=count,
            avg_hours=avg,
            median_hours=median,
            p75_hours=p75,
            p90_hours=p90,
            min_hours=values[0],
            max_hours=values[-1],
        )

    return {
        "count": stats.count,
        "avg_hours": stats.avg_hours,
        "median_hours": stats.median_hours,
        "p75_hours": stats.p75_hours,
        "p90_hours": stats.p90_hours,
        "min_hours": stats.min_hours,
        "max_hours": stats.max_hours,
    }
