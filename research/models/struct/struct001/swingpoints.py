"""
swingpoints.py — STRUCT-001 swing-structure module (entry point).

Swing DETECTION itself is the shared, parity-audited engine
b2b/sigma_core/b2b/detectors/swing_points.py (close-based pivot, honors
config.swing_window with the MQH odd/>=3 guard; live EA = InpSwingWindow=3).
This module is STRUCT-001's interface over it: load D1 bars + detect swings, and
the future home for market-structure labeling (HH/HL/LH/LL) built on the swings.

Render functions live in visual.py (universal struct visualizer), not here —
detection stays pure.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "b2b"))
sys.path.insert(0, str(REPO / "research" / "code"))

import pandas as pd                                                  # noqa: E402
import arctic_io as aio                                             # noqa: E402
from sigma_core.b2b.detectors.swing_points import detect_swings     # noqa: E402
from sigma_core.b2b.models.structures import (                      # noqa: E402
    DetectionConfig, SwingPointInfo,
)

__all__ = ["load_d1", "swings_d1", "detect_swings", "DetectionConfig"]


def load_d1() -> pd.DataFrame:
    """Canonical D1 OHLC frame from Arctic, columns time/open/high/low/close."""
    d = aio.daily_bars().reset_index()
    d.columns = [c.lower() for c in d.columns]
    return d.rename(columns={"date": "time"})[["time", "open", "high", "low", "close"]]


def swings_d1(swing_window: int = 3) -> tuple[pd.DataFrame, list[SwingPointInfo]]:
    """Load D1 + detect swings at `swing_window` (default 3 = live EA). Returns (df, swings)."""
    df = load_d1()
    swings = detect_swings(df, DetectionConfig(swing_window=swing_window))
    return df, swings
