
from app.database.connection import get_db_connection

try:
    connection = get_db_connection()

    print("MySQL connected successfully!")
    print("Database:", connection.database)

    cursor = connection.cursor()

    tables = [
        "departments",
        "employees",
        "attendance",
        "leave_requests"
    ]

    print("\nDatabase table counts:")

    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
        count = cursor.fetchone()[0]
        print(f"{table}: {count} records")

    cursor.close()
    connection.close()

except Exception as error:
    print("MySQL connection failed:", error)
