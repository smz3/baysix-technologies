"""040 — drop tester_runs, the last platform-named table. Starting fresh.

Completes 038 + 039. research.db becomes a pure Protocol 4.0 spine: ideas, papers,
gates, results, three logs, four views. Nothing named after a strategy or a platform.

Decision (Syafiq, 2026-08-16): starting fresh, so the run registry goes too — AND the
payload it indexed goes with it. Deleting the registry while keeping the files would
leave 88 MB of unidentifiable data, which is the exact "what is this folder" problem
this whole cleanup began with. The two are deleted together or not at all.

State at drop time (measured):
  tester_runs        4 rows — run 16/17/18 (payload already gone), run 19 (payload here)
  referenced by      nothing. No FK in the ledger points at tester_runs.
  run_19 payload     research/data/fob_payload/run_19/ — cycles/events/zones.parquet, 88 MB

The payload is NOT practically regenerable: the source capture CSV is backed up to
G:\\My Drive\\baysix_backups, but the code that turns it into these files (ingest_fob ->
tester.ingest_fob) was disabled by 038. Rebuilding means finishing task 353 first.
This is a deliberate, authorised loss, not an oversight.

A future `runs` registry — generic, with a `platform` column — is still the right idea
when the DB moves to baysix.db. It just starts empty rather than carrying four rows of
superseded FOB emitter history.

Run: python db/migrations/040_drop_tester_runs.py
"""
import shutil
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DB_PATH = REPO / "research" / "db" / "research.db"
PAYLOAD_DIR = REPO / "research" / "data" / "fob_payload"

EXPECTED_SPINE = {
    "step1_ideas", "step2_papers", "step3_gates", "step4_results",
    "log_agent", "log_strategy", "log_tasks",
    "gate_pipeline", "idea_lifecycle", "open_backlog", "papers_queue",
}


def main():
    conn = sqlite3.connect(DB_PATH)

    # Refuse if anything grew a dependency on tester_runs since this was written.
    for (name,) in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name != 'tester_runs'"):
        refs = [f[2] for f in conn.execute(f"PRAGMA foreign_key_list({name})")]
        if "tester_runs" in refs:
            print(f"ABORT: {name} still references tester_runs.")
            return 1

    n = conn.execute("SELECT COUNT(*) FROM tester_runs").fetchone()[0]
    print(f"  tester_runs: {n} rows -> dropping")
    conn.execute("DROP TABLE IF EXISTS tester_runs")
    conn.commit()

    after = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table','view') "
        "AND name NOT LIKE 'sqlite_%'")}
    if after != EXPECTED_SPINE:
        print(f"FAIL: unexpected end state.\n  extra:   {sorted(after - EXPECTED_SPINE)}"
              f"\n  missing: {sorted(EXPECTED_SPINE - after)}")
        return 1

    size_before = DB_PATH.stat().st_size
    conn.execute("VACUUM")
    conn.close()
    print(f"  spine intact: {len(after)} objects; "
          f"file {size_before:,} -> {DB_PATH.stat().st_size:,} bytes")

    # The indexed payload goes with its index — see the module docstring.
    run19 = PAYLOAD_DIR / "run_19"
    if run19.exists():
        mb = sum(f.stat().st_size for f in run19.rglob("*") if f.is_file()) / 1e6
        shutil.rmtree(run19)
        print(f"  deleted {run19.relative_to(REPO)} ({mb:.0f} MB)")
    leftover = [p.name for p in PAYLOAD_DIR.iterdir()] if PAYLOAD_DIR.exists() else []
    print(f"  fob_payload/ now holds: {leftover or 'nothing'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
