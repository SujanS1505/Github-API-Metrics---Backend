from repo_metrics.domain.metrics.graphql_total_commits import get_exact_total_commits
from repo_metrics.domain.metrics.active_contributors import get_active_contributors
from repo_metrics.domain.metrics.bus_factor import calculate_bus_factor


class MetricsService:
    """
    Orchestrates metric collection from domain layer
    """

    def collect(self) -> dict:
        total_commits = get_exact_total_commits()
        active_contributors = get_active_contributors()
        bus_factor = calculate_bus_factor()

        return {
            "total_commits": total_commits,
            "active_contributors": active_contributors,
            "bus_factor": bus_factor,
        }
