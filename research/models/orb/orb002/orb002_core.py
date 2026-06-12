"""
ORB-002 core — NY-session ORB primitives (NYSE 09:30 ET, DST-aware).

Transplant of ORB-001 (London anchor 08:00 UTC fixed) to the NY session.
Anchor = America/New_York 09:30 -> 13:30 UTC (EDT, Mar-Nov) / 14:30 UTC (EST, Nov-Mar).
Config inherited verbatim from ORB-001 live: N=5 / trail_1R / Mode-A 5% cap.

IS/OOS boundary: shared with ORB-001 at 2024-05-02.

NOTE: Unlike ORB-001 (London 08:00 UTC is DST-immune due to Dukascopy's 07-08 UTC
maintenance gap), the NY session is fully observable and requires real DST handling.
"""
from __future__ import annotations

import pytz
from datetime import datetime, time as dtime
from pathlib import Path

import numpy as np
import pandas as pd

import sys
_REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(_REPO))
# Canonical tick source = SORTED ArcticDB store via arctic_io (task 51, 2026-06-12).
from research.code.arctic_io import tick_months, read_tick_month

NY_TZ = pytz.timezone("America/New_York")
NY_ANCHOR_LOCAL = dtime(9, 30)          # 09:30 ET
IS_END = pd.Timestamp("2024-05-02")    # shared IS/OOS boundary (matches ORB-001/HMM)


def ny_anchor_ns(day0_ns: int) -> int:
    """
    Convert UTC midnight in ns to 09:30 ET anchor in ns (DST-aware).

    Examples:
      2024-01-15 (EST, UTC-5): 09:30 ET -> 14:30 UTC -> 14.5 * 3.6e12 ns since midnight UTC
      2024-03-15 (EDT, UTC-4): 09:30 ET -> 13:30 UTC -> 13.5 * 3.6e12 ns since midnight UTC
    """
    date = pd.Timestamp(day0_ns).date()
    dt_naive = datetime.combine(date, NY_ANCHOR_LOCAL)
    dt_ny = NY_TZ.localize(dt_naive)
    return int(dt_ny.timestamp() * 1_000_000_000)


def _tick_files(year_months: list[tuple[int, int]] | None = None) -> list[tuple[int, int]]:
    """The (year, month) Arctic partitions to iterate (name kept for back-compat;
    mirrors orb_core._tick_files). Pair with read_tick_month()."""
    return tick_months(year_months)


def load_minute_bars(year_months: list[tuple[int, int]] | None = None,
                     is_only: bool = True) -> pd.DataFrame:
    """
    Load ticks (sorted, from Arctic) and resample to 1-min mid OHLC (tz-naive UTC).
    Used primarily for Gate 2 sanity visuals.
    """
    months = _tick_files(year_months)
    if not months:
        raise FileNotFoundError("ArcticDB store returned no months (data/arctic).")

    from tqdm import tqdm
    frames = []
    for ym in tqdm(months, desc="load+resample ticks"):
        df = read_tick_month(ym, columns=["ts_utc", "bid", "ask"])
        df["mid"] = (df["bid"] + df["ask"]) * 0.5
        bars = (df.set_index("ts_utc")["mid"]
                  .resample("1min").ohlc()
                  .dropna(how="all"))
        frames.append(bars)
        print(f"  {ym[0]}-{ym[1]:02d}: {len(df):>9,} ticks -> {len(bars):>6,} 1-min bars")

    bars = pd.concat(frames).sort_index()
    bars = bars[~bars.index.duplicated(keep="first")]
    if is_only:
        bars = bars[bars.index < IS_END]
    return bars


def opening_range_breakouts_ny(bars_1m: pd.DataFrame,
                                n_minutes: int = 5,
                                search_end_hour_utc: int = 21) -> pd.DataFrame:
    """
    Per day: build the NY opening range over [09:30 ET, 09:30+N) ET (DST-aware),
    then find the FIRST breakout after the window closes.

    bars_1m: tz-naive UTC 1-min OHLC (from load_minute_bars).
    No look-ahead: OR uses only [anchor, anchor+N); breakout search is strictly after.

    Returns one row per day: or_high, or_low, range_w, direction, break_time (UTC), entry_px.
    """
    from tqdm import tqdm

    rows = []
    days = list(bars_1m.groupby(bars_1m.index.normalize()))
    for day, g in tqdm(days, desc=f"NY-ORB N={n_minutes}m"):
        day0_ns = day.value
        anchor_ns = ny_anchor_ns(day0_ns)
        anchor_ts = pd.Timestamp(anchor_ns)                          # tz-naive UTC
        win_end_ts = anchor_ts + pd.Timedelta(minutes=n_minutes)
        search_end_ts = day + pd.Timedelta(hours=search_end_hour_utc)

        or_win = g[(g.index >= anchor_ts) & (g.index < win_end_ts)]
        if or_win.empty:
            continue

        or_hi = float(or_win["high"].max())
        or_lo = float(or_win["low"].min())

        post = g[(g.index >= win_end_ts) & (g.index < search_end_ts)]

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
