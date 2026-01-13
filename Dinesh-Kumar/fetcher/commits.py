import requests
from github_repo_analyzer.auth import Auth
import datetime

class CommitsFetcher:
    @staticmethod
    def fetch_commits(owner, repo):
        """
        Fetch the commit history of the repository (Past 90 days).
        """
        # Fetch commits from the last 90 days as requested by user
        since = (datetime.datetime.now() - datetime.timedelta(days=90)).isoformat()
        url = f"https://api.github.com/repos/{owner}/{repo}/commits?since={since}"
        
        headers = {"Authorization": f"token {Auth.get_github_token()}"}
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            print(f"Failed to fetch commits: {response.status_code}, {response.text}")
            return {"LOC added": 0, "LOC deleted": 0, "Net LOC growth": 0, "num_commits": 0}
            
        data = response.json()

        # Fetch commit diffs and analyze LOC changes
        loc_added = 0
        loc_deleted = 0
        commits_analyzed = 0

        for commit in data:
            if 'sha' in commit:
                diff_url = f"https://api.github.com/repos/{owner}/{repo}/commits/{commit['sha']}"
                diff_response = requests.get(diff_url, headers=headers)
                if diff_response.status_code == 200:
                    diff_data = diff_response.json()
                    stats = diff_data.get('stats', {'additions': 0, 'deletions': 0})
                    loc_added += stats['additions']
                    loc_deleted += stats['deletions']
                    commits_analyzed += 1
                else:
                    print(f"Error fetching diff for {commit['sha']}: {diff_response.status_code}")
        
        print(f"Calculated stats from {commits_analyzed} commits.")

        return {
            "LOC added": loc_added,
            "LOC deleted": loc_deleted,
            "Net LOC growth": loc_added - loc_deleted,
            "num_commits": commits_analyzed
        }
