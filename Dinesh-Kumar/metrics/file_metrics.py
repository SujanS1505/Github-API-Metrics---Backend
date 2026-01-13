from metrics.base import BaseMetric
import os

class FileMetrics(BaseMetric):
    def calculate(self, data):
        """
        Calculate file metrics.
        """
        num_files = len(data)
        total_size = sum(file['size'] for file in data)
        avg_file_size = total_size / num_files if num_files > 0 else 0
        largest_file_size = max((file['size'] for file in data), default=0)

        return {
            "num_files": num_files,
            "avg_file_size": avg_file_size,
            "largest_file_size": largest_file_size
        }
