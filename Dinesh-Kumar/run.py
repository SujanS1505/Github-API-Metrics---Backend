import sys
import os

# Ensure the current directory is in the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from config import Config
from fetcher.cloner import RepoCloner
from fetcher.commits import CommitsFetcher
from fetcher.local_walker import LocalFileWalker
from analyzer import Analyzer
from exporters.csv_exporter import CSVExporter
from exporters.pdf_exporter import PDFExporter

import argparse
import datetime

if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description="GitHub Repository Analyzer")
    parser.add_argument("repo", nargs="?", help="Repository in format 'owner/repo' (e.g. kubernetes/kubernetes) or full HTTPS URL")
    args = parser.parse_args()

    # Determine owner and repo
    if args.repo:
        input_repo = args.repo.strip()
        # Check if it is a full URL
        if input_repo.startswith("https://github.com/"):
            clean_url = input_repo.replace(".git", "")
            parts = clean_url.split('/')
            try:
                owner = parts[-2]
                repo = parts[-1]
            except IndexError:
                print("Error: Invalid GitHub URL format.")
                sys.exit(1)
        else:
            try:
                owner, repo = input_repo.split('/')
            except ValueError:
                print("Error: Invalid format. Please use 'owner/repo' or a full GitHub URL.")
                sys.exit(1)
    else:
        # Fallback to config
        owner, repo = Config.get_owner_repo() if hasattr(Config, 'get_owner_repo') else ("kubernetes", "kubernetes")
        print(f"No repository argument provided. Using default: {owner}/{repo}")

    output_dir = Config.get_output_dir()
    
    # Generate timestamp for unique filenames
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_repo_name = f"{owner}_{repo}"
    
    csv_filename = f"{safe_repo_name}_metrics_{timestamp}.csv"
    pdf_filename = f"{safe_repo_name}_report_{timestamp}.pdf"
    csv_path = os.path.join(output_dir, csv_filename)
    pdf_path = os.path.join(output_dir, pdf_filename)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    print(f"Starting analysis for {owner}/{repo}...")

    # Clone the repository
    try:
        # Clone repo (skip if exists for speed)
        cloned_path = RepoCloner.clone_repo(owner, repo, output_dir, skip_if_exists=True)
    except Exception as e:
        print(f"Error cloning repository: {e}")
        sys.exit(1)

    # Walk local files
    print("Walking local file tree...")
    tree = LocalFileWalker.walk_tree(cloned_path)
    files = tree 

    # Fetch Commits
    try:
        commits = CommitsFetcher.fetch_commits(owner, repo)
    except Exception as e:
        print(f"Error fetching commits from API: {e}")
        commits = {"LOC added": 0, "LOC deleted": 0, "Net LOC growth": 0, "num_commits": 0}

    print(f"Analyzed {len(files)} files.")

    # Analyze data
    analyzer = Analyzer()
    metrics = analyzer.analyze({"tree": tree, "files": files, "commits": commits})

    # Export results
    print(f"Exporting results to {output_dir}...")
    CSVExporter.export(metrics, csv_path)
    PDFExporter.export(metrics, pdf_path, f"{owner}/{repo}")
