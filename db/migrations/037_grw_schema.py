"""037 — GRW-001 factory schema + tester-DDL drift repair + WAL.

Closes backlog tasks 287 and 289. Spec: docs/reference/grw_autonomous_workflow.md
(§2 promotion ladder, §4 storage, §5 known gaps).

Decision (2026-08-03, Syafiq): GRW-001 SHARES research.db — it does not get its own
file. The multiplicity ledger (`trial_family_id`) only works if every trial ever run
lands in one denominator; two databases would be two denominators and Loop B would
lose its teeth silently.

What this does — all additive, all idempotent:

  1. TASK 287 — tester_* DDL drift. `db_init.py` carried a SECOND, stale copy of the
     MT5 ledger DDL. Measured drift vs the live DB / tester.py:
         tester_runs   missing run_role, git_sha, git_dirty
         tester_trades missing zone_id, gross_usd, cost_usd
         missing entirely: tester_run_summary, fob_cycles, fob_zones, fob_events,
                           fob_run_stats
     A rebuild from db_init would have produced a narrower schema than every writer
     expects, with no error. Fixed at the root: the DDL now lives once in
     core/infra/schema_ledger.py and BOTH db_init.py and tester.py import it.
     This migration re-asserts that canonical DDL against the live file.

  2. TASK 289 — GRW schema: grw_batches, grw_passes, views grw_family_trials and
     grw_batch_scoreboard, plus step4_results.trial_family_id / .n_trials.

  3. TASK 289 — `is_runs` reconcile. CLAUDE.md and the GRW spec both call the missing
     `is_runs` table a blocking gap. It is NOT a gap: migration 033_collapse_is_runs.py
     deliberately folded it into step4_results.is_run / .what_changed (Protocol 4.0
     lean). Nothing to create — the docs were stale. This migration asserts the
     collapse actually held and prints the verdict.

  4. WAL. journal_mode was `delete`; Loop C writes on a timer while the dashboard and
     interactive queries read, and rollback journaling takes an exclusive writer lock.
     journal_mode is persisted in the DB file, so this is a one-time switch.

Run: python db/migrations/037_grw_schema.py
"""
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from core.infra.schema_ledger import SCHEMA_MT5, SCHEMA_GRW  # noqa: E402

DB_PATH = REPO / "research" / "db" / "research.db"


def _add_col(conn, table, coldef):
    col = coldef.split()[0]
    have = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
    if col not in have:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {coldef}")
        print(f"  + {table}.{col}")
    else:
        print(f"  = {table}.{col} (exists)")


def _tables(conn):
    return {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table','view')")}


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    before = _tables(conn)

    print(f"[037] {DB_PATH}")

    print("\n-- 1. task 287: re-assert canonical MT5 ledger DDL --")
    conn.executescript(SCHEMA_MT5)
    for tbl, cols in (
        ("tester_runs",   ("run_role", "git_sha", "git_dirty")),
        ("tester_trades", ("zone_id", "gross_usd", "cost_usd")),
    ):
        have = {r[1] for r in conn.execute(f"PRAGMA table_info({tbl})")}
        missing = [c for c in cols if c not in have]
        print(f"  {tbl}: {'OK — all drift columns present' if not missing else 'MISSING ' + str(missing)}")

    print("\n-- 2. task 289: GRW factory schema --")
    conn.executescript(SCHEMA_GRW)
    _add_col(conn, "step4_results", "trial_family_id TEXT")
    _add_col(conn, "step4_results", "n_trials INTEGER")

    print("\n-- 3. task 289: is_runs reconcile --")
    has_is_runs = "is_runs" in _tables(conn)
    s4 = {r[1] for r in conn.execute("PRAGMA table_info(step4_results)")}
    collapsed = {"is_run", "what_changed"} <= s4
    if has_is_runs:
        print("  ! is_runs table EXISTS — unexpected; migration 033 said it was collapsed.")
    elif collapsed:
        print("  OK — is_runs was collapsed into step4_results.is_run/.what_changed by")
        print("       migration 033. It is NOT a missing table; the docs were stale.")
    else:
        print("  ! is_runs absent AND step4_results.is_run/.what_changed missing — real gap.")

    print("\n-- 4. WAL --")
    was = conn.execute("PRAGMA journal_mode").fetchone()[0]
    now = conn.execute("PRAGMA journal_mode=WAL").fetchone()[0]
    print(f"  journal_mode: {was} -> {now}")

    conn.commit()
    after = _tables(conn)
    print("\n-- new objects --")
    for t in sorted(after - before):
        print(f"  + {t}")
    print(f"\n[037] done — {len(after)} tables/views")
    conn.close()


if __name__ == "__main__":
    main()
