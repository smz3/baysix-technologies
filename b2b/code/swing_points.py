"""
SIGMA Swing Point Detector
Port of SwingPointDetector.mqh → Vectorized Python.
Uses CLOSE prices (not high/low) — this is the SIGMA doctrinal rule.
"""
import pandas as pd
from core.models.structures import SwingPointInfo, SwingType, DetectionConfig


def detect_swings(df: pd.DataFrame, config: DetectionConfig = None) -> list[SwingPointInfo]:
    """
    Detect swing highs and lows using close prices.
    Uses a 3-bar local extrema check for highest sensitivity (The DNA).
    """
    if config is None:
        config = DetectionConfig()

    closes = df['close'].values
    times = df['time'].values
    n = len(closes)
    swings = []

    # Bar-by-bar scan for local turns (Pivot logic)
    for i in range(1, n - 1):
        prev = closes[i - 1]
        curr = closes[i]
        nxt = closes[i + 1]

        # Local Peak
        if curr > prev and curr > nxt:
            swings.append(SwingPointInfo(
                price=float(curr),
                time=pd.Timestamp(times[i]).to_pydatetime(),
                close_price=float(curr),
                type=SwingType.HIGH,
                bar_index=i,
            ))
        # Local Valley
        elif curr < prev and curr < nxt:
            swings.append(SwingPointInfo(
                price=float(curr),
                time=pd.Timestamp(times[i]).to_pydatetime(),
                close_price=float(curr),
                type=SwingType.LOW,
                bar_index=i,
            ))

    return swings
