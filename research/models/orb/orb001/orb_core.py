"""
ORB-001 core — Opening-Range Breakout primitives for XAUUSD (Dukascopy ticks).

London anchor = 08:00:00 UTC, fixed year-round (Gate 1 decision, step5 call_id=10).
The Dukascopy feed has a systematic daily 07:00-08:00 UTC maintenance gap
(verified 0 ticks every weekday across 2016/2019/2022/2023), so the summer
London open (07:00 UTC under BST) is UNOBSERVABLE; 08:00 UTC is the first clean
tick and the data's daily/weekly session reset. A DST-aware London-local anchor
therefore collapses to 08:00 UTC anyway -> we hardcode it. DST-immune by design.

Pipeline:  tick parquet  ->  1-min mid OHLC (UTC)
           ->  per-day opening range over [08:00, 08:00+N)
           ->  first breakout of range high/low after the window closes.

NOTE: NY phase (later) is NOT in any gap and DOES need real DST handling
(America/New_York 09:30 -> 13:30/14:30 UTC). This module is London-only.
"""
from __future__ import annotations

import glob
from pathlib import Path

import numpy as np
import pandas as pd

# Resolve repo root from this file so the module runs from anywhere.
_REPO = Path(__file__).resolve().parents[4]
_TICK_DIR = _REPO / "data" / "parquet" / "CS-GOLD-DUKAS-TICK"

IS_END = pd.Timestamp("2024-05-02")     # sealed IS/OOS boundary (matches hmm)
LONDON_ANCHOR_HOUR = 8                   # 08:00:00 UTC, fixed (see docstring)


def _tick_files(year_months: list[tuple[int, int]] | None) -> list[str]:
    """Resolve parquet partition paths for the requested (year, month) list, or all."""
    if year_months is None:
        return sorted(str(p) for p in _TICK_DIR.glob("year=*/month=*/*.parquet"))
    out = []
    for yr, mo in year_months:
        out += [str(p) for p in _TICK_DIR.glob(f"year={yr}/month={mo}/*.parquet")]
    return sorted(out)


def load_minute_bars(year_months: list[tuple[int, int]] | None = None,
                     is_only: bool = True) -> pd.DataFrame:
    """
    Load tick parquet partitions and resample to 1-minute mid-price OHLC (UTC).

    Returns a DataFrame indexed by UTC minute with columns [open, high, low, close].
    Empty minutes (incl. the 07-08 UTC gap and weekends) are dropped, not filled.
    """
    files = _tick_files(year_months)
    if not files:
        raise FileNotFoundError(f"No tick parquet found under {_TICK_DIR}")

    from tqdm import tqdm
    frames = []
    for f in tqdm(files, desc="load+resample ticks"):
        df = pd.read_parquet(f, columns=["ts_utc", "bid", "ask"])
        df["mid"] = (df["bid"] + df["ask"]) * 0.5
        bars = (df.set_index("ts_utc")["mid"]
                  .resample("1min").ohlc()
                  .dropna(how="all"))
        frames.append(bars)
        print(f"  {Path(f).parent.name:>9} {Path(f).parents[1].name}: "
              f"{len(df):>9,} ticks -> {len(bars):>6,} 1-min bars")

    bars = pd.concat(frames).sort_index()
    bars = bars[~bars.index.duplicated(keep="first")]
    if is_only:
        bars = bars[bars.index < IS_END]
    return bars


def opening_range_breakouts(bars_1m: pd.DataFrame,
                            n_minutes: int = 15,
                            search_end_hour: int = 17) -> pd.DataFrame:
    """
    Per trading day, build the opening range over [08:00, 08:00+N) UTC, then find
    the FIRST breakout of the range high/low after the window closes.

    No look-ahead: the range uses only [08:00, 08:00+N); the breakout search is
    strictly from 08:00+N onward, capped at search_end_hour:00 UTC. Entry price is
    the breached range level (realistic stop-entry fill).

    Returns one row per day with: or_high, or_low, range_w, direction
    ('long'/'short'/'none'), break_time, entry_px.
    """
    from tqdm import tqdm

    rows = []
    days = list(bars_1m.groupby(bars_1m.index.normalize()))
    for day, g in tqdm(days, desc=f"ORB N={n_minutes}m"):
        anchor = day + pd.Timedelta(hours=LONDON_ANCHOR_HOUR)
        or_win = g[(g.index >= anchor) & (g.index < anchor + pd.Timedelta(minutes=n_minutes))]
        if or_win.empty:
            continue  # holiday / no 08:00 session this day

        or_hi = float(or_win["high"].max())
        or_lo = float(or_win["low"].min())

        post = g[(g.index >= anchor + pd.Timedelta(minutes=n_minutes)) &
                 (g.index < day + pd.Timedelta(hours=search_end_hour))]

        long_hit = post.index[post["high"] > or_hi]
        short_hit = post.index[post["low"] < or_lo]
        t_long = long_hit[0] if len(long_hit) else None
        t_short = short_hit[0] if len(short_hit) else None

        if t_long is None and t_short is None:
            direction, btime, entry = "none", None, np.nan
        elif t_short is None or (t_long is not None and t_long <= t_short):
            direction, btime, entry = "long", t_long, or_hi
        else:
            direction, btime, entry = "short", t_short, or_lo

        rows.append({
            "date": day.date(), "or_high": or_hi, "or_low": or_lo,
            "range_w": or_hi - or_lo, "direction": direction,
            "break_time": None if btime is None else btime.time(),
            "entry_px": entry,
        })

    return pd.DataFrame(rows).set_index("date")
