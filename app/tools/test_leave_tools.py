
from app.tools.leave_tools import get_employee_leave_requests

employee_id = "EMP001"

requests = get_employee_leave_requests(employee_id)

if requests:
    print(f"\nLeave Requests for {employee_id}")
    print("--------------------------------")

    for request in requests:
        print(request)

else:
    print("No leave requests found.")
