from __future__ import annotations

import csv
import os
import sys

import config

from repo_metrics import (
    average_time_between_commits,
    calculate_bus_factor,
    calculate_bus_factor_details,
    commit_frequency_by_author,
    commits_per_day_week_month,
    fetch_merged_pull_requests,
    fetch_commits,
    get_branch_count,
    get_active_contributors,
    list_branches,
    lines_added_vs_deleted,
    merge_frequency_summary,
    merges_per_day_week_month,
    pr_merge_lead_time_hours,
    pr_merge_lead_time_summary,
    pr_merged_vs_closed_summary,
    fetch_closed_not_merged_prs,
    pr_reopen_rate_summary,
    pr_quality_summary,
)

from datetime import datetime, UTC


def main() -> None:
    print("Calculating repository activity metrics...\n")

    repo_root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(repo_root)

    os.makedirs("data", exist_ok=True)

    # =========================================================
    # 1. SUMMARY METRICS (SINGLE ROW PER METRIC)
    # =========================================================
    summary_csv = os.path.join("data", "repository_activity_metrics.csv")
    summary_rows: list[list[object]] = []

    active_contributors = get_active_contributors(days=config.DAYS)
    summary_rows.append(["active_contributors", active_contributors, f"last {config.DAYS} days"])

    avg_commit_time = average_time_between_commits(days=config.DAYS)
    summary_rows.append(
        [
            "avg_time_between_commits_hours",
            round(avg_commit_time, 2) if avg_commit_time is not None else "N/A",
            f"last {config.DAYS} days",
        ]
    )

    additions, deletions = lines_added_vs_deleted(days=config.DAYS, max_commits=200)
    summary_rows.append(["lines_added", additions, f"last {config.DAYS} days (sampled)"])
    summary_rows.append(["lines_deleted", deletions, f"last {config.DAYS} days (sampled)"])

    bus_factor, ownership = calculate_bus_factor(days=config.DAYS, threshold_percent=50)
    summary_rows.append(["bus_factor", bus_factor or "N/A", "contributors reaching 50% ownership"])
    summary_rows.append(
        [
            "bus_factor_ownership_percent",
            round(ownership, 2) if ownership is not None else "N/A",
            f"last {config.DAYS} days",
        ]
    )
    # Number of branches (parallel development complexity)
    branch_count = get_branch_count()
    summary_rows.append(
        [
            "branch_count",
            branch_count,
            "Number of branches – Parallel development complexity",
        ]
    )

    # Merge frequency (integration cadence)
    merged_prs = fetch_merged_pull_requests(days=config.DAYS)
    merge_summary = merge_frequency_summary(merged_prs=merged_prs, days=config.DAYS)

    # Average PR merge time (lead time for change)
    pr_lead_time_summary = pr_merge_lead_time_summary(merged_prs)

    # PRs merged vs closed (development efficiency)
    pr_efficiency_summary = pr_merged_vs_closed_summary(days=config.DAYS)
    closed_not_merged_prs = fetch_closed_not_merged_prs(days=config.DAYS, max_prs=500)

    # PR reopen rate (review quality signal)
    pr_reopen_summary = pr_reopen_rate_summary(days=config.DAYS, max_prs_scanned=500, max_reopened_prs=500)

    # PR quality metrics
    pr_quality = pr_quality_summary(days=config.DAYS, max_prs=500)
    summary_rows.append(
        [
            "merge_frequency_merged_prs",
            merge_summary["merged_prs"],
            f"Merge frequency – Integration cadence (last {config.DAYS} days)",
        ]
    )
    summary_rows.append(
        [
            "merge_frequency_merges_per_week",
            round(float(merge_summary["merges_per_week"]), 2),
            f"last {config.DAYS} days",
        ]
    )
    avg_merge_hours = merge_summary["avg_time_between_merges_hours"]
    summary_rows.append(
        [
            "avg_time_between_merges_hours",
            round(avg_merge_hours, 2) if isinstance(avg_merge_hours, (int, float)) else "N/A",
            f"last {config.DAYS} days",
        ]
    )

    summary_rows.append(
        [
            "avg_pr_merge_lead_time_hours",
            round(float(pr_lead_time_summary["avg_hours"]), 2)
            if isinstance(pr_lead_time_summary.get("avg_hours"), (int, float))
            else "N/A",
            f"Average PR merge time – Lead time for change (last {config.DAYS} days)",
        ]
    )
    summary_rows.append(
        [
            "median_pr_merge_lead_time_hours",
            round(float(pr_lead_time_summary["median_hours"]), 2)
            if isinstance(pr_lead_time_summary.get("median_hours"), (int, float))
            else "N/A",
            f"last {config.DAYS} days",
        ]
    )
    summary_rows.append(
        [
            "p75_pr_merge_lead_time_hours",
            round(float(pr_lead_time_summary["p75_hours"]), 2)
            if isinstance(pr_lead_time_summary.get("p75_hours"), (int, float))
            else "N/A",
            f"last {config.DAYS} days",
        ]
    )
    summary_rows.append(
        [
            "p90_pr_merge_lead_time_hours",
            round(float(pr_lead_time_summary["p90_hours"]), 2)
            if isinstance(pr_lead_time_summary.get("p90_hours"), (int, float))
            else "N/A",
            f"last {config.DAYS} days",
        ]
    )

    summary_rows.append(
        [
            "prs_closed",
            pr_efficiency_summary.get("closed_prs"),
            f"PRs closed (last {config.DAYS} days)",
        ]
    )
    summary_rows.append(
        [
            "prs_merged",
            pr_efficiency_summary.get("merged_prs"),
            f"PRs merged (last {config.DAYS} days)",
        ]
    )
    summary_rows.append(
        [
            "prs_closed_not_merged",
            pr_efficiency_summary.get("closed_not_merged_prs"),
            "PRs closed without merge (includes rejected/abandoned)",
        ]
    )
    merge_rate = pr_efficiency_summary.get("merge_rate")
    summary_rows.append(
        [
            "prs_merge_rate_percent",
            round(float(merge_rate) * 100.0, 2) if isinstance(merge_rate, (int, float)) else "N/A",
            "Merged PRs / Closed PRs",
        ]
    )

    reopen_rate = pr_reopen_summary.get("reopen_rate")
    scanned_prs = pr_reopen_summary.get("prs_scanned")
    summary_rows.append(
        [
            "prs_reopened",
            pr_reopen_summary.get("reopened_prs"),
            f"PRs reopened at least once – Review quality signal (last {config.DAYS} days; scanned {scanned_prs} recently-updated PRs)",
        ]
    )
    summary_rows.append(
        [
            "prs_reopen_events",
            pr_reopen_summary.get("reopen_events"),
            f"Total reopen events (last {config.DAYS} days; scanned {scanned_prs} recently-updated PRs)",
        ]
    )
    summary_rows.append(
        [
            "prs_reopen_rate_percent",
            round(float(reopen_rate) * 100.0, 2) if isinstance(reopen_rate, (int, float)) else "N/A",
            "Reopened PRs / Closed PRs",
        ]
    )

    with open(summary_csv, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["metric_name", "metric_value", "notes"])
        writer.writerows(summary_rows)

    print(f"[INFO] Summary metrics written to {summary_csv}")

    # =========================================================
    # 1b. PR QUALITY METRICS (SUMMARY CSV)
    # =========================================================
    pr_quality_csv = os.path.join("data", "pr_quality_metrics.csv")

    def _pct(v: object) -> str:
        return f"{(float(v) * 100.0):.2f}" if isinstance(v, (int, float)) else "N/A"

    prq_rows: list[list[object]] = [
        ["prs_scanned", pr_quality.get("prs_scanned"), f"PRs created in last {config.DAYS} days"],
        ["prs_non_draft", pr_quality.get("non_draft_prs_count"), "Draft PRs excluded from most calculations"],
        [
            "review_turnaround_avg_hours",
            round(float(pr_quality.get("review_turnaround_avg_hours")), 2)
            if isinstance(pr_quality.get("review_turnaround_avg_hours"), (int, float))
            else "N/A",
            "createdAt -> first non-author review submitted (draft PRs excluded)",
        ],
        [
            "review_turnaround_median_hours",
            round(float(pr_quality.get("review_turnaround_median_hours")), 2)
            if isinstance(pr_quality.get("review_turnaround_median_hours"), (int, float))
            else "N/A",
            "Median turnaround (hours)",
        ],
        [
            "avg_reviewers_per_pr",
            round(float(pr_quality.get("avg_reviewers_per_pr")), 2)
            if isinstance(pr_quality.get("avg_reviewers_per_pr"), (int, float))
            else "N/A",
            "Distinct reviewers who submitted a review",
        ],
        [
            "avg_pr_loc_changed",
            round(float(pr_quality.get("avg_pr_loc_changed")), 2)
            if isinstance(pr_quality.get("avg_pr_loc_changed"), (int, float))
            else "N/A",
            "additions + deletions",
        ],
        [
            "median_pr_loc_changed",
            round(float(pr_quality.get("median_pr_loc_changed")), 2)
            if isinstance(pr_quality.get("median_pr_loc_changed"), (int, float))
            else "N/A",
            "Median additions + deletions",
        ],
        [
            "avg_pr_total_comments",
            round(float(pr_quality.get("avg_pr_total_comments")), 2)
            if isinstance(pr_quality.get("avg_pr_total_comments"), (int, float))
            else "N/A",
            "issue comments + review thread count (proxy)",
        ],
        [
            "approval_rate_percent",
            _pct(pr_quality.get("approval_rate")),
            "Merged PRs with >=1 approval / merged PRs",
        ],
        [
            "merged_prs_count",
            pr_quality.get("merged_prs_count"),
            "Non-draft PRs created in window that were merged",
        ],
    ]

    with open(pr_quality_csv, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["metric_name", "metric_value", "notes"])
        writer.writerows(prq_rows)

    print(f"[INFO] PR quality metrics written to {pr_quality_csv}")

    # =========================================================
    # 2. COMMIT FREQUENCY BY AUTHOR
    # =========================================================
    author_csv = os.path.join("data", "commit_frequency_by_author.csv")
    author_frequency = commit_frequency_by_author(days=config.DAYS)

    with open(author_csv, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["author", "commit_count"])
        for author, count in sorted(author_frequency.items(), key=lambda x: x[1], reverse=True):
            writer.writerow([author, count])

    print(f"[INFO] Commit frequency by author written to {author_csv}")

    # =========================================================
    # 2c. BRANCHES TABLE
    # =========================================================
    branches_csv = os.path.join("data", "branches.csv")
    branches = list_branches()

    with open(branches_csv, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["branch_name", "protected", "head_sha"])
        for b in sorted(branches, key=lambda x: (x.get("name") or "")):
            writer.writerow([b.get("name"), "yes" if b.get("protected") else "no", b.get("sha")])

    print(f"[INFO] Branch list written to {branches_csv}")

    # =========================================================
    # 2d. MERGED PRS TABLE + TIME DISTRIBUTION
    # =========================================================
    merged_prs_csv = os.path.join("data", "merged_prs.csv")
    merges_time_csv = os.path.join("data", "merges_time_distribution.csv")

    pr_lead_time_csv = os.path.join("data", "pr_merge_lead_time.csv")
    pr_closed_not_merged_csv = os.path.join("data", "prs_closed_not_merged.csv")
    pr_reopened_csv = os.path.join("data", "prs_reopened.csv")

    with open(merged_prs_csv, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "number",
                "created_at",
                "merged_at",
                "author",
                "base",
                "head",
                "title",
                "url",
            ]
        )
        for pr in merged_prs:
            writer.writerow(
                [
                    pr.get("number"),
                    pr.get("created_at"),
                    pr.get("merged_at"),
                    pr.get("author"),
                    pr.get("base"),
                    pr.get("head"),
                    pr.get("title"),
                    pr.get("url"),
                ]
            )

    # Detailed lead time table
    with open(pr_lead_time_csv, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "number",
                "created_at",
                "merged_at",
                "lead_time_hours",
                "lead_time_days",
                "author",
                "title",
                "url",
            ]
        )
        for pr in merged_prs:
            lt = pr_merge_lead_time_hours(pr)
            writer.writerow(
                [
                    pr.get("number"),
                    pr.get("created_at"),
                    pr.get("merged_at"),
                    round(lt, 2) if isinstance(lt, (int, float)) else "N/A",
                    round((lt / 24.0), 2) if isinstance(lt, (int, float)) else "N/A",
                    pr.get("author"),
                    pr.get("title"),
                    pr.get("url"),
                ]
            )

    # Closed-not-merged PRs (development efficiency detail)
    with open(pr_closed_not_merged_csv, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "number",
                "created_at",
                "closed_at",
                "author",
                "title",
                "url",
            ]
        )
        for pr in closed_not_merged_prs:
            writer.writerow(
                [
                    pr.get("number"),
                    pr.get("created_at"),
                    pr.get("closed_at"),
                    pr.get("author"),
                    pr.get("title"),
                    pr.get("url"),
                ]
            )

    # Reopened PRs (review quality signal detail)
    reopened_details = pr_reopen_summary.get("reopened_prs_details") or []
    with open(pr_reopened_csv, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "number",
                "reopened_at",
                "updated_at",
                "closed_at",
                "author",
                "title",
                "url",
            ]
        )
        for pr in reopened_details:
            writer.writerow(
                [
                    getattr(pr, "number", ""),
                    getattr(pr, "reopened_at", ""),
                    getattr(pr, "updated_at", ""),
                    getattr(pr, "closed_at", ""),
                    getattr(pr, "author", ""),
                    getattr(pr, "title", ""),
                    getattr(pr, "url", ""),
                ]
            )

    merges_per_day, merges_per_week, merges_per_month = merges_per_day_week_month(merged_prs)
    with open(merges_time_csv, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["time_granularity", "time_key", "merge_count"])
        for day in sorted(merges_per_day):
            writer.writerow(["day", day, merges_per_day[day]])
        for week in sorted(merges_per_week):
            writer.writerow(["week", week, merges_per_week[week]])
        for month in sorted(merges_per_month):
            writer.writerow(["month", month, merges_per_month[month]])

    print(f"[INFO] Merged PR list written to {merged_prs_csv}")
    print(f"[INFO] PR merge lead time written to {pr_lead_time_csv}")
    print(f"[INFO] Closed-not-merged PR list written to {pr_closed_not_merged_csv}")
    print(f"[INFO] Reopened PR list written to {pr_reopened_csv}")
    print(f"[INFO] Merge time distribution written to {merges_time_csv}")

    # =========================================================
    # 2b. BUS FACTOR DETAILS (WHO IS IN THE LIST)
    # =========================================================
    bus_factor_details_csv = os.path.join("data", "bus_factor_details.csv")
    bus_details = calculate_bus_factor_details(days=config.DAYS, threshold_percent=50)

    with open(bus_factor_details_csv, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "author",
                "commit_count",
                "ownership_percent",
                "cumulative_ownership_percent",
                "in_bus_factor",
            ]
        )
        for row in bus_details["contributors"]:
            writer.writerow(
                [
                    row["author"],
                    row["commits"],
                    f"{row['ownership_percent']:.2f}",
                    f"{row['cumulative_ownership_percent']:.2f}",
                    "yes" if row["in_bus_factor"] else "no",
                ]
            )

    print(f"[INFO] Bus factor details written to {bus_factor_details_csv}")

    # =========================================================
    # 3. COMMITS PER DAY / WEEK / MONTH (SINGLE CSV)
    # =========================================================
    time_csv = os.path.join("data", "commits_time_distribution.csv")

    commits = fetch_commits(days=config.DAYS)
    per_day, per_week, per_month = commits_per_day_week_month(commits)

    with open(time_csv, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["time_granularity", "time_key", "commit_count"])

        for day in sorted(per_day):
            writer.writerow(["day", day, per_day[day]])

        for week in sorted(per_week):
            writer.writerow(["week", week, per_week[week]])

        for month in sorted(per_month):
            writer.writerow(["month", month, per_month[month]])

    print(f"[INFO] Commit time distribution written to {time_csv}")

    # =========================================================
    # 4. PDF REPORT (PRETTY)
    # =========================================================
    pdf_path = os.path.join("data", "repository_activity_report.pdf")
    try:
        from repo_metrics.adapters.exporters.pdf_report import write_repository_activity_pdf

        write_repository_activity_pdf(
            output_path=pdf_path,
            owner=config.OWNER,
            repo=config.REPO,
            days=config.DAYS,
            generated_at_utc=datetime.now(UTC),
            summary_rows=summary_rows,
            bus_factor_details=bus_details,
            author_frequency=author_frequency,
            per_day=per_day,
            per_week=per_week,
            per_month=per_month,
            branches=branches,
            merge_summary=merge_summary,
            merged_prs=merged_prs,
            pr_lead_time_summary=pr_lead_time_summary,
            pr_efficiency_summary=pr_efficiency_summary,
            closed_not_merged_prs=closed_not_merged_prs,
            pr_reopen_rate_summary=pr_reopen_summary,
            pr_quality_summary=pr_quality,
            merges_per_day=merges_per_day,
            merges_per_week=merges_per_week,
            merges_per_month=merges_per_month,
        )
        print(f"[INFO] PDF report written to {pdf_path}")
    except ModuleNotFoundError as exc:
        if (exc.name or "").startswith("reportlab"):
            exe = sys.executable
            venv_hint = os.path.join(".venv", "Scripts", "python.exe")
            print(
                "[WARN] PDF generation skipped because 'reportlab' is not installed. "
                f"You're running: {exe}  "
                f"Install it with: \"{exe}\" -m pip install reportlab  "
                f"(recommended: run using {venv_hint} run_metrics.py)"
            )
        else:
            raise

    print("\n[INFO] ALL repository activity metrics exported successfully")


if __name__ == "__main__":
    main()
