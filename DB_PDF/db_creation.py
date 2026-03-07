import sqlite3
from contextlib import contextmanager
from datetime import datetime

DB_PATH = "emergency.db"


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    conn = sqlite3.connect(DB_PATH)
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
    conn.close()
    print(f"Database initialised at: {DB_PATH}")


def seed_sample_data():
    sample_calls = [
        {
            "call_id":             "CA001",
            "caller_number":       "+12135550182",
            "caller_name":         "Maria Gonzalez",
            "location_raw":        "1247 Maple Ave, Los Angeles, CA 90012",
            "latitude":            34.0522,
            "longitude":           -118.2437,
            "priority":            1,
            "emergency_type":      "structural collapse",
            "status":              "active",
            "injuries_reported":   1,
            "hazards_present":     "Collapsed ceiling, gas leak",
            "num_people_affected": 1,
            "call_start":          "2026-03-07 11:06:02",
            "call_end":            None,
        },
        {
            "call_id":             "CA002",
            "caller_number":       "+17035559234",
            "caller_name":         "James Park",
            "location_raw":        "88 Oakwood Blvd, Tysons, VA 22102",
            "latitude":            38.9187,
            "longitude":           -77.2311,
            "priority":            2,
            "emergency_type":      "fire",
            "status":              "active",
            "injuries_reported":   1,
            "hazards_present":     "Active fire on 2nd floor, smoke inhalation risk",
            "num_people_affected": 6,
            "call_start":          "2026-03-07 11:14:30",
            "call_end":            None,
        },
        {
            "call_id":             "CA003",
            "caller_number":       "+13105554781",
            "caller_name":         "Linda Torres",
            "location_raw":        "500 Sunset Strip, West Hollywood, CA 90069",
            "latitude":            34.0900,
            "longitude":           -118.3617,
            "priority":            3,
            "emergency_type":      "medical emergency",
            "status":              "dispatched",
            "injuries_reported":   1,
            "hazards_present":     None,
            "num_people_affected": 1,
            "call_start":          "2026-03-07 10:52:10",
            "call_end":            "2026-03-07 11:01:45",
        },
        {
            "call_id":             "CA004",
            "caller_number":       "+14085558820",
            "caller_name":         "Derek Nguyen",
            "location_raw":        "220 Mission Street, San Jose, CA 95112",
            "latitude":            37.3382,
            "longitude":           -121.8863,
            "priority":            4,
            "emergency_type":      "minor flooding",
            "status":              "ended",
            "injuries_reported":   0,
            "hazards_present":     "Water in basement, possible electrical risk",
            "num_people_affected": 3,
            "call_start":          "2026-03-07 10:30:00",
            "call_end":            "2026-03-07 10:41:22",
        },
    ]

    sample_transcripts = {
        "CA001": [
            ("caller", "Hello? Please help me, my ceiling collapsed!",                                                                               "2026-03-07 11:06:02"),
            ("ai",     "I'm here with you. You're going to be okay. Can you breathe normally?",                                                      "2026-03-07 11:06:08"),
            ("caller", "Yes I can breathe but my leg is stuck under something heavy.",                                                               "2026-03-07 11:06:20"),
            ("ai",     "Good — do NOT try to move the debris yourself. Help is already on its way to you.",                                          "2026-03-07 11:06:28"),
            ("caller", "I can also smell something, like rotten eggs.",                                                                              "2026-03-07 11:06:40"),
            ("ai",     "That is likely a gas leak. Stay as still as possible and do not use any switches or lighters. I am notifying the team now.", "2026-03-07 11:06:47"),
        ],
        "CA002": [
            ("caller", "There is a fire in my building, second floor is completely on fire!",                                                        "2026-03-07 11:14:30"),
            ("ai",     "I hear you. Is everyone out of the building?",                                                                               "2026-03-07 11:14:35"),
            ("caller", "I don't know, I think there are still people on the third floor.",                                                           "2026-03-07 11:14:42"),
            ("ai",     "Fire and rescue are being dispatched right now. Do not go back inside. What is the address?",                                "2026-03-07 11:14:48"),
            ("caller", "88 Oakwood Blvd, the apartment complex.",                                                                                    "2026-03-07 11:14:55"),
            ("ai",     "Got it. Move everyone at least 200 feet away from the building. Help will arrive in minutes.",                               "2026-03-07 11:15:02"),
        ],
        "CA003": [
            ("caller", "My father collapsed, he is not responding, I think it is his heart.",                                                        "2026-03-07 10:52:10"),
            ("ai",     "Stay calm. Is he breathing?",                                                                                                "2026-03-07 10:52:14"),
            ("caller", "I am not sure, I can barely see his chest moving.",                                                                          "2026-03-07 10:52:20"),
            ("ai",     "An ambulance is on the way. I am going to walk you through CPR right now. Can you do that?",                                 "2026-03-07 10:52:26"),
            ("caller", "Yes, yes I will try.",                                                                                                       "2026-03-07 10:52:30"),
            ("ai",     "Place the heel of your hand on the center of his chest and push down hard and fast, about 100 times per minute.",            "2026-03-07 10:52:36"),
        ],
        "CA004": [
            ("caller", "Hi, our basement is flooding from the earthquake, water is coming in fast.",                                                 "2026-03-07 10:30:00"),
            ("ai",     "Are you and your family safe and out of the basement?",                                                                      "2026-03-07 10:30:06"),
            ("caller", "Yes we are all upstairs.",                                                                                                   "2026-03-07 10:30:10"),
            ("ai",     "Good. Do not go back down there. Can you see or hear anything electrical sparking?",                                         "2026-03-07 10:30:16"),
            ("caller", "Not right now but the breaker box is down there.",                                                                           "2026-03-07 10:30:24"),
            ("ai",     "I am sending a team to assist. Stay upstairs and away from any water contact.",                                              "2026-03-07 10:30:30"),
        ],
    }

    sample_dispatches = {
        "CA001": [
            ("ambulance", "operator", "2026-03-07 11:06:35"),
            ("fire",      "operator", "2026-03-07 11:06:36"),
        ],
        "CA002": [
            ("fire",      "operator", "2026-03-07 11:14:52"),
            ("ambulance", "system",   "2026-03-07 11:14:53"),
            ("police",    "operator", "2026-03-07 11:15:10"),
        ],
        "CA003": [
            ("ambulance", "operator", "2026-03-07 10:52:28"),
        ],
        "CA004": [
            ("fire",      "operator", "2026-03-07 10:30:35"),
        ],
    }

    with get_db() as conn:
        conn.execute("DELETE FROM dispatches")
        conn.execute("DELETE FROM transcript_entries")
        conn.execute("DELETE FROM calls")

        for call in sample_calls:
            conn.execute("""
                INSERT INTO calls (
                    call_id, caller_number, caller_name, location_raw,
                    latitude, longitude, priority, emergency_type, status,
                    injuries_reported, hazards_present, num_people_affected,
                    call_start, call_end
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                call["call_id"], call["caller_number"], call["caller_name"],
                call["location_raw"], call["latitude"], call["longitude"],
                call["priority"], call["emergency_type"], call["status"],
                call["injuries_reported"], call["hazards_present"],
                call["num_people_affected"], call["call_start"], call["call_end"],
            ))

        for call_id, entries in sample_transcripts.items():
            for speaker, message, ts in entries:
                conn.execute("""
                    INSERT INTO transcript_entries (call_id, speaker, message, timestamp)
                    VALUES (?, ?, ?, ?)
                """, (call_id, speaker, message, ts))

        for call_id, dispatches in sample_dispatches.items():
            for dispatch_type, dispatched_by, dispatched_at in dispatches:
                conn.execute("""
                    INSERT INTO dispatches (call_id, dispatch_type, dispatched_by, dispatched_at)
                    VALUES (?, ?, ?, ?)
                """, (call_id, dispatch_type, dispatched_by, dispatched_at))

    print(f"Seeded {len(sample_calls)} calls with transcripts and dispatches.")


# ── CRUD helpers ──────────────────────────────────────────────────────────────

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
    update_call(call_id, status="ended", call_end=datetime.now().isoformat())


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
if __name__ == "__main__":
    init_db()
    seed_sample_data()