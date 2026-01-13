import csv

def read_csv_as_table(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.reader(f))
