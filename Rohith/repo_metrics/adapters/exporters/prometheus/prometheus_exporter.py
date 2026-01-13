from prometheus_client import Gauge, start_http_server


class RepoMetricsExporter:
    def __init__(self):
        # --- Core Repository Metrics ---
        self.total_commits = Gauge(
            "github_repo_commits_total",
            "Total number of commits in the repository"
        )

        self.active_contributors = Gauge(
            "github_repo_active_contributors",
            "Number of active contributors"
        )

        self.bus_factor = Gauge(
            "github_repo_bus_factor",
            "Bus factor of the repository"
        )

    def update(self, metrics: dict):
        """
        Update Prometheus gauges using collected metrics
        """
        self.total_commits.set(metrics["total_commits"])
        self.active_contributors.set(metrics["active_contributors"])
        self.bus_factor.set(metrics["bus_factor"])

    def start(self, port: int = 8000):
        """
        Start Prometheus HTTP metrics server
        """
        start_http_server(port)
        print(f"[Prometheus] Metrics server started on port {port}")
