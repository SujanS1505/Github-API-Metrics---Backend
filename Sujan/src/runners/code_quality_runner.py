from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from api.commits import fetch_recent_commits, fetch_commit_details
from metrics.code_quality_metrics import (
    calculate_code_churn,
    find_hotspot_files,
    test_to_code_ratio,
    find_stale_files
)
from reports.csv_writer import (
    ensure_dir,
    write_key_value_csv,
    write_time_series_csv
)


def fetch_commit_details_parallel(client, owner, repo, commits, max_workers=6):
    details = []
    commit_dates = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(fetch_commit_details, client, owner, repo, c["sha"]): c
            for c in commits
        }

        for future in as_completed(futures):
            try:
                detail = future.result()
                details.append(detail)

                commit_time = datetime.strptime(
                    detail["commit"]["author"]["date"],
                    "%Y-%m-%dT%H:%M:%SZ"
                )

                for file in detail.get("files", []):
                    commit_dates[file["filename"]] = commit_time
            except Exception as e:
                print("Skipping commit due to error:", e)

    return details, commit_dates


def run_code_quality_metrics(client, owner, repo):
    print("\n📦 CODE QUALITY METRICS")

    commits = fetch_recent_commits(client, owner, repo, since_days=90)
    print(f"Commits fetched (non-merge): {len(commits)}")

    commit_details, commit_dates = fetch_commit_details_parallel(
        client, owner, repo, commits
    )

    churn, commit_count = calculate_code_churn(commit_details)
    hotspots = find_hotspot_files(churn, commit_count)
    test_ratio = test_to_code_ratio(churn.keys())
    stale_files = find_stale_files(commit_dates)

    print("Files analyzed:", len(churn))
    print("Hotspot files:", len(hotspots))
    print("Test-to-code ratio:", test_ratio)
    print("Stale files:", len(stale_files))

    # CSV

    REPORT_DIR = "reports"
    ensure_dir(REPORT_DIR)

    # Code quality summary
    write_key_value_csv(
        f"{REPORT_DIR}/code_quality_summary.csv",
        {
            "files_analyzed": len(churn),
            "hotspot_files": len(hotspots),
            "test_to_code_ratio": test_ratio,
            "stale_files": len(stale_files),
        }
    )

    # Code churn per file
    churn_rows = [
        [file, churn[file], commit_count[file]]
        for file in churn
    ]

    write_time_series_csv(
        f"{REPORT_DIR}/code_churn_by_file.csv",
        churn_rows,
        headers=["file_path", "code_churn", "commit_count"]
    )

    # Hotspot files
    hotspot_rows = [
        [h["file"], h["churn"], h["commits"]]
        for h in hotspots
    ]

    write_time_series_csv(
        f"{REPORT_DIR}/hotspot_files.csv",
        hotspot_rows,
        headers=["file_path", "code_churn", "commit_count"]
    )

    # Stale files (details)
    stale_rows = []
    for file_path in sorted(stale_files):
        last_date = commit_dates.get(file_path)
        stale_rows.append([
            file_path,
            last_date.strftime("%Y-%m-%d") if last_date else "",
        ])

    write_time_series_csv(
        f"{REPORT_DIR}/stale_files.csv",
        stale_rows,
        headers=["file_path", "last_commit_date"],
    )

    print("✅ Code quality CSV reports generated")
