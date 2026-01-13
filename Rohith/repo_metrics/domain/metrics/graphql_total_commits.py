from __future__ import annotations

from ...adapters.github.github_client import default_client

TOTAL_COMMIT_QUERY = """
query ($owner: String!, $repo: String!, $cursor: String) {
  repository(owner: $owner, name: $repo) {
    defaultBranchRef {
      target {
        ... on Commit {
          history(first: 100, after: $cursor) {
            edges {
              node { oid }
            }
            pageInfo {
              hasNextPage
              endCursor
            }
          }
        }
      }
    }
  }
}
"""


def get_exact_total_commits() -> int:
    """Return exact total commits on the default branch (GraphQL history pagination)."""

    client = default_client()

    cursor = None
    total = 0

    while True:
        payload = client.graphql(
            TOTAL_COMMIT_QUERY,
            {
                "owner": client.owner,
                "repo": client.repo,
                "cursor": cursor,
            },
        )

        history = payload["data"]["repository"]["defaultBranchRef"]["target"]["history"]

        total += len(history["edges"])

        if not history["pageInfo"]["hasNextPage"]:
            break

        cursor = history["pageInfo"]["endCursor"]

    return total
