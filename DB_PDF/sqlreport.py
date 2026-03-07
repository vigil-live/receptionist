import sqlite3
from pdf_generation import generate_report

DB_PATH = "emergency.db"


def create_report_from_db(call_id: str) -> str:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    call_row = conn.execute(
        "SELECT * FROM calls WHERE call_id = ?", (call_id,)
    ).fetchone()
    if not call_row:
        conn.close()
        raise ValueError(f"No call found with id: {call_id}")
    call_data = dict(call_row)
    transcript_rows = conn.execute("""
        SELECT speaker, message, timestamp
        FROM transcript_entries
        WHERE call_id = ?
        ORDER BY timestamp ASC
    """, (call_id,)).fetchall()
    transcript = [dict(r) for r in transcript_rows]
    dispatch_rows = conn.execute("""
        SELECT dispatch_type, dispatched_at, dispatched_by
        FROM dispatches
        WHERE call_id = ?
    """, (call_id,)).fetchall()
    dispatches = [dict(r) for r in dispatch_rows]

    conn.close()

    path = generate_report(call_data, transcript, dispatches)
    return path


if __name__ == "__main__":
    call_id = "CA003"
    path = create_report_from_db(call_id)
    print(f"Report generated: {path}")