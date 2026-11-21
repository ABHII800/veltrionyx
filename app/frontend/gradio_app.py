import html
import os
import socket
import threading
import time
from pathlib import Path

import gradio as gr

from app.agents.graph import ask_assistant_stream
from app.database.connection import get_db_connection

# ==================================================
# 1. PROJECT PATHS
# ==================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOCUMENT_FOLDER = PROJECT_ROOT / "data" / "documents"

# Cloud hosts (Cloud Run, Render, Railway, Hugging Face...) set the PORT
# variable. On your own PC it is not set, so the app runs in local mode.
IS_SERVER = bool(os.getenv("PORT"))

# ==================================================
# 2. DATABASE FUNCTIONS
# ==================================================

# On a server the database is far away, so every query costs time.
# Dashboard numbers are remembered for a short while. Locally the
# time is 0, so the numbers are always fresh, as before.
CACHE_SECONDS = 60 if IS_SERVER else 0
_query_cache = {}

def _cached(kind, query, load):
    """Run load() and remember the result for CACHE_SECONDS."""

    if CACHE_SECONDS:

        saved = _query_cache.get((kind, query))

        if saved and time.monotonic() - saved[0] < CACHE_SECONDS:
            return saved[1]

    result = load()

    if CACHE_SECONDS:
        _query_cache[(kind, query)] = (time.monotonic(), result)

    return result

def fetch_one(query):

    def load():
        connection = get_db_connection()
        cursor = connection.cursor()

        try:
            cursor.execute(query)
            return cursor.fetchone()
        finally:
            cursor.close()
            connection.close()

    return _cached("one", query, load)

def fetch_all(query):

    def load():
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        try:
            cursor.execute(query)
            return cursor.fetchall()
        finally:
            cursor.close()
            connection.close()

    return _cached("all", query, load)

def get_dashboard_data():

    employees = fetch_one(
        "SELECT COUNT(*) FROM employees"
    )[0]

    departments = fetch_one(
        "SELECT COUNT(*) FROM departments"
    )[0]

    attendance = fetch_one(
        "SELECT COUNT(*) FROM attendance"
    )[0]

    leave_requests = fetch_one(
        "SELECT COUNT(*) FROM leave_requests"
    )[0]

    attendance_rows = fetch_all("""
        SELECT attendance_status, COUNT(*) AS total
        FROM attendance
        GROUP BY attendance_status
    """)

    department_rows = fetch_all("""
        SELECT
            d.department_name,
            COUNT(e.employee_id) AS total
        FROM departments d
        LEFT JOIN employees e
            ON d.department_id = e.department_id
        GROUP BY d.department_id, d.department_name
        ORDER BY total DESC
    """)

    leave_rows = fetch_all("""
        SELECT leave_status, COUNT(*) AS total
        FROM leave_requests
        GROUP BY leave_status
    """)

    return {
        "employees": employees,
        "departments": departments,
        "attendance": attendance,
        "leave_requests": leave_requests,
        "attendance_rows": attendance_rows,
        "department_rows": department_rows,
        "leave_rows": leave_rows
    }

# ==================================================
# 3. HTML HELPERS
# ==================================================

LOADING_HTML = "<div class='panel'><p class='muted'>Loading...</p></div>"

# Status colours: green = good, amber = needs attention, red = negative.
# Anything not listed here uses the default blue.
STATUS_COLORS = {
    "present": ("#34d399", "#059669"),
    "approved": ("#34d399", "#059669"),
    "active": ("#34d399", "#059669"),
    "late": ("#fbbf24", "#d97706"),
    "pending": ("#fbbf24", "#d97706"),
    "absent": ("#f87171", "#dc2626"),
    "rejected": ("#f87171", "#dc2626"),
}
DEFAULT_COLORS = ("#3b82f6", "#6366f1")

def page_title(title, subtitle):

    return f"""
    <div class="page-title">
        <h2>{html.escape(title)}</h2>
        <p>{html.escape(subtitle)}</p>
    </div>
    """

def metric_card(label, value, icon, description, tone="blue"):

    return f"""
    <div class="metric-card tone-{tone}">
        <div class="metric-top">
            <span class="metric-icon">{icon}</span>
            <span class="metric-label">{label}</span>
        </div>

        <div class="metric-value">{value:,}</div>

        <div class="metric-description">
            {description}
        </div>
    </div>
    """

def make_bar_chart(rows, label_key, value_key, show_percent=False):

    if not rows:
        return "<p class='muted'>No records available.</p>"

    values = [int(row[value_key]) for row in rows]

    maximum = max(values) or 1
    total = sum(values) or 1

    # Status charts show each status as a share of all records.
    # Other charts compare each bar with the largest one.
    scale = total if show_percent else maximum

    output = ""

    for row, value in zip(rows, values):

        raw_label = str(row[label_key])
        label = html.escape(raw_label)

        start, end = STATUS_COLORS.get(
            raw_label.strip().lower(),
            DEFAULT_COLORS
        )

        width = (value / scale) * 100

        value_text = f"{value:,}"

        if show_percent:
            value_text += f" &middot; {value / total * 100:.0f}%"

        output += f"""
        <div class="bar-item">

            <div class="bar-heading">
                <span class="bar-label">
                    <span class="bar-dot"
                          style="background:{end}"></span>
                    {label}
                </span>
                <span class="bar-value">{value_text}</span>
            </div>

            <div class="bar-track">
                <div
                    class="bar-fill"
                    style="width:{width:.1f}%;
                           background:linear-gradient(90deg,{start},{end})">
                </div>
            </div>

        </div>
        """

    return output

# ==================================================
# 4. DASHBOARD
# ==================================================

def make_dashboard():

    try:

        data = get_dashboard_data()

        cards = (
            metric_card(
                "Employees",
                data["employees"],
                "👥",
                "Registered employee records",
                "blue"
            )
            +
            metric_card(
                "Departments",
                data["departments"],
                "🏢",
                "Company departments",
                "violet"
            )
            +
            metric_card(
                "Attendance",
                data["attendance"],
                "📅",
                "Attendance records",
                "green"
            )
            +
            metric_card(
                "Leave Requests",
                data["leave_requests"],
                "📝",
                "Submitted leave records",
                "amber"
            )
        )

        departments = make_bar_chart(
            data["department_rows"],
            "department_name",
            "total"
        )

        attendance = make_bar_chart(
            data["attendance_rows"],
            "attendance_status",
            "total",
            show_percent=True
        )

        leaves = make_bar_chart(
            data["leave_rows"],
            "leave_status",
            "total",
            show_percent=True
        )

        return f"""
        <div class="dashboard">

            <div class="hero">
                <div class="eyebrow">
                    VELTRIONYX &bull; ENTERPRISE INTELLIGENCE
                </div>

                <h1>Business Overview</h1>

                <p>
                    Your AI-powered company knowledge
                    and analytics workspace.
                </p>
            </div>

            <div class="metric-grid">
                {cards}
            </div>

            <div class="section-heading">
                <div>
                    <h2>Business Analytics</h2>
                    <p>
                        Live summaries from your MySQL database
                    </p>
                </div>

                <span class="live-label">
                    ● DATABASE CONNECTED
                </span>
            </div>

            <div class="analytics-grid">

                <div class="panel">
                    <h3>Department Distribution</h3>
                    <p class="panel-subtitle">
                        Employees by department
                    </p>
                    {departments}
                </div>

                <div class="panel">
                    <h3>Attendance Overview</h3>
                    <p class="panel-subtitle">
                        Records grouped by status
                    </p>
                    {attendance}
                </div>

                <div class="panel">
                    <h3>Leave Request Overview</h3>
                    <p class="panel-subtitle">
                        Requests grouped by status
                    </p>
                    {leaves}
                </div>

            </div>

            <div class="bottom-banner">
                <h3>
                    Smarter Insights. Greater Business Impact.
                </h3>

                <p>
                    Ask questions, explore company data and
                    retrieve policy information using your
                    AI assistant.
                </p>
            </div>

        </div>
        """

    except Exception as error:

        return f"""
        <div class="error-panel">
            <h2>Database connection issue</h2>

            <p>
                The dashboard could not load its MySQL data.
            </p>

            <pre>{html.escape(str(error))}</pre>

            <p>
                Check your MySQL service and local .env configuration.
            </p>
        </div>
        """

# ==================================================
# 5. COMPANY ANALYTICS
# ==================================================

def make_analytics():

    try:

        data = get_dashboard_data()

        department_chart = make_bar_chart(
            data["department_rows"],
            "department_name",
            "total"
        )

        attendance_chart = make_bar_chart(
            data["attendance_rows"],
            "attendance_status",
            "total",
            show_percent=True
        )

        leave_chart = make_bar_chart(
            data["leave_rows"],
            "leave_status",
            "total",
            show_percent=True
        )

        return f"""
        <div class="dashboard">

            {page_title(
                "Company Analytics",
                "Explore your company's structured data."
            )}

            <div class="analytics-grid">

                <div class="panel">
                    <h3>Employees by Department</h3>
                    {department_chart}
                </div>

                <div class="panel">
                    <h3>Attendance Status</h3>
                    {attendance_chart}
                </div>

                <div class="panel">
                    <h3>Leave Request Status</h3>
                    {leave_chart}
                </div>

            </div>
        </div>
        """

    except Exception as error:

        return (
            "<div class='error-panel'>"
            f"Analytics error: {html.escape(str(error))}"
            "</div>"
        )

# ==================================================
# 6. EMPLOYEE DIRECTORY
# ==================================================

def make_employee_directory():

    try:

        rows = fetch_all("""
            SELECT
                e.employee_id,
                e.first_name,
                e.last_name,
                e.email,
                e.designation,
                d.department_name,
                e.employment_status

            FROM employees e

            LEFT JOIN departments d
                ON e.department_id = d.department_id

            ORDER BY e.employee_id
        """)

        table_rows = ""

        for row in rows:

            table_rows += "<tr>"

            for value in row.values():

                safe_value = html.escape(
                    str(value if value is not None else "-")
                )

                table_rows += f"<td>{safe_value}</td>"

            table_rows += "</tr>"

        return f"""
        <div class="panel table-panel">

            <h2>Employee Directory</h2>

            <p class="panel-subtitle">
                {len(rows)} employee records
            </p>

            <div class="table-scroll">

                <table>

                    <thead>
                        <tr>
                            <th>Employee ID</th>
                            <th>First Name</th>
                            <th>Last Name</th>
                            <th>Email</th>
                            <th>Designation</th>
                            <th>Department</th>
                            <th>Status</th>
                        </tr>
                    </thead>

                    <tbody>
                        {table_rows}
                    </tbody>

                </table>

            </div>
        </div>
        """

    except Exception as error:

        return (
            "<div class='error-panel'>"
            "Employee directory error: "
            f"{html.escape(str(error))}"
            "</div>"
        )

# ==================================================
# 7. DOCUMENT SEARCH
# ==================================================

def make_document_list():

    if not DOCUMENT_FOLDER.exists():

        return """
        <div class="error-panel">
            Document folder not found.
        </div>
        """

    files = sorted(
        DOCUMENT_FOLDER.glob("*.txt")
    )

    if not files:

        return """
        <div class="panel">
            No policy documents found.
        </div>
        """

    items = ""

    for file in files:

        safe_name = html.escape(file.name)

        items += f"""
        <div class="document-item">

            <span class="document-icon">📄</span>

            <div>
                <strong>{safe_name}</strong>

                <p>Company knowledge document</p>
            </div>

            <span class="document-status">
                Available
            </span>

        </div>
        """

    return f"""
    <div class="panel">

        <h2>Knowledge Base Documents</h2>

        <p class="panel-subtitle">
            {len(files)} documents available to the RAG assistant
        </p>

        {items}

    </div>
    """

# ==================================================
# 8. AI ASSISTANT
# ==================================================

def respond(message, history):

    history = history or []

    if not message or not message.strip():

        yield history, ""
        return

    question = message.strip()

    # A public app should not send huge texts to the model.
    if IS_SERVER:
        question = question[:500]

    user_turn = {
        "role": "user",
        "content": question
    }

    # Show the question and a "thinking" bubble straight away,
    # so the screen never looks frozen while the answer is built.
    yield history + [
        user_turn,
        {
            "role": "assistant",
            "content": "⏳ Thinking..."
        }
    ], ""

    started = time.perf_counter()
    first_words = None
    last_update = 0.0
    answer = ""

    try:

        # The answer arrives in pieces; show each one as it comes.
        for answer in ask_assistant_stream(question):

            now = time.perf_counter()

            if first_words is None:
                first_words = now - started

            # Refresh the chat about 20 times a second, not on every word.
            if now - last_update >= 0.05:

                last_update = now

                yield history + [
                    user_turn,
                    {
                        "role": "assistant",
                        "content": answer
                    }
                ], ""

    except Exception as error:

        print(f"[error] {type(error).__name__}: {error}")

        if IS_SERVER:

            # Public visitors should not see hosts, keys or file paths.
            # The full error is in the server log.
            answer = (
                "Sorry, something went wrong while answering. "
                "Please try again in a moment."
            )

        else:

            answer = (
                "Sorry, I encountered an error. "
                f"{error}"
            )

    # Timing is printed in the terminal to help find slow steps.
    if first_words is None:
        first_words = time.perf_counter() - started

    print(
        f"[timing] first words after {first_words:.1f}s, "
        f"finished in {time.perf_counter() - started:.1f}s"
    )

    yield history + [
        user_turn,
        {
            "role": "assistant",
            "content": answer
        }
    ], ""

def warm_up_rag():
    """Load the embedding model and vector store once at startup,
    so the first real question is not slow."""

    try:

        from app.rag.retriever import retrieve_documents

        started = time.perf_counter()

        retrieve_documents("leave policy", top_k=1)

        print(
            f"[warm-up] RAG pipeline ready in "
            f"{time.perf_counter() - started:.1f}s"
        )

    except Exception as error:

        print(f"[warm-up] skipped: {error}")

def warm_up_groq():
    """Open the connection to Groq now, so the first question
    does not pay for the network handshake."""

    try:

        from app.agents.llm import client

        started = time.perf_counter()

        client.models.list()

        print(
            f"[warm-up] Groq connection ready in "
            f"{time.perf_counter() - started:.1f}s"
        )

    except Exception as error:

        print(f"[warm-up] Groq connection skipped: {error}")

def warm_up():
    warm_up_rag()
    warm_up_groq()

def refresh_all():
    """Fill every data tab each time the page is opened,
    so the numbers are always fresh."""

    return (
        make_dashboard(),
        make_analytics(),
        make_document_list(),
        make_employee_directory()
    )

# ==================================================
# 9. LIGHT THEME CSS
# ==================================================

CSS = """

/* ==================================================
   1. FORCE ONE CONSISTENT LIGHT THEME
   Gradio switches to dark colours when the browser or
   Windows is in dark mode. These overrides keep every
   Gradio component light, so text is always readable.
================================================== */

:root,
body,
.dark,
body.dark,
.gradio-container,
.gradio-container.dark {
    color-scheme: light !important;

    --body-background-fill: #f4f7fc !important;
    --body-text-color: #1e293b !important;
    --body-text-color-subdued: #64748b !important;

    --background-fill-primary: #ffffff !important;
    --background-fill-secondary: #f1f5f9 !important;

    --block-background-fill: #ffffff !important;
    --block-border-color: #e2e8f0 !important;
    --block-label-background-fill: #f1f5f9 !important;
    --block-label-text-color: #475569 !important;
    --block-title-text-color: #1e293b !important;
    --block-info-text-color: #64748b !important;

    --panel-background-fill: #ffffff !important;
    --panel-border-color: #e2e8f0 !important;
    --border-color-primary: #e2e8f0 !important;
    --border-color-accent: #93c5fd !important;

    --input-background-fill: #ffffff !important;
    --input-background-fill-focus: #ffffff !important;
    --input-background-fill-hover: #ffffff !important;
    --input-border-color: #cbd5e1 !important;
    --input-border-color-focus: #3b82f6 !important;
    --input-placeholder-color: #94a3b8 !important;

    --color-accent: #2563eb !important;
    --color-accent-soft: #e8f0fe !important;

    --button-secondary-background-fill: #ffffff !important;
    --button-secondary-background-fill-hover: #eff6ff !important;
    --button-secondary-text-color: #1e3a8a !important;
    --button-secondary-border-color: #cbd5e1 !important;

    --link-text-color: #1d4ed8 !important;
    --table-even-background-fill: #ffffff !important;
    --table-odd-background-fill: #f8fafc !important;
    --table-border-color: #e2e8f0 !important;
}

body,
.gradio-container {
    background: #f4f7fc !important;
    color: #1e293b !important;
    font-family: Inter, "Segoe UI", Arial, sans-serif !important;
}

.gradio-container {
    max-width: 1400px !important;
}

footer {
    display: none !important;
}

/* ==================================================
   2. APP HEADER
================================================== */

#app-header {
    background: linear-gradient(120deg, #0b1d42, #1e4fa3);
    border-radius: 16px;
    padding: 20px 26px;
    margin-bottom: 12px;
    box-shadow: 0 8px 24px rgba(12, 36, 77, .14);
}

.gradio-container #app-header h1 {
    margin: 0;
    font-size: 24px;
    color: #ffffff !important;
}

.gradio-container #app-header p {
    margin: 6px 0 0;
    font-size: 14px;
    color: #d8e5fa !important;
}

.gradio-container #app-header #brand {
    margin-bottom: 6px;
    font-size: 12px;
    font-weight: 800;
    letter-spacing: 3px;
    color: #93c5fd !important;
}

/* ==================================================
   3. TABS
================================================== */

.tab-container {
    border-bottom: 1px solid #d7e1f0 !important;
    gap: 4px !important;
}

.gradio-container button[role="tab"],
.gradio-container .tab-container button {
    background: transparent !important;
    color: #475569 !important;
    font-size: 14px !important;
    font-weight: 600 !important;
    padding: 10px 16px !important;
    border-radius: 10px 10px 0 0 !important;
    border: none !important;
}

.gradio-container button[role="tab"]:hover,
.gradio-container .tab-container button:hover {
    background: #eaf2ff !important;
    color: #1d4ed8 !important;
}

.gradio-container button[role="tab"].selected,
.gradio-container button[role="tab"][aria-selected="true"] {
    background: #e3eeff !important;
    color: #1d4ed8 !important;
}

/* ==================================================
   4. PAGE TITLES AND DASHBOARD
================================================== */

.dashboard {
    padding: 6px 0 16px;
}

.page-title h2 {
    margin: 6px 0 4px;
    font-size: 21px;
}

.page-title p {
    margin: 0 0 12px;
    font-size: 14px;
}

.gradio-container .page-title h2 {
    color: #0f2347 !important;
}

.gradio-container .page-title p {
    color: #64748b !important;
}

.hero {
    background: linear-gradient(120deg, #e8f0ff, #f1ecff);
    border: 1px solid #d9e4f7;
    border-left: 5px solid #2563eb;
    border-radius: 14px;
    padding: 20px 26px;
    margin-bottom: 18px;
}

.gradio-container .hero h1 {
    margin: 4px 0 6px;
    font-size: 26px;
    color: #0f2347 !important;
}

.gradio-container .hero p {
    margin: 0;
    color: #475569 !important;
}

.gradio-container .hero .eyebrow {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1.8px;
    color: #2563eb !important;
}

/* ---------- Metric cards and panels ---------- */

.metric-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 14px;
    margin-bottom: 22px;
}

.metric-card,
.panel {
    background: #ffffff !important;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 18px 20px;
    box-shadow: 0 2px 10px rgba(15, 35, 71, .05);
    transition: transform .2s ease, box-shadow .2s ease;
}

.metric-card:hover,
.panel:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 22px rgba(15, 35, 71, .09);
}

.metric-card {
    border-top: 4px solid var(--tone, #2563eb);
}

.tone-blue { --tone: #2563eb; }
.tone-violet { --tone: #7c3aed; }
.tone-green { --tone: #059669; }
.tone-amber { --tone: #d97706; }

.metric-top {
    display: flex;
    align-items: center;
    gap: 10px;
}

.metric-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 34px;
    height: 34px;
    font-size: 18px;
    border-radius: 10px;
    background: #eef4ff;
    background: color-mix(in srgb, var(--tone) 12%, white);
}

.gradio-container .metric-label {
    font-size: 13px;
    font-weight: 600;
    color: #475569 !important;
}

.gradio-container .metric-value {
    margin-top: 12px;
    font-size: 32px;
    font-weight: 800;
    color: #0f2347 !important;
}

.gradio-container .metric-description {
    margin-top: 4px;
    font-size: 12px;
    color: #64748b !important;
}

/* ---------- Section headings ---------- */

.section-heading {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin: 24px 0 14px;
}

.gradio-container .section-heading h1,
.gradio-container .section-heading h2 {
    margin: 0;
    color: #0f2347 !important;
}

.gradio-container .section-heading p {
    margin: 5px 0 0;
    font-size: 13px;
    color: #64748b !important;
}

.gradio-container .live-label {
    padding: 8px 12px;
    border-radius: 20px;
    background: #dcfce7;
    font-size: 10px;
    font-weight: 800;
    color: #047857 !important;
}

/* ==================================================
   5. CHARTS
================================================== */

.analytics-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 16px;
}

.gradio-container .panel h2,
.gradio-container .panel h3 {
    margin-top: 0;
    color: #0f2347 !important;
}

.gradio-container .panel h3 {
    font-size: 16px;
}

.gradio-container .panel-subtitle {
    margin-top: 4px;
    font-size: 12px;
    color: #64748b !important;
}

.bar-item {
    margin-top: 16px;
}

.bar-heading {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 7px;
    font-size: 13px;
}

.gradio-container .bar-label {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-weight: 500;
    color: #334155 !important;
}

.bar-dot {
    display: inline-block;
    width: 9px;
    height: 9px;
    border-radius: 50%;
}

.gradio-container .bar-value {
    font-weight: 700;
    color: #0f2347 !important;
}

.bar-track {
    height: 10px;
    border-radius: 10px;
    background: #e9eef7;
    overflow: hidden;
}

.bar-fill {
    height: 100%;
    border-radius: 10px;
}

/* ---------- Bottom banner ---------- */

.bottom-banner {
    margin-top: 20px;
    padding: 22px 24px;
    border-radius: 14px;
    background: linear-gradient(110deg, #102b5c, #3a3aa8);
}

.gradio-container .bottom-banner h3 {
    margin: 0 0 8px;
    color: #ffffff !important;
}

.gradio-container .bottom-banner p {
    margin: 0;
    font-size: 13px;
    color: #dbe6ff !important;
}

/* ==================================================
   6. DOCUMENTS AND EMPLOYEE TABLE
================================================== */

.document-item {
    display: flex;
    align-items: center;
    gap: 13px;
    padding: 14px 2px;
    border-bottom: 1px solid #edf1f7;
}

.document-icon {
    font-size: 23px;
}

.gradio-container .document-item strong {
    color: #0f2347 !important;
}

.gradio-container .document-item p {
    margin: 4px 0 0;
    font-size: 12px;
    color: #64748b !important;
}

.gradio-container .document-status {
    margin-left: auto;
    padding: 6px 10px;
    border-radius: 15px;
    background: #dcfce7;
    font-size: 11px;
    font-weight: 600;
    color: #047857 !important;
}

.table-scroll {
    overflow-x: auto;
}

table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
}

.gradio-container table,
.gradio-container thead,
.gradio-container tbody,
.gradio-container tr {
    border: none !important;
}

.gradio-container th,
.gradio-container td {
    padding: 12px;
    border: none !important;
    border-bottom: 1px solid #e9eef6 !important;
    white-space: nowrap;
    text-align: left;
}

.gradio-container th {
    background: #eaf1fc !important;
    color: #1e3a8a !important;
}

.gradio-container td {
    background: transparent !important;
    color: #334155 !important;
}

tr:hover td {
    background: #f3f7ff !important;
}

/* ==================================================
   7. CHAT
================================================== */

.gradio-container .bubble-wrap {
    background: #ffffff !important;
    border: 1px solid #dbe4f1 !important;
    border-radius: 14px !important;
}

.gradio-container .message-wrap {
    background: #ffffff !important;
}

/* The share / clear / copy-all icons float over the top message.
   The Clear button below the chat already covers this. */
.gradio-container .icon-button-wrapper.top-panel {
    display: none !important;
}

/* Gradio dims chat text to 80% opacity, which looks washed out */
.gradio-container .message .prose,
.gradio-container .message .md,
.gradio-container .message-content,
.gradio-container .message-content * {
    opacity: 1 !important;
}

.gradio-container .bot.message,
.gradio-container .message.bot {
    background: #f1f5f9 !important;
    border: 1px solid #e2e8f0 !important;
    color: #1e293b !important;
}

.gradio-container .bot.message *,
.gradio-container .message.bot * {
    color: #1e293b !important;
}

.gradio-container .user.message,
.gradio-container .message.user {
    background: #1d4ed8 !important;
    border: none !important;
    color: #ffffff !important;
}

.gradio-container .user.message *,
.gradio-container .message.user * {
    color: #ffffff !important;
}

/* ---------- Tables inside assistant answers ---------- */

.gradio-container .bot.message table {
    width: 100% !important;
    margin: 6px 0 2px !important;
    font-size: 12.5px !important;
    border-collapse: separate !important;
    border-spacing: 0 !important;
    background: #ffffff !important;
    border: 1px solid #d5e0f2 !important;
    border-radius: 10px !important;
    overflow: hidden;
}

.gradio-container .bot.message th,
.gradio-container .bot.message td {
    padding: 3px 14px !important;
    text-align: left !important;
    white-space: nowrap;
    border: none !important;
    border-bottom: 1px solid #e6edf7 !important;
}

.gradio-container .bot.message th {
    background: #dfe9fb !important;
    color: #1e3a8a !important;
    font-weight: 700 !important;
}

.gradio-container .bot.message td {
    background: #ffffff !important;
    color: #1e293b !important;
}

.gradio-container .bot.message tr:last-child td {
    border-bottom: none !important;
}

.gradio-container .bot.message tr:hover td {
    background: #f3f7ff !important;
}

.gradio-container .bot.message .message-content {
    overflow-x: auto;
}

.gradio-container textarea,
.gradio-container input {
    background: #ffffff !important;
    color: #1e293b !important;
}

.gradio-container textarea {
    border: 1px solid #cbd5e1 !important;
    border-radius: 10px !important;
}

.gradio-container textarea:focus {
    border-color: #3b82f6 !important;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, .15) !important;
}

.gradio-container textarea::placeholder,
.gradio-container input::placeholder {
    color: #94a3b8 !important;
    opacity: 1 !important;
}

/* ==================================================
   8. BUTTONS
================================================== */

.gradio-container button {
    transition: background .2s ease, border-color .2s ease,
                box-shadow .2s ease;
}

.gradio-container button.primary {
    background: linear-gradient(120deg, #1d4ed8, #4f46e5) !important;
    border: none !important;
    color: #ffffff !important;
    font-weight: 700 !important;
}

.gradio-container button.primary:hover {
    box-shadow: 0 5px 14px rgba(29, 78, 216, .28);
}

.gradio-container button.secondary {
    background: #ffffff !important;
    border: 1px solid #cbd5e1 !important;
    color: #1e3a8a !important;
    font-weight: 600 !important;
}

.gradio-container button.secondary:hover {
    background: #eff6ff !important;
    border-color: #93c5fd !important;
}

/* ==================================================
   9. ERRORS AND SMALL HELPERS
================================================== */

.error-panel {
    padding: 20px;
    background: #fff1f1;
    border: 1px solid #ffd3d3;
    border-radius: 12px;
    color: #8f2525 !important;
}

.error-panel pre {
    white-space: pre-wrap;
    overflow-wrap: anywhere;
}

.gradio-container .muted {
    color: #64748b !important;
}

/* ==================================================
   10. RESPONSIVE DESIGN
================================================== */

@media (max-width: 1100px) {

    .metric-grid,
    .analytics-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }
}

@media (max-width: 650px) {

    .metric-grid,
    .analytics-grid {
        grid-template-columns: 1fr;
    }

    .gradio-container .hero h1 {
        font-size: 22px;
    }

    .section-heading {
        align-items: flex-start;
        gap: 10px;
        flex-direction: column;
    }
}

"""

# ==================================================
# 10. BUILD GRADIO APPLICATION
# ==================================================

EXAMPLE_QUESTIONS = [
    ["How many sick leaves are available per year?"],
    ["Show details of EMP001"],
    ["Attendance of EMP005"],
    ["Leave requests of EMP010"],
    ["Employees in Engineering"],
    ["Show all departments"],
]

with gr.Blocks(
    title="Veltrionyx Enterprise AI"
) as demo:

    gr.HTML("""
    <div id="app-header">

        <div id="brand">
            V E L T R I O N Y X
        </div>

        <h1>
            Enterprise AI Intelligence Platform
        </h1>

        <p>
            One workspace for company knowledge,
            employee data and intelligent insights.
        </p>

    </div>
    """)

    with gr.Tabs():

        # ------------------------------------------
        # DASHBOARD
        # ------------------------------------------

        with gr.Tab("Dashboard"):

            dashboard_html = gr.HTML(
                value=LOADING_HTML
            )

        # ------------------------------------------
        # AI ASSISTANT
        # ------------------------------------------

        with gr.Tab("Ask Assistant"):

            gr.HTML(
                page_title(
                    "Veltrionyx AI Assistant",
                    "Ask about company policies, employees, "
                    "departments, attendance and leave requests."
                )
            )

            chatbot = gr.Chatbot(
                height=450,
                show_label=False,
                placeholder=(
                    "**Ask me anything about your company**\n\n"
                    "Try: *How many sick leaves are available "
                    "per year?* or *Show details of EMP001*"
                )
            )

            with gr.Row():

                message = gr.Textbox(
                    placeholder=(
                        "Ask something about your company..."
                    ),
                    show_label=False,
                    container=False,
                    scale=8
                )

                send_button = gr.Button(
                    "Send ➤",
                    variant="primary",
                    scale=1,
                    min_width=110
                )

                clear_button = gr.Button(
                    "Clear",
                    variant="secondary",
                    scale=1,
                    min_width=110
                )

            gr.Examples(
                examples=EXAMPLE_QUESTIONS,
                inputs=message,
                label="Try an example"
            )

            message.submit(
                fn=respond,
                inputs=[message, chatbot],
                outputs=[chatbot, message],
                show_progress="hidden"
            )

            send_button.click(
                fn=respond,
                inputs=[message, chatbot],
                outputs=[chatbot, message],
                show_progress="hidden"
            )

            clear_button.click(
                fn=lambda: [],
                inputs=None,
                outputs=chatbot
            )

        # ------------------------------------------
        # COMPANY ANALYTICS
        # ------------------------------------------

        with gr.Tab("Company Analytics"):

            analytics_html = gr.HTML(
                value=LOADING_HTML
            )

            refresh_analytics = gr.Button(
                "↻ Refresh Analytics",
                variant="secondary"
            )

            refresh_analytics.click(
                fn=make_analytics,
                inputs=None,
                outputs=analytics_html
            )

        # ------------------------------------------
        # DOCUMENT SEARCH
        # ------------------------------------------

        with gr.Tab("Document Search"):

            gr.HTML(
                page_title(
                    "Company Knowledge Base",
                    "These documents are indexed by the RAG "
                    "pipeline. Ask the AI Assistant a question "
                    "to search their contents."
                )
            )

            documents_html = gr.HTML(
                value=LOADING_HTML
            )

        # ------------------------------------------
        # EMPLOYEE DIRECTORY
        # ------------------------------------------

        with gr.Tab("Employee Directory"):

            employee_html = gr.HTML(
                value=LOADING_HTML
            )

            refresh_employees = gr.Button(
                "↻ Refresh Employee List",
                variant="secondary"
            )

            refresh_employees.click(
                fn=make_employee_directory,
                inputs=None,
                outputs=employee_html
            )

    # Fill all data tabs when the page opens.
    demo.load(
        fn=refresh_all,
        inputs=None,
        outputs=[
            dashboard_html,
            analytics_html,
            documents_html,
            employee_html
        ],
        show_progress="hidden"
    )

# ==================================================
# 11. LAUNCH APPLICATION
# ==================================================

def port_problem(port):
    """Return None if the port is free, otherwise the reason it is not.
    The reason is the exact Windows / OS message, which shows whether
    the port is in use (10048) or blocked by permissions (10013)."""

    with socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    ) as test_socket:

        try:
            test_socket.bind(("127.0.0.1", port))
        except OSError as error:
            return str(error)

    return None

def launch_app(first_port=7861, attempts=30):
    """Start the app on the first port that works.

    If an older copy of the app is still running on 7861, Gradio
    alone stops with "Cannot find empty port". This tries the next
    port instead, and prints why each port was skipped."""

    for port in range(first_port, first_port + attempts):

        problem = port_problem(port)

        if problem:

            print(
                f"Port {port} is not available ({problem}). "
                f"Trying port {port + 1}..."
            )
            continue

        print(f"\nStarting the app on port {port}...\n")

        try:

            demo.launch(
                server_name="127.0.0.1",
                server_port=port,
                inbrowser=True,
                share=False,
                ssr_mode=False,
                show_error=True,
                theme=gr.themes.Soft(
                    primary_hue="blue",
                    secondary_hue="slate",
                    neutral_hue="slate"
                ),
                css=CSS
            )

            return

        except OSError as error:

            # Only a port problem is retried. Anything else is a real bug.
            if "empty port" not in str(error):
                raise

            print(
                f"Gradio could not start on port {port}. "
                f"Trying port {port + 1}..."
            )

    raise RuntimeError(
        f"No working port between {first_port} and "
        f"{first_port + attempts - 1}. Close older copies of the "
        "app (or restart the PC) and try again."
    )

def launch_server(port):
    """Start the app on a hosting service (Cloud Run, Render, ...).

    The host decides the port (PORT variable) and must be able to
    reach the app from outside, so it listens on 0.0.0.0. No browser
    is opened and there is no port hopping."""

    print(f"\nStarting the app in server mode on port {port}...\n")

    demo.queue(max_size=20)

    demo.launch(
        server_name="0.0.0.0",
        server_port=port,
        inbrowser=False,
        share=False,
        ssr_mode=False,
        show_error=False,
        theme=gr.themes.Soft(
            primary_hue="blue",
            secondary_hue="slate",
            neutral_hue="slate"
        ),
        css=CSS
    )

if __name__ == "__main__":

    if IS_SERVER:

        # The embedding model loads first, so the port opens only when
        # the first question can be answered fast. The Groq handshake
        # can take a few seconds, so it runs in the background.
        warm_up_rag()

        threading.Thread(
            target=warm_up_groq,
            daemon=True
        ).start()

        launch_server(int(os.environ["PORT"]))

    else:

        # Preload the RAG pipeline in the background while the page opens.
        threading.Thread(
            target=warm_up,
            daemon=True
        ).start()

        # Normally 7861. Set GRADIO_SERVER_PORT to start from another port.
        launch_app(
            int(os.getenv("GRADIO_SERVER_PORT", "7861"))
        )
