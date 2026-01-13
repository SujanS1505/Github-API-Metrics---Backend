import requests
from config import GITHUB_TOKEN, GITHUB_API_URL


class GitHubClient:
    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json"
        }

    def get(self, endpoint, params=None):
        url = f"{GITHUB_API_URL}{endpoint}"
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()
