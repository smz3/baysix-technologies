"""
rawbreakout.py — STRUCT-001 self-contained faithful re-port of
mt5/.../Detection/RawBreakoutDetector.mqh (V5.0.5).

Deliberately NOT a wrapper over b2b/sigma_core/.../breakouts.py — that shared
port omits L2. This module reproduces the MQH Detect() in full so STRUCT-001 owns
a parity-faithful breakout primitive independent of the B2B engine.

Faithful to MQH:
  • per-bar TWO-PASS scan with SHARED L2 (V5.0.5): when one bar breaks several
    swings in the same direction, L2 is computed ONCE from the EARLIEST broken
    swing and shared to all of them.
  • FindImpulseSwingPrice (L2): most-recent OPPOSITE-type swing strictly between
    the broken swing's time and the breakout bar (bull→latest LOW, bear→latest HIGH).
  • bullish = close > swing HIGH price; bearish = close < swing LOW price.
  • max_breakout_age_bars age filter; stateful has_been_broken (a swing breaks once).

Hardened beyond the MQH (research correctness, only bites at window>3):
  • CONFIRMATION GATE — a breakout may not fire until the broken swing is confirmed
    (bar_idx >= swing.bar_index + radius, radius = swing_window//2). The live EA's
    swing array only ever holds confirmed swings, so this just makes that explicit
    and kills look-ahead at wide windows. At window=3 (radius 1) it is a no-op.

Intentional deviation:
  • breakout_bar_time = the bar's own timestamp (Arctic D1 = bar date). MQH stamps
    GetBarCloseTime (open+period); we carry breakout_bar_index for exact alignment.

Input swings are NOT mutated (each is shallow-copied; has_been_broken is tracked
on the copies during the scan).

Usage:
  python research/models/struct/struct001/rawbreakout.py            # D1, window 3
  python research/models/struct/struct001/rawbreakout.py --window 5
"""
from __future__ import annotations

import copy
import sys

import numpy as np
import pandas as pd
from numba import njit

import swingpoints as sp
from structures import (
    SwingPointInfo, RawBreakoutInfo, SwingType, SignalDirection, DetectionConfig,
)


def _find_impulse_swing_price(
    broken: SwingPointInfo,
    swings: list[SwingPointInfo],
    target_type: SwingType,
    breakout_bar_time,
) -> float:
    """L2: most-recent `target_type` swing strictly after `broken` and before the
    breakout bar. Mirrors CRawBreakoutDetector::FindImpulseSwingPrice. 0.0 if none."""
    latest_time = None
    found_price = 0.0
    for s in swings:
        if s.type != target_type:
            continue
        if s.time <= broken.time:
            continue
        if s.time >= breakout_bar_time:
            continue
        if latest_time is None or s.time > latest_time:
            latest_time = s.time
            found_price = s.price
    return found_price


def _detect_raw_breakouts_py(
    df: pd.DataFrame,
    swings: list[SwingPointInfo],
    config: DetectionConfig = None,
) -> list[RawBreakoutInfo]:
    """FROZEN PARITY ORACLE — faithful per-bar two-pass re-port of MQH Detect().
    df oldest→newest. Kept verbatim as the byte-identical reference the vectorized
    `detect_raw_breakouts` is parity-tested against (task 77). Do not optimize."""
    if config is None:
        config = DetectionConfig()
    radius = config.swing_window // 2
    max_age = config.max_breakout_age

    swings = [copy.copy(s) for s in swings]   # don't pollute caller's swings
    closes = df["close"].values
    times = df["time"].values
    n = len(closes)
    breakouts: list[RawBreakoutInfo] = []

    for bar_idx in range(n):
        bar_close = float(closes[bar_idx])
        bar_time = pd.Timestamp(times[bar_idx]).to_pydatetime()

        def _eligible(s: SwingPointInfo) -> bool:
            if s.has_been_broken or s.time is None or s.time >= bar_time:
                return False
            if bar_idx < s.bar_index + radius:          # confirmation gate
                return False
            if max_age > 0 and (bar_idx - s.bar_index) > max_age:
                return False
            return True

        # PASS 1 — earliest broken swing per direction → shared L2
        shared_l2_bull = 0.0
        shared_l2_bear = 0.0
        earliest_bull = None
        earliest_bear = None
        for s in swings:
            if not _eligible(s):
                continue
            if s.type == SwingType.HIGH and bar_close > s.price:
                if earliest_bull is None or s.time < earliest_bull:
                    earliest_bull = s.time
                    shared_l2_bull = _find_impulse_swing_price(s, swings, SwingType.LOW, bar_time)
            elif s.type == SwingType.LOW and bar_close < s.price:
                if earliest_bear is None or s.time < earliest_bear:
                    earliest_bear = s.time
                    shared_l2_bear = _find_impulse_swing_price(s, swings, SwingType.HIGH, bar_time)

        # PASS 2 — create breakouts with the shared L2, mark swings broken
        for s in swings:
            if not _eligible(s):
                continue
            is_bull = s.type == SwingType.HIGH and bar_close > s.price
            is_bear = s.type == SwingType.LOW and bar_close < s.price
            if not (is_bull or is_bear):
                continue

            s.has_been_broken = True
            breakouts.append(RawBreakoutInfo(
                breakout_bar_time=bar_time,
                breakout_bar_close_price=bar_close,
                direction=SignalDirection.BULLISH if is_bull else SignalDirection.BEARISH,
                timeframe=s.original_tf,
                broken_swing_price=s.price,
                broken_swing_time=s.time,
                broken_swing_close_price=s.close_price,
                broken_swing_type=s.type,
                impulse_start_price=shared_l2_bull if is_bull else shared_l2_bear,
                breakout_bar_index=bar_idx,
                broken_swing_bar_index=s.bar_index,
            ))

    return breakouts


# ── Vectorized path (task 77) ─────────────────────────────────────────────────
# Numba nopython kernel = the EXACT two-pass logic of _detect_raw_breakouts_py,
# operating on numpy arrays (int64-ns times, float prices, int8 swing types) so
# the per-bar × per-swing scan runs at native speed. Swing type: 1=HIGH, 2=LOW.
# Each swing breaks at most once → total breakouts ≤ len(swings), so outputs are
# preallocated to m and sliced to the count. Byte-identical to the oracle, proven
# by parity_rawbreakout.py across windows 3/5/7 on D1/H1/M15.

_INT64_MAX = np.int64(9223372036854775807)
_INT64_MIN = np.int64(-9223372036854775808)


@njit(cache=True)
def _rb_kernel(closes, bar_times, s_time, s_price, s_type, s_bar_index,
               radius, max_age):
    n = closes.shape[0]
    m = s_time.shape[0]
    broken = np.zeros(m, dtype=np.bool_)
    out_bar = np.empty(m, dtype=np.int64)
    out_sidx = np.empty(m, dtype=np.int64)
    out_dir = np.empty(m, dtype=np.int8)
    out_l2 = np.empty(m, dtype=np.float64)
    cnt = 0

    for bar_idx in range(n):
        bc = closes[bar_idx]
        bt = bar_times[bar_idx]

        # PASS 1 — earliest unbroken swing broken per direction → shared L2
        eb_time = _INT64_MAX
        eb_sidx = -1
        ebr_time = _INT64_MAX
        ebr_sidx = -1
        for j in range(m):
            if broken[j]:
                continue
            if s_time[j] >= bt:
                continue
            if bar_idx < s_bar_index[j] + radius:          # confirmation gate
                continue
            if max_age > 0 and (bar_idx - s_bar_index[j]) > max_age:
                continue
            if s_type[j] == 1 and bc > s_price[j]:
                if s_time[j] < eb_time:
                    eb_time = s_time[j]
                    eb_sidx = j
            elif s_type[j] == 2 and bc < s_price[j]:
                if s_time[j] < ebr_time:
                    ebr_time = s_time[j]
                    ebr_sidx = j

        # shared L2 = most-recent OPPOSITE swing strictly between earliest-broken
        # swing's time and this bar (bull→latest LOW, bear→latest HIGH).
        l2_bull = 0.0
        if eb_sidx >= 0:
            bst = s_time[eb_sidx]
            latest = _INT64_MIN
            for k in range(m):
                if s_type[k] != 2:
                    continue
                if s_time[k] <= bst or s_time[k] >= bt:
                    continue
                if s_time[k] > latest:
                    latest = s_time[k]
                    l2_bull = s_price[k]
        l2_bear = 0.0
        if ebr_sidx >= 0:
            bst = s_time[ebr_sidx]
            latest = _INT64_MIN
            for k in range(m):
                if s_type[k] != 1:
                    continue
                if s_time[k] <= bst or s_time[k] >= bt:
                    continue
                if s_time[k] > latest:
                    latest = s_time[k]
                    l2_bear = s_price[k]

        # PASS 2 — emit breakouts in swing-list order, mark broken
        for j in range(m):
            if broken[j]:
                continue
            if s_time[j] >= bt:
                continue
            if bar_idx < s_bar_index[j] + radius:
                continue
            if max_age > 0 and (bar_idx - s_bar_index[j]) > max_age:
                continue
            is_bull = s_type[j] == 1 and bc > s_price[j]
            is_bear = s_type[j] == 2 and bc < s_price[j]
            if not (is_bull or is_bear):
                continue
            broken[j] = True
            out_bar[cnt] = bar_idx
            out_sidx[cnt] = j
            out_dir[cnt] = 1 if is_bull else 2
            out_l2[cnt] = l2_bull if is_bull else l2_bear
            cnt += 1

    return out_bar[:cnt], out_sidx[:cnt], out_dir[:cnt], out_l2[:cnt]


def detect_raw_breakouts(
    df: pd.DataFrame,
    swings: list[SwingPointInfo],
    config: DetectionConfig = None,
) -> list[RawBreakoutInfo]:
    """Vectorized (numba) port of _detect_raw_breakouts_py — same output, native
    speed. df oldest→newest. Falls through to an empty list on empty input."""
    if config is None:
        config = DetectionConfig()
    radius = config.swing_window // 2
    max_age = config.max_breakout_age
    n = len(df)
    m = len(swings)
    if n == 0 or m == 0:
        return []

    closes = np.ascontiguousarray(df["close"].values, dtype=np.float64)
    bar_times = pd.DatetimeIndex(pd.to_datetime(df["time"].values)).asi8.astype(np.int64)
    times = df["time"].values

    s_time = pd.DatetimeIndex(pd.to_datetime([s.time for s in swings])).asi8.astype(np.int64)
    s_price = np.array([s.price for s in swings], dtype=np.float64)
    s_type = np.array(
        [1 if s.type == SwingType.HIGH else (2 if s.type == SwingType.LOW else 0)
         for s in swings], dtype=np.int8)
    s_bar_index = np.array([s.bar_index for s in swings], dtype=np.int64)

    out_bar, out_sidx, out_dir, out_l2 = _rb_kernel(
        closes, bar_times, s_time, s_price, s_type, s_bar_index,
        int(radius), int(max_age))

    breakouts: list[RawBreakoutInfo] = []
    for i in range(out_bar.shape[0]):
        bidx = int(out_bar[i])
        s = swings[int(out_sidx[i])]
        is_bull = out_dir[i] == 1
        breakouts.append(RawBreakoutInfo(
            breakout_bar_time=pd.Timestamp(times[bidx]).to_pydatetime(),
            breakout_bar_close_price=float(closes[bidx]),
            direction=SignalDirection.BULLISH if is_bull else SignalDirection.BEARISH,
            timeframe=s.original_tf,
            broken_swing_price=s.price,
            broken_swing_time=s.time,
            broken_swing_close_price=s.close_price,
            broken_swing_type=s.type,
            impulse_start_price=float(out_l2[i]),
            breakout_bar_index=bidx,
            broken_swing_bar_index=s.bar_index,
        ))
    return breakouts


def raw_breakouts(tf: str = "D1", swing_window: int = 3, venue: str = "JM_EET"):
    """Convenience: `tf` bars + swings + breakouts, broker-clock bucketed.
    Returns (df, swings, breakouts). Any TF in arctic_io.TF_RULE."""
    df, swings = sp.swings(tf, swing_window=swing_window, venue=venue)
    bk = detect_raw_breakouts(df, swings, DetectionConfig(swing_window=swing_window))
    return df, swings, bk


def raw_breakouts_d1(swing_window: int = 3):
    """Back-compat alias → raw_breakouts('D1')."""
    return raw_breakouts("D1", swing_window=swing_window)


def _main(argv: list[str]) -> None:
    window = int(argv[argv.index("--window") + 1]) if "--window" in argv else 3
    tf = argv[argv.index("--tf") + 1].upper() if "--tf" in argv else "D1"
    df, swings, bk = raw_breakouts(tf, swing_window=window)
    bull = sum(1 for b in bk if b.direction == SignalDirection.BULLISH)
    bear = len(bk) - bull
    with_l2 = sum(1 for b in bk if b.impulse_start_price != 0.0)
    print(f"{tf} bars={len(df)}  window={window}  swings={len(swings)}  breakouts={len(bk)} "
          f"(bull={bull} bear={bear})  with_L2={with_l2}")


if __name__ == "__main__":
    _main(sys.argv[1:])
