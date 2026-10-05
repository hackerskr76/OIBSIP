import sqlite3
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from contextlib import contextmanager


class DatabaseError(Exception):
    pass


DEFAULT_DB_PATH = str(Path(__file__).resolve().parent / "bmi_records.db")


@contextmanager
def get_connection(db_path: Optional[str] = None):
    path = db_path if db_path is not None else DEFAULT_DB_PATH
    conn = None
    try:
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        yield conn
        conn.commit()
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        raise DatabaseError(f"Database error on '{path}': {e}") from e
    finally:
        if conn:
            conn.close()


def init_db(db_path: Optional[str] = None) -> None:
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS bmi_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_name TEXT NOT NULL,
        weight REAL NOT NULL,
        height REAL NOT NULL,
        bmi REAL NOT NULL,
        category TEXT NOT NULL,
        timestamp TEXT NOT NULL
    );
    """
    create_index_user_sql = """
    CREATE INDEX IF NOT EXISTS idx_bmi_user_name ON bmi_records(user_name);
    """
    create_index_time_sql = """
    CREATE INDEX IF NOT EXISTS idx_bmi_timestamp ON bmi_records(timestamp);
    """

    try:
        with get_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(create_table_sql)
            cursor.execute(create_index_user_sql)
            cursor.execute(create_index_time_sql)
    except DatabaseError:
        raise
    except Exception as e:
        raise DatabaseError(f"Failed to initialize database tables: {e}") from e


def add_record(
    user_name: str,
    weight: float,
    height: float,
    bmi: float,
    category: str,
    timestamp: Optional[str] = None,
    db_path: Optional[str] = None
) -> int:
    if not user_name or not user_name.strip():
        raise ValueError("User name cannot be empty.")
    if weight <= 0 or height <= 0 or bmi <= 0:
        raise ValueError("Weight, height, and BMI must be greater than zero.")

    clean_user = user_name.strip()
    record_time = timestamp if timestamp else datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    query = """
    INSERT INTO bmi_records (user_name, weight, height, bmi, category, timestamp)
    VALUES (?, ?, ?, ?, ?, ?);
    """

    try:
        with get_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                query,
                (clean_user, round(weight, 2), round(height, 2), round(bmi, 2), category, record_time)
            )
            return cursor.lastrowid
    except DatabaseError:
        raise
    except Exception as e:
        raise DatabaseError(f"Failed to insert BMI record for '{clean_user}': {e}") from e


def get_user_records(user_name: str, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    clean_user = user_name.strip() if user_name else ""
    if not clean_user:
        return []

    query = """
    SELECT id, user_name, weight, height, bmi, category, timestamp
    FROM bmi_records
    WHERE LOWER(user_name) = LOWER(?)
    ORDER BY timestamp ASC, id ASC;
    """

    try:
        with get_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, (clean_user,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    except DatabaseError:
        raise
    except Exception as e:
        raise DatabaseError(f"Failed to fetch records for user '{clean_user}': {e}") from e


def get_all_users(db_path: Optional[str] = None) -> List[str]:
    query = """
    SELECT DISTINCT user_name
    FROM bmi_records
    ORDER BY user_name COLLATE NOCASE ASC;
    """

    try:
        with get_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            return [row["user_name"] for row in rows]
    except DatabaseError:
        raise
    except Exception as e:
        raise DatabaseError(f"Failed to fetch unique users: {e}") from e


def get_all_records(db_path: Optional[str] = None, limit: int = 500) -> List[Dict[str, Any]]:
    query = """
    SELECT id, user_name, weight, height, bmi, category, timestamp
    FROM bmi_records
    ORDER BY timestamp DESC, id DESC
    LIMIT ?;
    """

    try:
        with get_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    except DatabaseError:
        raise
    except Exception as e:
        raise DatabaseError(f"Failed to fetch all records: {e}") from e


def delete_record(record_id: int, db_path: Optional[str] = None) -> bool:
    query = "DELETE FROM bmi_records WHERE id = ?;"

    try:
        with get_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, (record_id,))
            return cursor.rowcount > 0
    except DatabaseError:
        raise
    except Exception as e:
        raise DatabaseError(f"Failed to delete record ID {record_id}: {e}") from e


def get_user_stats(user_name: str, db_path: Optional[str] = None) -> Dict[str, Any]:
    records = get_user_records(user_name, db_path)
    if not records:
        return {
            "count": 0,
            "min_bmi": None,
            "max_bmi": None,
            "latest_bmi": None,
            "latest_category": None,
            "latest_date": None,
        }

    bmis = [r["bmi"] for r in records]
    latest = records[-1]

    return {
        "count": len(records),
        "min_bmi": min(bmis),
        "max_bmi": max(bmis),
        "latest_bmi": latest["bmi"],
        "latest_category": latest["category"],
        "latest_date": latest["timestamp"],
    }


try:
    init_db()
except Exception:
    pass
