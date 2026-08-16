"""039 — drop the MT5 tester payload tables; keep the run registry.

Follows 038. Same rule: the ledger keeps SHAPES and the INDEX, never bulk per-run
payload. Bulk output belongs in files (Parquet), keyed by the run_id in the path.

Dropped (all zero rows):
  tester_trades      — per-trade payload. Also already broken by 038: it carries an FK
                       to fob_zones, which 038 dropped, so inserts fail under
                       PRAGMA foreign_keys=ON.
  tester_zones       — per-zone payload (BRC's 5-pointer shape; BRC is parked).
  tester_run_summary — never populated.

KEPT DELIBERATELY: tester_runs (4 rows). It is the RUN REGISTRY, not payload — the
row that makes research/data/fob_payload/run_19/ mean "FOB-001, fob_baysix v1.33.0,
XAUUSD_dukas, emitter" instead of 88 MB of anonymous files. Dropping it would recreate
the exact "what is this folder" problem this whole cleanup started from. It is also
already generic in shape (idea_id / ea_name / ea_version / symbol / window / git_sha /
run_role) and should be RENAMED to `runs` with a `platform` column when the DB moves to
baysix.db — one round of path churn instead of two.

KNOWN CONSEQUENCE: the tester-trade ingest path is disabled. Guards added in tester.py
(ingest_tester_trade, ingest_brc_zones). NOT edited here — ingest_grw.py, which fills
tester_trades, has uncommitted changes from another session; it was already broken by
038 (grw_passes) and is tracked as its own task.

Run: python research/migrations/039_drop_tester_payload_tables.py
"""
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DB_PATH = REPO / "research" / "db" / "research.db"

TABLES = ["tester_trades", "tester_zones", "tester_run_summary"]
KEEP = "tester_runs"


def main():
    conn = sqlite3.connect(DB_PATH)
    have = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table','view')")}

    # Never drop a table that gained rows since this migration was written.
    for t in TABLES:
        if t in have:
            n = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            if n:
                print(f"ABORT: {t} has {n} rows — this migration assumes empty. "
                      f"Export to Parquet first, then re-run.")
                return 1

    for t in TABLES:
        conn.execute(f"DROP TABLE IF EXISTS {t}")
        print(f"  - {t}" if t in have else f"  = {t} (absent)")
    conn.commit()

    after = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table','view')")}
    if KEEP not in after:
        print(f"FAIL: {KEEP} is the run registry and must survive this migration.")
        return 1
    left = [t for t in TABLES if t in after]
    if left:
        print(f"FAIL: still present: {left}")
        return 1

    size_before = DB_PATH.stat().st_size
    conn.execute("VACUUM")
    conn.close()
    print(f"\n{KEEP} kept: {sqlite3.connect(DB_PATH).execute(f'SELECT COUNT(*) FROM {KEEP}').fetchone()[0]} rows")
    print(f"{len(after)} objects remain; file {size_before:,} -> {DB_PATH.stat().st_size:,} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
