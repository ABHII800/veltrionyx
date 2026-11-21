
from app.database.connection import get_db_connection


def get_department_details(department_name: str):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        query = """
            SELECT
                d.department_id,
                d.department_name,
                d.department_head,
                COUNT(e.employee_id) AS total_employees
            FROM departments d
            LEFT JOIN employees e
                ON d.department_id = e.department_id
            WHERE d.department_name = %s
            GROUP BY
                d.department_id,
                d.department_name,
                d.department_head
        """

        cursor.execute(query, (department_name,))
        return cursor.fetchone()

    finally:
        cursor.close()
        connection.close()

def get_all_department_details():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        query = """
            SELECT
                d.department_name,
                d.department_head,
                COUNT(e.employee_id) AS total_employees
            FROM departments d
            LEFT JOIN employees e
                ON d.department_id = e.department_id
            GROUP BY
                d.department_id,
                d.department_name,
                d.department_head
            ORDER BY d.department_name
        """

        cursor.execute(query)
        return cursor.fetchall()

    finally:
        cursor.close()
        connection.close()