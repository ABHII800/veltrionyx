# Veltrionyx – Enterprise Agentic AI Knowledge Assistant

Starter scaffold for a document RAG + MySQL + agentic AI project.

## Setup (Windows / VS Code)

1. Extract the ZIP and open this folder in VS Code.
2. Open Terminal → New Terminal.
3. Create and activate a virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

4. Install packages:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

5. Copy `.env.example` to `.env` and enter your own local MySQL settings.
6. Test the connection:

```powershell
python test_mysql_connection.py
```

Expected database: `veltrionyx_db`. Expected tables: `departments`, `employees`, `attendance`, `leave_requests`.

This ZIP contains a starter structure and connection test, not your CSV data, documents, ChromaDB index, Colab notebook, or credentials. Copy your existing data into `data/` when ready. Never share or commit `.env`. Do not expose MySQL port 3306 publicly.
