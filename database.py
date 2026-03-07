# database.py
import sqlite3
from datetime import datetime

DB_PATH = "transcriptions.db"

def init_db():
    """Create the database and table if they don't exist yet."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transcriptions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            text        TEXT NOT NULL,
            call_sid    TEXT,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()
    print("✅ Database ready.")

def save_transcription(text: str, call_sid: str = None):
    """Save a transcript chunk to the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO transcriptions (text, call_sid) VALUES (?, ?)",
        (text, call_sid)
    )
    conn.commit()
    conn.close()

def get_transcriptions(limit: int = 50):
    """Fetch the most recent transcriptions."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, text, call_sid, created_at FROM transcriptions ORDER BY created_at DESC LIMIT ?",
        (limit,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {"id": r[0], "text": r[1], "call_sid": r[2], "created_at": r[3]}
        for r in rows
    ]