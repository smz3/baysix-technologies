"""
Migration 021 — add the tester schema to execution.db (tester_runs + tester_trades).

The two tables are defined in the canonical execution._SCHEMA (single source of
truth); this migration just re-runs init_db(), which is additive + idempotent
(CREATE TABLE IF NOT EXISTS), so existing tables are untouched and the two new ones
appear. Provenance-first: every tester run records its data_source (broker_history /
dukascopy / custom) and tick model, so a run is captured, not just watched.

Spec/why: docs/reference/execution_schema.md + this session's tester discussion. Build
task: log_tasks #42 (pairs with #40, the first Dukascopy tester run).

Run: python research/migrations/021_create_tester_schema.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from research.code import execution


def main():
    path = execution.init_db()
    import sqlite3
    conn = sqlite3.connect(path)
    new = [t for t in ("tester_runs", "tester_trades")
           if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                           (t,)).fetchone()]
    cols = {t: [r[1] for r in conn.execute(f"PRAGMA table_info({t})")] for t in new}
    conn.close()
    for t in new:
        print(f"  {t}: {len(cols[t])} cols -> {', '.join(cols[t])}")
    print(f"tester schema present: {', '.join(new)}")


if __name__ == "__main__":
    main()
