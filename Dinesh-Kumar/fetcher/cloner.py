import os
import shutil
import subprocess

class RepoCloner:
    @staticmethod
    def clone_repo(owner, repo, output_path, skip_if_exists=False):
        """
        Clones the repository to the specified output directory.
        Returns the absolute path to the cloned repository.
        """
        repo_url = f"https://github.com/{owner}/{repo}.git"
        # Use unique directory to avoid locks and conflicts
        clone_path = os.path.abspath(os.path.join(output_path, f"cloned_{owner}_{repo}"))

        if skip_if_exists and os.path.exists(clone_path):
            print(f"Repository already exists at {clone_path}. Skipping clone.")
            return clone_path

        # Clean up existing directory if it exists
        if os.path.exists(clone_path):
            try:
                # Handle readonly files on Windows
                def remove_readonly(func, path, _):
                    os.chmod(path, 0o777)
                    func(path)
                    
                shutil.rmtree(clone_path, onerror=remove_readonly)
            except Exception as e:
                print(f"Warning: Failed to clean up existing clone directory: {e}")

        try:
            print(f"Cloning {repo_url} into {clone_path}...")
            # Use -c core.longpaths=true to handle deep paths on Windows
            subprocess.check_call(["git", "clone", "-c", "core.longpaths=true", "--depth", "1", repo_url, clone_path])
            return clone_path
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to clone repository: {e}")
