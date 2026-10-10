"""Local SQLite store: single-user demo, no accounts. Data never leaves the machine."""
import json
import sqlite3
from pathlib import Path


class Store:
    def __init__(self, path: str | Path = "ai4human.db") -> None:
        self.conn = sqlite3.connect(str(path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS profile (id INTEGER PRIMARY KEY CHECK (id = 1), data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS checkin (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              day TEXT NOT NULL DEFAULT (date('now')),
              weight_kg REAL, sleep_hours REAL, mood INTEGER, stress INTEGER, workout_done INTEGER, notes TEXT
            );
            """
        )

    def get_profile(self) -> dict:
        row = self.conn.execute("SELECT data FROM profile WHERE id = 1").fetchone()
        return json.loads(row["data"]) if row else {}

    def set_profile(self, data: dict) -> None:
        self.conn.execute(
            "INSERT INTO profile (id, data) VALUES (1, ?) ON CONFLICT(id) DO UPDATE SET data = excluded.data",
            (json.dumps(data),),
        )
        self.conn.commit()

    def add_checkin(self, **fields) -> None:
        cols = ("weight_kg", "sleep_hours", "mood", "stress", "workout_done", "notes")
        self.conn.execute(
            f"INSERT INTO checkin ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
            tuple(fields.get(c) for c in cols),
        )
        self.conn.commit()

    def recent_checkins(self, n: int = 14) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM checkin ORDER BY id DESC LIMIT ?", (n,)).fetchall()
        return [dict(r) for r in reversed(rows)]

    def delete_all(self) -> None:
        self.conn.executescript("DELETE FROM profile; DELETE FROM checkin;")
        self.conn.commit()
