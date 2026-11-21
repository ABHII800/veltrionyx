"""Copy your local MySQL database to a cloud MySQL database (TiDB Cloud).

Put this file in the project root (next to .env) and run:

    python copy_db_to_cloud.py

Local database  -> read from your .env (MYSQL_HOST, MYSQL_USER, ...)
Cloud database  -> asked when you run it. The password is typed
                   hidden and is not saved anywhere.

Your local database is only READ. Nothing in it is changed.
"""

import getpass
import os
import re
import sys
from pathlib import Path

import certifi
import mysql.connector
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

BATCH_SIZE = 500


# --------------------------------------------------
# Small helpers (no database needed)
# --------------------------------------------------

def strip_foreign_keys(ddl):
    """Remove FOREIGN KEY lines from a CREATE TABLE statement."""

    lines = [
        line
        for line in ddl.splitlines()
        if not re.match(r"\s*CONSTRAINT\s+.*FOREIGN KEY", line, re.I)
    ]

    # The line before the closing bracket must not end with a comma.
    for i in range(len(lines) - 1):
        if lines[i + 1].lstrip().startswith(")"):
            lines[i] = lines[i].rstrip().rstrip(",")

    return "\n".join(lines)


def simple_collation(ddl):
    """Replace the newest MySQL 8 collations with an older, widely
    supported one."""

    return re.sub(r"utf8mb4_0900_\w+", "utf8mb4_general_ci", ddl)


def order_tables(tables, depends_on):
    """Put tables that others point to first (departments before
    employees). depends_on maps a table to the tables it points to."""

    ordered = []
    waiting = list(tables)

    while waiting:

        ready = [
            t for t in waiting
            if all(
                d in ordered or d == t or d not in tables
                for d in depends_on.get(t, [])
            )
        ]

        # A circular link: just continue in the original order.
        if not ready:
            ready = [waiting[0]]

        for t in ready:
            ordered.append(t)
            waiting.remove(t)

    return ordered


def ask(label, default=None, secret=False):

    suffix = f" [{default}]" if default else ""
    prompt = f"{label}{suffix}: "

    value = getpass.getpass(prompt) if secret else input(prompt)
    value = value.strip()

    return value or default


# --------------------------------------------------
# Connections
# --------------------------------------------------

def connect_local():

    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE"),
    )


def connect_cloud():

    print("\nCloud database details (from the TiDB Cloud 'Connect' window):")

    host = ask("  Host")
    port = int(ask("  Port", "4000"))
    user = ask("  Username (looks like xxxxxxx.root)")
    # Ctrl+V often does not paste into a hidden password prompt on
    # Windows. So the password can also come from CLOUD_MYSQL_PASSWORD
    # (set it in the terminal first - see the steps).
    password = os.getenv("CLOUD_MYSQL_PASSWORD")

    if password:
        print("  Password: taken from CLOUD_MYSQL_PASSWORD")
    else:
        password = ask(
            "  Password (right-click to paste; nothing shows)",
            secret=True
        )

    # Only the length is shown, never the password. A TiDB password
    # is usually 16 characters, so a very different number means
    # the paste did not work.
    print(f"  (username: {user} | password length: {len(password or '')})")

    connection = mysql.connector.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        use_pure=True,
        ssl_ca=certifi.where(),
        ssl_verify_cert=True,
        ssl_verify_identity=True,
        connection_timeout=20,
    )

    return connection


# --------------------------------------------------
# Copy
# --------------------------------------------------

def table_names(cursor):

    cursor.execute("SHOW FULL TABLES WHERE Table_type = 'BASE TABLE'")

    return [row[0] for row in cursor.fetchall()]


def foreign_key_map(cursor, database):

    cursor.execute(
        "SELECT TABLE_NAME, REFERENCED_TABLE_NAME "
        "FROM information_schema.KEY_COLUMN_USAGE "
        "WHERE TABLE_SCHEMA = %s AND REFERENCED_TABLE_NAME IS NOT NULL",
        (database,)
    )

    depends_on = {}

    for table, referenced in cursor.fetchall():
        depends_on.setdefault(table, []).append(referenced)

    return depends_on


def create_table(cloud_cursor, ddl):
    """Create the table. If the cloud database rejects something,
    retry with a simpler version and say what was changed."""

    attempts = [
        ("as it is", ddl),
        ("without foreign keys", strip_foreign_keys(ddl)),
        (
            "without foreign keys and with an older collation",
            simple_collation(strip_foreign_keys(ddl))
        ),
    ]

    last_error = None

    for note, statement in attempts:

        try:
            cloud_cursor.execute(statement)

            if note != "as it is":
                print(f"    (created {note})")

            return

        except mysql.connector.Error as error:
            last_error = error

    raise last_error


def copy_table(local, cloud, table):

    local_cursor = local.cursor()
    cloud_cursor = cloud.cursor()

    local_cursor.execute(f"SHOW CREATE TABLE `{table}`")
    ddl = local_cursor.fetchall()[0][1]

    cloud_cursor.execute(f"DROP TABLE IF EXISTS `{table}`")
    create_table(cloud_cursor, ddl)

    local_cursor.execute(f"SELECT * FROM `{table}`")

    columns = [f"`{name}`" for name in local_cursor.column_names]

    insert = (
        f"INSERT INTO `{table}` ({', '.join(columns)}) "
        f"VALUES ({', '.join(['%s'] * len(columns))})"
    )

    copied = 0

    while True:

        rows = local_cursor.fetchmany(BATCH_SIZE)

        if not rows:
            break

        cloud_cursor.executemany(insert, rows)
        copied += len(rows)

    cloud.commit()

    local_cursor.close()
    cloud_cursor.close()

    return copied


def count_rows(connection, table):

    cursor = connection.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
    total = cursor.fetchall()[0][0]
    cursor.close()

    return total


def main():

    database = os.getenv("MYSQL_DATABASE") or "veltrionyx_db"

    print("Connecting to your local MySQL...")

    try:
        local = connect_local()
    except mysql.connector.Error as error:
        sys.exit(f"Could not connect to local MySQL: {error}")

    try:
        cloud = connect_cloud()
    except mysql.connector.Error as error:
        sys.exit(f"Could not connect to the cloud database: {error}")

    print("Connected to both.\n")

    cloud_name = ask("Name for the database in the cloud", database)

    answer = input(
        f"Tables with the same names inside '{cloud_name}' in the cloud "
        "will be deleted and replaced.\nType yes to continue: "
    ).strip().lower()

    if answer != "yes":
        sys.exit("Stopped. Nothing was changed.")

    cloud_cursor = cloud.cursor()
    cloud_cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{cloud_name}`")
    cloud_cursor.execute(f"USE `{cloud_name}`")
    cloud_cursor.execute("SET FOREIGN_KEY_CHECKS = 0")

    local_cursor = local.cursor()
    tables = table_names(local_cursor)
    tables = order_tables(tables, foreign_key_map(local_cursor, local.database))

    print(f"\nCopying {len(tables)} tables: {', '.join(tables)}\n")

    for table in tables:

        print(f"  {table} ...")
        copied = copy_table(local, cloud, table)
        print(f"    {copied} rows copied")

    print("\nChecking row counts (local vs cloud):\n")

    all_match = True

    for table in tables:

        here = count_rows(local, table)
        there = count_rows(cloud, table)
        match = "OK" if here == there else "DIFFERENT"

        if here != there:
            all_match = False

        print(f"  {table:<18} {here:>6} {there:>6}   {match}")

    print()

    if all_match:
        print(f"Done. Use '{cloud_name}' as MYSQL_DATABASE for the cloud app.")
    else:
        print("Some counts are different. Do not deploy yet - send me this output.")

    local.close()
    cloud.close()


if __name__ == "__main__":
    main()