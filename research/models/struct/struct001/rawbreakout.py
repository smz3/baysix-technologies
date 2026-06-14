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

import pandas as pd

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


def detect_raw_breakouts(
    df: pd.DataFrame,
    swings: list[SwingPointInfo],
    config: DetectionConfig = None,
) -> list[RawBreakoutInfo]:
    """Faithful per-bar two-pass re-port of MQH Detect(). df oldest→newest."""
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


def raw_breakouts_d1(swing_window: int = 3):
    """Convenience: D1 bars + swings + breakouts. Returns (df, swings, breakouts)."""
    df, swings = sp.swings_d1(swing_window=swing_window)
    bk = detect_raw_breakouts(df, swings, DetectionConfig(swing_window=swing_window))
    return df, swings, bk


def _main(argv: list[str]) -> None:
    window = int(argv[argv.index("--window") + 1]) if "--window" in argv else 3
    df, swings, bk = raw_breakouts_d1(swing_window=window)
    bull = sum(1 for b in bk if b.direction == SignalDirection.BULLISH)
    bear = len(bk) - bull
    with_l2 = sum(1 for b in bk if b.impulse_start_price != 0.0)
    print(f"D1 bars={len(df)}  window={window}  swings={len(swings)}  breakouts={len(bk)} "
          f"(bull={bull} bear={bear})  with_L2={with_l2}")


if __name__ == "__main__":
    _main(sys.argv[1:])
