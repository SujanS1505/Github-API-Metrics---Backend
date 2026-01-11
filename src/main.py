import argparse
from github_client import GitHubClient

OWNER = "srikanthtn"
REPO = "Copilot"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, help="owner/repo")
    args = parser.parse_args()

    owner, repo = args.repo.split("/")
    client = GitHubClient()

    data = client.get(f"/repos/{owner}/{repo}")
    print("Repository:", data["full_name"])
    print("Stars:", data["stargazers_count"])

    rate = client.get("/rate_limit")
    print("Remaining requests:", rate["rate"]["remaining"])

if __name__ == "__main__":
    main()
