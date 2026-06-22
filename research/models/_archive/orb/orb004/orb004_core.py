"""
ORB-004 core — VWAP/ATR-conditioned, multi-session Opening-Range Breakout (XAUUSD).

Spec (research.db ORB-004, Gates 0+1 passed):
  - Range  : first completed M15 bar of EACH session sets [or_high, or_low].
  - Entry  : first break of that range AFTER the M15 closes (stop at range extreme),
             taken ONLY IF (a) break direction is aligned with the PRIOR-24H ROLLING
             VWAP (long above value / short below), and (b) range_w clears a regime
             gate (range_w >= k * trailing-median range, self-normalising).

WHY PRIOR-24H VWAP (not session VWAP): a VWAP anchored at the session open and read
at the breakout instant is TAUTOLOGICAL — the break high is, by construction, above
the cumulative average of the bars just built, so 100% of breakouts "align" and the
filter does nothing (Gate-2 sanity, 2026-06-13). A trailing-24h VWAP is a genuine
value reference: a 15-min range shifts it <1%, so a breakout can sit on EITHER side
of the day's value area, and the alignment flag carries real information.

WHY TRAILING-MEDIAN REGIME (not daily ATR): the first-M15 range is ~0.07-0.24x daily
ATR, so a daily-ATR gate at k>=0.25 rejects ~all trades (wrong yardstick). Gating the
range against its own trailing median per session is scale-correct and regime-aware.
  - Exit   : flat at session close, opposite-range-edge stop, no trail.
  - Sizing : Mode-A fixed 15% cap, 1/session, <=3/day  (scored at Gate 3, not here).

THIS MODULE = the FEATURE LAYER only (Gate 2). It builds every input the entry
rule needs (range, direction, vwap-at-break, atr, regime ratio, alignment flag)
WITHOUT deciding the trade — the k-sweep + cost + scoring live at Gate 3
(run_and_log). Keeping the raw, unfiltered breakout here lets Gate 3 measure what
each filter actually removes.

Sessions (UTC anchors):
  asian  = Tokyo 09:00 JST = 00:00 UTC   (JST has no DST -> fixed)
  london = 08:00 UTC fixed               (Dukascopy 07-08 UTC gap -> DST-immune,
                                           inherited from ORB-001 orb_core)
  ny     = NYSE 09:30 America/New_York    (DST-AWARE -> 13:30 UTC EDT / 14:30 EST,
                                           inherited from ORB-002 anchor decision)

No look-ahead: range uses only [anchor, anchor+15m); the breakout/VWAP search is
strictly from anchor+15m onward; ATR is shifted one day (prior-day close-of-info).
Ticks come SORTED from arctic_io (the unsorted-tick look-ahead is impossible here).
"""
from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pandas as pd

_REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(_REPO))
from research.code.arctic_io import tick_months, read_tick_month, daily_bars

IS_END = pd.Timestamp("2024-05-02")     # sealed IS/OOS boundary
M15 = 15                                 # range bar = first M15 of the session
SESSION_HOURS = 8                        # breakout search window / "session close"

# session anchors. 'utc_hour' = fixed UTC hour; 'ny' uses DST-aware local time.
SESSIONS = ("asian", "london", "ny")
_UTC_ANCHOR = {"asian": 0, "london": 8}          # fixed UTC hour
_NY_LOCAL = ("09:30", "America/New_York")        # DST-aware


def session_anchor(day: pd.Timestamp, session: str) -> pd.Timestamp:
    """UTC anchor timestamp for `session` on calendar `day` (tz-naive UTC)."""
    day = pd.Timestamp(day).normalize()
    if session in _UTC_ANCHOR:
        return day + pd.Timedelta(hours=_UTC_ANCHOR[session])
    if session == "ny":
        hhmm, tz = _NY_LOCAL
        local = pd.Timestamp(f"{day.date()} {hhmm}", tz=tz)
        return local.tz_convert("UTC").tz_localize(None)
    raise ValueError(f"unknown session {session!r}")


# ── data ────────────────────────────────────────────────────────────────────────

def load_minute_bars(year_months: list[tuple[int, int]] | None = None,
                     is_only: bool = True) -> pd.DataFrame:
    """1-minute mid-OHLC + summed tick volume (UTC). Volume is needed for VWAP, so
    unlike ORB-001's loader this one keeps it. Empty minutes dropped, not filled."""
    months = tick_months(year_months)
    if not months:
        raise FileNotFoundError("ArcticDB store returned no months (data/arctic).")

    from tqdm import tqdm
    frames = []
    for ym in tqdm(months, desc="load+resample ticks"):
        df = read_tick_month(ym, columns=["ts_utc", "bid", "ask", "volume"])
        df["mid"] = (df["bid"] + df["ask"]) * 0.5
        g = df.set_index("ts_utc")
        bars = g["mid"].resample("1min").ohlc()
        bars["volume"] = g["volume"].resample("1min").sum()
        bars = bars.dropna(subset=["open"])          # drop empty minutes (keep vol=0)
        frames.append(bars)
        print(f"  {ym[0]}-{ym[1]:02d}: {len(df):>9,} ticks -> {len(bars):>6,} 1-min bars")

    bars = pd.concat(frames).sort_index()
    bars = bars[~bars.index.duplicated(keep="first")]
    if is_only:
        bars = bars[bars.index < IS_END]
    return bars


def daily_atr(period: int = 14) -> pd.Series:
    """Daily ATR(period) on the sorted XAUUSD_DAILY mid-OHLC symbol, SHIFTED one day
    so each trading day only ever sees ATR computed from prior-day-and-earlier
    closes (no same-day look-ahead). Indexed by date (the day it MAY be used)."""
    d = daily_bars(columns=["open", "high", "low", "close"]).copy()
    prev_close = d["close"].shift(1)
    tr = pd.concat([
        d["high"] - d["low"],
        (d["high"] - prev_close).abs(),
        (d["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr = tr.rolling(period).mean().shift(1)         # info available at session open
    atr.index = pd.DatetimeIndex(atr.index).normalize()
    atr.name = "atr"
    return atr


def rolling_vwap(bars_1m: pd.DataFrame, window: str = "24h") -> pd.Series:
    """Trailing-`window` VWAP over the 1-min bars: sum(typ*vol)/sum(vol) on a
    time-based rolling window (handles the irregular index / weekend+gap holes).
    typ = (h+l+c)/3. This is the VALUE reference the breakout is judged against —
    NOT session-anchored (that's tautological for an immediate breakout)."""
    typ = (bars_1m["high"] + bars_1m["low"] + bars_1m["close"]) / 3.0
    pv = (typ * bars_1m["volume"]).rolling(window).sum()
    v = bars_1m["volume"].rolling(window).sum()
    return (pv / v.replace(0, np.nan)).rename("vwap24h")


# ── per-session signal build ──────────────────────────────────────────────────

def build_session_signals(bars_1m: pd.DataFrame,
                          atr: pd.Series | None = None,
                          sessions: tuple[str, ...] = SESSIONS,
                          regime_lookback: int = 20,
                          spread_price: float = 0.0) -> pd.DataFrame:
    """One row per (date, session): the first-M15 range, the RAW first breakout, its
    simulated outcome (R), and the filter inputs (vwap_aligned, range_w_regime).

    No filter is applied here — every breakout is recorded with its filter flags, so
    Gate 3 can sweep (vwap_on x regime-k) and measure what each filter buys.

    EXIT SIM (1-min, conservative): risk = range_w (=1R); stop = opposite range edge;
    exit = flat at session close (anchor + SESSION_HOURS). Spread is a half-spread
    barrier shift (B-book win-rate drag, NOT a payoff cut — ORB-001 corrected model):
    a long stops when bar-low <= or_lo + half, the close-out fills a half-spread worse.
    Same-bar entry+stop -> counted as the stop (conservative; no optimism manufactured).
    spread_price = round-trip spread in PRICE units (JM 2 pip = 0.20); 0.0 = raw.
    """
    half = spread_price * 0.5
    from tqdm import tqdm
    if atr is None:
        atr = daily_atr()
    vwap24h = rolling_vwap(bars_1m)                   # value reference, computed once

    rows = []
    days = list(bars_1m.groupby(bars_1m.index.normalize()))
    for day, g in tqdm(days, desc="session signals"):
        day_atr = float(atr.get(day, np.nan))
        for session in sessions:
            anchor = session_anchor(day, session)
            win = g[(g.index >= anchor) & (g.index < anchor + pd.Timedelta(minutes=M15))]
            if win.empty:
                continue                              # holiday / gap / no session
            or_hi = float(win["high"].max())
            or_lo = float(win["low"].min())
            range_w = or_hi - or_lo

            post = g[(g.index >= anchor + pd.Timedelta(minutes=M15)) &
                     (g.index < anchor + pd.Timedelta(hours=SESSION_HOURS))]
            if post.empty:
                continue

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

            # alignment vs the PRIOR-24H value reference (read at the breakout minute)
            vwap_at_break = float(vwap24h.get(btime, np.nan)) if btime is not None else np.nan
            if direction == "long":
                aligned = bool(entry > vwap_at_break)
            elif direction == "short":
                aligned = bool(entry < vwap_at_break)
            else:
                aligned = False

            # exit sim: stop (opposite edge, half-spread shift) vs session-close flat
            outcome, R = "none", np.nan
            if direction != "none":
                seg = g[(g.index >= btime) & (g.index < anchor + pd.Timedelta(hours=SESSION_HOURS))]
                if direction == "long":
                    stop_hit = seg.index[seg["low"] <= or_lo + half]
                else:
                    stop_hit = seg.index[seg["high"] >= or_hi - half]
                if len(stop_hit):
                    outcome, R = "stop", -1.0
                else:
                    last = seg["close"].iloc[-1]
                    exit_fill = last - half if direction == "long" else last + half
                    R = ((exit_fill - entry) if direction == "long"
                         else (entry - exit_fill)) / range_w
                    outcome = "sessionclose"

            rows.append({
                "date": day.date(), "session": session,
                "or_high": or_hi, "or_low": or_lo, "range_w": range_w,
                "direction": direction,
                "break_time": None if btime is None else btime.time(),
                "entry_px": entry, "outcome": outcome, "R": R,
                "vwap_at_break": vwap_at_break, "atr": day_atr,
                "range_w_over_atr": range_w / day_atr if day_atr and day_atr > 0 else np.nan,
                "vwap_aligned": aligned,
            })

    sig = pd.DataFrame(rows).set_index(["date", "session"])

    # self-normalising regime metric: range_w vs its trailing per-session median
    # (shifted -> only past ranges, no look-ahead). The Gate-3 gate is r_regime >= k.
    sig = sig.sort_index()
    med = (sig.groupby(level="session")["range_w"]
              .transform(lambda s: s.shift(1).rolling(regime_lookback, min_periods=5).median()))
    sig["range_w_regime"] = sig["range_w"] / med
    return sig
