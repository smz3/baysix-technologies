"""
Migration 017 — Add 'parked' to log_tasks.status CHECK constraint.

Requested 2026-06-16: we need a *revisitable* shelf state distinct from 'dropped'
(killed/abandoned). 'parked' tasks fall off the open_backlog view (which filters
status IN ('open','in_progress')) so they don't clutter the SessionStart brief, but
stay queryable and can be un-parked later. SQLite can't alter a CHECK in place, so
this rebuilds the table (create-new / copy / drop / rename) preserving column order
(task_id, idea_id, status, ...), FK, kind/priority CHECKs, defaults, AUTOINCREMENT,
and rebuilds the dependent open_backlog VIEW.

Safe: *.bak copy first (gitignored), single transaction, idempotent (skips if
'parked' already in the status CHECK).
Run: python db/migrations/017_add_parked_task_status.py
"""

import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parents[1] / "db" / "research.db"

COLS = [
    "task_id", "idea_id", "status", "title", "detail", "kind", "priority",
    "created_at", "updated_at", "resolved_at", "resolution",
]

NEW_TABLE_DDL = """
CREATE TABLE log_tasks_new (
    task_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    idea_id     TEXT REFERENCES step1_ideas(idea_id),
    status      TEXT NOT NULL DEFAULT 'open'
                  CHECK(status IN ('open','in_progress','done','dropped','parked')),
    title       TEXT NOT NULL,
    detail      TEXT,
    kind        TEXT NOT NULL CHECK(kind IN
                  ('variant','sizing','filter','port','infra','data','cleanup')),
    priority    TEXT NOT NULL DEFAULT 'P2'
                  CHECK(priority IN ('P0','P1','P2')),
    created_at  DATETIME NOT NULL,
    updated_at  DATETIME NOT NULL,
    resolved_at DATETIME,
    resolution  TEXT
);
"""

CREATE_VIEW = """
CREATE VIEW open_backlog AS
SELECT b.task_id, b.idea_id, i.name AS idea_name, b.status, b.title,
       b.kind, b.priority,
       CAST((julianday('now') - julianday(b.created_at)) AS INTEGER) AS age_days
FROM log_tasks b
LEFT JOIN step1_ideas i ON i.idea_id = b.idea_id
WHERE b.status IN ('open','in_progress')
ORDER BY b.priority ASC, b.created_at ASC;
"""


def run():
    conn = sqlite3.connect(DB_PATH)
    conn.isolation_level = None
    cur = conn.cursor()

    ddl = cur.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='log_tasks'"
    ).fetchone()[0]
    if "'parked'" in ddl:
        print("[017] 'parked' already in status CHECK — nothing to do.")
        conn.close()
        return

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = DB_PATH.with_suffix(f".pre017_{stamp}.bak")
    shutil.copy2(DB_PATH, bak)
    print(f"  backup -> {bak.name}")

    row_count = cur.execute("SELECT COUNT(*) FROM log_tasks").fetchone()[0]
    max_id = cur.execute("SELECT COALESCE(MAX(task_id), 0) FROM log_tasks").fetchone()[0]

    cur.execute("PRAGMA foreign_keys=OFF")
    try:
        cur.execute("BEGIN")
        cur.execute("DROP VIEW IF EXISTS open_backlog")
        cur.execute(NEW_TABLE_DDL)
        collist = ", ".join(COLS)
        cur.execute(
            f"INSERT INTO log_tasks_new ({collist}) SELECT {collist} FROM log_tasks")
        cur.execute("DROP TABLE log_tasks")
        cur.execute("ALTER TABLE log_tasks_new RENAME TO log_tasks")
        cur.execute("DELETE FROM sqlite_sequence WHERE name='log_tasks'")
        cur.execute("INSERT INTO sqlite_sequence(name, seq) VALUES ('log_tasks', ?)", (max_id,))
        cur.execute(CREATE_VIEW)
        cur.execute("COMMIT")
    except Exception:
        cur.execute("ROLLBACK")
        conn.close()
        raise
    finally:
        cur.execute("PRAGMA foreign_keys=ON")

    new_count = cur.execute("SELECT COUNT(*) FROM log_tasks").fetchone()[0]
    fk_ok = not cur.execute("PRAGMA foreign_key_check(log_tasks)").fetchall()
    new_ddl = cur.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='log_tasks'"
    ).fetchone()[0]
    parked_ok = "'parked'" in new_ddl
    count_ok = new_count == row_count
    ok = parked_ok and count_ok and fk_ok
    print(f"  rows  : {new_count} (was {row_count})  fk_ok={fk_ok}  parked_in_check={parked_ok}")
    print(f"[017] {'OK' if ok else '*** FAILED — restore from .bak'} — "
          f"'parked' status added; open_backlog view rebuilt.")
    conn.close()
    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    run()
