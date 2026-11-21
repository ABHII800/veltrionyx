
from app.database.connection import get_db_connection


def get_employee_leave_requests(employee_id: str):
    """
    Retrieve all leave requests for an employee.
    """

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        query = """
            SELECT
                leave_id,
                employee_id,
                leave_type,
                start_date,
                end_date,
                leave_days,
                leave_status,
                reason
            FROM leave_requests
            WHERE employee_id = %s
            ORDER BY start_date DESC
        """

        cursor.execute(query, (employee_id,))
        return cursor.fetchall()

    finally:
        cursor.close()
        connection.close()
