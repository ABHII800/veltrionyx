import datetime
import decimal
import difflib
import re
from collections import Counter
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import TypedDict

from langgraph.graph import StateGraph, START, END

try:
    # Lets a node send text to the chat while it is still being written.
    from langgraph.config import get_stream_writer
    STREAMING_SUPPORTED = True
except ImportError:
    # Older LangGraph: answers still work, they just appear all at once.
    STREAMING_SUPPORTED = False

    def get_stream_writer():
        return lambda chunk: None

from app.rag.answer import stream_answer

from app.tools.employee_tools import get_employee_details
from app.tools.department_tools import (
    get_department_details,
    get_all_department_details
)
from app.tools.attendance_tools import get_employee_attendance
from app.tools.leave_tools import get_employee_leave_requests

# --------------------------------------------------
# 1. ASSISTANT STATE
# --------------------------------------------------

class AssistantState(TypedDict):
    question: str
    route: str
    employee_id: str
    department_name: str
    answer: str

# --------------------------------------------------
# 2. QUESTION CLASSIFICATION
# Rule-based routing: no Groq classification call
# --------------------------------------------------

# Words the router depends on. A misspelled word that is very close
# to one of these ("engeering", "employes") is corrected first.
ROUTING_WORDS = [
    "engineering",
    "marketing",
    "finance",
    "operations",
    "resources",
    "employees",
    "employee",
    "department",
    "departments",
    "attendance"
]

# Questions that sound like "what does the policy say" go to the
# company documents, even if they mention a department or leave.
POLICY_PATTERN = re.compile(
    r"\b(?:policy|policies|rules?|procedures?|process|guidelines?"
    r"|how do i|how to|how can i|eligib\w*|entitle\w*|allowed"
    r"|notice period|per year|per month)\b"
)

# With an employee ID in the question, these single words decide
# between the attendance table and the leave table.
ATTENDANCE_WORDS = re.compile(
    r"\b(?:late|absent|present|attendance|check[- ]?in|check[- ]?out"
    r"|working hours)\b"
)

LEAVE_WORDS = re.compile(
    r"\b(?:leave|leaves)\b"
)

def correct_typos(question: str) -> str:

    def fix(match):

        word = match.group(0)

        close = difflib.get_close_matches(
            word,
            ROUTING_WORDS,
            n=1,
            cutoff=0.8
        )

        return close[0] if close else word

    return re.sub(r"[a-z]{5,}", fix, question)

def classify_question(state: AssistantState):

    question = correct_typos(
        state["question"].strip().lower()
    )

    employee_match = re.search(
        r"\bemp\d+\b",
        question,
        re.IGNORECASE
    )

    employee_id = (
        employee_match.group(0).upper()
        if employee_match else ""
    )

    departments = {
        "engineering": "Engineering",
        "human resources": "Human Resources",
        "hr": "Human Resources",
        "finance": "Finance",
        "marketing": "Marketing",
        "operations": "Operations"
    }

    department_name = ""

    for keyword, department in departments.items():

        if re.search(
            r"\b" + re.escape(keyword) + r"\b",
            question
        ):

            department_name = department
            break

    attendance_keywords = [
        "attendance",
        "check in",
        "check-in",
        "check out",
        "check-out",
        "present days",
        "absent days",
        "working hours",
        "late arrival"
    ]

    leave_keywords = [
        "leave request",
        "leave requests",
        "leave application",
        "leave applications",
        "leave history",
        "leave status",
        "leave approval",
        "leave approvals",
        "pending leave",
        "approved leave",
        "rejected leave",
        "sick leave request",
        "casual leave request",
        "earned leave request"
    ]

    department_keywords = [
        "department",
        "departments",
        "department head",
        "department manager",
        "employees in",
        "employee count",
        "employee distribution",
        "all departments",
        "each department",
        "every department",
        "total employees"
    ]

    if employee_id and (
        any(
            keyword in question
            for keyword in attendance_keywords
        )
        or ATTENDANCE_WORDS.search(question)
    ):

        route = "ATTENDANCE"

    elif employee_id and (
        any(
            keyword in question
            for keyword in leave_keywords
        )
        or LEAVE_WORDS.search(question)
    ):

        route = "LEAVE"

    elif employee_id:

        route = "EMPLOYEE"

    elif POLICY_PATTERN.search(question):

        route = "POLICY"

    elif (
        any(
            keyword in question
            for keyword in department_keywords
        )
        or department_name
    ):

        route = "DEPARTMENT"

    elif any(
        keyword in question
        for keyword in leave_keywords
    ):

        route = "LEAVE"

    elif re.search(
        r"\b(?:my|his|her|their)\s+(?:attendance|check[- ]?ins?)\b"
        r"|\battendance\s+(?:of|for|records?|history|summary)\b",
        question
    ):

        # About a person's records, but no ID given: ask for the ID.
        route = "ATTENDANCE"

    elif re.search(
        r"\b(?:my|his|her|their)\s+leaves?\b",
        question
    ):

        route = "LEAVE"

    else:

        route = "POLICY"

    print(f"\nQuestion category: {route}")

    return {
        "question": question,
        "route": route,
        "employee_id": employee_id,
        "department_name": department_name
    }

# --------------------------------------------------
# 3. FORMAT DATABASE RESULTS
# No additional Groq call.
# Results are shown as tables in the chat.
# --------------------------------------------------

# Coloured dots match the bars on the dashboard.
STATUS_ICONS = {
    "present": "🟢",
    "approved": "🟢",
    "active": "🟢",
    "late": "🟠",
    "pending": "🟠",
    "absent": "🔴",
    "rejected": "🔴"
}

# Which columns to show, in which order, for lists of records.
# Internal IDs (attendance_id, leave_id) are left out on purpose.
TABLE_COLUMNS = {
    "attendance": [
        ("attendance_date", "Date"),
        ("check_in", "Check-in"),
        ("check_out", "Check-out"),
        ("working_hours", "Hours"),
        ("attendance_status", "Status")
    ],
    "leave": [
        ("leave_type", "Type"),
        ("start_date", "From"),
        ("end_date", "To"),
        ("leave_days", "Days"),
        ("leave_status", "Status"),
        ("reason", "Reason")
    ],
    "departments": [
        ("department_name", "Department"),
        ("department_head", "Head"),
        ("total_employees", "Employees")
    ]
}

# Which rows to show for a single record (Field | Details).
DETAIL_FIELDS = {
    "employee": [
        ("employee_id", "Employee ID"),
        ("name", "Name"),
        ("designation", "Designation"),
        ("department_name", "Department"),
        ("email", "Email"),
        ("gender", "Gender"),
        ("joining_date", "Joined"),
        ("employment_status", "Status")
    ],
    "department": [
        ("department_name", "Department"),
        ("department_head", "Head"),
        ("total_employees", "Employees")
    ]
}

# Column used for the "🟢 6 Present · 🟠 4 Late" summary line.
STATUS_COLUMN = {
    "attendance": "attendance_status",
    "leave": "leave_status"
}

def plural(count: int, word: str) -> str:

    return f"{count} {word}" + ("" if count == 1 else "s")

def format_value(key: str, value) -> str:
    """Turn a database value into short, readable text."""

    if value is None or value == "":
        return "—"

    # datetime must be checked before date (it is a kind of date).
    if isinstance(value, datetime):
        return value.strftime("%d %b %Y, %H:%M")

    if isinstance(value, date):
        return value.strftime("%d %b %Y")

    if isinstance(value, time):
        return value.strftime("%H:%M")

    # MySQL TIME columns come back from Python as timedelta.
    if isinstance(value, timedelta):
        minutes = int(value.total_seconds() // 60)
        return f"{minutes // 60:02d}:{minutes % 60:02d}"

    # Working hours always show two decimals (9.30, not 9.3) so the
    # column lines up. Other numbers drop useless trailing zeros.
    if isinstance(value, (Decimal, float)):

        if key == "working_hours":
            return f"{value:.2f}"

        return f"{value:.2f}".rstrip("0").rstrip(".")

    # One line of text; a "|" would break the table, so it is escaped.
    text = " ".join(str(value).split()).replace("|", "\\|")

    icon = STATUS_ICONS.get(text.lower())

    if icon and key.endswith("status"):
        text = f"{icon} {text}"

    return text

def markdown_table(headers: list, rows: list) -> str:

    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |"
    ]

    for row in rows:
        lines.append("| " + " | ".join(row) + " |")

    return "\n".join(lines)

def status_summary(rows: list, key: str) -> str:

    counts = Counter(
        str(row.get(key) or "").strip()
        for row in rows
    )

    counts.pop("", None)

    parts = []

    for status, count in counts.most_common():

        icon = STATUS_ICONS.get(status.lower(), "")

        parts.append(f"{icon} {count} {status}".strip())

    return " · ".join(parts)

def format_database_answer(
    question: str,
    data,
    kind: str = None,
    title: str = None,
    subtitle: str = None,
    empty_message: str = None
) -> str:

    if not data:

        return empty_message or (
            "I couldn't find matching information "
            "in the company database."
        )

    parts = []

    if title:
        parts.append(f"**{title}**")

    # ---------- one record: Field | Details ----------

    if isinstance(data, dict):

        record = dict(data)

        if kind == "employee":

            record["name"] = " ".join(
                str(record[key])
                for key in ("first_name", "last_name")
                if record.get(key)
            )

        fields = DETAIL_FIELDS.get(kind) or [
            (key, key.replace("_", " ").title())
            for key in record
        ]

        rows = [
            [label, format_value(key, record.get(key))]
            for key, label in fields
        ]

        parts.append(markdown_table(["Field", "Details"], rows))

        return "\n\n".join(parts)

    # ---------- several records: one row each ----------

    columns = TABLE_COLUMNS.get(kind) or [
        (key, key.replace("_", " ").title())
        for key in data[0]
    ]

    info = [subtitle]

    if kind in STATUS_COLUMN:
        info.append(status_summary(data, STATUS_COLUMN[kind]))

    info = " · ".join(text for text in info if text)

    if info:
        parts.append(info)

    rows = [
        [format_value(key, row.get(key)) for key, _ in columns]
        for row in data
    ]

    parts.append(
        markdown_table([label for _, label in columns], rows)
    )

    return "\n\n".join(parts)

# --------------------------------------------------
# 4. POLICY NODE
# Uses RAG + Groq, and streams the answer while it is written
# --------------------------------------------------

def policy_node(state: AssistantState):

    writer = get_stream_writer()

    answer = ""

    for answer in stream_answer(state["question"]):

        writer({"partial": answer})

    return {
        "answer": answer
    }

# --------------------------------------------------
# 5. EMPLOYEE NODE
# --------------------------------------------------

def employee_node(state: AssistantState):

    employee_id = state["employee_id"]

    if not employee_id:

        return {
            "answer": (
                "Please provide an employee ID, "
                "such as EMP001."
            )
        }

    data = get_employee_details(employee_id)

    return {
        "answer": format_database_answer(
            state["question"],
            data,
            kind="employee",
            title=f"Employee {employee_id}",
            empty_message=(
                f"I couldn't find an employee with ID {employee_id}."
            )
        )
    }

# --------------------------------------------------
# 6. DEPARTMENT NODE
# --------------------------------------------------

def department_node(state: AssistantState):

    question = state["question"].lower()

    department_name = state["department_name"]

    all_department_keywords = [
        "all departments",
        "each department",
        "every department",
        "total employees",
        "employee distribution",
        "overall department"
    ]

    if any(
        keyword in question
        for keyword in all_department_keywords
    ):

        data = get_all_department_details()
        kind = "departments"
        title = "All departments"

    elif department_name:

        data = get_department_details(
            department_name
        )
        kind = "department"
        title = f"{department_name} department"

    else:

        return {
            "answer": (
                "Please specify a department, such as Engineering, "
                "or ask for information about all departments."
            )
        }

    return {
        "answer": format_database_answer(
            state["question"],
            data,
            kind=kind,
            title=title,
            empty_message="I couldn't find that department."
        )
    }

# --------------------------------------------------
# 7. ATTENDANCE NODE
# --------------------------------------------------

def attendance_node(state: AssistantState):

    employee_id = state["employee_id"]

    if not employee_id:

        return {
            "answer": (
                "Please provide an employee ID, "
                "such as EMP001."
            )
        }

    data = get_employee_attendance(employee_id)

    return {
        "answer": format_database_answer(
            state["question"],
            data,
            kind="attendance",
            title=f"Attendance for {employee_id}",
            subtitle=(
                f"Latest {plural(len(data), 'record')}"
                if data else None
            ),
            empty_message=(
                f"I couldn't find attendance records for "
                f"{employee_id}. Please check the employee ID."
            )
        )
    }

# --------------------------------------------------
# 8. LEAVE NODE
# --------------------------------------------------

def leave_node(state: AssistantState):

    employee_id = state["employee_id"]

    if not employee_id:

        return {
            "answer": (
                "Please provide an employee ID, "
                "such as EMP001."
            )
        }

    data = get_employee_leave_requests(employee_id)

    return {
        "answer": format_database_answer(
            state["question"],
            data,
            kind="leave",
            title=f"Leave requests for {employee_id}",
            subtitle=(
                plural(len(data), "request")
                if data else None
            ),
            empty_message=(
                f"I couldn't find leave requests for "
                f"{employee_id}. Please check the employee ID."
            )
        )
    }

# --------------------------------------------------
# 9. ROUTING FUNCTION
# --------------------------------------------------

def route_question(state: AssistantState):

    return state["route"]

# --------------------------------------------------
# 10. BUILD LANGGRAPH WORKFLOW
# --------------------------------------------------

def build_assistant_graph():

    workflow = StateGraph(AssistantState)

    workflow.add_node(
        "classify",
        classify_question
    )

    workflow.add_node(
        "policy",
        policy_node
    )

    workflow.add_node(
        "employee",
        employee_node
    )

    workflow.add_node(
        "department",
        department_node
    )

    workflow.add_node(
        "attendance",
        attendance_node
    )

    workflow.add_node(
        "leave",
        leave_node
    )

    workflow.add_edge(
        START,
        "classify"
    )

    workflow.add_conditional_edges(
        "classify",
        route_question,
        {
            "POLICY": "policy",
            "EMPLOYEE": "employee",
            "DEPARTMENT": "department",
            "ATTENDANCE": "attendance",
            "LEAVE": "leave"
        }
    )

    for node in [
        "policy",
        "employee",
        "department",
        "attendance",
        "leave"
    ]:

        workflow.add_edge(
            node,
            END
        )

    return workflow.compile()

# Compile graph

assistant = build_assistant_graph()

# --------------------------------------------------
# 11. MAIN ASSISTANT FUNCTIONS
# --------------------------------------------------

def _initial_state(question: str) -> dict:

    return {
        "question": question.strip(),
        "route": "",
        "employee_id": "",
        "department_name": "",
        "answer": ""
    }

def ask_assistant(question: str) -> str:
    """Return the complete answer in one go."""

    if not question or not question.strip():

        return "Please enter a question."

    result = assistant.invoke(_initial_state(question))

    return result["answer"]

def ask_assistant_stream(question: str):
    """Yield the answer as it is written.
    Every item is the full answer so far, so the last item is final.
    Database answers arrive in one piece."""

    if not question or not question.strip():

        yield "Please enter a question."
        return

    if not STREAMING_SUPPORTED:

        yield ask_assistant(question)
        return

    final = ""

    for mode, chunk in assistant.stream(
        _initial_state(question),
        stream_mode=["custom", "values"]
    ):

        if mode == "custom":

            yield chunk["partial"]

        else:

            final = chunk.get("answer") or final

    if final:
        yield final
