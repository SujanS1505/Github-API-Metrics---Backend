from datetime import datetime, timedelta
from requests.exceptions import HTTPError

MAX_COMMIT_PAGES = 3
PER_PAGE = 100


def fetch_recent_commits(client, owner, repo, since_days=90):
    """
    Fetch recent commits (metadata only)
    """
    commits = []
    page = 1
    since_date = (datetime.utcnow() - timedelta(days=since_days)).isoformat() + "Z"

    while True:
        try:
            response = client.get(
                f"/repos/{owner}/{repo}/commits",
                params={
                    "per_page": PER_PAGE,
                    "page": page,
                    "since": since_date
                }
            )
        except HTTPError as e:
            print(f"Stopping commit fetch at page {page}: {e}")
            break

        if not response:
            break

        commits.extend(response)
        page += 1

        if page > MAX_COMMIT_PAGES:
            print("Reached max commit page limit.")
            break

    return commits


def fetch_commit_details(client, owner, repo, sha):
    """
    Fetch detailed commit info including file changes
    """
    return client.get(f"/repos/{owner}/{repo}/commits/{sha}")
