import csv
import os

class CSVExporter:
    @staticmethod
    def export(data, output_path):
        """
        Export metrics to a CSV file.
        """
        try:
            # Check if file is writable (not locked)
            if os.path.exists(output_path):
                try:
                    with open(output_path, 'a'): pass
                except PermissionError:
                    print(f"Error: CSV file {output_path} is open/locked. Skipping CSV export.")
                    return

            with open(output_path, mode='w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(["Metric", "Value"])
                for key, value in data.items():
                    writer.writerow([key, value])
            print(f"Data successfully written to {output_path}")
        except Exception as e:
             print(f"Failed to write CSV: {e}")
