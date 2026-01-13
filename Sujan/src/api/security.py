from requests.exceptions import HTTPError


def fetch_dependabot_alerts(client, owner, repo):
    """
    Fetch Dependabot alerts.

    NOTE:
    - Dependabot Alerts API does NOT reliably support query params
      (state, pagination) for fine-grained tokens.
    - GitHub returns all OPEN alerts by default.
    """

    try:
        alerts = client.get(
            f"/repos/{owner}/{repo}/dependabot/alerts"
        )

        # GitHub returns a list
        if not alerts:
            return []

        return alerts

    except HTTPError as e:
        print("Dependabot alerts not accessible:", e)
        return []
