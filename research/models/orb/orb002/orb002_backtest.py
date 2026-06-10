"""
ORB-002 tick-level event backtest (NY-session, DST-aware anchor).

Honest intrabar resolution: actual ticks resolve stop vs target ordering.
Spread model: B-book/swap-free = win-rate drag (same as ORB-001 orb_backtest.py).
See orb_backtest.py header for the full spread-model notarisation.

Two exit modes:
  fixed   : fixed target_R (for Gate 3 raw edge sweep)
  trail_1R: trailing stop 1R behind running peak (ORB-001 live config, Task 25)

Anchor: NYSE 09:30 ET, DST-aware (13:30 UTC EDT / 14:30 UTC EST).
EOD flat: 21:00 UTC (end of US/NY session).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from research.models.orb.orb002.orb002_core import _tick_files, IS_END, ny_anchor_ns

EOD_CUTOFF_HOUR = 21
NS_H = 3_600_000_000_000
NS_M =    60_000_000_000
NS_D = 86_400_000_000_000


def _simulate_day_fixed(ts: np.ndarray, mid: np.ndarray,
                        day0: int, n_minutes: int,
                        spread_price: float = 0.0,
                        target_R: float = 3.0) -> dict | None:
    """
    Simulate one NY-session day with a FIXED target. DST-aware anchor.
    Spread model identical to orb_backtest._simulate_day (win-rate drag via bid/ask fills).
    Returns trade dict or None if no valid setup.
    """
    half = spread_price * 0.5
    anchor = ny_anchor_ns(day0)
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

    post = (ts >= win_end) & (ts < eod)
    if not post.any():
        return None
    pts, pmid = ts[post], mid[post]

    # entry: buy-stop fills on ASK (mid+half) reaching or_hi -> mid >= or_hi-half
    #        sell-stop fills on BID (mid-half) reaching or_lo -> mid <= or_lo+half
    up = pmid >= or_hi - half
    dn = pmid <= or_lo + half
    i_up = int(np.argmax(up)) if up.any() else None
    i_dn = int(np.argmax(dn)) if dn.any() else None
    if i_up is None and i_dn is None:
        return None

    if i_dn is None or (i_up is not None and i_up <= i_dn):
        direction, i_entry, entry = "long", i_up, or_hi
        stop = or_lo
        target = or_hi + target_R * range_w
    else:
        direction, i_entry, entry = "short", i_dn, or_lo
        stop = or_hi
        target = or_lo - target_R * range_w

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
        outcome, R, i_exit = "target", float(target_R), i_t
    elif i_s is not None:
        outcome, R, i_exit = "stop", -1.0, i_s
    else:
        exit_fill = (emid[-1] - half) if direction == "long" else (emid[-1] + half)
        R = ((exit_fill - entry) if direction == "long" else (entry - exit_fill)) / range_w
        outcome, i_exit = "eod", len(emid) - 1

    return {
        "direction": direction, "range_w": range_w, "entry_px": entry,
        "outcome": outcome, "R": float(R),
        "entry_ts": pd.Timestamp(ets[0]), "exit_ts": pd.Timestamp(ets[i_exit]),
    }


def _simulate_day_trail(ts: np.ndarray, mid: np.ndarray,
                        day0: int, n_minutes: int,
                        spread_price: float = 0.0) -> dict | None:
    """
    Simulate one NY-session day with TRAIL_1R exit. DST-aware anchor.

    trail_1R: trailing stop 1R (range_w) behind the running peak.
    No fixed target — let winners run until the trail is triggered or EOD.

    Spread model: entry fills on bid/ask; trail exit closes on the opposite quote.
    Matches structures.py _exit_R arm='trail_1R' and trail_oos.py logic.
    """
    half = spread_price * 0.5
    anchor = ny_anchor_ns(day0)
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

    ets = pts[i_entry:]
    emid = pmid[i_entry:]
    if len(emid) < 2:
        return None

    g = pdir * (emid - entry)           # favorable distance from entry
    peak_g = np.maximum.accumulate(g)   # running peak of favorable distance

    # trail fires when g drops 1R below the running peak (half-spread adjustment mirrors
    # structures.py: rel = g <= peak_g - rw + half)
    rel = g <= peak_g - range_w + half
    i_x = int(np.argmax(rel)) if rel.any() else None

    # exit fill: long closes on bid (mid-half), short closes on ask (mid+half)
    exit_fill = emid - pdir * half

    if i_x is not None:
        R = float(pdir * (exit_fill[i_x] - entry) / range_w)
        i_exit = i_x
        outcome = "trail"
    else:
        R = float(pdir * (exit_fill[-1] - entry) / range_w)
        i_exit = len(emid) - 1
        outcome = "eod"

    direction = "long" if pdir > 0 else "short"
    return {
        "direction": direction, "range_w": range_w, "entry_px": entry,
        "outcome": outcome, "R": R,
        "entry_ts": pd.Timestamp(ets[0]), "exit_ts": pd.Timestamp(ets[i_exit]),
    }


def run_backtest_multi_fixed(year_months, n_list, is_only=True,
                              spread_price=0.0, target_R=3.0,
                              oos_only=False) -> dict[int, pd.DataFrame]:
    """
    Read each tick partition ONCE; simulate NY ORB with fixed target for each N.
    Returns {N: trades_df}. Matches orb_backtest.run_backtest_multi interface.
    """
    from tqdm import tqdm

    files = _tick_files(year_months)
    if not files:
        raise FileNotFoundError("No tick parquet found")
    is_cut = np.datetime64(IS_END)

    trades = {N: [] for N in n_list}
    for f in tqdm(files, desc=f"NY fixed backtest N={n_list}"):
        df = pd.read_parquet(f, columns=["ts_utc", "bid", "ask"])
        if oos_only:
            df = df[df["ts_utc"].values >= is_cut]
        elif is_only:
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
                tr = _simulate_day_fixed(tsd, midd, day0, N,
                                          spread_price=spread_price, target_R=target_R)
                if tr is not None:
                    tr["date"] = pd.Timestamp(day0).date()
                    trades[N].append(tr)

    return {N: pd.DataFrame(rows) for N, rows in trades.items()}


def run_backtest_multi_trail(year_months, n_list, is_only=True,
                              spread_price=0.0, oos_only=False) -> dict[int, pd.DataFrame]:
    """
    Read each tick partition ONCE; simulate NY ORB with trail_1R for each N.
    Returns {N: trades_df}. One pass per spread value (barriers shift -> cannot post-process).
    """
    from tqdm import tqdm

    files = _tick_files(year_months)
    if not files:
        raise FileNotFoundError("No tick parquet found")
    is_cut = np.datetime64(IS_END)

    trades = {N: [] for N in n_list}
    for f in tqdm(files, desc=f"NY trail backtest N={n_list}"):
        df = pd.read_parquet(f, columns=["ts_utc", "bid", "ask"])
        if oos_only:
            df = df[df["ts_utc"].values >= is_cut]
        elif is_only:
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
                tr = _simulate_day_trail(tsd, midd, day0, N, spread_price=spread_price)
                if tr is not None:
                    tr["date"] = pd.Timestamp(day0).date()
                    trades[N].append(tr)

    return {N: pd.DataFrame(rows) for N, rows in trades.items()}


def edge_stats(trades: pd.DataFrame) -> dict:
    """
    Per-trade expectancy in R + t-stat (per-period Sharpe x sqrt(n)).
    Win = R > 0 (works for both fixed-target and trail exits).
    """
    R = trades["R"].values
    n = len(R)
    mean, sd = float(R.mean()), float(R.std(ddof=1))
    t = mean / (sd / np.sqrt(n)) if sd > 0 else np.nan
    wins = int((R > 0).sum())
    return {
        "n_trades": n, "E_R": mean, "sd_R": sd, "t_stat": t,
        "win_rate": wins / n,
        "n_win": wins,
        "n_loss": int((R < 0).sum()),
        "n_eod": int(trades["outcome"].eq("eod").sum()),
    }
