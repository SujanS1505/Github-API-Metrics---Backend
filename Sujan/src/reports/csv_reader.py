import csv


def read_csv_as_table(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.reader(f))


def read_key_value_csv(path):
    """Reads a 2-column key/value metrics CSV written by write_key_value_csv."""
    rows = read_csv_as_table(path)
    if not rows:
        return {}

    # Expected: header = [metric, value]
    data = {}
    for row in rows[1:]:
        if not row or len(row) < 2:
            continue
        key = (row[0] or "").strip()
        value = (row[1] or "").strip()
        if not key:
            continue
        data[key] = value

    return data


def read_csv_as_dicts(path):
    """Reads a CSV into a list of dictionaries using its header row."""
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return [dict(r) for r in reader]
