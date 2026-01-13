from metrics.base import BaseMetric
import os

class LOCMetrics(BaseMetric):
    def calculate(self, data):
        total_loc = 0
        comment_lines = 0

        for file in data:
            ext = os.path.splitext(file['path'])[1].lower()
            name = os.path.basename(file['path'])
            
            if ext in ('.py', '.java', '.js', '.cpp', '.c', '.rb', '.go', '.html', '.css', '.md', '.sh', '.yaml', '.yml', '.json', '.proto', '.mod', '.bazel', '.scala', '.sbt') or name in ('Dockerfile', 'Makefile'):
                try:
                    # Robust reading with errors='ignore'
                    with open(file['path'], 'r', encoding='utf-8', errors='ignore') as f:
                        for line in f:
                            total_loc += 1
                            if line.strip().startswith('#') or line.strip().startswith('//'):
                                comment_lines += 1
                except Exception as e:
                    # Silent ignore or debug print
                    # print(f"Error reading file {file['path']}: {e}")
                    pass

        comment_to_code_ratio = comment_lines / total_loc if total_loc > 0 else 0
        return {"total_loc": total_loc, "comment_to_code_ratio": comment_to_code_ratio}
