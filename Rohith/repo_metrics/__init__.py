from .domain.metrics.graphql_total_commits import get_exact_total_commits
from .domain.metrics.commits_time_distribution import fetch_commits, commits_per_day_week_month
from .domain.metrics.active_contributors import get_active_contributors
from .domain.metrics.commit_frequency import commit_frequency_by_author
from .domain.metrics.commit_cadence import average_time_between_commits
from .domain.metrics.code_churn import lines_added_vs_deleted
from .domain.metrics.bus_factor import calculate_bus_factor, calculate_bus_factor_details
from .domain.metrics.branches import get_branch_count, list_branches
from .domain.metrics.merge_frequency import (
    fetch_merged_pull_requests,
    merge_frequency_summary,
    merges_per_day_week_month,
)
from .domain.metrics.pr_lead_time import pr_merge_lead_time_hours, pr_merge_lead_time_summary
from .domain.metrics.pr_efficiency import pr_merged_vs_closed_summary, fetch_closed_not_merged_prs
from .domain.metrics.pr_reopen_rate import pr_reopen_rate_summary
from .domain.metrics.pr_quality import pr_quality_summary
try:
    from .adapters.exporters.pdf_report import write_repository_activity_pdf
except ModuleNotFoundError as exc:  # pragma: no cover
    # Allow importing the package even when optional PDF deps aren't installed.
    if (exc.name or "").startswith("reportlab"):
        def write_repository_activity_pdf(*args, **kwargs):  # type: ignore[no-redef]
            raise ModuleNotFoundError(
                "PDF generation requires 'reportlab'. Install it with: "
                "python -m pip install reportlab  (or run .venv\\Scripts\\python.exe run_metrics.py)"
            )
    else:
        raise

__all__ = [
    "get_exact_total_commits",
    "fetch_commits",
    "commits_per_day_week_month",
    "get_active_contributors",
    "commit_frequency_by_author",
    "average_time_between_commits",
    "lines_added_vs_deleted",
    "calculate_bus_factor",
    "calculate_bus_factor_details",
    "get_branch_count",
    "list_branches",
    "fetch_merged_pull_requests",
    "merge_frequency_summary",
    "merges_per_day_week_month",
    "pr_merge_lead_time_hours",
    "pr_merge_lead_time_summary",
    "pr_merged_vs_closed_summary",
    "fetch_closed_not_merged_prs",
    "pr_reopen_rate_summary",
    "pr_quality_summary",
    "write_repository_activity_pdf",
]
