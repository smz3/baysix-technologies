"""
Migration 023 — rebuild execution.db from the re-locked 12-table schema.

The old execution.db is D0-era and obsolete (43 D0-parity d3_signals, the JM-DEMO-ORB
D0 deployment, the biased $50 tester run, and the misplaced tester_runs/tester_trades
from migration 021 — tester now lives in research.db, migration 022). Nothing precious.

This renames the old file aside (execution.db.d0obsolete — a safety net, not a hard
delete) and recreates execution.db from research.code.execution._SCHEMA (12 tables:
d1_accounts, d1_instruments, d1_deployments, d2_deploy_gates, d3_signals, d3_orders, d3_fills, d3_trades,
d4_equity_snapshots, d5_recon_results, log_deploy, log_incidents).

Spec: braindump/execution_schema.md (RE-LOCKED 2026-06-11, two databases).
Run: python research/migrations/023_rebuild_execution_db.py
"""
import sys
import sqlite3
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from research.code import execution

DB = Path(__file__).resolve().parents[1] / "db" / "execution.db"

_EXPECTED = {
    "d1_accounts", "d1_instruments", "d1_deployments", "d2_deploy_gates",
    "d3_signals", "d3_orders", "d3_fills", "d3_trades",
    "d4_equity_snapshots", "d5_recon_results", "log_deploy", "log_incidents",
}


def main():
    if DB.exists():
        aside = DB.with_suffix(".db.d0obsolete")
        if aside.exists():
            aside.unlink()
        DB.rename(aside)
        print(f"old execution.db moved aside -> {aside.name} (D0-era, obsolete)")

    execution.init_db()

    conn = sqlite3.connect(DB)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )}
    conn.close()

    missing = _EXPECTED - tables
    extra = tables - _EXPECTED
    assert not missing, f"missing tables after rebuild: {missing}"
    assert not extra, f"unexpected tables after rebuild: {extra}"
    print(f"execution.db rebuilt: {len(tables)} tables -> {', '.join(sorted(tables))}")
    print("migration 023 complete")


if __name__ == "__main__":
    main()
