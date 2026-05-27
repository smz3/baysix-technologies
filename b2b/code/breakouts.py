"""
SIGMA Raw Breakout Detector
Port of RawBreakoutDetector.mqh → Python.
Scans bars left-to-right, checks if each bar's close breaks any unbroken swing.
"""
import pandas as pd
from core.models.structures import (
    SwingPointInfo, RawBreakoutInfo, SwingType,
    SignalDirection, DetectionConfig,
)


def detect_breakouts(
    df: pd.DataFrame,
    swings: list[SwingPointInfo],
    config: DetectionConfig = None,
) -> list[RawBreakoutInfo]:
    """
    Detect breakouts by scanning bars left-to-right.
    
    For each bar, check if its close price breaks any unbroken swing:
    - Bullish breakout: close > swing_high.price
    - Bearish breakout: close < swing_low.price
    
    When broken:
    - Mark swing as has_been_broken = True
    - Calculate L2 (impulse swing): most recent opposite-type swing
      before the breakout bar that started the breaking move.
    
    Args:
        df: OHLCV DataFrame sorted oldest→newest.
        swings: List of SwingPointInfo from detect_swings().
        config: Detection parameters.
    
    Returns:
        List of RawBreakoutInfo, chronologically ordered.
    """
    if config is None:
        config = DetectionConfig()

    closes = df['close'].values
    times = df['time'].values
    n = len(closes)
    breakouts = []

    for bar_idx in range(n):
        bar_close = closes[bar_idx]
        bar_time = pd.Timestamp(times[bar_idx]).to_pydatetime()

        for swing in swings:
            if swing.has_been_broken:
                continue
            if swing.time is None or swing.time >= bar_time:
                continue

            if config.max_breakout_age > 0:
                age = bar_idx - swing.bar_index
                if age > config.max_breakout_age:
                    continue

            is_bullish_break = (swing.type == SwingType.HIGH and bar_close > swing.price)
            is_bearish_break = (swing.type == SwingType.LOW and bar_close < swing.price)

            if not (is_bullish_break or is_bearish_break):
                continue

            swing.has_been_broken = True
            direction = SignalDirection.BULLISH if is_bullish_break else SignalDirection.BEARISH

            breakouts.append(RawBreakoutInfo(
                breakout_bar_time=bar_time,
                breakout_bar_close_price=float(bar_close),
                direction=direction,
                broken_swing_price=swing.price,
                broken_swing_time=swing.time,
                broken_swing_close_price=swing.close_price,
                broken_swing_type=swing.type,
                breakout_bar_index=bar_idx,
                broken_swing_bar_index=swing.bar_index,
            ))

    return breakouts
