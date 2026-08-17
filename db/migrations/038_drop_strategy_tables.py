"""038 — drop the per-strategy tables from research.db.

Decision (Syafiq, 2026-08-16): the ledger stops carrying strategy-shaped tables.
Every new strategy was costing 4 tables + a migration; an autonomous strategy loop
would have had to write its own DDL to file results. The schema now grows only when
a genuinely new SHAPE appears, never when a new strategy does.

Dropped here:
  fob_cycles / fob_zones / fob_events  — transient ingest staging. Emptied after every
      run by tester.clear_fob_payload_run(); the durable copy is Parquet under
      research/data/fob_payload/run_<id>/. Zero rows at drop time.
  fob_run_stats  — 8 rows (run 19, 2026-07-04 per-setup_tf rollup). Regenerable from
      run_19's Parquet payload (88 MB, on disk, verified present before the drop).
  grw_batches / grw_passes  — zero rows. GRW-001 has never run.
  grw_batch_scoreboard / grw_family_trials  — views over the two GRW tables above.

KNOWN CONSEQUENCE, logged as a task rather than papered over: FOB CSV ingest
(ingest_fob.py -> tester.derive_fob_payload) staged into fob_cycles/zones/events and
therefore no longer runs. It must be rewritten to write Parquet directly, which is
the agreed direction anyway (files for finished output, DB for live mutable state).
Guards were added at both entry points so it fails loudly instead of at a stray
"no such table" three layers down.

OPEN, must be settled before GRW-001 starts: grw_passes carried `trial_family_id`,
the multiplicity ledger that raises the significance bar as the search widens. That
bookkeeping needs a generic home in the spine. Nothing about this migration weakens
it today (there were no rows), but starting GRW without a replacement would.

Run: python db/migrations/038_drop_strategy_tables.py
"""
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DB_PATH = REPO / "research" / "db" / "research.db"
PAYLOAD_DIR = REPO / "research" / "data" / "fob_payload"

VIEWS = ["grw_batch_scoreboard", "grw_family_trials"]
# child -> parent, so FK references are gone before their target is
TABLES = ["fob_events", "fob_zones", "fob_cycles", "fob_run_stats",
          "grw_passes", "grw_batches"]


def _objects(conn):
    return {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table','view')")}


def main():
    conn = sqlite3.connect(DB_PATH)
    before = _objects(conn)

    # fob_run_stats is the only object here holding rows. It is only safe to drop
    # because the payload it was derived from still exists — assert that, don't assume.
    if "fob_run_stats" in before:
        n = conn.execute("SELECT COUNT(*) FROM fob_run_stats").fetchone()[0]
        runs = [r[0] for r in conn.execute(
            "SELECT DISTINCT run_id FROM fob_run_stats ORDER BY run_id")]
        missing = [r for r in runs if not (PAYLOAD_DIR / f"run_{r}" / "cycles.parquet").exists()]
        if missing:
            print(f"ABORT: fob_run_stats has {n} rows for run(s) {runs}, but no Parquet "
                  f"payload for {missing} — those numbers would be unrecoverable.")
            return 1
        print(f"  fob_run_stats: {n} rows, run(s) {runs} — payload present, regenerable. OK to drop.")

    for v in VIEWS:
        conn.execute(f"DROP VIEW IF EXISTS {v}")
        print(f"  - view  {v}" if v in before else f"  = view  {v} (absent)")
    for t in TABLES:
        conn.execute(f"DROP TABLE IF EXISTS {t}")
        print(f"  - table {t}" if t in before else f"  = table {t} (absent)")

    conn.commit()

    after = _objects(conn)
    left = [o for o in VIEWS + TABLES if o in after]
    if left:
        print(f"FAIL: still present after drop: {left}")
        return 1

    size_before = DB_PATH.stat().st_size
    conn.execute("VACUUM")          # DROP frees pages but does not shrink the file
    conn.close()
    size_after = DB_PATH.stat().st_size

    print(f"\ndropped {len(before - after)} objects; {len(after)} remain")
    print(f"file: {size_before:,} -> {size_after:,} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
