
from app.database.connection import get_db_connection


def get_employee_attendance(employee_id: str, limit: int = 10):
    """
    Retrieve recent attendance records for an employee.
    """

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        query = """
            SELECT
                attendance_id,
                employee_id,
                attendance_date,
                check_in,
                check_out,
                working_hours,
                attendance_status
            FROM attendance
            WHERE employee_id = %s
            ORDER BY attendance_date DESC
            LIMIT %s
        """

        cursor.execute(query, (employee_id, limit))
        return cursor.fetchall()

    finally:
        cursor.close()
        connection.close()
