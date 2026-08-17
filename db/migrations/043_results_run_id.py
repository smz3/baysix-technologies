"""043 — link step4_results to a runs row (task 364 call 3, Syafiq's ruling 2026-08-16).

THE RULING: back-fill, not forward-only.

WHY THE LINK HAS TO EXIST FOR THE BACK-FILL TO MEAN ANYTHING
Migration 042 gave the spine a `runs` table but no way to say which measurements came
out of which run. Without that column a back-filled run row is decoration — you can read
it, but you cannot get from a number back to the search that produced it. This adds the
one nullable column that makes the join possible.

WHAT THIS IS *NOT*
This is not the promotion function (task 364 call 2, still undecided and unspecified).
It adds a column and nothing else — no trigger, no automatic copying, no rule about who
writes it. Filling it stays a deliberate call by the code layer.

NULLABLE ON PURPOSE
63 of the 71 existing result rows predate any run registry and will never have one.
Making the column NOT NULL would mean inventing a run for each of them, which is the
same mistake task 352 nearly made with idea_id — a fabricated owner is worse than an
absent one, because a filter learns to trust it.

Run: python db/migrations/043_results_run_id.py
"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from core.infra.db_path import DB_PATH  # noqa: E402


def main():
    conn = sqlite3.connect(DB_PATH)

    cols = [r[1] for r in conn.execute("PRAGMA table_info(step4_results)")]
    if "run_id" in cols:
        print("ABORT: step4_results.run_id already exists — 043 has already run.")
        return 1
    if not conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='runs'"
    ).fetchone()[0]:
        print("ABORT: table `runs` is missing — run 042 first.")
        return 1

    # SQLite cannot add a column with a FK constraint to an existing table, so the
    # reference is enforced by the code layer (lineage/runs.py) rather than the schema.
    # Noted here so a later reader does not assume the DB is checking it.
    conn.execute("ALTER TABLE step4_results ADD COLUMN run_id INTEGER")
    conn.execute("CREATE INDEX idx_results_run ON step4_results(run_id)")
    conn.commit()

    cols = [r[1] for r in conn.execute("PRAGMA table_info(step4_results)")]
    if "run_id" not in cols:
        print("FAIL: run_id missing after ALTER.")
        return 1
    total = conn.execute("SELECT COUNT(*) FROM step4_results").fetchone()[0]
    linked = conn.execute(
        "SELECT COUNT(*) FROM step4_results WHERE run_id IS NOT NULL").fetchone()[0]
    print(f"  step4_results: {total} rows, run_id added ({linked} linked so far)")
    print("  next: python db/migrations/backfill_grw001_runs.py")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
