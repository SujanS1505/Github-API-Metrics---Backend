from requests.exceptions import HTTPError


def fetch_dependabot_alerts(client, owner, repo, state="open"):
    """
    Fetch Dependabot alerts if enabled
    """
    alerts = []
    page = 1

    while True:
        try:
            response = client.get(
                f"/repos/{owner}/{repo}/dependabot/alerts",
                params={"state": state, "per_page": 100, "page": page}
            )
        except HTTPError as e:
            print("Dependabot alerts not accessible:", e)
            break

        if not response:
            break

        alerts.extend(response)
        page += 1

    return alerts
