import sqlite3

DB_PATH = "transcriptions.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transcriptions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            text        TEXT NOT NULL,
            call_sid    TEXT,
            role        TEXT DEFAULT 'caller',
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    try:
        cursor.execute("ALTER TABLE transcriptions ADD COLUMN role TEXT DEFAULT 'caller'")
    except Exception:
        pass
    conn.commit()
    conn.close()
    print("Database ready.")

def save_transcription(text: str, call_sid: str = None, role: str = "caller"):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO transcriptions (text, call_sid, role) VALUES (?, ?, ?)",
        (text, call_sid, role)
    )
    conn.commit()
    conn.close()

def get_transcriptions(limit: int = 50):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, text, call_sid, role, created_at FROM transcriptions ORDER BY created_at DESC LIMIT ?",
        (limit,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {"id": r[0], "text": r[1], "call_sid": r[2], "role": r[3], "created_at": r[4]}
        for r in rows
    ]