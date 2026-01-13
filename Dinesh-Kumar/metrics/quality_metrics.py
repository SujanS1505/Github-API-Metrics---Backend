from metrics.base import BaseMetric
import hashlib

class QualityMetrics(BaseMetric):
    def calculate(self, data):
        """
        Calculate code quality metrics.
        """
        duplicates = 0
        hashes = set()

        for file in data:
            # Check for duplicates in source code files only
            if file['path'].endswith(('.py', '.java', '.js', '.cpp', '.c', '.rb', '.go', '.scala')):
                try:
                    with open(file['path'], 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        # Use hash to save memory
                        file_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
                        if file_hash in hashes:
                            duplicates += 1
                        hashes.add(file_hash)
                except Exception:
                    pass

        duplicate_code_percentage = (duplicates / len(data)) * 100 if len(data) > 0 else 0

        # Expanded definitions
        binary_files_count = sum(1 for file in data if file['path'].endswith(('.exe', '.dll', '.bin', '.o', '.so', '.dylib', '.class', '.jar', '.pyc', '.zip', '.tar.gz', '.png', '.jpg', '.jpeg', '.gif', '.pdf', '.iso')))
        generated_files_count = sum(1 for file in data if file['path'].endswith(('.gen', '.generated', '.min.js', '.min.css', '.map', '.log')))
        config_files_count = sum(1 for file in data if file['path'].endswith(('.json', '.yaml', '.yml', '.ini', '.toml', '.conf')))

        # Heuristic for tests
        test_files = sum(1 for file in data if 'test' in file['path'].lower())
        production_files = len(data) - test_files
        test_to_production_ratio = test_files / production_files if production_files > 0 else 0

        return {
            "test_to_production_ratio": test_to_production_ratio,
            "duplicate_code_percentage": duplicate_code_percentage,
            "binary_files_count": binary_files_count,
            "generated_files_count": generated_files_count,
            "config_files_count": config_files_count
        }
