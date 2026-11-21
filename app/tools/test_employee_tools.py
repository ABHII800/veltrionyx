
from app.tools.employee_tools import get_employee_details

employee_id = "EMP001"

result = get_employee_details(employee_id)

if result:
    print("\nEmployee Details")
    print("------------------------")

    for key, value in result.items():
        print(f"{key}: {value}")

else:
    print("Employee not found.")
