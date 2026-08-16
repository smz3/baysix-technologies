"""Back-fill: give GRW-001's existing measurements a runs row (task 364 call 3).

SYAFIQ'S RULING 2026-08-16: back-fill, not forward-only.

WHAT IS ACTUALLY THERE (MEASURED before writing this)
8 rows in step4_results carry `trial_family_id = grw_v0.2.0_fit1.1.0`. They fall into
two distinct backtests, separated by their data window:
    jm_tight  XAUUSD.s  2021-04-01 -> 2021-04-06   4 metrics
    jm_wide   XAUUSD.s  2021-04-01 -> 2021-04-07   4 metrics
Both are stage IS, both git_sha 41713c7, both labelled is_run=IS-01.

THE PART THAT CANNOT BE BACK-FILLED, AND WHY THAT MATTERS
`n_trials` is NULL on all 8 rows. It is NULL on every row in the table. So the number
this whole redesign is meant to protect — how many configurations were tried before
these numbers were kept — was never recorded for GRW-001 at all. This script does NOT
invent one. A back-filled trial count that nobody measured is worse than a missing one:
it makes the search look accounted-for when it is not.

Consequence, stated plainly so it is not discovered later: GRW-001's measured results
have no multiplicity denominator and cannot get one retroactively. Any future GRW work
starts a NEW trial family and counts from the first config.

The GRW v0.x machinery was deleted 2026-08-16 (strategy_log 128), so no output folder
exists for either run — both rows are created with make_dir=False.

Idempotent: refuses to run twice.
Run: python research/migrations/backfill_grw001_runs.py
"""
import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from research.code.infra.db_path import DB_PATH  # noqa: E402
from research.code.lineage import runs  # noqa: E402

NOTE = ("Back-filled 2026-08-16 from step4_results (task 364 call 3). n_trials NULL "
        "because it was never recorded — see backfill_grw001_runs.py docstring.")


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    rows = conn.execute("""
        SELECT result_id, idea_id, stage, instrument, data_start, data_end,
               git_sha, trial_family_id, n_trials, metric_key
        FROM step4_results
        WHERE trial_family_id IS NOT NULL
        ORDER BY result_id
    """).fetchall()
    if not rows:
        print("nothing to back-fill: no result carries a trial_family_id.")
        return 0

    already = conn.execute(
        "SELECT COUNT(*) FROM step4_results "
        "WHERE trial_family_id IS NOT NULL AND run_id IS NOT NULL").fetchone()[0]
    if already:
        print(f"ABORT: {already} of those rows already have a run_id — already done.")
        return 1

    # One run per distinct backtest. The data window is what separates them; two
    # measurements over different spans did not come out of the same execution.
    groups: dict[tuple, list[int]] = {}
    for r in rows:
        key = (r["idea_id"], r["stage"], r["instrument"], r["data_start"],
               r["data_end"], r["git_sha"], r["trial_family_id"])
        groups.setdefault(key, []).append(r["result_id"])

    print(f"  {len(rows)} result rows -> {len(groups)} run(s)")
    conn.close()

    for (idea_id, stage, symbol, start, end, sha, family), result_ids in groups.items():
        m = re.search(r"v\d+\.\d+\.\d+", family or "")
        run = runs.open_run(
            platform="MT5", stage=stage, symbol=symbol, idea_id=idea_id,
            version=m.group(0) if m else None,
            data_start=start, data_end=end, git_sha=sha,
            trial_family_id=family, n_trials=None,   # never measured — see docstring
            notes=NOTE, make_dir=False,
        )
        n = runs.attach_results(run["run_id"], result_ids)
        print(f"    run_id={run['run_id']} {start}..{end} <- {n} result rows")

    conn = sqlite3.connect(DB_PATH)
    linked = conn.execute(
        "SELECT COUNT(*) FROM step4_results WHERE run_id IS NOT NULL").fetchone()[0]
    orphan = conn.execute(
        "SELECT COUNT(*) FROM step4_results "
        "WHERE trial_family_id IS NOT NULL AND run_id IS NULL").fetchone()[0]
    conn.close()
    if orphan:
        print(f"FAIL: {orphan} rows carry a family but still have no run.")
        return 1
    print(f"  linked {linked} result rows; every family-tagged row has a run.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
