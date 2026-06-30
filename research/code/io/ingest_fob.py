"""
Task 191 — ingest a FOB capture CSV into research.db (fob_cycles/fob_zones/fob_events).

The FOB emitter (fob_baysix.mq5 + fob_csv.mqh) writes one UTF-8 wide CSV per run:
one row per classified event (PBO/VR/CF), each carrying its FobZone (event<->zone
1:1 at emit). This script opens a tester_runs header (run_role='emitter', symbol /
data_source / tester_model / period / git provenance) and derives all three FOB
payload tables under that run_id via tester.ingest_fob. Cycles are reconstructed
by grouping on (setup_tf, seq). All writes go through research.code.io.tester
(CLAUDE.md rule 10 — never raw sqlite3). Mirrors the retired ingest_brc_zones.

Usage:
    python research/code/io/ingest_fob.py \
        --csv "<...>/fob_capture_XAUUSD_dukas_v1.24.0_20220101_0000.csv" \
        --period-start 2022-01-01 --period-end 2022-04-01

Defaults: idea_id=FOB-001, ea=fob_baysix, data_source=dukascopy,
tester_model=real_ticks, timeframe=M1 (chart period; detection is multi-TF).
Symbol/ea_version are parsed from the filename if not given.
"""
import argparse
import re
import subprocess
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from research.code.io import tester

_REPO = Path(__file__).resolve().parents[3]


def _parse_filename(name: str):
    """fob_capture_<symbol>_v<ver>_<runtag>.csv -> (symbol, version)."""
    m = re.match(r"fob_capture_(?P<sym>.+?)_v(?P<ver>[\d.]+)_", name)
    if not m:
        return None, None
    return m.group("sym"), m.group("ver")


def _git_provenance():
    """(short_sha, dirty_flag) for the repo HEAD, or (None, None) if git unavailable."""
    try:
        sha = subprocess.check_output(["git", "-C", str(_REPO), "rev-parse", "--short", "HEAD"],
                                      text=True).strip()
        dirty = subprocess.check_output(["git", "-C", str(_REPO), "status", "--porcelain"],
                                        text=True).strip()
        return sha, (1 if dirty else 0)
    except Exception:
        return None, None


def main():
    ap = argparse.ArgumentParser(description="Ingest a FOB capture CSV into research.db")
    ap.add_argument("--csv", required=True, help="path to fob_capture_*.csv (UTF-8)")
    ap.add_argument("--idea-id", default="FOB-001")
    ap.add_argument("--ea-name", default="fob_baysix")
    ap.add_argument("--ea-version", default=None, help="defaults to version parsed from filename")
    ap.add_argument("--symbol", default=None, help="defaults to symbol parsed from filename")
    ap.add_argument("--data-source", default="dukascopy",
                    choices=list(tester.VALID_DATA_SOURCE))
    ap.add_argument("--tester-model", default="real_ticks",
                    choices=list(tester.VALID_TESTER_MODEL))
    ap.add_argument("--timeframe", default="M1", help="chart period the emitter ran on (detection is multi-TF)")
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

    sha, dirty = _git_provenance()
    tester.init_db()  # idempotent

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
        run_role="emitter",
        git_sha=sha,
        git_dirty=dirty,
        notes=args.notes or f"FOB emitter ingest from {csv_path.name}",
    )

    counts = tester.ingest_fob(run_id, csv_path)

    # ── verify ──────────────────────────────────────────────────────────────
    import sqlite3
    conn = sqlite3.connect(tester.DB_PATH)
    per_tf = conn.execute(
        "SELECT setup_tf, COUNT(*) FROM fob_cycles WHERE run_id=? GROUP BY setup_tf "
        "ORDER BY COUNT(*) DESC", (run_id,)).fetchall()
    rng = conn.execute(
        "SELECT MIN(bar_time), MAX(bar_time) FROM fob_events WHERE run_id=?", (run_id,)).fetchone()
    by_label = conn.execute(
        "SELECT label, COUNT(*) FROM fob_events WHERE run_id=? GROUP BY label", (run_id,)).fetchall()
    status = conn.execute(
        "SELECT status, COUNT(*) FROM fob_cycles WHERE run_id=? GROUP BY status", (run_id,)).fetchall()
    zstats = conn.execute(
        "SELECT SUM(zone_valid), SUM(alive_at_end), SUM(vr_fresh), "
        "       SUM(CASE WHEN invalidation_time IS NOT NULL THEN 1 ELSE 0 END) "
        "FROM fob_zones WHERE run_id=?", (run_id,)).fetchone()
    orphans = conn.execute(
        "SELECT COUNT(*) FROM fob_events WHERE run_id=? AND (cycle_id IS NULL OR zone_id IS NULL)",
        (run_id,)).fetchone()[0]
    conn.close()

    print(f"\n=== VERIFY run #{run_id} (FOB-001, emitter) ===")
    print(f"cycles : {counts['cycles']}   zones: {counts['zones']}   events: {counts['events']}")
    print(f"event rng : {rng[0]} -> {rng[1]}")
    print(f"by label  : " + ", ".join(f"{l}={c}" for l, c in by_label))
    print(f"cycle/setup_tf : " + ", ".join(f"{tf}={c}" for tf, c in per_tf))
    print(f"cycle status   : " + ", ".join(f"{s}={c}" for s, c in status))
    print(f"zones: valid={zstats[0]}  alive@end={zstats[1]}  vr_fresh={zstats[2]}  invalidated={zstats[3]}")
    print(f"orphan events (no cycle/zone): {orphans}   git={sha}-{'DIRTY' if dirty else 'clean'}")


if __name__ == "__main__":
    main()
