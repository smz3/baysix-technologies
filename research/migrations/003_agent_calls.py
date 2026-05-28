"""
Migration 003 — Create agent_log.db with agent_calls table.
Tracks every QR agent invocation: gear, model used, task, papers pulled.
"""

import sqlite3
from pathlib import Path

DB = Path(__file__).parents[1] / "db" / "agent_log.db"


def up():
    DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS agent_calls (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            idea_id    INTEGER,
            idea_code  TEXT,
            gear       TEXT NOT NULL,
            model      TEXT NOT NULL,
            task       TEXT,
            papers     TEXT DEFAULT '[]',
            timestamp  TEXT
        )
    """)
    conn.commit()
    conn.close()
    print(f"Migration 003 applied — agent_calls table created in {DB}")


if __name__ == "__main__":
    up()
