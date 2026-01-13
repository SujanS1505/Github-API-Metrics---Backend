from metrics.base import BaseMetric
import os
from collections import Counter

class LanguageMetrics(BaseMetric):
    def calculate(self, data):
        language_distribution = {}
        total_files = len(data)

        # Extended mapping
        ext_map = {
            '.py': 'Python', '.java': 'Java', '.js': 'JavaScript', '.ts': 'TypeScript',
            '.cpp': 'C++', '.c': 'C', '.h': 'C/C++', '.hpp': 'C++',
            '.rb': 'Ruby', '.go': 'Go', '.rs': 'Rust', '.php': 'PHP',
            '.html': 'HTML', '.css': 'CSS', '.scss': 'SCSS',
            '.md': 'Markdown', '.sh': 'Shell', '.bash': 'Shell',
            '.yaml': 'YAML', '.yml': 'YAML', '.json': 'JSON', '.xml': 'XML',
            '.sql': 'SQL', '.dockerfile': 'Dockerfile', '.make': 'Makefile',
            '.proto': 'Protobuf', '.pb': 'Protobuf',
            '.mod': 'Go Modules', '.sum': 'Go Sum',
            '.txt': 'Text', '.bazel': 'Bazel',
            '.scala': 'Scala', '.sbt': 'SBT'
        }

        lang_counts = Counter()

        for file in data:
            ext = os.path.splitext(file['path'])[1].lower()
            name = os.path.basename(file['path'])
            
            lang = 'Unknown'
            if name == 'Dockerfile': lang = 'Dockerfile'
            elif name == 'Makefile': lang = 'Makefile'
            elif ext in ext_map:
                lang = ext_map[ext]
            
            lang_counts[lang] += 1
            
        # Convert to normal dict
        language_distribution = dict(lang_counts)

        language_percentage = {
            lang: (count / total_files) * 100 
            for lang, count in language_distribution.items()
        }

        return {
            "language_distribution": language_distribution,
            "language_percentage": language_percentage
        }
