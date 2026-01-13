from collections import Counter, defaultdict
from datetime import datetime, timedelta


def calculate_code_churn(commit_details):
    """
    Returns churn per file:
    churn = additions + deletions
    """
    churn = Counter()
    commit_count = Counter()

    for commit in commit_details:
        for file in commit.get("files", []):
            filename = file["filename"]
            churn[filename] += file.get("additions", 0) + file.get("deletions", 0)
            commit_count[filename] += 1



    return churn, commit_count


def find_hotspot_files(churn, commit_count, churn_threshold=500, commit_threshold=10):
    """
    Hotspots = high churn + high commit frequency
    """
    hotspots = []

    for file in churn:
        if churn[file] >= churn_threshold and commit_count[file] >= commit_threshold:
            hotspots.append({
                "file": file,
                "churn": churn[file],
                "commits": commit_count[file]
            })

    return hotspots


def test_to_code_ratio(files):
    """
    Calculates test-to-production file ratio
    """
    test_files = 0
    prod_files = 0

    for f in files:
        f_lower = f.lower()
        if "test" in f_lower or "spec" in f_lower:
            test_files += 1
        else:
            prod_files += 1

    if prod_files == 0:
        return None

    return round(test_files / prod_files, 2)


def find_stale_files(commit_dates, stale_days=180):
    """
    Files not modified in the last N days
    """
    cutoff = datetime.utcnow() - timedelta(days=stale_days)
    stale = []

    for file, last_date in commit_dates.items():
        if last_date < cutoff:
            stale.append(file)

    return stale


def identify_hotspots(code_churn, churn_threshold=50):
    """
    Identify hotspot files based on churn threshold.
    """
    return {
        file: churn
        for file, churn in code_churn.items()
        if churn >= churn_threshold
    }

