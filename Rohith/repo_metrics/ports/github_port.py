from __future__ import annotations

from typing import Any, Dict, Iterator, Optional, Protocol


class GitHubPort(Protocol):
    """Port used by domain metrics to talk to GitHub.

    This keeps the domain layer independent of a specific GitHub client
    implementation (REST/GraphQL library, retries, etc.).
    """

    owner: str
    repo: str

    def graphql(self, query: str, variables: Dict[str, Any]) -> Dict[str, Any]:
        ...

    def rest_get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        ...

    def rest_get_paginated(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        per_page: int = 100,
        page_start: int = 1,
        page_limit: Optional[int] = None,
    ) -> Iterator[Any]:
        ...
