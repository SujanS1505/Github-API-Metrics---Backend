import csv
import os


def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)


def write_key_value_csv(filepath, data: dict):
    """
    Writes simple key-value metrics to CSV
    """
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "value"])
        for key, value in data.items():
            writer.writerow([key, value])


def write_time_series_csv(filepath, rows, headers):
    """
    Writes time-series metrics to CSV
    """
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for row in rows:
            writer.writerow(row)
