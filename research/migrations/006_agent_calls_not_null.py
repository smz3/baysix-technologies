"""
Migration 006 — Enforce NOT NULL on agent_calls.idea_id and agent_calls.idea_code.

SQLite cannot ALTER COLUMN to add NOT NULL constraints.
Safe path: recreate the table with the new constraints, copy all rows, drop old, rename.

Pre-condition: all existing rows must have non-NULL idea_id and idea_code.
The migration verifies this before proceeding and aborts if violated.
"""

import sqlite3
from pathlib import Path

DB = Path(__file__).parents[1] / "db" / "agent_log.db"


def up():
    conn = sqlite3.connect(DB)
    conn.execute("PRAGMA foreign_keys = OFF")

    # Pre-condition check
    nulls = conn.execute(
        "SELECT id FROM agent_calls WHERE idea_id IS NULL OR idea_code IS NULL"
    ).fetchall()
    if nulls:
        conn.close()
        raise RuntimeError(
            f"Migration 006 aborted — {len(nulls)} rows still have NULL idea_id or idea_code: "
            + str([r[0] for r in nulls])
            + ". Backfill these first."
        )
    print(f"Pre-condition OK — all {conn.execute('SELECT COUNT(*) FROM agent_calls').fetchone()[0]} rows have non-NULL idea_id and idea_code.")

    conn.executescript("""
        BEGIN;

        CREATE TABLE agent_calls_new (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            idea_id    INTEGER NOT NULL,
            idea_code  TEXT    NOT NULL,
            gear       TEXT    NOT NULL,
            model      TEXT    NOT NULL,
            task       TEXT,
            timestamp  TEXT
        );

        INSERT INTO agent_calls_new (id, idea_id, idea_code, gear, model, task, timestamp)
        SELECT id, idea_id, idea_code, gear, model, task, timestamp
        FROM agent_calls;

        DROP TABLE agent_calls;

        ALTER TABLE agent_calls_new RENAME TO agent_calls;

        COMMIT;
    """)

    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()

    print("\n--- agent_calls schema after migration ---")
    for row in conn.execute("PRAGMA table_info(agent_calls)"):
        notnull = "NOT NULL" if row[3] else "nullable"
        print(f"  {row[1]:12s}  {row[2]:10s}  {notnull}")

    print("\n--- agent_calls rows ---")
    for row in conn.execute("SELECT id, idea_id, idea_code, gear, model, timestamp FROM agent_calls ORDER BY id"):
        print(f"  {row}")

    conn.close()
    print("\nMigration 006 complete.")


if __name__ == "__main__":
    up()
