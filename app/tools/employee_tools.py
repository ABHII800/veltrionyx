
from app.database.connection import get_db_connection


def get_employee_details(employee_id: str):
    """
    Retrieve employee details using their employee ID.
    """

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        query = """
            SELECT
                e.employee_id,
                e.first_name,
                e.last_name,
                e.email,
                e.gender,
                e.designation,
                e.joining_date,
                e.employment_status,
                d.department_name
            FROM employees e
            LEFT JOIN departments d
                ON e.department_id = d.department_id
            WHERE e.employee_id = %s
        """

        cursor.execute(query, (employee_id,))
        employee = cursor.fetchone()

        return employee

    finally:
        cursor.close()
        connection.close()
