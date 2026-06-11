"""
ORB-001 Gate-7 FIDELITY diff: MT5 Strategy-Tester (10k) vs Python research OOS.

Question (Gate 7): does the compiled EA reproduce the Python research backtest on the
SAME data (Dukascopy)? Aggregate already says NO (win 56.70% Python -> 33.21% tester).
This script does the PER-TRADE diff to localise WHERE the port diverges — the trail exit
is the suspect (entries cluster at 09:0x UTC, so OR detection ported fine).

Method (no EA change, no tester re-run needed):
  1. Python side  — re-run ONLY the OOS trail_1R slice via trail_oos._run_slice (the exact
     validated _simulate_day), dump per-trade rows {session_date, direction, range_w, R, entry}.
  2. Tester side  — parse the 10k ReportTester xlsx (Orders+Deals) into round-trips:
     direction, entry/exit fills+times, profit, exit_reason (from the order comment, e.g.
     'sl 2288.37' = stopped/trailed out at that level), initial SL (= or_low).
  3. range_w (1R) for the tester is BORROWED from Python per (session_date, direction) —
     valid because OR detection ported correctly; the trail exit is what we are testing.
     tester_R = realized_profit_usd / (range_w * CONTRACT_OZ * MIN_LOT)   [= profit / range_w].
  4. Diff: trade-overlap %, R-correlation, E[R] delta, win-rate delta, and the exit_reason
     breakdown that explains the win-rate collapse.

Outputs -> research/outputs/orb/fidelity/
    python_oos_trades.csv  tester_trades_parsed.csv  fidelity_merged.csv
Writes NOTHING to research.db — ingest is a reviewed follow-up step.

    python -X utf8 research/models/orb/orb001/fidelity_diff.py
"""
from __future__ import annotations
import re
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
import openpyxl

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))

from research.models.orb.orb001.trail_oos import _run_slice, OOS_MONTHS
from research.models.orb.orb001.equity_sim import MIN_LOT, CONTRACT_OZ
from research.code.session_cache import session_files

REPORT = REPO / "mt5" / "strategy_tester_xlsx" / "ReportTester-1100438548_10k.xlsx"
OUT = REPO / "research" / "outputs" / "orb" / "fidelity"
R1_USD_PER_RW = CONTRACT_OZ * MIN_LOT  # USD risked per 1.0 of range_w at min lot (=1.0)


# ── 1. Python OOS per-trade dump ──────────────────────────────────────────────
def python_oos_trades() -> pd.DataFrame:
    print("[1/3] Python OOS trail_1R slice (faithful _simulate_day) ...")
    files_oos = session_files(OOS_MONTHS)
    if not files_oos:
        sys.exit("No session-cache files. Build first: python research/code/session_cache.py build")
    _, trail_rows = _run_slice(files_oos, is_slice=False, oos_slice=True,
                               slip_extra=0.0, desc="OOS slip=0x")
    df = pd.DataFrame(trail_rows)
    df["session_date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    df = df.rename(columns={"R": "py_R", "entry_px": "py_entry", "range_w": "range_w"})
    df = df[["session_date", "direction", "range_w", "py_entry", "py_R"]]
    print(f"      python OOS trades: n={len(df)}  win={ (df['py_R']>0).mean():.4f}  "
          f"E[R]={df['py_R'].mean():+.4f}")
    return df


# ── 2. Tester report parse ────────────────────────────────────────────────────
def _section(rows, name):
    """Return (label_idx, header_idx, col_map) for a named section ('Orders'/'Deals')."""
    for i, r in enumerate(rows):
        cells = [str(c).strip() for c in r if c is not None and str(c).strip() != ""]
        if len(cells) == 1 and cells[0] == name:
            hdr = [str(c).strip() if c is not None else "" for c in rows[i + 1]]
            col = {h: j for j, h in enumerate(hdr) if h}
            return i, i + 1, col
    sys.exit(f"section {name!r} not found in report")


def _data_rows(rows, header_idx, end_idx=None):
    """Yield data rows after a header until a fully-empty row or end_idx (exclusive)."""
    stop = end_idx if end_idx is not None else len(rows)
    for r in rows[header_idx + 1:stop]:
        if all(c is None or str(c).strip() == "" for c in r):
            return
        yield r


def tester_trades() -> pd.DataFrame:
    print(f"[2/3] Parsing tester report {REPORT.name} ...")
    rows = list(openpyxl.load_workbook(REPORT, read_only=True).active.iter_rows(values_only=True))

    # locate both sections up front so Orders parsing stops at the Deals boundary
    _, o_hdr, oc = _section(rows, "Orders")
    d_label, d_hdr, dc = _section(rows, "Deals")

    # Orders -> ticket -> comment (exit reason) + S/L (initial stop = or_low/or_high)
    orders = {}
    for r in _data_rows(rows, o_hdr, end_idx=d_label):
        oid = r[oc["Order"]]
        if oid is None or not str(oid).strip().replace(".0", "").isdigit():
            continue
        orders[str(int(oid))] = {
            "comment": (str(r[oc["Comment"]]).strip() if "Comment" in oc and r[oc["Comment"]] is not None else ""),
            "sl": r[oc.get("S / L")] if "S / L" in oc else None,
            "type": (str(r[oc["Type"]]).strip() if r[oc["Type"]] is not None else ""),
        }

    # Deals -> pair in/out into round-trips
    def g(r, key):
        return r[dc[key]] if key in dc and dc[key] < len(r) else None

    open_pos = None
    trades = []
    for r in _data_rows(rows, d_hdr):
        sym = g(r, "Symbol")
        if sym is None or str(sym).strip() in ("", "balance"):
            continue
        direction_io = str(g(r, "Direction")).strip()   # 'in' / 'out' / 'in/out'
        dtype = str(g(r, "Type")).strip()                # buy / sell
        price = float(g(r, "Price"))
        tval = str(g(r, "Time")).strip()
        oid = g(r, "Order")
        oid = str(int(oid)) if oid is not None else None
        profit = g(r, "Profit")
        profit = float(profit) if profit not in (None, "") else 0.0

        if direction_io == "in":
            open_pos = {"entry_ts": tval, "entry_px": price,
                        "direction": "long" if dtype == "buy" else "short", "oid_in": oid}
        elif direction_io == "out" and open_pos is not None:
            ocom = orders.get(oid, {})
            comment = ocom.get("comment", "")
            sl0 = orders.get(open_pos["oid_in"], {}).get("sl")
            reason = _exit_reason(comment)
            sess = open_pos["entry_ts"][:10].replace(".", "-")
            trades.append({
                "session_date": sess,
                "direction": open_pos["direction"],
                "entry_ts": open_pos["entry_ts"], "entry_px": open_pos["entry_px"],
                "exit_ts": tval, "exit_px": price,
                "profit_usd": profit,
                "exit_comment": comment, "exit_reason": reason,
                "init_sl": float(sl0) if sl0 not in (None, "", 0, "0.0") else None,
            })
            open_pos = None

    df = pd.DataFrame(trades)
    print(f"      tester trades: n={len(df)}  win={ (df['profit_usd']>0).mean():.4f}")
    print("      exit_reason counts:", df["exit_reason"].value_counts().to_dict())
    return df


def _exit_reason(comment: str) -> str:
    c = comment.lower()
    if c.startswith("sl"):
        return "stop_or_trail"   # MT5 labels both initial-stop and trailed-stop hits 'sl'
    if c.startswith("tp"):
        return "target"
    if c.startswith("so"):
        return "stop_out_margin"
    if "eod" in c or "end" in c or "close" in c:
        return "eod"
    return comment if comment else "other"


# ── 3. Diff ───────────────────────────────────────────────────────────────────
def diff(py: pd.DataFrame, te: pd.DataFrame):
    print("\n[3/3] FIDELITY diff (match on session_date + direction) ...")
    # Borrow range_w from Python per (session_date, direction) for the tester R.
    key = ["session_date", "direction"]
    rw = py[key + ["range_w", "py_R", "py_entry"]].drop_duplicates(key)
    m = te.merge(rw, on=key, how="outer", indicator=True)
    m["tester_R"] = np.where(m["profit_usd"].notna() & m["range_w"].notna(),
                             m["profit_usd"] / (m["range_w"] * R1_USD_PER_RW), np.nan)

    n_py, n_te = len(py), len(te)
    both = m[m["_merge"] == "both"]
    py_only = m[m["_merge"] == "right_only"]
    te_only = m[m["_merge"] == "left_only"]
    # direction flips: same session_date, opposite direction (caught as separate py_only+te_only)
    flips = set(te["session_date"]) & set(py["session_date"]) - set(both["session_date"])

    overlap_union = len(both) / len(set(py["session_date"].astype(str) + py["direction"])
                                    | set(te["session_date"].astype(str) + te["direction"])) * 100
    overlap_vs_py = len(both) / n_py * 100

    print(f"\n  n_python = {n_py}   n_tester = {n_te}   matched(date+dir) = {len(both)}")
    print(f"  overlap = {overlap_union:.1f}% (of union)   {overlap_vs_py:.1f}% (of python)")
    print(f"  python-only sessions (tester missed): {len(py_only)}")
    print(f"  tester-only sessions (python had none): {len(te_only)}")
    print(f"  same-date direction FLIPS: {len(flips)}")

    if len(both):
        b = both.dropna(subset=["tester_R", "py_R"])
        corr = b["tester_R"].corr(b["py_R"])
        er_delta = b["tester_R"].mean() - b["py_R"].mean()
        print(f"\n  --- MATCHED subset (n={len(b)}) ---")
        print(f"  win:   python {(b['py_R']>0).mean():.4f}   tester {(b['tester_R']>0).mean():.4f}")
        print(f"  E[R]:  python {b['py_R'].mean():+.4f}   tester {b['tester_R'].mean():+.4f}   "
              f"delta {er_delta:+.4f}")
        print(f"  R correlation (tester vs python): {corr:+.4f}")
        print(f"\n  tester exit_reason -> mean tester_R vs mean py_R (matched):")
        for reason, grp in b.groupby("exit_reason"):
            print(f"    {reason:<16} n={len(grp):>4}  tester_R={grp['tester_R'].mean():+.4f}  "
                  f"py_R={grp['py_R'].mean():+.4f}  win_te={ (grp['tester_R']>0).mean():.3f}")

    OUT.mkdir(parents=True, exist_ok=True)
    py.to_csv(OUT / "python_oos_trades.csv", index=False)
    te.to_csv(OUT / "tester_trades_parsed.csv", index=False)
    m.sort_values("session_date").to_csv(OUT / "fidelity_merged.csv", index=False)
    print(f"\n  outputs -> {OUT}")
    print("  (no research.db write — ingest is a reviewed follow-up)")


def main():
    print("=" * 80)
    print("ORB-001 GATE-7 FIDELITY DIFF  (MT5 10k tester vs Python research OOS)")
    print("=" * 80)
    py = python_oos_trades()
    te = tester_trades()
    diff(py, te)
    print("=" * 80)


if __name__ == "__main__":
    main()
