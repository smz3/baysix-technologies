"""
Task 119 — ingest a BRC zone-lifecycle CSV into research.db.

The BRC emitter (brc_baysix.mq5 + brc_csv.mqh) writes one UTF-8 CSV per run:
one row per confirmed zone per TF. This script opens a tester_runs header
(provenance: symbol / data_source / tester_model / period) and bulk-loads every
zone into tester_zones under that run_id. All writes go through research.code.tester
(CLAUDE.md rule 10 — never raw sqlite3).

Usage:
    python research/code/ingest_brc_zones.py \
        --csv "<...>/brc_zones_XAUUSD_dukas_v1.0.0_20240101_0000.csv" \
        --period-start 2024-01-01 --period-end 2024-12-31

Defaults: idea_id=BRC-001, ea=brc_baysix, data_source=dukascopy, tester_model=open_only,
base timeframe=M5. Symbol/ea_version are parsed from the filename if not given.
"""
import argparse
import re
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from research.code import tester


def _parse_filename(name: str):
    """brc_zones_<symbol>_v<ver>_<runtag>.csv -> (symbol, version)."""
    m = re.match(r"brc_zones_(?P<sym>.+?)_v(?P<ver>[\d.]+)_", name)
    if not m:
        return None, None
    return m.group("sym"), m.group("ver")


def main():
    ap = argparse.ArgumentParser(description="Ingest a BRC zone-lifecycle CSV into research.db")
    ap.add_argument("--csv", required=True, help="path to brc_zones_*.csv (UTF-8)")
    ap.add_argument("--idea-id", default="BRC-001")
    ap.add_argument("--ea-name", default="brc_baysix")
    ap.add_argument("--ea-version", default=None, help="defaults to version parsed from filename")
    ap.add_argument("--symbol", default=None, help="defaults to symbol parsed from filename")
    ap.add_argument("--data-source", default="dukascopy",
                    choices=list(tester.VALID_DATA_SOURCE))
    ap.add_argument("--tester-model", default="open_only",
                    choices=list(tester.VALID_TESTER_MODEL))
    ap.add_argument("--timeframe", default="M5", help="base TF the emitter ran on")
    ap.add_argument("--period-start", default=None)
    ap.add_argument("--period-end", default=None)
    ap.add_argument("--notes", default=None)
    args = ap.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        raise SystemExit(f"CSV not found: {csv_path}")

    f_sym, f_ver = _parse_filename(csv_path.name)
    symbol  = args.symbol or f_sym
    version = args.ea_version or f_ver
    if not symbol:
        raise SystemExit("could not parse symbol from filename; pass --symbol")

    tester.init_db()  # idempotent — ensures tester_zones exists

    run_id = tester.ingest_tester_run(
        idea_id=args.idea_id,
        symbol=symbol,
        data_source=args.data_source,
        ea_name=args.ea_name,
        ea_version=version,
        tester_model=args.tester_model,
        timeframe=args.timeframe,
        period_start=args.period_start,
        period_end=args.period_end,
        notes=args.notes or f"BRC zone-emitter ingest from {csv_path.name}",
    )

    n = tester.ingest_brc_zones(run_id, csv_path)

    # ── verify ──────────────────────────────────────────────────────────────
    import sqlite3
    conn = sqlite3.connect(tester.DB_PATH)
    per_tf = conn.execute(
        "SELECT tf, COUNT(*) FROM tester_zones WHERE run_id=? GROUP BY tf ORDER BY COUNT(*) DESC",
        (run_id,)).fetchall()
    rng = conn.execute(
        "SELECT MIN(confirm_time), MAX(confirm_time) FROM tester_zones WHERE run_id=?",
        (run_id,)).fetchone()
    alive = conn.execute(
        "SELECT SUM(alive_at_end), SUM(continued), "
        "       SUM(CASE WHEN invalidation_time IS NOT NULL THEN 1 ELSE 0 END), "
        "       SUM(CASE WHEN t1_time IS NOT NULL THEN 1 ELSE 0 END) "
        "FROM tester_zones WHERE run_id=?", (run_id,)).fetchone()
    conn.close()

    print(f"\n=== VERIFY run #{run_id} ===")
    print(f"total zones : {n}")
    print(f"confirm rng : {rng[0]} -> {rng[1]}")
    print(f"per TF      : " + ", ".join(f"{tf}={c}" for tf, c in per_tf))
    print(f"alive@end   : {alive[0]}   continued: {alive[1]}   "
          f"invalidated: {alive[2]}   L1-touched: {alive[3]}")


if __name__ == "__main__":
    main()
