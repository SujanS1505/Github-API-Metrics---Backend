from pathlib import Path
import time
import pandas as pd
from prometheus_client import Gauge, start_http_server

# ============================================================
# Paths
# ============================================================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
METRICS_CSV = DATA_DIR / "repository_activity_metrics.csv"

# ============================================================
# Prometheus Gauges
# ============================================================
github_repo_active_contributors = Gauge(
    "github_repo_active_contributors",
    "Number of active contributors"
)

github_repo_bus_factor = Gauge(
    "github_repo_bus_factor",
    "Bus factor of the repository"
)

github_repo_avg_time_between_commits_hours = Gauge(
    "github_repo_avg_time_between_commits_hours",
    "Average time between commits in hours"
)

github_repo_lines_added = Gauge(
    "github_repo_lines_added",
    "Lines of code added"
)

github_repo_lines_deleted = Gauge(
    "github_repo_lines_deleted",
    "Lines of code deleted"
)

repo_metrics_last_run_timestamp = Gauge(
    "repo_metrics_last_run_timestamp",
    "Last time metrics were updated (unix timestamp)"
)

# ============================================================
# Generic CSV Metric Reader (Schema-Agnostic)
# ============================================================
def read_metric_value(metric_name: str) -> float:
    if not METRICS_CSV.exists():
        print(f"[WARN] Missing CSV file: {METRICS_CSV.name}")
        return 0.0

    df = pd.read_csv(METRICS_CSV)

    if df.empty:
        print("[WARN] CSV is empty")
        return 0.0

    # Identify first string column (metric name)
    string_cols = df.select_dtypes(include=["object"]).columns
    numeric_cols = df.select_dtypes(include=["int64", "float64"]).columns

    if len(string_cols) == 0 or len(numeric_cols) == 0:
        print("[WARN] Could not infer metric/value columns")
        return 0.0

    metric_col = string_cols[0]
    value_col = numeric_cols[0]

    row = df[df[metric_col] == metric_name]

    if row.empty:
        print(f"[WARN] Metric not found: {metric_name}")
        return 0.0

    try:
        return float(row[value_col].iloc[0])
    except Exception as e:
        print(f"[WARN] Failed reading metric {metric_name}: {e}")
        return 0.0

# ============================================================
# Metric Updater
# ============================================================
def update_metrics():
    github_repo_active_contributors.set(
        read_metric_value("active_contributors")
    )

    github_repo_bus_factor.set(
        read_metric_value("bus_factor")
    )

    github_repo_avg_time_between_commits_hours.set(
        read_metric_value("avg_time_between_commits_hours")
    )

    github_repo_lines_added.set(
        read_metric_value("lines_added")
    )

    github_repo_lines_deleted.set(
        read_metric_value("lines_deleted")
    )

    repo_metrics_last_run_timestamp.set(time.time())

    print("[OK] Metrics updated")

# ============================================================
# Main
# ============================================================
if __name__ == "__main__":
    print("[START] CSV-based Prometheus exporter running on :8000")
    start_http_server(8000)

    while True:
        try:
            update_metrics()
        except Exception as e:
            print("[ERROR]", e)

        time.sleep(60)
