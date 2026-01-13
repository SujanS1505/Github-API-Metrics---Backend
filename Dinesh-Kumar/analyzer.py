from metrics.loc_metrics import LOCMetrics
from metrics.file_metrics import FileMetrics
from metrics.language_metrics import LanguageMetrics
from metrics.commit_metrics import CommitMetrics
from metrics.quality_metrics import QualityMetrics

class Analyzer:
    def __init__(self):
        self.metrics = [
            LOCMetrics(),
            FileMetrics(),
            LanguageMetrics(),
            CommitMetrics(),
            QualityMetrics()
        ]

    def analyze(self, data):
        """
        Run all metrics calculations.
        """
        results = {}
        for metric in self.metrics:
            if isinstance(metric, LOCMetrics):
                results.update(metric.calculate(data['tree']))
            elif isinstance(metric, FileMetrics):
                results.update(metric.calculate(data['files']))
            elif isinstance(metric, LanguageMetrics):
                results.update(metric.calculate(data['files']))
            elif isinstance(metric, CommitMetrics):
                results.update(metric.calculate(data['commits']))
            elif isinstance(metric, QualityMetrics):
                results.update(metric.calculate(data['files']))
        return results
