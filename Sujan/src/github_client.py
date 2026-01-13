import time

import requests
from requests.exceptions import ConnectionError, Timeout

from config import GITHUB_API_URL, GITHUB_TOKEN


class GitHubClient:
    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "github-api-metrics-backend",
        }

        self._session = requests.Session()

    def get(self, endpoint, params=None, timeout=30, max_retries=3):
        url = f"{GITHUB_API_URL}{endpoint}"

        last_error = None
        for attempt in range(max_retries):
            try:
                response = self._session.get(
                    url,
                    headers=self.headers,
                    params=params,
                    timeout=timeout,
                )

                # Handle rate limiting gracefully.
                if response.status_code == 403 and response.headers.get("X-RateLimit-Remaining") == "0":
                    reset = response.headers.get("X-RateLimit-Reset")
                    if reset and reset.isdigit():
                        sleep_seconds = max(0, int(reset) - int(time.time()) + 1)
                        time.sleep(min(sleep_seconds, 60))
                        continue

                response.raise_for_status()
                return response.json()
            except (Timeout, ConnectionError) as e:
                last_error = e
                time.sleep(0.5 * (2**attempt))

        raise last_error
