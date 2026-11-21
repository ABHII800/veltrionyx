
from app.tools.department_tools import get_department_details

result = get_department_details("Engineering")

if result:
    print("\nDepartment Details")
    print("------------------------")

    for key, value in result.items():
        print(f"{key}: {value}")

else:
    print("Department not found.")
