
import csv
import random
from pathlib import Path
from datetime import date, timedelta

random.seed(42)

DATA_DIR = Path(__file__).resolve().parent / "data" / "sample_data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def save_csv(filename, rows):
    path = DATA_DIR / filename
    with open(path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"Created {filename}: {len(rows)} records")


# 1. Departments
departments = [
    {"department_id": 1, "department_name": "Engineering", "department_head": "Rahul Sharma"},
    {"department_id": 2, "department_name": "Human Resources", "department_head": "Priya Reddy"},
    {"department_id": 3, "department_name": "Finance", "department_head": "Amit Kumar"},
    {"department_id": 4, "department_name": "Marketing", "department_head": "Sneha Rao"},
    {"department_id": 5, "department_name": "Operations", "department_head": "Vikram Singh"},
]

# 2. Employees
first_names = ["Aarav", "Ananya", "Arjun", "Diya", "Ishaan",
               "Kavya", "Rohan", "Meera", "Aditya", "Nisha"]
last_names = ["Sharma", "Reddy", "Kumar", "Rao", "Singh"]

employees = []

for i in range(1, 51):
    first = first_names[(i - 1) % len(first_names)]
    last = last_names[(i - 1) % len(last_names)]
    dept_id = ((i - 1) % 5) + 1

    employees.append({
        "employee_id": f"EMP{i:03}",
        "first_name": first,
        "last_name": f"{last}{i}",
        "gender": "Male" if i % 2 else "Female",
        "email": f"employee{i}@veltrionyx.demo",
        "department_id": dept_id,
        "designation": "Software Engineer" if dept_id == 1 else "Associate",
        "joining_date": (date(2024, 1, 1) + timedelta(days=i * 10)).isoformat(),
        "employment_status": "Active"
    })

# 3. Attendance - 1000 records
attendance = []
start_date = date(2026, 10, 1)
attendance_id = 1
day = start_date

while len(attendance) < 1000:
    if day.weekday() < 5:
        for emp in employees:
            if len(attendance) >= 1000:
                break

            check_in_hour = random.choice([8, 8, 9, 9, 9, 10])
            check_in_minute = random.randint(0, 59)
            check_out_hour = random.choice([17, 18, 18, 19])

            check_in = f"{check_in_hour:02}:{check_in_minute:02}:00"
            check_out = f"{check_out_hour:02}:{random.randint(0, 59):02}:00"

            working_hours = round(
                check_out_hour - check_in_hour
                - check_in_minute / 60
                + random.uniform(-0.2, 0.2), 2
            )

            attendance.append({
                "attendance_id": attendance_id,
                "employee_id": emp["employee_id"],
                "attendance_date": day.isoformat(),
                "check_in": check_in,
                "check_out": check_out,
                "working_hours": max(0, working_hours),
                "attendance_status": "Late" if check_in > "09:15:00" else "Present"
            })
            attendance_id += 1

    day += timedelta(days=1)

# 4. Leave requests - 100 records
leave_requests = []

for i in range(1, 101):
    emp = employees[(i - 1) % len(employees)]
    start = date(2026, 10, 1) + timedelta(days=(i - 1) % 25)
    days = random.randint(1, 3)

    leave_requests.append({
        "leave_id": f"LEV{i:03}",
        "employee_id": emp["employee_id"],
        "leave_type": random.choice(["Casual", "Sick", "Earned"]),
        "start_date": start.isoformat(),
        "end_date": (start + timedelta(days=days - 1)).isoformat(),
        "leave_days": days,
        "leave_status": random.choice(["Approved", "Pending", "Rejected"]),
        "reason": "Personal reasons"
    })


save_csv("departments.csv", departments)
save_csv("employees.csv", employees)
save_csv("attendance.csv", attendance)
save_csv("leave_requests.csv", leave_requests)

print("\nAll synthetic datasets generated successfully!")
