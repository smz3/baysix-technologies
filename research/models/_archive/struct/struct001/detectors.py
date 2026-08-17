"""
detectors.py — STRUCT-001 self-owned swing-point detector.

Faithful, decoupled re-port of b2b/sigma_core/b2b/detectors/swing_points.py
(itself a port of SwingPointDetector.mqh). CLOSE-based pivot — the SIGMA
doctrinal rule. STRUCT-001 owns this so it no longer imports the detector from
the b2b package; a parity test guards against drift from the audited b2b engine.

Breakout detection is NOT here — it lives in rawbreakout.py (the faithful L2
two-pass re-port), which STRUCT-001 has always owned.
"""
from __future__ import annotations

import pandas as pd

from structures import SwingPointInfo, SwingType, DetectionConfig


def detect_swings(df: pd.DataFrame, config: DetectionConfig = None) -> list[SwingPointInfo]:
    """Detect swing highs/lows on CLOSE prices.

    Mirrors MQL5 CSwingPointDetector::IsSwingHigh/IsSwingLow: a pivot's close must
    be STRICTLY greater (high) / lower (low) than EVERY other close in a window of
    `config.swing_window` bars centred on it (radius = swing_window // 2).

    Parity contract w/ the live EA: swing_window must be ODD and >= 3, exactly the
    MQH guard `if(swing_window < 3 || swing_window % 2 == 0) return ...`. Live EA
    runs InpSwingWindow=3 (radius 1 = classic 3-bar pivot).

    NOTE (2026-06-14 profiling): the per-bar `break` early-exit makes this ~O(n) in
    practice — 0.69s on 236k M15 bars. NOT the intraday bottleneck. The cost is
    detect_raw_breakouts (1.9s at D1 alone, scales as bars x active swings). A
    vectorize attempt here was reverted (~0x gain). See backlog task for the real
    target.
    """
    if config is None:
        config = DetectionConfig()

    window = config.swing_window
    if window < 3 or window % 2 == 0:
        raise ValueError(
            f"swing_window must be odd and >= 3 (got {window}) — matches MQH guard"
        )
    radius = window // 2

    closes = df["close"].values
    times = df["time"].values
    n = len(closes)
    swings = []

    # Bar-by-bar scan for local turns (pivot must beat ALL neighbours in the window)
    for i in range(radius, n - radius):
        curr = closes[i]
        is_high = True
        is_low = True
        for j in range(i - radius, i + radius + 1):
            if j == i:
                continue
            if curr <= closes[j]:
                is_high = False
            if curr >= closes[j]:
                is_low = False
            if not is_high and not is_low:
                break

        if is_high:
            swing_type = SwingType.HIGH
        elif is_low:
            swing_type = SwingType.LOW
        else:
            continue

        swings.append(SwingPointInfo(
            price=float(curr),
            time=pd.Timestamp(times[i]).to_pydatetime(),
            close_price=float(curr),
            type=swing_type,
            bar_index=i,
        ))

    return swings
