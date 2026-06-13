"""
Migration 020 — create execution.db (the downstream twin of research.db).

Thin wrapper over research.code.execution.init_db(): builds all 10 tables from the
canonical _SCHEMA. Additive + idempotent (CREATE TABLE IF NOT EXISTS throughout) —
safe to re-run. Creates research/db/execution.db.

Spec: docs/reference/execution_schema.md. Build task: log_tasks #31.

Run: python research/migrations/020_create_execution_db.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from research.code import execution


def main():
    path = execution.init_db()
    # report what was built
    import sqlite3
    conn = sqlite3.connect(path)
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' "
        "ORDER BY name"
    ).fetchall()]
    conn.close()
    print(f"execution.db has {len(tables)} tables: {', '.join(tables)}")


if __name__ == "__main__":
    main()
