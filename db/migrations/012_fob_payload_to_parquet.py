"""Migration 012 — task 229 Lever 2: move the raw FOB payload out of research.db.

For every run present in fob_cycles: export its raw rows to Parquet-per-run
(core.io.fob_payload.export_run), VERIFY the Parquet row counts equal the
DB row counts, then clear the DB rows (tester.clear_fob_payload_run). Finally VACUUM
so the file shrinks. research.db keeps the run headers (tester_runs) + rollup
(fob_run_stats). Fully reversible — source of truth is the emit CSV on G:\\My Drive.

Idempotent-ish: a run whose rows are already cleared (0 in DB) is skipped. Safe to
re-run. Aborts a run's clear if the Parquet verify fails (never deletes unverified).

Run:  python db/migrations/012_fob_payload_to_parquet.py
"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from core.io import fob_payload, tester

DB = tester.DB_PATH


def _size_mb() -> float:
    return DB.stat().st_size / (1024 * 1024)


def _db_counts(conn, run_id):
    return {
        "cycles": conn.execute("SELECT COUNT(*) FROM fob_cycles WHERE run_id=?", (run_id,)).fetchone()[0],
        "zones":  conn.execute("SELECT COUNT(*) FROM fob_zones  WHERE run_id=?", (run_id,)).fetchone()[0],
        "events": conn.execute("SELECT COUNT(*) FROM fob_events WHERE run_id=?", (run_id,)).fetchone()[0],
    }


def main():
    print(f"=== migration 012: FOB payload -> Parquet ===")
    print(f"research.db before: {_size_mb():.1f} MB")

    conn = sqlite3.connect(DB)
    runs = [r[0] for r in conn.execute(
        "SELECT DISTINCT run_id FROM fob_cycles ORDER BY run_id").fetchall()]
    if not runs:
        print("no runs with raw payload in fob_cycles — nothing to migrate.")
    for run_id in runs:
        db_n = _db_counts(conn, run_id)
        if sum(db_n.values()) == 0:
            print(f"run {run_id}: already cleared (0 rows) — skip")
            continue

        print(f"\nrun {run_id}: DB rows cycles/zones/events = "
              f"{db_n['cycles']}/{db_n['zones']}/{db_n['events']}")
        pq_n = fob_payload.export_run(run_id)
        print(f"run {run_id}: Parquet rows -> {pq_n['cycles']}/{pq_n['zones']}/{pq_n['events']} "
              f"@ {fob_payload.run_dir(run_id)}")

        # VERIFY before deleting anything
        if pq_n != db_n:
            raise SystemExit(
                f"ABORT run {run_id}: Parquet counts {pq_n} != DB counts {db_n}. "
                "Nothing cleared — investigate before re-running.")
        print(f"run {run_id}: verify OK (Parquet == DB) — clearing DB rows")
        tester.clear_fob_payload_run(run_id)
    conn.close()

    tester.vacuum()
    print(f"\nresearch.db after : {_size_mb():.1f} MB")
    print(f"Parquet runs on disk: {fob_payload.available_runs()}")
    print("done.")


if __name__ == "__main__":
    main()
