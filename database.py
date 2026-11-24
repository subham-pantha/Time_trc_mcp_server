
"""
TimeTrack's persistence layer -- MySQL, shared by every tool in this
project. Migrated from the original SQLite implementation.
"""

import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
import os

load_dotenv()


def get_connection():
    try:
        connection = mysql.connector.connect(
            host="xv53rk.h.filess.io",
            database="Client_mcp_use_terribleof",
            user="Client_mcp_use_terribleof",
            password="b01471149f40d70350a3790b2dc9037060d6fb36",
            port="61031"
        )

        if connection.is_connected():
            return connection

    except Error as e:
        print("Error while connecting to MySQL:", e)

    return None


def init_db():
    conn = get_connection()

    if conn is None:
        raise ConnectionError("Could not connect to MySQL database")

    try:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS time_entries (
                id INT AUTO_INCREMENT PRIMARY KEY,
                employee_name VARCHAR(255) NOT NULL,
                project VARCHAR(255) NOT NULL,
                entry_date DATE NOT NULL,
                hours DECIMAL(10, 2) NOT NULL,
                description TEXT NOT NULL DEFAULT ''
            )
        """)

        cursor.execute("SELECT COUNT(*) FROM time_entries")
        count = cursor.fetchone()[0]

        if count == 0:
            seed = [
                ("Asha Patel", "Website Redesign", "2026-09-08", 6.5, "Homepage layout"),
                ("Asha Patel", "Website Redesign", "2026-09-09", 7.0, "Mobile responsive fixes"),
                ("Asha Patel", "Client Onboarding", "2026-09-10", 3.0, "Kickoff call + notes"),
                ("Rahul Mehta", "Website Redesign", "2026-09-08", 5.5, "API integration"),
                ("Rahul Mehta", "Internal Tools", "2026-09-09", 8.0, "Dashboard bug fixes"),
            ]

            cursor.executemany(
                """
                INSERT INTO time_entries
                (employee_name, project, entry_date, hours, description)
                VALUES (%s, %s, %s, %s, %s)
                """,
                seed,
            )

            conn.commit()

    except Error as e:
        conn.rollback()
        raise RuntimeError(f"Database initialization failed: {e}") from e

    finally:
        cursor.close()
        conn.close()


def _row_to_dict(row) -> dict:
    return {
        "id": row["id"],
        "employee_name": row["employee_name"],
        "project": row["project"],
        "entry_date": str(row["entry_date"]),
        "hours": float(row["hours"]),
        "description": row["description"],
    }


def list_all_entries() -> list[dict]:
    conn = get_connection()

    if conn is None:
        raise ConnectionError("Could not connect to MySQL database")

    try:
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM time_entries ORDER BY entry_date DESC, id DESC"
        )

        rows = cursor.fetchall()

        return [_row_to_dict(r) for r in rows]

    finally:
        cursor.close()
        conn.close()


def log_time(
    employee_name: str,
    project: str,
    entry_date: str,
    hours: float,
    description: str = ""
) -> dict:

    if hours <= 0:
        raise ValueError("hours must be a positive number")

    conn = get_connection()

    if conn is None:
        raise ConnectionError("Could not connect to MySQL database")

    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO time_entries
            (employee_name, project, entry_date, hours, description)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (employee_name, project, entry_date, hours, description),
        )

        conn.commit()

        new_id = cursor.lastrowid

        cursor.close()

        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM time_entries WHERE id = %s",
            (new_id,)
        )

        row = cursor.fetchone()

        return _row_to_dict(row)

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()


def get_timesheet(
    employee_name: str,
    start_date: str | None = None,
    end_date: str | None = None
) -> list[dict]:

    conn = get_connection()

    if conn is None:
        raise ConnectionError("Could not connect to MySQL database")

    try:
        cursor = conn.cursor(dictionary=True)

        query = "SELECT * FROM time_entries WHERE employee_name = %s"
        params = [employee_name]

        if start_date:
            query += " AND entry_date >= %s"
            params.append(start_date)

        if end_date:
            query += " AND entry_date <= %s"
            params.append(end_date)

        query += " ORDER BY entry_date"

        cursor.execute(query, params)

        rows = cursor.fetchall()

        return [_row_to_dict(r) for r in rows]

    finally:
        cursor.close()
        conn.close()


def list_projects() -> list[str]:

    conn = get_connection()

    if conn is None:
        raise ConnectionError("Could not connect to MySQL database")

    try:
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT DISTINCT project FROM time_entries ORDER BY project"
        )

        rows = cursor.fetchall()

        return [r["project"] for r in rows]

    finally:
        cursor.close()
        conn.close()


def get_project_summary(project: str) -> dict:

    conn = get_connection()

    if conn is None:
        raise ConnectionError("Could not connect to MySQL database")

    
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT employee_name, SUM(hours) AS total_hours
        FROM time_entries
        WHERE project = %s
        GROUP BY employee_name
        ORDER BY employee_name
        """,
        (project,),
    )

    rows = cursor.fetchall()

    if not rows:
        raise ValueError(
            f"No time logged against project '{project}'"
        )

    by_employee = {
        r["employee_name"]: float(r["total_hours"])
        for r in rows
    }

    return {
        "project": project,
        "total_hours": sum(by_employee.values()),
        "by_employee": by_employee,
    }

    # finally:
    #     cursor.close()
    #     conn.close()
