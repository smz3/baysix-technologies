"""
Migration 015 — Rename the three cross-cutting log tables (drop the stepN_ prefix).

The stepN_ prefix encodes pipeline order, which is real for step1_ideas..step4_results
but misleading for the cross-cutting logs (written throughout, not at a "step"). They
get a clean log_ namespace:

    step5_agent_log    -> log_agent
    step6_backlog      -> log_tasks
    step7_strategy_log -> log_strategy

Pipeline tables (step1..step4) are unchanged. No table is referenced by any FK, so
renaming is FK-safe. The only dependent object is the open_backlog VIEW (on the
backlog table) — recreated on the new name below.

Safe to re-run — each rename is guarded on table existence.
Run: python research/migrations/015_rename_logs.py
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parents[1] / "db" / "research.db"

RENAMES = [
    ("step5_agent_log",    "log_agent"),
    ("step6_backlog",      "log_tasks"),
    ("step7_strategy_log", "log_strategy"),
]


def run():
    conn = sqlite3.connect(DB_PATH)   # FK pragma left OFF — pure DDL rename
    cur = conn.cursor()

    tables = {r[0] for r in cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}

    for old, new in RENAMES:
        if new in tables:
            print(f"  {new:14} already exists — skip")
        elif old in tables:
            cur.execute(f"ALTER TABLE {old} RENAME TO {new}")
            print(f"  renamed {old:18} -> {new}")
        else:
            print(f"  {old:18} not found — skip")

    # The open_backlog view referenced step6_backlog — recreate it on log_tasks.
    cur.executescript("""
        DROP VIEW IF EXISTS open_backlog;
        CREATE VIEW open_backlog AS
        SELECT b.task_id, b.idea_id, i.name AS idea_name, b.title,
               b.kind, b.priority, b.status,
               CAST((julianday('now') - julianday(b.created_at)) AS INTEGER) AS age_days
        FROM log_tasks b
        LEFT JOIN step1_ideas i ON i.idea_id = b.idea_id
        WHERE b.status IN ('open','in_progress')
        ORDER BY b.priority ASC, b.created_at ASC;
    """)
    conn.commit()

    final = {r[0] for r in cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    ok = all(new in final for _, new in RENAMES) and \
         not any(old in final for old, _ in RENAMES)
    print(f"[015] rename {'OK' if ok else '*** INCOMPLETE'} — "
          f"log_agent/log_tasks/log_strategy present; open_backlog view rebuilt.")
    conn.close()


if __name__ == "__main__":
    run()
