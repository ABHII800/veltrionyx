
import csv
from pathlib import Path

DATA_PATH = Path("data/sample_data")

for file_path in DATA_PATH.glob("*.csv"):
    print("\n" + "=" * 50)
    print("FILE:", file_path.name)

    with open(file_path, "r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        print("COLUMNS:", reader.fieldnames)

        rows = list(reader)
        print("TOTAL ROWS:", len(rows))

        if rows:
            print("FIRST ROW:", rows[0])
