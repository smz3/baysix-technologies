"""
Task 200 — ingest_fob phase-2: derive Tier-C zone outcomes on an already-ingested run.

PART A (this script): zone.continued + confirm_time/confirm_price via next-CF linkage
(tester.derive_fob_tier_c_continued). Deterministic, no external data, no look-ahead.
Unblocks the storyline-alignment HIT-RATE screen (task 192).

PART B (deferred): mfe_r/mae_r/realized_r excursion in R units (R = |entry - SL|, the
trader's real SL rule) walked forward from arctic ticks. Heavier + the magnitude edge is
known-confounded by the 2016-24 secular bull, so it's secondary to the hit-rate finding.

Usage:
    python research/code/io/ingest_fob_phase2.py --run-id 18
"""
import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from research.code.io import tester


def main():
    ap = argparse.ArgumentParser(description="FOB ingest phase-2 Tier-C (task 200)")
    ap.add_argument("--run-id", type=int, required=True)
    ap.add_argument("--idea-id", default="FOB-001")
    ap.add_argument("--target-r", type=float, default=2.0, help="reward multiple vs 1R stop")
    args = ap.parse_args()

    hdr = tester.get_tester_run(args.run_id)
    if not hdr:
        raise SystemExit(f"run_id {args.run_id} not found")
    if hdr["idea_id"] != args.idea_id:
        raise SystemExit(f"ISOLATION GUARD: run_id {args.run_id} is idea_id={hdr['idea_id']!r}, "
                         f"expected {args.idea_id!r}")

    tester.derive_fob_confirm_linkage(args.run_id)
    out = tester.derive_fob_tier_c_outcome(args.run_id, target_r=args.target_r)
    print(f"=== Tier-C done: run #{args.run_id} ===")
    print(f"    {out}")


if __name__ == "__main__":
    main()
