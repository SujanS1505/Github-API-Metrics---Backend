def fetch_repo_metadata(client, owner, repo):
    data = client.get(f"/repos/{owner}/{repo}")

    return {
        "full_name": data["full_name"],
        "description": data.get("description", "N/A"),
        "language": data.get("language", "N/A"),
        "stars": data["stargazers_count"],
        "forks": data["forks_count"],
        "open_issues": data["open_issues_count"],
        "default_branch": data["default_branch"],
        "created_at": data["created_at"][:10],
        "updated_at": data["updated_at"][:10],
        "license": data["license"]["name"] if data["license"] else "N/A",
        "visibility": data["visibility"],
        "archived": data["archived"]
    }
