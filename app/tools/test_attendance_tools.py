
from app.tools.attendance_tools import get_employee_attendance

employee_id = "EMP001"

records = get_employee_attendance(employee_id)

if records:
    print(f"\nAttendance Records for {employee_id}")
    print("--------------------------------")

    for record in records:
        print(record)

else:
    print("No attendance records found.")
