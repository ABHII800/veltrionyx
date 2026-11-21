
import csv
from pathlib import Path

from app.database.connection import get_db_connection

DATA_DIR = Path(__file__).resolve().parent / "data" / "sample_data"

files = [
    "departments.csv",
    "employees.csv",
    "attendance.csv",
    "leave_requests.csv"
]

print("========== CSV VALIDATION ==========")

for filename in files:
    path = DATA_DIR / filename

    with open(path, "r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        rows = list(reader)

    print(f"\nFile: {filename}")
    print("Columns:", reader.fieldnames)
    print("CSV records:", len(rows))

    if rows:
        print("First record:", rows[0])


print("\n========== MYSQL VALIDATION ==========")

connection = get_db_connection()
cursor = connection.cursor()

tables = [
    "departments",
    "employees",
    "attendance",
    "leave_requests"
]

for table in tables:
    cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
    print(f"{table}: {cursor.fetchone()[0]} records")

# Check existing attendance ID range
cursor.execute(
    "SELECT MIN(attendance_id), MAX(attendance_id) FROM attendance"
)
print("\nExisting attendance ID range:", cursor.fetchone())

cursor.close()
connection.close()

print("\nValidation completed!")
