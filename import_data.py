
import csv
from pathlib import Path
from app.database.connection import get_db_connection

DATA_DIR = Path(__file__).resolve().parent / "data" / "sample_data"


def import_leave_requests():
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        file_path = DATA_DIR / "leave_requests.csv"

        with open(file_path, "r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)

            query = """
                INSERT INTO leave_requests (
                    leave_id, employee_id, leave_type,
                    start_date, end_date, leave_days,
                    leave_status, reason
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """

            rows = [
                (
                    row["leave_id"],
                    row["employee_id"],
                    row["leave_type"],
                    row["start_date"],
                    row["end_date"],
                    int(row["leave_days"]),
                    row["leave_status"],
                    row["reason"]
                )
                for row in reader
            ]

        cursor.executemany(query, rows)
        connection.commit()

        print(f"Successfully imported {cursor.rowcount} leave requests!")

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    import_leave_requests()
