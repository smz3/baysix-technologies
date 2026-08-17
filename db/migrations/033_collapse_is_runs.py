"""Migration 033 — collapse the is_runs registry into step4_results.

The separate `is_runs` table duplicated a concept the result row already carries:
the IS-run label. It sat between step3_gates and step4_results as a third level and
forced a pre-register step (log_is_run before log_result). 4.0 simplification: the
IS-run label lives on step4_results.is_run; `what_changed` moves onto the result row
too; the shot-count is `COUNT(DISTINCT is_run)`. No registry, no pre-register friction.

Changes:
  1. ADD COLUMN step4_results.what_changed TEXT   (was is_runs.what_changed)
  2. Carry forward any is_runs.what_changed onto matching step4_results rows
  3. DROP TABLE is_runs  (+ its index)

Both tables are empty at write time (BRC-001 has logged no IS result yet), so step 2
is a no-op in practice — kept for correctness if re-run on a populated backup.

Run:  python db/migrations/033_collapse_is_runs.py
Idempotent: column add + drop both guarded; safe to re-run.
"""
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LIVE = REPO / "research" / "db" / "research.db"


def _has_col(conn, table: str, col: str) -> bool:
    return col in [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]


def _has_table(conn, table: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone() is not None


def main() -> None:
    if not LIVE.exists():
        sys.exit(f"FATAL: {LIVE} not found")
    conn = sqlite3.connect(LIVE)
    try:
        # 1. add the column (idempotent)
        if not _has_col(conn, "step4_results", "what_changed"):
            conn.execute("ALTER TABLE step4_results ADD COLUMN what_changed TEXT")
            print("  + step4_results.what_changed added")
        else:
            print("  = step4_results.what_changed already present")

        # 2. carry forward what_changed from the registry, if it still exists
        if _has_table(conn, "is_runs"):
            moved = conn.execute("""
                UPDATE step4_results
                   SET what_changed = (
                       SELECT ir.what_changed FROM is_runs ir
                       WHERE ir.idea_id = step4_results.idea_id
                         AND ir.label   = step4_results.is_run)
                 WHERE what_changed IS NULL
                   AND is_run IS NOT NULL
                   AND EXISTS (SELECT 1 FROM is_runs ir
                               WHERE ir.idea_id = step4_results.idea_id
                                 AND ir.label   = step4_results.is_run)
            """).rowcount
            print(f"  ~ carried what_changed onto {moved} result row(s)")

            # 3. drop the registry
            conn.execute("DROP INDEX IF EXISTS idx_is_runs_idea")
            conn.execute("DROP TABLE is_runs")
            print("  - is_runs table dropped")
        else:
            print("  = is_runs already gone")

        conn.commit()

        # verify
        assert _has_col(conn, "step4_results", "what_changed")
        assert not _has_table(conn, "is_runs")
        print("OK — is_runs collapsed into step4_results.what_changed")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
