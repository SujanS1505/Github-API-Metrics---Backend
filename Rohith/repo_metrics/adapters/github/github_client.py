from __future__ import annotations

from dataclasses import dataclass
import random
import time
from typing import Any, Dict, Iterator, Optional

import requests
from requests import Response
from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import Timeout as RequestsTimeout

import config


@dataclass(frozen=True)
class GitHubClient:
    """Small helper around GitHub REST + GraphQL with sane defaults."""

    owner: str
    repo: str
    token: str

    base_url: str = "https://api.github.com"
    graphql_url: str = "https://api.github.com/graphql"

    max_retries: int = 5
    backoff_seconds: float = 1.0

    def __post_init__(self) -> None:
        if not (self.owner and self.repo and self.token):
            raise ValueError("owner, repo, and token are required")

    @property
    def rest_headers(self) -> Dict[str, str]:
        return {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.token}",
        }

    @property
    def graphql_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def graphql(self, query: str, variables: Dict[str, Any]) -> Dict[str, Any]:
        resp = self._request_with_retries(
            method="POST",
            url=self.graphql_url,
            headers=self.graphql_headers,
            json={"query": query, "variables": variables},
            timeout=60,
        )
        payload = resp.json()
        if payload.get("errors"):
            raise RuntimeError(f"GraphQL errors: {payload['errors']}")
        return payload

    def rest_get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        resp = self._request_with_retries(
            method="GET",
            url=f"{self.base_url}{path}",
            headers=self.rest_headers,
            params=params or {},
            timeout=60,
        )
        return resp.json()

    def _request_with_retries(
        self,
        *,
        method: str,
        url: str,
        headers: Dict[str, str],
        timeout: int,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
    ) -> Response:
        last_exc: Optional[BaseException] = None

        for attempt in range(1, self.max_retries + 1):
            try:
                resp = requests.request(
                    method,
                    url,
                    headers=headers,
                    params=params,
                    json=json,
                    timeout=timeout,
                )

                if resp.status_code in (429, 500, 502, 503, 504):
                    if attempt >= self.max_retries:
                        resp.raise_for_status()

                    retry_after = resp.headers.get("Retry-After")
                    if retry_after and retry_after.isdigit():
                        sleep_seconds = float(retry_after)
                    else:
                        sleep_seconds = (self.backoff_seconds * (2 ** (attempt - 1))) + random.uniform(
                            0.0, 0.25
                        )

                    time.sleep(sleep_seconds)
                    continue

                resp.raise_for_status()
                return resp
            except (RequestsConnectionError, RequestsTimeout) as exc:
                last_exc = exc
                if attempt >= self.max_retries:
                    raise

                sleep_seconds = (self.backoff_seconds * (2 ** (attempt - 1))) + random.uniform(
                    0.0, 0.25
                )
                time.sleep(sleep_seconds)

        if last_exc:
            raise last_exc

        raise RuntimeError("Request failed unexpectedly")

    def rest_get_paginated(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        per_page: int = 100,
        page_start: int = 1,
        page_limit: Optional[int] = None,
    ) -> Iterator[Any]:
        page = page_start
        while True:
            if page_limit is not None and page > page_limit:
                return

            merged = {**(params or {}), "per_page": per_page, "page": page}
            data = self.rest_get(path, params=merged)
            if not data:
                return

            for item in data:
                yield item

            page += 1


def default_client() -> GitHubClient:
    token = (config.GITHUB_TOKEN or "").strip()
    owner = (config.OWNER or "").strip()
    repo = (config.REPO or "").strip()

    if not token or token == "<PASTE_GITHUB_TOKEN_HERE>":
        raise RuntimeError(
            "Set GITHUB_TOKEN in config.py to a valid GitHub token before running."
        )
    if not owner or not repo:
        raise RuntimeError("Set OWNER and REPO in config.py before running.")

    return GitHubClient(owner=config.OWNER, repo=config.REPO, token=config.GITHUB_TOKEN)
