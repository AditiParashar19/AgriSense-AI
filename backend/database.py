
"""
database.py
------------
Handles all SQLite database operations for SoilSenseAU.

Tables:
    - crop_predictions
    - yield_predictions
    - soil_reports
    - chat_history

All functions in this module open a short-lived connection per call,
which is safe and simple for a small-to-medium Streamlit/FastAPI app.
"""

import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

# Database file lives inside backend/data/
DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DB_PATH = os.path.join(DB_DIR, "soilsense.db")


def get_connection() -> sqlite3.Connection:
    """
    Create and return a new SQLite connection with row access by column name.
    """
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """
    Initialize the database and create all required tables if they
    do not already exist. Safe to call multiple times.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Crop Recommendation predictions
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS crop_predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nitrogen REAL NOT NULL,
            phosphorus REAL NOT NULL,
            potassium REAL NOT NULL,
            temperature REAL NOT NULL,
            humidity REAL NOT NULL,
            ph REAL NOT NULL,
            rainfall REAL NOT NULL,
            predicted_crop TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    # Yield Prediction results
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS yield_predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            area TEXT NOT NULL,
            item TEXT NOT NULL,
            year INTEGER NOT NULL,
            rainfall REAL NOT NULL,
            pesticides REAL NOT NULL,
            temperature REAL NOT NULL,
            predicted_yield REAL NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    # Soil Report Analysis results
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS soil_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            session_id TEXT,
            nitrogen REAL,
            phosphorus REAL,
            potassium REAL,
            ph REAL,
            organic_carbon REAL,
            ec REAL,
            health_score REAL,
            summary TEXT,
            suggested_crops TEXT,
            suggested_fertilizers TEXT,
            soil_improvements TEXT,
            created_at TEXT NOT NULL
        )
    """)

    # Chatbot conversation history
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    _migrate_soil_reports_table(conn)
    conn.close()


def _migrate_soil_reports_table(conn: sqlite3.Connection) -> None:
    """
    Add session_id / health_score columns to soil_reports if this is an
    existing database created before those columns existed. Safe to run
    on every startup - no-ops once the columns are present.
    """
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(soil_reports)")
    existing_columns = {row["name"] for row in cursor.fetchall()}

    if "session_id" not in existing_columns:
        cursor.execute("ALTER TABLE soil_reports ADD COLUMN session_id TEXT")
    if "health_score" not in existing_columns:
        cursor.execute("ALTER TABLE soil_reports ADD COLUMN health_score REAL")

    conn.commit()


def _now() -> str:
    """Return the current timestamp as an ISO-formatted string."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# Crop Predictions


def insert_crop_prediction(nitrogen: float, phosphorus: float, potassium: float,
                            temperature: float, humidity: float, ph: float,
                            rainfall: float, predicted_crop: str) -> int:
    """Insert a new crop prediction record and return its new row id."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO crop_predictions
        (nitrogen, phosphorus, potassium, temperature, humidity, ph, rainfall, predicted_crop, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (nitrogen, phosphorus, potassium, temperature, humidity, ph, rainfall,
          predicted_crop, _now()))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id


def get_crop_predictions(limit: int = 50) -> List[Dict[str, Any]]:
    """Fetch the most recent crop predictions."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM crop_predictions ORDER BY id DESC LIMIT ?
    """, (limit,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def count_crop_predictions() -> int:
    """Return total number of crop predictions made so far."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as total FROM crop_predictions")
    total = cursor.fetchone()["total"]
    conn.close()
    return total


# -------------------------------------------------------------------
# Yield Predictions
# -------------------------------------------------------------------

def insert_yield_prediction(area: str, item: str, year: int, rainfall: float,
                             pesticides: float, temperature: float,
                             predicted_yield: float) -> int:
    """Insert a new yield prediction record and return its new row id."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO yield_predictions
        (area, item, year, rainfall, pesticides, temperature, predicted_yield, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (area, item, year, rainfall, pesticides, temperature, predicted_yield, _now()))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id


def get_yield_predictions(limit: int = 50) -> List[Dict[str, Any]]:
    """Fetch the most recent yield predictions."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM yield_predictions ORDER BY id DESC LIMIT ?
    """, (limit,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def count_yield_predictions() -> int:
    """Return total number of yield predictions made so far."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as total FROM yield_predictions")
    total = cursor.fetchone()["total"]
    conn.close()
    return total


# -------------------------------------------------------------------
# Soil Reports
# -------------------------------------------------------------------

def insert_soil_report(filename: str, session_id: Optional[str], nitrogen: Optional[float],
                        phosphorus: Optional[float], potassium: Optional[float], ph: Optional[float],
                        organic_carbon: Optional[float], ec: Optional[float], health_score: Optional[float],
                        summary: str, suggested_crops: str,
                        suggested_fertilizers: str, soil_improvements: str) -> int:
    """
    Insert a new soil report analysis record, tagged with the session_id
    it belongs to, and return its new row id.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO soil_reports
        (filename, session_id, nitrogen, phosphorus, potassium, ph, organic_carbon, ec, health_score,
         summary, suggested_crops, suggested_fertilizers, soil_improvements, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (filename, session_id, nitrogen, phosphorus, potassium, ph, organic_carbon, ec, health_score,
          summary, suggested_crops, suggested_fertilizers, soil_improvements, _now()))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id


def get_soil_reports(limit: int = 50) -> List[Dict[str, Any]]:
    """Fetch the most recent soil report analyses."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM soil_reports ORDER BY id DESC LIMIT ?
    """, (limit,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def count_soil_reports() -> int:
    """Return total number of soil reports uploaded so far."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as total FROM soil_reports")
    total = cursor.fetchone()["total"]
    conn.close()
    return total


# -------------------------------------------------------------------
# Chat History
# -------------------------------------------------------------------

def insert_chat_message(session_id: str, question: str, answer: str) -> int:
    """Insert a new chatbot Q&A record and return its new row id."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO chat_history (session_id, question, answer, created_at)
        VALUES (?, ?, ?, ?)
    """, (session_id, question, answer, _now()))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id


def get_chat_history(session_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Fetch recent chat history. If session_id is provided, only messages
    from that session are returned (in chronological order); otherwise
    the most recent messages across all sessions are returned.
    """
    conn = get_connection()
    cursor = conn.cursor()
    if session_id:
        cursor.execute("""
            SELECT * FROM chat_history WHERE session_id = ? ORDER BY id ASC LIMIT ?
        """, (session_id, limit))
    else:
        cursor.execute("""
            SELECT * FROM chat_history ORDER BY id DESC LIMIT ?
        """, (limit,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def count_chat_sessions() -> int:
    """Return total number of distinct chat sessions."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(DISTINCT session_id) as total FROM chat_history")
    total = cursor.fetchone()["total"]
    conn.close()
    return total


# -------------------------------------------------------------------
# Dashboard summary
# -------------------------------------------------------------------

def get_dashboard_summary() -> Dict[str, Any]:
    """
    Return aggregate counts and recent activity used to populate
    the Streamlit dashboard page.
    """
    return {
        "total_crop_predictions": count_crop_predictions(),
        "total_yield_predictions": count_yield_predictions(),
        "total_soil_reports": count_soil_reports(),
        "total_chat_sessions": count_chat_sessions(),
        "recent_crop_predictions": get_crop_predictions(limit=5),
        "recent_yield_predictions": get_yield_predictions(limit=5),
        "recent_soil_reports": get_soil_reports(limit=5),
        "recent_chat_messages": get_chat_history(limit=5),
    }


init_db()
