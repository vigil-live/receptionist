import sqlite3
from contextlib import contextmanager
from datetime import datetime
import uuid

DB_PATH="emergency.db"
@contextmanager
def get_db():
    conn=sqlite3.connect(DB_PATH)
    conn.row_factory=sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
    finally:
        conn.close()

def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS calls (
                call_id TEXT PRIMARY KEY,
                caller_number TEXT,
                caller_name TEXT,
                location_raw TEXT,
                latitude REAL,
                longitude REAL,
                priority INTEGER,
                emergency_type TEXT,
                status TEXT DEFAULT 'active',
                injuries_reported BOOLEAN,
                hazards_present TEXT,
                num_people_affected INTEGER,
                call_start TEXT,
                call_end TEXT,
                pdf_path TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS transcript_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                call_id TEXT,
                speaker TEXT,
                message TEXT,
                timestamp TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (call_id) REFERENCES calls(call_id)
            );

            CREATE TABLE IF NOT EXISTS dispatches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                call_id TEXT,
                dispatch_type TEXT,
                dispatched_at TEXT DEFAULT (datetime('now')),
                dispatched_by TEXT,
                FOREIGN KEY (call_id) REFERENCES calls(call_id)
            );
        """)
def create_call(call_id: str, caller_number: str):
    with get_db() as conn:
        conn.execute("""
            INSERT INTO calls (call_id, caller_number, call_start)
            VALUES (?, ?, ?)
        """, (call_id, caller_number, datetime.now().isoformat()))
def update_call(call_id: str, **kwargs):
    if not kwargs:
        return
    fields = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [call_id]
    with get_db() as conn:
        conn.execute(f"UPDATE calls SET {fields} WHERE call_id = ?", values)

def get_call(call_id: str):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM calls WHERE call_id = ?", (call_id,)
        ).fetchone()
        return dict(row) if row else None

def get_all_active_calls():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM calls WHERE status = 'active' ORDER BY priority ASC"
        ).fetchall()
        return [dict(r) for r in rows]

def end_call(call_id: str):
    update_call(call_id, status='ended', call_end=datetime.now().isoformat())

def add_transcript_entry(call_id: str, speaker: str, message: str):
    with get_db() as conn:
        conn.execute("""
            INSERT INTO transcript_entries (call_id, speaker, message)
            VALUES (?, ?, ?)
        """, (call_id, speaker, message))

def get_transcript(call_id: str):
    with get_db() as conn:
        rows = conn.execute("""
            SELECT speaker, message, timestamp
            FROM transcript_entries
            WHERE call_id = ?
            ORDER BY timestamp ASC
        """, (call_id,)).fetchall()
        return [dict(r) for r in rows]

def add_dispatch(call_id: str, dispatch_type: str, dispatched_by: str = "operator"):
    with get_db() as conn:
        conn.execute("""
            INSERT INTO dispatches (call_id, dispatch_type, dispatched_by)
            VALUES (?, ?, ?)
        """, (call_id, dispatch_type, dispatched_by))

def get_dispatches(call_id: str):
    with get_db() as conn:
        rows = conn.execute("""
            SELECT dispatch_type, dispatched_at, dispatched_by
            FROM dispatches WHERE call_id = ?
        """, (call_id,)).fetchall()
        return [dict(r) for r in rows]       