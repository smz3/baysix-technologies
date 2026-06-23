"""
Ingest the BRC trader's auto-written per-trade ledger CSV into research.db.

The trader EA (brc_trader.mq5) writes one CSV per tester run on OnDeinit —
Common\\Files\\BRC\\brc_trades_<symbol>_v<ver>_<stamp>.csv — with one row per
closed round-trip (entry/exit time+price, broker exit_reason, lots, 1R unit,
realized_R, PnL, zone_key). No manual MT5 "Export XLSX" step (closes task 43).

This tool:
  1. parses that CSV,
  2. opens a tester_runs row (ea_name=brc_trader) via tester.ingest_tester_run()
     with the run-level summary (n_trades, net, win-rate) computed from the rows,
  3. writes each trade via tester.ingest_tester_trade() -> tester_trades,
  4. prints a time-to-exit + exit-reason breakdown (the immediate-vs-hours answer).

Usage:
    python research/code/io/ingest_brc_trades.py --idea BRC-001 --tf H1 \
        --period 2016-01-01:2024-06-30 --data-source dukascopy
    # --src <file> to pick an explicit CSV (default: newest brc_trades_*.csv)
"""
import sys
import csv
import argparse
import statistics
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from research.code.io import tester

COMMON_BRC = Path.home() / "AppData" / "Roaming" / "MetaQuotes" / "Terminal" / "Common" / "Files" / "BRC"


def _newest_csv() -> Path:
    cands = sorted(COMMON_BRC.glob("brc_trades_*.csv"), key=lambda p: p.stat().st_mtime)
    if not cands:
        sys.exit(f"no brc_trades_*.csv found in {COMMON_BRC}")
    return cands[-1]


def _parse_rows(path: Path) -> list[dict]:
    with open(path, newline="", encoding="ansi") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for k in ("entry_px", "exit_px", "lots", "range_w", "realized_r", "realized_pnl_usd"):
            r[k] = float(r[k]) if r[k] not in ("", None) else None
        r["position_id"] = int(r["position_id"])
    return rows


def _ts_dt(s: str):
    # EA writes 'YYYY.MM.DD HH:MM:SS'
    return datetime.strptime(s.strip(), "%Y.%m.%d %H:%M:%S")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--idea", default="BRC-001")
    ap.add_argument("--tf", default="H1")
    ap.add_argument("--period", required=True, help="start:end as YYYY-MM-DD:YYYY-MM-DD")
    ap.add_argument("--data-source", default="dukascopy", choices=list(tester.VALID_DATA_SOURCE))
    ap.add_argument("--symbol", default="XAUUSD_dukas")
    ap.add_argument("--deposit", type=float, default=10000.0)
    ap.add_argument("--magic", type=int, default=2001)
    ap.add_argument("--src", default=None)
    ap.add_argument("--notes", default=None)
    args = ap.parse_args()

    csv_path = Path(args.src) if args.src else _newest_csv()
    rows = _parse_rows(csv_path)
    if not rows:
        sys.exit(f"{csv_path.name} has no trade rows")
    p_start, p_end = args.period.split(":")

    # run-level summary from the rows
    n = len(rows)
    net = sum(r["realized_pnl_usd"] for r in rows)
    wins = sum(1 for r in rows if r["realized_pnl_usd"] > 0)
    win_rate = wins / n

    tester.init_db()
    run_id = tester.ingest_tester_run(
        idea_id=args.idea, symbol=args.symbol, data_source=args.data_source,
        ea_name="brc_trader", ea_version="1.10",
        tester_model="open_only", timeframe=args.tf,
        period_start=p_start, period_end=p_end,
        magic_number=args.magic, initial_deposit=args.deposit,
        n_trades=n, net_profit_usd=round(net, 2), win_rate=round(win_rate, 4),
        notes=args.notes or f"BRC trader ledger ingest from {csv_path.name}",
    )

    for r in rows:
        ttx_min = (_ts_dt(r["exit_ts"]) - _ts_dt(r["entry_ts"])).total_seconds() / 60.0
        tester.ingest_tester_trade(
            run_id=run_id, ticket=r["position_id"],
            direction=("long" if r["direction"] == "BUY" else "short"),
            entry_ts=_ts_dt(r["entry_ts"]).strftime("%Y-%m-%d %H:%M:%S"), entry_px=r["entry_px"],
            exit_ts=_ts_dt(r["exit_ts"]).strftime("%Y-%m-%d %H:%M:%S"), exit_px=r["exit_px"],
            exit_reason=r["exit_reason"], lots=r["lots"], risk_unit=r["range_w"],
            realized_R=r["realized_r"], realized_pnl_usd=r["realized_pnl_usd"],
            meta={"zone_key": r["zone_key"], "time_to_exit_min": round(ttx_min, 1)},
        )

    # ── the answer Syafiq asked for: immediate vs hours, and gross vs net ──
    ttx = [(_ts_dt(r["exit_ts"]) - _ts_dt(r["entry_ts"])).total_seconds() / 60.0 for r in rows]
    by_reason: dict[str, int] = {}
    for r in rows:
        by_reason[r["exit_reason"]] = by_reason.get(r["exit_reason"], 0) + 1

    print(f"\n[ingest] run #{run_id}  {csv_path.name}")
    print(f"  trades        : {n}")
    print(f"  net           : ${net:,.2f}  ({net/n:+.3f}/trade)   win-rate {win_rate:.1%}")
    print(f"  exit reasons  : " + "  ".join(f"{k}={v} ({v/n:.0%})" for k, v in sorted(by_reason.items())))
    print(f"  time-to-exit  : min {min(ttx):.0f}m  median {statistics.median(ttx):.0f}m  "
          f"mean {statistics.mean(ttx):.0f}m  max {max(ttx):.0f}m")
    fast = sum(1 for t in ttx if t <= 60)
    print(f"  <=60m exits   : {fast} ({fast/n:.0%})   <- 'immediate' stop-outs")


if __name__ == "__main__":
    main()
