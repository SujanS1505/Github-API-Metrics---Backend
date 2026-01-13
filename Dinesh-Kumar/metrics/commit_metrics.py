from metrics.base import BaseMetric

class CommitMetrics(BaseMetric):
    def calculate(self, data):
        """
        Calculate commit-related metrics.
        """
        # If data is already a dict (from CommitsFetcher), return it directly
        if isinstance(data, dict):
            return data
            
        # Fallback for raw commit lists (if used elsewhere)
        num_commits = len(data)
        loc_added = sum(commit['stats']['additions'] for commit in data if 'stats' in commit)
        loc_deleted = sum(commit['stats']['deletions'] for commit in data if 'stats' in commit)
        net_loc_growth = loc_added - loc_deleted
        return {"LOC added": loc_added, "LOC deleted": loc_deleted, "Net LOC growth": net_loc_growth, "num_commits": num_commits}
