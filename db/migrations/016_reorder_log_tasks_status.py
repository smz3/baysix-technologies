"""
Migration 016 — Move log_tasks.status next to idea_id (column reorder for readability).

Pure cosmetic reorder requested 2026-06-09: status should sit right after idea_id so
the backlog reads idea -> status -> title at a glance. SQLite can't reorder columns in
place, so this rebuilds the table (create-new / copy / drop / rename) preserving every
constraint (FK to step1_ideas, kind/priority/status CHECKs, defaults, AUTOINCREMENT) and
rebuilds the dependent open_backlog VIEW.

New column order:
    task_id, idea_id, status, title, detail, kind, priority,
    created_at, updated_at, resolved_at, resolution

Safe: makes a *.bak copy of the DB first (gitignored), wraps the rebuild in a
transaction, and is idempotent — skips if status is already the 3rd column.
Run: python db/migrations/016_reorder_log_tasks_status.py
"""

import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parents[1] / "db" / "research.db"

# Single source of truth for the desired column order.
COLS = [
    "task_id", "idea_id", "status", "title", "detail", "kind", "priority",
    "created_at", "updated_at", "resolved_at", "resolution",
]

NEW_TABLE_DDL = """
CREATE TABLE log_tasks_new (
    task_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    idea_id     TEXT REFERENCES step1_ideas(idea_id),
    status      TEXT NOT NULL DEFAULT 'open'
                  CHECK(status IN ('open','in_progress','done','dropped')),
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
    conn.isolation_level = None   # autocommit; we manage the txn manually (no executescript)
    cur = conn.cursor()

    current = [r[1] for r in cur.execute("PRAGMA table_info(log_tasks)")]
    if current[:3] == ["task_id", "idea_id", "status"]:
        print("[016] status already 3rd column — nothing to do.")
        conn.close()
        return

    # 1. Backup (gitignored *.bak)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = DB_PATH.with_suffix(f".pre016_{stamp}.bak")
    shutil.copy2(DB_PATH, bak)
    print(f"  backup -> {bak.name}")

    row_count = cur.execute("SELECT COUNT(*) FROM log_tasks").fetchone()[0]
    max_id = cur.execute("SELECT COALESCE(MAX(task_id), 0) FROM log_tasks").fetchone()[0]

    # 2. Rebuild inside a transaction. FK off during the swap (DDL on a referenced-by-none table).
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
        # Keep AUTOINCREMENT continuing past the highest existing id.
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

    # 3. Verify
    new_order = [r[1] for r in cur.execute("PRAGMA table_info(log_tasks)")]
    new_count = cur.execute("SELECT COUNT(*) FROM log_tasks").fetchone()[0]
    fk_ok = not cur.execute("PRAGMA foreign_key_check(log_tasks)").fetchall()
    order_ok = new_order == COLS
    count_ok = new_count == row_count
    ok = order_ok and count_ok and fk_ok
    print(f"  order : {new_order}")
    print(f"  rows  : {new_count} (was {row_count})  fk_ok={fk_ok}")
    print(f"[016] reorder {'OK' if ok else '*** FAILED — restore from .bak'} — "
          f"status now sits after idea_id; open_backlog view rebuilt.")
    conn.close()
    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    run()
