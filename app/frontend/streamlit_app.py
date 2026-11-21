
import html
from pathlib import Path

import streamlit as st

from app.agents.graph import ask_assistant
from app.database.connection import get_db_connection

# ==========================================================
# 1. PAGE CONFIGURATION
# ==========================================================

st.set_page_config(
    page_title="Veltrionyx | Enterprise AI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================================
# 2. PROJECT PATHS
# ==========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DOCUMENT_FOLDER = PROJECT_ROOT / "data" / "documents"

# ==========================================================
# 3. CUSTOM CSS - OPTION A: MODERN CORPORATE
# ==========================================================

st.markdown("""
<style>

    /* Main background */

    .stApp {
        background-color: #f3f6fc;
    }

    [data-testid="stMainBlockContainer"] {
        padding-top: 1.5rem;
    }

    /* Sidebar */

    [data-testid="stSidebar"] {
        background: linear-gradient(
            180deg,
            #101d35 0%,
            #192d4c 100%
        );
    }

    [data-testid="stSidebar"] * {
        color: #ffffff;
    }

    .brand {
        font-size: 27px;
        font-weight: 800;
        color: #ffffff;
        margin-bottom: 0;
    }

    .tagline {
        font-size: 12px;
        color: #b9cbe7;
        margin-top: 0;
    }

    /* Hero banner */

    .hero {
        background: linear-gradient(
            110deg,
            #10294e,
            #1763a9,
            #398ed4
        );

        padding: 30px;
        border-radius: 15px;
        color: white;
        margin-bottom: 20px;
        box-shadow: 0 5px 18px rgba(20, 70, 130, 0.12);
    }

    .hero h1 {
        color: white;
        font-size: 38px;
        font-weight: 800;
        margin-bottom: 5px;
    }

    .hero h3 {
        color: white;
        font-size: 21px;
        margin-bottom: 8px;
    }

    .hero p {
        color: #e4efff;
        font-size: 15px;
        margin-bottom: 0;
    }

    /* Status */

    .status {
        color: #15965b;
        font-weight: 700;
        text-align: right;
        font-size: 13px;
    }

    /* Metric cards */

    div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e0e9f6;
        padding: 16px;
        border-radius: 12px;
        box-shadow: 0 3px 10px rgba(30, 65, 110, 0.05);
    }

    div[data-testid="stMetricLabel"] {
        color: #53657e;
        font-weight: 600;
    }

    div[data-testid="stMetricValue"] {
        color: #142b4c;
        font-weight: 800;
    }

    /* Panels */

    .panel {
        background: #ffffff;
        border: 1px solid #dce6f5;
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 15px;
        box-shadow: 0 3px 10px rgba(30, 65, 110, 0.04);
    }

    .panel-title {
        color: #14294a;
        font-size: 19px;
        font-weight: 750;
    }

    .small-note {
        color: #75849a;
        font-size: 12px;
    }

    /* Chat messages */

    .stChatMessage {
        border-radius: 12px;
    }

    /* Buttons */

    div.stButton > button {
        border-radius: 9px;
        border: 1px solid #c7dcfa;
        color: #1456a0;
        background: #edf5ff;
        font-weight: 600;
        min-height: 40px;
    }

    div.stButton > button:hover {
        background: #d9eaff;
        border-color: #4d91e8;
        color: #104b90;
    }

    /* HTML tables */

    .custom-table {
        width: 100%;
        border-collapse: collapse;
        background: #ffffff;
        font-size: 13px;
    }

    .custom-table th {
        background: #eaf2ff;
        color: #173d70;
        text-align: left;
        padding: 11px;
        border-bottom: 1px solid #dce6f5;
    }

    .custom-table td {
        color: #243852;
        padding: 10px;
        border-bottom: 1px solid #edf1f7;
    }

    .custom-table tr:hover {
        background: #f5f9ff;
    }

/* ===== TEXT VISIBILITY FIX ===== */

.stApp,
[data-testid="stAppViewContainer"] {
    color: #172b4d !important;
}

[data-testid="stMainBlockContainer"] h1,
[data-testid="stMainBlockContainer"] h2,
[data-testid="stMainBlockContainer"] h3,
[data-testid="stMainBlockContainer"] h4 {
    color: #142b4c !important;
    font-weight: 750 !important;
}

[data-testid="stMainBlockContainer"] p,
[data-testid="stMainBlockContainer"] label,
[data-testid="stMainBlockContainer"] span {
    color: #344762;
}

[data-testid="stCaptionContainer"] {
    color: #667891 !important;
}

[data-testid="stMarkdownContainer"] {
    color: #243852;
}

/* Chat input */

[data-testid="stChatInput"] {
    background: #ffffff !important;
    border: 1px solid #b9d1f2 !important;
    border-radius: 12px !important;
}

[data-testid="stChatInput"] textarea {
    color: #17365f !important;
    background: #ffffff !important;
    -webkit-text-fill-color: #17365f !important;
}

[data-testid="stChatInput"] textarea::placeholder {
    color: #788ba5 !important;
    -webkit-text-fill-color: #788ba5 !important;
}

/* Metric and panel headings */

[data-testid="stMetricLabel"] {
    color: #53657e !important;
}

[data-testid="stMetricValue"] {
    color: #142b4c !important;
}
</style>
""", unsafe_allow_html=True)

# ==========================================================
# 4. DATABASE FUNCTIONS
# ==========================================================

def load_dashboard_data():

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:

        data = {}

        # Total employees

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM employees
        """)

        data["employees"] = cursor.fetchone()["total"]

        # Total departments

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM departments
        """)

        data["departments"] = cursor.fetchone()["total"]

        # Total attendance records

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM attendance
        """)

        data["attendance"] = cursor.fetchone()["total"]

        # Total leave requests

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM leave_requests
        """)

        data["leaves"] = cursor.fetchone()["total"]

        # Department distribution

        cursor.execute("""
            SELECT
                d.department_name,
                COUNT(e.employee_id) AS total_employees

            FROM departments d

            LEFT JOIN employees e
                ON d.department_id = e.department_id

            GROUP BY
                d.department_id,
                d.department_name

            ORDER BY d.department_name
        """)

        data["department_distribution"] = cursor.fetchall()

        # Attendance summary

        cursor.execute("""
            SELECT
                attendance_status,
                COUNT(*) AS total_records

            FROM attendance

            GROUP BY attendance_status

            ORDER BY attendance_status
        """)

        data["attendance_summary"] = cursor.fetchall()

        return data

    finally:

        cursor.close()
        connection.close()

# ==========================================================
# 5. HTML TABLE FUNCTION - NO PANDAS OR PYARROW
# ==========================================================

def render_html_table(rows, columns):

    if not rows:
        st.info("No records available.")
        return

    header = "".join(
        f"<th>{html.escape(column.replace('_', ' ').title())}</th>"
        for column in columns
    )

    body = ""

    for row in rows:

        cells = ""

        for column in columns:

            value = row.get(column, "")

            cells += (
                f"<td>{html.escape(str(value))}</td>"
            )

        body += f"<tr>{cells}</tr>"

    table_html = f"""
    <div style="overflow-x:auto; border-radius:10px;">

        <table class="custom-table">

            <thead>
                <tr>{header}</tr>
            </thead>

            <tbody>
                {body}
            </tbody>

        </table>

    </div>
    """

    st.markdown(
        table_html,
        unsafe_allow_html=True
    )

# ==========================================================
# 6. CSS BAR CHART FUNCTION
# ==========================================================

def render_bar_chart(rows, label_key, value_key):

    if not rows:
        st.info("No chart data available.")
        return

    maximum = max(
        (int(row[value_key]) for row in rows),
        default=1
    )

    for row in rows:

        label = html.escape(str(row[label_key]))

        value = int(row[value_key])

        percentage = (
            value / maximum * 100
            if maximum > 0
            else 0
        )

        st.markdown(
            f"""
            <div style="margin-bottom:17px;">

                <div style="
                    display:flex;
                    justify-content:space-between;
                    margin-bottom:6px;
                    color:#19375f;
                    font-size:14px;
                ">

                    <span>{label}</span>

                    <b>{value}</b>

                </div>

                <div style="
                    background:#e8eef7;
                    border-radius:8px;
                    height:13px;
                ">

                    <div style="
                        width:{percentage:.1f}%;
                        background:linear-gradient(
                            90deg,
                            #1763bd,
                            #48a0ed
                        );
                        height:13px;
                        border-radius:8px;
                    "></div>

                </div>

            </div>
            """,
            unsafe_allow_html=True
        )

# ==========================================================
# 7. AI CHAT FUNCTION
# ==========================================================

def process_question(question):

    if not question or not question.strip():

        return

    st.session_state.messages.append({
        "role": "user",
        "content": question
    })

    try:

        with st.spinner("Veltrionyx AI is thinking..."):

            answer = ask_assistant(question)

    except Exception as error:

        print(f"Assistant error: {error}")

        answer = (
            "Sorry, something went wrong. "
            "Please check the application terminal."
        )

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer
    })

    st.rerun()

# ==========================================================
# 8. DISPLAY CHAT HISTORY
# ==========================================================

def display_chat_history():

    for message in st.session_state.messages:

        with st.chat_message(message["role"]):

            st.markdown(message["content"])

# ==========================================================
# 9. INITIALIZE SESSION STATE
# ==========================================================

if "messages" not in st.session_state:

    st.session_state.messages = []

# ==========================================================
# 10. LOAD DATABASE STATISTICS
# ==========================================================

dashboard = None

database_connected = False

database_error = None

try:

    dashboard = load_dashboard_data()

    database_connected = True

except Exception as error:

    database_error = str(error)

    print(f"Dashboard database error: {error}")

# ==========================================================
# 11. COUNT POLICY DOCUMENTS
# ==========================================================

document_count = 0

if DOCUMENT_FOLDER.exists():

    document_count = len(
        list(DOCUMENT_FOLDER.glob("*.txt"))
    )

# ==========================================================
# 12. SIDEBAR NAVIGATION
# ==========================================================

with st.sidebar:

    st.markdown(
        '<p class="brand">🔷 Veltrionyx</p>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<p class="tagline">Innovating Tomorrow</p>',
        unsafe_allow_html=True
    )

    st.divider()

    selected_page = st.radio(
        "NAVIGATION",
        [
            "🏠 Home",
            "💬 Ask Assistant",
            "📊 Company Analytics",
            "📄 Document Search",
            "👥 Employee Directory",
            "⚙️ System Status"
        ],
        label_visibility="collapsed"
    )

    st.divider()

    st.markdown("### ✨ About This Project")

    st.write(
        "Enterprise Agentic AI Knowledge Assistant"
    )

    st.caption(
        "Powered by Python • LangGraph • RAG "
        "• MySQL • ChromaDB • Groq"
    )

# ==========================================================
# 13. CONNECTION STATUS
# ==========================================================

if database_connected:

    st.markdown(
        '<p class="status">🟢 MySQL Database Connected</p>',
        unsafe_allow_html=True
    )

else:

    st.markdown(
        '<p style="color:#d93636;text-align:right;">'
        '🔴 Database Disconnected</p>',
        unsafe_allow_html=True
    )

# ==========================================================
# 14. CORPORATE HERO BANNER
# ==========================================================

st.markdown("""
<div class="hero">

    <h1>Veltrionyx</h1>

    <h3>Enterprise Agentic AI Knowledge Assistant</h3>

    <p>
        Get instant answers about our company —
        from policies to people, data and procedures.
    </p>

</div>
""", unsafe_allow_html=True)

# ==========================================================
# 15. HOME DASHBOARD
# ==========================================================

if selected_page == "🏠 Home":

    st.subheader("Company Overview")

    if database_connected:

        col1, col2, col3, col4, col5 = st.columns(5)

        metrics = [
            ("👥 Employees", dashboard["employees"]),
            ("🏢 Departments", dashboard["departments"]),
            ("📅 Attendance Records", dashboard["attendance"]),
            ("📝 Leave Requests", dashboard["leaves"]),
            ("📚 Company Documents", document_count)
        ]

        columns = [col1, col2, col3, col4, col5]

        for column, (label, value) in zip(columns, metrics):

            column.metric(
                label,
                f"{value:,}"
            )

    else:

        st.warning(
            "Dashboard statistics are unavailable "
            "because MySQL is disconnected."
        )

    st.divider()

    # Main dashboard layout

    left, right = st.columns([2.1, 1])

    # ------------------------------------------------------
    # AI CHAT PANEL
    # ------------------------------------------------------

    with left:

        st.markdown("### 💬 Ask Our AI Assistant")

        st.caption(
            "Ask questions about company policies, employees, "
            "departments, attendance and leave."
        )

        display_chat_history()

        question = st.chat_input(
            "Ask anything about Veltrionyx...",
            key="home_chat_input"
        )

        if question:

            process_question(question)

        if st.button(
            "🗑️ Clear Conversation",
            key="home_clear"
        ):

            st.session_state.messages = []

            st.rerun()

    # ------------------------------------------------------
    # COMPANY OVERVIEW
    # ------------------------------------------------------

    with right:

        st.markdown("### 🏢 Company Overview")

        st.markdown("""
        <div class="panel">

            <b>Company:</b> Veltrionyx<br><br>

            <b>Industry:</b> Enterprise Technology<br><br>

            <b>Location:</b> Hyderabad, India<br><br>

            <b>Project:</b> Agentic AI Knowledge Assistant<br><br>

            <b>Technology:</b> Python, RAG and LangGraph

        </div>
        """, unsafe_allow_html=True)

        st.markdown("### 💡 Recent Insights")

        if database_connected:

            for row in dashboard["attendance_summary"]:

                st.write(
                    f"🟢 {row['attendance_status']}: "
                    f"{row['total_records']} records"
                )

            st.caption(
                "Insights based on current database records."
            )

        else:

            st.info("Database insights unavailable.")

    # ------------------------------------------------------
    # ANALYTICS
    # ------------------------------------------------------

    st.divider()

    st.subheader("📊 Company Analytics")

    chart1, chart2 = st.columns(2)

    with chart1:

        st.markdown("#### Department Distribution")

        if database_connected:

            render_bar_chart(
                dashboard["department_distribution"],
                "department_name",
                "total_employees"
            )

        else:

            st.info("Department data unavailable.")

    with chart2:

        st.markdown("#### Attendance Summary")

        if database_connected:

            render_bar_chart(
                dashboard["attendance_summary"],
                "attendance_status",
                "total_records"
            )

        else:

            st.info("Attendance data unavailable.")

    # ------------------------------------------------------
    # QUICK ACTIONS
    # ------------------------------------------------------

    st.divider()

    st.subheader("⚡ Quick Actions")

    q1, q2, q3 = st.columns(3)

    with q1:

        if st.button(
            "📄 Search Company Policies",
            use_container_width=True
        ):

            process_question(
                "What are the company working hours?"
            )

    with q2:

        if st.button(
            "👤 Check Employee Info",
            use_container_width=True
        ):

            process_question(
                "Show me the employee details for EMP001"
            )

    with q3:

        if st.button(
            "📅 View Leave Status",
            use_container_width=True
        ):

            process_question(
                "Show me all leave requests for EMP001"
            )

# ==========================================================
# 16. ASK ASSISTANT PAGE
# ==========================================================

elif selected_page == "💬 Ask Assistant":

    st.subheader("💬 Ask Veltrionyx AI")

    st.write(
        "Your enterprise assistant for policies, "
        "employee information and company data."
    )

    display_chat_history()

    question = st.chat_input(
        "Enter your question...",
        key="assistant_chat_input"
    )

    if question:

        process_question(question)

    if st.button(
        "🗑️ Clear Conversation",
        key="assistant_clear"
    ):

        st.session_state.messages = []

        st.rerun()

# ==========================================================
# 17. COMPANY ANALYTICS PAGE
# ==========================================================

elif selected_page == "📊 Company Analytics":

    st.subheader("📊 Company Analytics")

    if database_connected:

        st.markdown("### Department Distribution")

        render_html_table(
            dashboard["department_distribution"],
            [
                "department_name",
                "total_employees"
            ]
        )

        st.markdown("### Attendance Summary")

        render_html_table(
            dashboard["attendance_summary"],
            [
                "attendance_status",
                "total_records"
            ]
        )

        st.divider()

        st.markdown("### Department Chart")

        render_bar_chart(
            dashboard["department_distribution"],
            "department_name",
            "total_employees"
        )

    else:

        st.warning("Database unavailable.")

# ==========================================================
# 18. DOCUMENT SEARCH PAGE
# ==========================================================

elif selected_page == "📄 Document Search":

    st.subheader("📄 Company Documents")

    st.write(
        "These are the policy documents available "
        "in the Veltrionyx knowledge base."
    )

    if DOCUMENT_FOLDER.exists():

        documents = sorted(
            DOCUMENT_FOLDER.glob("*.txt")
        )

        if documents:

            for document in documents:

                with st.expander(f"📄 {document.name}"):

                    try:

                        content = document.read_text(
                            encoding="utf-8"
                        )

                        st.write(content)

                    except Exception as error:

                        st.error(
                            f"Unable to read document: {error}"
                        )

        else:

            st.info("No policy documents found.")

    else:

        st.warning("Policy document folder not found.")

    st.divider()

    st.markdown("### Ask about a document")

    question = st.chat_input(
        "Ask a question about company policies...",
        key="document_chat_input"
    )

    if question:

        process_question(question)

# ==========================================================
# 19. EMPLOYEE DIRECTORY PAGE
# ==========================================================

elif selected_page == "👥 Employee Directory":

    st.subheader("👥 Employee Directory")

    if database_connected:

        connection = get_db_connection()

        cursor = connection.cursor(dictionary=True)

        try:

            cursor.execute("""
                SELECT
                    e.employee_id,
                    e.first_name,
                    e.last_name,
                    e.email,
                    e.designation,
                    d.department_name

                FROM employees e

                LEFT JOIN departments d
                    ON e.department_id = d.department_id

                ORDER BY e.employee_id
            """)

            employees = cursor.fetchall()

            st.write(
                f"Total employee records: {len(employees)}"
            )

            render_html_table(
                employees,
                [
                    "employee_id",
                    "first_name",
                    "last_name",
                    "email",
                    "designation",
                    "department_name"
                ]
            )

        finally:

            cursor.close()
            connection.close()

    else:

        st.warning("Database unavailable.")

# ==========================================================
# 20. SYSTEM STATUS PAGE
# ==========================================================

elif selected_page == "⚙️ System Status":

    st.subheader("⚙️ System Status")

    st.markdown("### Component Status")

    if database_connected:

        st.success("MySQL Database: Connected")

    else:

        st.error("MySQL Database: Disconnected")

        if database_error:
            st.code(database_error)

    if DOCUMENT_FOLDER.exists():

        st.success(
            f"Policy Documents: {document_count} found"
        )

    else:

        st.error("Policy Documents: Folder unavailable")

    st.success("AI Workflow: LangGraph configured")

    st.success("Vector Database: ChromaDB configured")

    st.success("LLM Provider: Groq configured")

    st.info("Selected Model: openai/gpt-oss-120b")

    st.info(
        "Embedding Model: sentence-transformers/all-MiniLM-L6-v2"
    )

# ==========================================================
# 21. FOOTER
# ==========================================================

st.divider()

st.markdown(
    """
    <div style="
        text-align:center;
        color:#7c8da5;
        font-size:12px;
        padding:10px;
    ">
        © 2026 Veltrionyx |
        Enterprise Agentic AI Knowledge Assistant
    </div>
    """,
    unsafe_allow_html=True
)