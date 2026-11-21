import os
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv

# Load project environment variables (.env on your PC).
# On a server the same names are set as environment variables.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


def get_db_connection():
    """Open a new MySQL connection using the MYSQL_* settings."""

    settings = {
        "host": os.getenv("MYSQL_HOST", "localhost"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "database": os.getenv("MYSQL_DATABASE"),
        "user": os.getenv("MYSQL_USER"),
        "password": os.getenv("MYSQL_PASSWORD"),
        "connection_timeout": 10,
    }

    # Cloud databases (TiDB Cloud) require an encrypted connection.
    # Setting MYSQL_SSL_CA turns it on; leave it empty on your PC.
    ssl_ca = os.getenv("MYSQL_SSL_CA")

    # MYSQL_SSL_CA=certifi means "use the certificate list that comes
    # with Python's certifi package" (works on Windows and on servers).
    if ssl_ca and ssl_ca.strip().lower() == "certifi":
        import certifi
        ssl_ca = certifi.where()

    if ssl_ca:
        settings["use_pure"] = True
        settings["ssl_ca"] = ssl_ca
        settings["ssl_verify_cert"] = True
        settings["ssl_verify_identity"] = True

    return mysql.connector.connect(**settings)
