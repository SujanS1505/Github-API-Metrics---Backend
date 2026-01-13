# GitHub Repo Activity Metrics

This workspace exports repository activity metrics to CSV files in `./data`.

## Setup

1. Create a GitHub token with access to the repo.
2. Set environment variables:

```powershell
$env:GITHUB_TOKEN = "<token>"
$env:OWNER = "<org-or-user>"
$env:REPO = "<repo-name>"
```

3. Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

## Run

```powershell
python run_metrics.py
```

Outputs:
- `data/repository_activity_metrics.csv`
- `data/commit_frequency_by_author.csv`
- `data/commits_time_distribution.csv`
