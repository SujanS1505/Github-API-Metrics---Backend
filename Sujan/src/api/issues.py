from datetime import datetime
from requests.exceptions import HTTPError

MAX_PAGES = 40          # Safety limit
PER_PAGE = 100


def fetch_all_issues(client, owner, repo, state="all", max_pages=MAX_PAGES, per_page=PER_PAGE):
    """
    Fetch all issues (excluding PRs) from a GitHub repo.
    Handles pagination limits for large repositories.
    """
    issues = []
    page = 1

    while True:
        try:
            response = client.get(
                f"/repos/{owner}/{repo}/issues",
                params={
                    "state": state,
                    "per_page": per_page,
                    "page": page
                }
            )
        except HTTPError as e:
            # GitHub throws 422 when page number exceeds limits
            print(f"Stopping issue fetch at page {page}: {e}")
            break

        if not response:
            break

        for issue in response:
            # Exclude pull requests
            if "pull_request" in issue:
                continue

            issues.append(normalize_issue(issue))

        page += 1

        if page > max_pages:
            print(f"Reached max page limit ({max_pages}), stopping early.")
            break

    return issues


def normalize_issue(issue):
    return {
        "id": issue["id"],
        "number": issue["number"],
        "title": issue["title"],
        "state": issue["state"],            # open / closed
        "created_at": parse_date(issue["created_at"]),
        "closed_at": parse_date(issue["closed_at"]),
        "labels": [label["name"] for label in issue.get("labels", [])],
        "author": issue["user"]["login"],
        "comments": issue["comments"]
    }


def parse_date(value):
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
