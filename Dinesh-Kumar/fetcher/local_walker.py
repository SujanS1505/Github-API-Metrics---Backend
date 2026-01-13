import os

class LocalFileWalker:
    @staticmethod
    def walk_tree(root_path):
        """
        Walk the local file system and return a list of files with paths relative to the root.
        """
        file_list = []
        for root, dirs, files in os.walk(root_path):
            # Skip .git directory
            if '.git' in dirs:
                dirs.remove('.git')
            
            for file in files:
                full_path = os.path.join(root, file)
                # Keep full absolute path for easier reading later
                # But for 'path' relative might be needed?
                # Actually previously we used absolute path in 'path' for local reading.
                # The 'path' key should be absolute for open() calls to work.
                
                file_list.append({
                    'path': full_path,
                    'size': os.path.getsize(full_path)
                })
        return file_list
