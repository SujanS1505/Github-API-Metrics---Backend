import time

from repo_metrics.app.metrics_service import MetricsService
from repo_metrics.adapters.exporters.prometheus.prometheus_exporter import RepoMetricsExporter


def main():
    metrics_service = MetricsService()
    exporter = RepoMetricsExporter()

    # Start Prometheus server
    exporter.start(port=8000)

    print("[App] Prometheus exporter running...")

    while True:
        try:
            metrics = metrics_service.collect()
            exporter.update(metrics)
            print("[App] Metrics updated:", metrics)
        except Exception as e:
            print("[Error] Failed to update metrics:", e)

        time.sleep(60)  # refresh every 60 seconds


if __name__ == "__main__":
    main()
