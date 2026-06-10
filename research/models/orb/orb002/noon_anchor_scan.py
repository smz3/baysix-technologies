"""
ORB-002 variant — noon ET anchor scan (task 26).

Exploratory: does the ORB spec (N∈{5,15,30}, trail_1R, 2-pip spread)
produce a raw + net edge at a 12:00 ET clock-time anchor?

NOT literature-backed. Native hypothesis from tape only.
Gate 3 raw runs first; Gate 5 net only runs if Gate 3 passes at least one N.
Full gate ladder only if both clear.

Anchor: 12:00 ET DST-aware -> 16:00 UTC (EDT) / 17:00 UTC (EST)
EOD flat: 21:00 UTC (same as ORB-002)

Run in a new PowerShell window (~8-10 min, full IS):
    python research/models/orb/orb002/noon_anchor_scan.py
"""
from __future__ import annotations

import sys
from datetime import datetime, time as dtime
from pathlib import Path

import numpy as np
import pandas as pd
import pytz
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from research.models.orb.orb002.orb002_core import _tick_files, IS_END, NY_TZ
from research.models.orb.orb002.orb002_backtest import edge_stats

# ── noon anchor config ────────────────────────────────────────────────────────
NOON_LOCAL = dtime(12, 0)   # 12:00 ET (EDT: 16:00 UTC / EST: 17:00 UTC)
EOD_CUTOFF_HOUR = 21        # flat at 21:00 UTC

NS_H = 3_600_000_000_000
NS_M =    60_000_000_000
NS_D = 86_400_000_000_000

N_SWEEP   = [5, 15, 30]
PRIMARY_N = 5
TARGET_R  = 3.0      # Gate 3 fixed target
PIP_PRICE = 0.10     # $0.10 per pip on JM XAUUSD.s
SPREADS_PIPS = [0.0, 2.0, 3.0]
E_R_FLOOR = 0.10
T_FLOOR   = 3.0


# ── anchor function ───────────────────────────────────────────────────────────
def noon_anchor_ns(day0_ns: int) -> int:
    """UTC midnight in ns -> 12:00 ET anchor in ns (DST-aware)."""
    date = pd.Timestamp(day0_ns).date()
    dt_ny = NY_TZ.localize(datetime.combine(date, NOON_LOCAL))
    return int(dt_ny.timestamp() * 1_000_000_000)


# ── sim functions (noon anchor; logic mirrors orb002_backtest) ────────────────
def _sim_fixed(ts, mid, day0, n_minutes, spread_price=0.0, target_R=3.0):
    half = spread_price * 0.5
    anchor  = noon_anchor_ns(day0)
    win_end = anchor + n_minutes * NS_M
    eod     = day0 + EOD_CUTOFF_HOUR * NS_H

    in_win = (ts >= anchor) & (ts < win_end)
    if not in_win.any():
        return None
    or_hi, or_lo = mid[in_win].max(), mid[in_win].min()
    range_w = or_hi - or_lo
    if range_w <= 0:
        return None

    post = (ts >= win_end) & (ts < eod)
    if not post.any():
        return None
    pts, pmid = ts[post], mid[post]

    up = pmid >= or_hi - half
    dn = pmid <= or_lo + half
    i_up = int(np.argmax(up)) if up.any() else None
    i_dn = int(np.argmax(dn)) if dn.any() else None
    if i_up is None and i_dn is None:
        return None

    if i_dn is None or (i_up is not None and i_up <= i_dn):
        direction, i_entry, entry = "long",  i_up, or_hi
        stop, target = or_lo, or_hi + target_R * range_w
    else:
        direction, i_entry, entry = "short", i_dn, or_lo
        stop, target = or_hi, or_lo - target_R * range_w

    ets, emid = pts[i_entry:], pmid[i_entry:]
    hit_t = emid >= target + half if direction == "long" else emid <= target - half
    hit_s = emid <= stop  + half if direction == "long" else emid >= stop  - half
    i_t = int(np.argmax(hit_t)) if hit_t.any() else None
    i_s = int(np.argmax(hit_s)) if hit_s.any() else None

    if i_t is not None and (i_s is None or i_t <= i_s):
        outcome, R = "target", float(target_R)
    elif i_s is not None:
        outcome, R = "stop", -1.0
    else:
        ef = (emid[-1] - half) if direction == "long" else (emid[-1] + half)
        R  = ((ef - entry) if direction == "long" else (entry - ef)) / range_w
        outcome = "eod"

    return {"direction": direction, "range_w": range_w, "outcome": outcome, "R": float(R)}


def _sim_trail(ts, mid, day0, n_minutes, spread_price=0.0):
    half = spread_price * 0.5
    anchor  = noon_anchor_ns(day0)
    win_end = anchor + n_minutes * NS_M
    eod     = day0 + EOD_CUTOFF_HOUR * NS_H

    in_win = (ts >= anchor) & (ts < win_end)
    if not in_win.any():
        return None
    or_hi, or_lo = mid[in_win].max(), mid[in_win].min()
    range_w = or_hi - or_lo
    if range_w <= 0:
        return None

    post = (ts >= win_end) & (ts < eod)
    if not post.any():
        return None
    pts, pmid = ts[post], mid[post]

    up = pmid >= or_hi - half
    dn = pmid <= or_lo + half
    i_up = int(np.argmax(up)) if up.any() else None
    i_dn = int(np.argmax(dn)) if dn.any() else None
    if i_up is None and i_dn is None:
        return None

    if i_dn is None or (i_up is not None and i_up <= i_dn):
        pdir, entry, i_entry = 1.0, or_hi, i_up
    else:
        pdir, entry, i_entry = -1.0, or_lo, i_dn

    emid = pmid[i_entry:]
    if len(emid) < 2:
        return None

    g      = pdir * (emid - entry)
    peak_g = np.maximum.accumulate(g)
    rel    = g <= peak_g - range_w + half
    i_x    = int(np.argmax(rel)) if rel.any() else None
    ef     = emid - pdir * half

    if i_x is not None:
        R, outcome = float(pdir * (ef[i_x] - entry) / range_w), "trail"
    else:
        R, outcome = float(pdir * (ef[-1]   - entry) / range_w), "eod"

    return {"direction": "long" if pdir > 0 else "short",
            "range_w": range_w, "outcome": outcome, "R": float(R)}


# ── multi-day runner ──────────────────────────────────────────────────────────
def _run_multi(sim_fn, n_list, is_only=True, **kwargs):
    files = _tick_files(None)   # full IS date range
    if not files:
        raise FileNotFoundError("No tick parquet found")
    is_cut = np.datetime64(IS_END)
    trades = {N: [] for N in n_list}
    for f in tqdm(files, desc="noon scan"):
        df = pd.read_parquet(f, columns=["ts_utc", "bid", "ask"])
        df = df[df["ts_utc"].values < is_cut] if is_only else df
        if df.empty:
            continue
        ts_all  = df["ts_utc"].values.astype("datetime64[ns]").astype(np.int64)
        mid_all = (df["bid"].values + df["ask"].values) * 0.5
        day_key = ts_all // NS_D
        for d in np.unique(day_key):
            m = day_key == d
            tsd, midd, day0 = ts_all[m], mid_all[m], int(d) * NS_D
            for N in n_list:
                tr = sim_fn(tsd, midd, day0, N, **kwargs)
                if tr is not None:
                    trades[N].append(tr)
    return {N: pd.DataFrame(rows) for N, rows in trades.items()}


# ── gate 3 raw ────────────────────────────────────────────────────────────────
def run_gate3():
    print("=" * 72)
    print("NOON SCAN — GATE 3 RAW EDGE  |  XAUUSD  |  full IS  |  fixed 3R")
    print("anchor = 12:00 ET (16:00 UTC EDT / 17:00 UTC EST)")
    print(f"kill-line: E[R] >= {E_R_FLOOR}  AND  t >= {T_FLOOR}")
    print("=" * 72)

    all_trades = _run_multi(_sim_fixed, N_SWEEP, spread_price=0.0, target_R=TARGET_R)

    passers = []
    for N in N_SWEEP:
        s = edge_stats(all_trades[N])
        flag    = "[PRIMARY]" if N == PRIMARY_N else ""
        verdict = "PASS" if (s["E_R"] >= E_R_FLOOR and s["t_stat"] >= T_FLOOR) else "FAIL"
        print(f"  N={N:>2} {flag:<10}  trades={s['n_trades']:,}  "
              f"win={s['win_rate']:.1%}  E[R]={s['E_R']:+.4f}  "
              f"t={s['t_stat']:+.2f}  -> {verdict}")
        if verdict == "PASS":
            passers.append(N)

    return passers


# ── gate 5 net ────────────────────────────────────────────────────────────────
def run_gate5():
    print("\n" + "=" * 72)
    print("NOON SCAN — GATE 5 NET EDGE  |  trail_1R  |  full IS")
    print(f"anchor = 12:00 ET  |  kill-line: E[R] > 0  AND  t >= {T_FLOOR}  @ 2-pip")
    print("=" * 72)

    runs = {}
    for sp in SPREADS_PIPS:
        runs[sp] = _run_multi(_sim_trail, N_SWEEP, spread_price=sp * PIP_PRICE)

    for N in N_SWEEP:
        flag = "[PRIMARY]" if N == PRIMARY_N else ""
        print(f"\n  N={N} {flag}")
        for sp in SPREADS_PIPS:
            s     = edge_stats(runs[sp][N])
            label = "raw " if sp == 0 else f"{sp:.0f}pip"
            tag   = ""
            if sp != 0:
                tag = "  PASS" if (s["E_R"] > 0 and s["t_stat"] >= T_FLOOR) else "  FAIL"
            print(f"    {label}: win={s['win_rate']:.1%}  "
                  f"E[R]={s['E_R']:+.4f}  t={s['t_stat']:+.2f}{tag}")

    prim = edge_stats(runs[2.0][PRIMARY_N])
    ok   = prim["E_R"] > 0 and prim["t_stat"] >= T_FLOOR
    print()
    verdict_str = "PASS" if ok else "FAIL"
    print(f"GATE 5 {verdict_str}: N={PRIMARY_N} noon trail_1R @ 2-pip  "
          f"E[R]={prim['E_R']:+.4f}  t={prim['t_stat']:+.2f}")
    return ok


# ── entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    g3_passers = run_gate3()

    if not g3_passers:
        print("\nGate 3 FAIL across all N. Noon anchor has no raw edge -> stop here.")
        sys.exit(0)

    print(f"\nGate 3 passers: N={g3_passers}. Proceeding to Gate 5 net...")
    g5_ok = run_gate5()

    if not g5_ok:
        print("\nGate 5 FAIL. Noon anchor falsified at net level.")
        sys.exit(0)

    print("\nBoth gates pass. Log results and consider full gate ladder (gates 6+).")
