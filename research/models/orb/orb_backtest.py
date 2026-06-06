"""
ORB-001 tick-level event backtest (Gate 3 engine).

Honest intrabar resolution: after a breakout entry, we walk the ACTUAL ticks to
see whether the stop or the target is touched first. 1-min bars cannot resolve
that ordering; ticks can. This is our data edge.

Trade definition (per Gate 1, step5 call_id=9/10):
  range_w = or_high - or_low                       (= 1R)
  long  : entry=or_high, stop=or_low,  target=or_high + 2*range_w   (risk 1R / reward 2R)
  short : entry=or_low,  stop=or_high, target=or_low  - 2*range_w
  exit  : first of {stop, target} touched, else flat at EOD cutoff (no overnight).

Spread is applied via `spread_price` (0.0 = raw mid, Gate 3). See _simulate_day
for the model. London anchor = 08:00 UTC fixed (see orb_core).

NOTARIZATION — spread-cost model change (2026-06-06)
----------------------------------------------------
ORIGINAL (gate5_cost.py, now superseded): treated JM spread as a flat payoff
deduction, net_R = raw_R - spread/range_w. WRONG mechanism — it shrank the 2:1
payoff, implying smaller wins and bigger losses.
CORRECTED (here): on a B-book/swap-free account, spread does NOT debit on entry
and does NOT change the 2:1 payoff on the levels (Syafiq, 2026-06-06). It is
embedded in fills: buy-stop on ASK, target/stop on BID -> the barriers shift by
half a spread in true (mid) terms, so the spread is a WIN-RATE drag, not a payoff
cut. Same ~1-spread/round-trip magnitude, correct mechanism. Spread is the ONLY
cost (swap-free + intraday EOD-flat = $0 swap; Pro = $0 commission; leverage
irrelevant to edge). Synthetic bid/ask = Dukascopy mid +/- half the JM spread.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from research.models.orb.orb_core import _tick_files, IS_END, LONDON_ANCHOR_HOUR

EOD_CUTOFF_HOUR = 21  # flat by 21:00 UTC, fixed (end of US session, no overnight)


def _simulate_day(ts: np.ndarray, mid: np.ndarray,
                  day0: np.ndarray, n_minutes: int,
                  spread_price: float = 0.0) -> dict | None:
    """
    ts:   int64 ns timestamps for ONE calendar day (sorted ascending)
    mid:  float mid prices aligned with ts
    day0: int64 ns of that day's 00:00 UTC
    spread_price: JM round-trip spread in price units (0.0 = raw mid, Gate 3).

    SPREAD MODEL (corrected 2026-06-06, step5 call_id below — see notarization note
    in module header): spread is NOT a payoff deduction. The R:R payoff stays a
    clean 2:1 on the levels; spread shows up as a lower WIN RATE because fills are
    on bid/ask, not mid. A buy-stop fills on the ASK and the target/stop resolve on
    the BID, so in true (mid) terms the target sits a half-spread FARTHER and the
    stop a half-spread NEARER -> you hit the stop slightly more often. We synthesise
    bid/ask from Dukascopy mid +/- half the JM spread (yaml: model on Dukascopy mid,
    apply JM's spread, not Dukascopy's tight ECN spread).

    Returns a trade dict, or None if no valid setup.
    """
    NS_H = 3_600_000_000_000
    NS_M = 60_000_000_000
    half = spread_price * 0.5     # ask = mid + half, bid = mid - half
    anchor = day0 + LONDON_ANCHOR_HOUR * NS_H
    win_end = anchor + n_minutes * NS_M
    eod = day0 + EOD_CUTOFF_HOUR * NS_H

    in_win = (ts >= anchor) & (ts < win_end)
    if not in_win.any():
        return None
    or_hi = mid[in_win].max()
    or_lo = mid[in_win].min()
    range_w = or_hi - or_lo
    if range_w <= 0:
        return None

    # post-window, pre-EOD search space
    post = (ts >= win_end) & (ts < eod)
    if not post.any():
        return None
    pts, pmid = ts[post], mid[post]

    # entry: buy-stop fills on ASK (mid+half) reaching or_hi -> mid >= or_hi-half;
    #        sell-stop fills on BID (mid-half) reaching or_lo -> mid <= or_lo+half.
    up = pmid >= or_hi - half
    dn = pmid <= or_lo + half
    i_up = int(np.argmax(up)) if up.any() else None
    i_dn = int(np.argmax(dn)) if dn.any() else None
    if i_up is None and i_dn is None:
        return None
    if i_dn is None or (i_up is not None and i_up <= i_dn):
        direction, i_entry, entry = "long", i_up, or_hi          # filled at ask=or_hi
        stop, target = or_lo, or_hi + 2 * range_w
    else:
        direction, i_entry, entry = "short", i_dn, or_lo         # filled at bid=or_lo
        stop, target = or_hi, or_lo - 2 * range_w

    # walk ticks from entry; exits resolve on the opposite quote:
    #   long  -> sell side (BID=mid-half): target when mid>=target+half, stop when mid<=or_lo+half
    #   short -> buy side  (ASK=mid+half): target when mid<=target-half, stop when mid>=or_hi-half
    ets, emid = pts[i_entry:], pmid[i_entry:]
    if direction == "long":
        hit_t = emid >= target + half
        hit_s = emid <= stop + half
    else:
        hit_t = emid <= target - half
        hit_s = emid >= stop - half
    i_t = int(np.argmax(hit_t)) if hit_t.any() else None
    i_s = int(np.argmax(hit_s)) if hit_s.any() else None

    if i_t is not None and (i_s is None or i_t <= i_s):
        outcome, R, i_exit = "target", 2.0, i_t        # payoff clean +2R
    elif i_s is not None:
        outcome, R, i_exit = "stop", -1.0, i_s         # payoff clean -1R
    else:  # timeout -> flat at last tick before EOD, exit on the opposite quote
        exit_fill = (emid[-1] - half) if direction == "long" else (emid[-1] + half)
        R = ((exit_fill - entry) if direction == "long" else (entry - exit_fill)) / range_w
        outcome, i_exit = "eod", len(emid) - 1

    return {
        "direction": direction, "range_w": range_w, "entry_px": entry,
        "outcome": outcome, "R": float(R),
        "entry_ts": pd.Timestamp(ets[0]), "exit_ts": pd.Timestamp(ets[i_exit]),
    }


def run_backtest(year_months: list[tuple[int, int]] | None,
                 n_minutes: int, is_only: bool = True,
                 quiet: bool = False) -> pd.DataFrame:
    """Stream tick partitions month-by-month and simulate one ORB trade per day."""
    from tqdm import tqdm

    files = _tick_files(year_months)
    if not files:
        raise FileNotFoundError("No tick parquet found")
    is_cut = np.datetime64(IS_END)

    trades = []
    it = files if quiet else tqdm(files, desc=f"backtest N={n_minutes}m")
    for f in it:
        df = pd.read_parquet(f, columns=["ts_utc", "bid", "ask"])
        if is_only:
            df = df[df["ts_utc"].values < is_cut]
        if df.empty:
            continue
        ts_all = df["ts_utc"].values.astype("datetime64[ns]").astype(np.int64)
        mid_all = ((df["bid"].values + df["ask"].values) * 0.5)
        # day index = floor to days in ns
        NS_D = 86_400_000_000_000
        day_key = (ts_all // NS_D)
        for d in np.unique(day_key):
            m = day_key == d
            tr = _simulate_day(ts_all[m], mid_all[m], int(d) * NS_D, n_minutes)
            if tr is not None:
                tr["date"] = pd.Timestamp(int(d) * NS_D).date()
                trades.append(tr)

    return pd.DataFrame(trades)


def run_backtest_multi(year_months: list[tuple[int, int]] | None,
                       n_list: list[int], is_only: bool = True,
                       spread_price: float = 0.0) -> dict[int, pd.DataFrame]:
    """Read each tick partition ONCE and simulate every N per day (avoids 3x I/O).
    spread_price: JM round-trip spread in price units (0.0 = raw mid)."""
    from tqdm import tqdm

    files = _tick_files(year_months)
    if not files:
        raise FileNotFoundError("No tick parquet found")
    is_cut = np.datetime64(IS_END)
    NS_D = 86_400_000_000_000

    trades = {N: [] for N in n_list}
    for f in tqdm(files, desc=f"backtest N={n_list}"):
        df = pd.read_parquet(f, columns=["ts_utc", "bid", "ask"])
        if is_only:
            df = df[df["ts_utc"].values < is_cut]
        if df.empty:
            continue
        ts_all = df["ts_utc"].values.astype("datetime64[ns]").astype(np.int64)
        mid_all = (df["bid"].values + df["ask"].values) * 0.5
        day_key = ts_all // NS_D
        for d in np.unique(day_key):
            m = day_key == d
            tsd, midd, day0 = ts_all[m], mid_all[m], int(d) * NS_D
            for N in n_list:
                tr = _simulate_day(tsd, midd, day0, N, spread_price=spread_price)
                if tr is not None:
                    tr["date"] = pd.Timestamp(day0).date()
                    trades[N].append(tr)

    return {N: pd.DataFrame(rows) for N, rows in trades.items()}


def edge_stats(trades: pd.DataFrame) -> dict:
    """Per-trade expectancy in R + t-stat (per-period Sharpe x sqrt(n))."""
    R = trades["R"].values
    n = len(R)
    mean, sd = float(R.mean()), float(R.std(ddof=1))
    t = mean / (sd / np.sqrt(n)) if sd > 0 else np.nan
    wins = trades["outcome"].eq("target").sum()
    return {
        "n_trades": n, "E_R": mean, "sd_R": sd, "t_stat": t,
        "win_rate": wins / n,
        "n_target": int(wins),
        "n_stop": int(trades["outcome"].eq("stop").sum()),
        "n_eod": int(trades["outcome"].eq("eod").sum()),
    }
