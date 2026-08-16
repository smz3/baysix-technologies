"""042 — the generic `runs` registry (task 356). Starts empty.

WHY IT EXISTS
Migration 040 dropped `tester_runs`, the last platform-named table, leaving the spine
clean but leaving every output folder anonymous. A results folder with no registry row
is the "what is this folder" problem that started the whole 2026-08-16 cleanup. The
registry row and the path rule (task 349) are the two halves of one answer: the folder
is named `outputs/<idea_id>/<run_id>/`, and this table says what run_id MEANS.

GENERIC BY CONSTRUCTION
`platform` is a column, not a table name. That is the standing rule adopted 2026-08-16
(strategy_log 125/126/127): the ledger carries SHAPES, never STRATEGIES. A new strategy
or a new venue files here without a migration of its own.

trial_family_id / n_trials LIVE HERE, NOT ON step4_results
Measured 2026-08-16: they currently sit on `step4_results`, which is one row per METRIC,
so a single backtest writes its trial count once per number and the copies are free to
disagree. A trial count describes the SEARCH, not the measurement. The columns on
step4_results are LEFT IN PLACE and untouched — the 5 existing GRW values stay exactly
where they are. Whether they get back-filled onto a runs row or the new home applies
forward only is task 364 call 3, which is Syafiq's and is NOT decided here.

WHAT THIS MIGRATION DELIBERATELY DOES NOT DO
  - No FK from step4_results.run_id up to here. Wiring results to runs is the promotion
    design (task 364 call 2), which has no spec yet.
  - No back-fill of anything. Zero rows in, zero rows out.

Run: python research/migrations/042_runs_registry.py
"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from research.code.infra.db_path import DB_PATH  # noqa: E402

TABLE_SQL = """
CREATE TABLE runs (
    run_id          INTEGER PRIMARY KEY,
    platform        TEXT NOT NULL,          -- MT5 / NinjaTrader / IBKR
    idea_id         TEXT,                   -- optional: NULL for exploratory work
    stage           TEXT NOT NULL,          -- IS / OOS / WF / smoke, matches step4_results.stage
    symbol          TEXT NOT NULL,
    version         TEXT,                   -- strategy or EA version under test
    data_start      DATE,
    data_end        DATE,
    git_sha         TEXT NOT NULL,          -- what code produced it
    output_dir      TEXT,                   -- task 349's outputs/<idea_id>/<run_id>/
    trial_family_id TEXT,                   -- the search this run belongs to
    n_trials        INTEGER,                -- how many configs that search has burned
    notes           TEXT,
    created_at      DATETIME NOT NULL,
    FOREIGN KEY (idea_id) REFERENCES step1_ideas(idea_id)
)
"""

INDEX_SQL = [
    "CREATE INDEX idx_runs_platform ON runs(platform)",
    "CREATE INDEX idx_runs_idea ON runs(idea_id)",
    "CREATE INDEX idx_runs_family ON runs(trial_family_id)",
]

EXPECTED = {
    "step1_ideas", "step2_papers", "step3_gates", "step4_results",
    "log_agent", "log_strategy", "log_tasks", "runs",
    "gate_pipeline", "idea_lifecycle", "open_backlog", "papers_queue",
}


def main():
    conn = sqlite3.connect(DB_PATH)

    exists = conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='runs'"
    ).fetchone()[0]
    if exists:
        print("ABORT: table `runs` already exists — 042 has already run.")
        return 1

    conn.execute(TABLE_SQL)
    for sql in INDEX_SQL:
        conn.execute(sql)
    conn.commit()
    print("  created table runs + 3 indexes")

    after = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table','view') "
        "AND name NOT LIKE 'sqlite_%'")}
    if after != EXPECTED:
        print(f"FAIL: unexpected end state.\n  extra:   {sorted(after - EXPECTED)}"
              f"\n  missing: {sorted(EXPECTED - after)}")
        return 1

    n = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
    cols = [r[1] for r in conn.execute("PRAGMA table_info(runs)")]
    print(f"  runs: {n} rows, {len(cols)} columns")
    print(f"  spine intact: {len(after)} objects")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
