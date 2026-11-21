
from app.database.connection import get_db_connection

connection = get_db_connection()
cursor = connection.cursor()

print("========== FOREIGN KEY RELATIONSHIPS ==========")

cursor.execute("""
    SELECT
        TABLE_NAME,
        COLUMN_NAME,
        REFERENCED_TABLE_NAME,
        REFERENCED_COLUMN_NAME
    FROM information_schema.KEY_COLUMN_USAGE
    WHERE TABLE_SCHEMA = DATABASE()
      AND REFERENCED_TABLE_NAME IS NOT NULL
""")

relationships = cursor.fetchall()

if relationships:
    for relationship in relationships:
        print(relationship)
else:
    print("No foreign key relationships found.")

print("\n========== EXISTING ATTENDANCE DATA ==========")

cursor.execute("""
    SELECT employee_id, COUNT(*)
    FROM attendance
    GROUP BY employee_id
    ORDER BY employee_id
    LIMIT 15
""")

for row in cursor.fetchall():
    print(row)

print("\n========== EMPLOYEE MATCH CHECK ==========")

cursor.execute("""
    SELECT COUNT(*)
    FROM attendance a
    LEFT JOIN employees e
        ON a.employee_id = e.employee_id
    WHERE e.employee_id IS NULL
""")

print("Attendance records without matching employees:", cursor.fetchone()[0])

cursor.close()
connection.close()

print("\nInspection completed!")
