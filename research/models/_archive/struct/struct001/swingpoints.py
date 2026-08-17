"""
swingpoints.py — STRUCT-001 swing-structure module (entry point).

Swing DETECTION is STRUCT-001's own close-based pivot engine (detectors.py) — a
faithful, decoupled port of the parity-audited b2b detector; honors
config.swing_window with the MQH odd/>=3 guard (live EA = InpSwingWindow=3).
STRUCT-001 no longer reaches into the b2b package; a parity test guards drift.
This module is the interface over it: load D1 bars + detect swings, and the
future home for market-structure labeling (HH/HL/LH/LL) built on the swings.

Render functions live in visual.py (universal struct visualizer), not here —
detection stays pure.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "research" / "code" / "io"))

import pandas as pd                                                  # noqa: E402
import arctic_io as aio                                             # noqa: E402
from detectors import detect_swings                                 # noqa: E402
from structures import DetectionConfig, SwingPointInfo              # noqa: E402

__all__ = ["load", "load_d1", "swings", "swings_d1", "detect_swings", "DetectionConfig"]


def load(tf: str = "D1", venue: str = "JM_EET") -> pd.DataFrame:
    """OHLC frame for any TF, broker-clock bucketed (task 76 derive layer).
    Columns time/open/high/low/close. Default D1 on JustMarkets (EET) — the
    MT5-aligned source that replaces the old UTC-bucketed XAUUSD_DAILY."""
    d = aio.bars(tf, venue).reset_index()
    d.columns = [c.lower() for c in d.columns]
    return d[["time", "open", "high", "low", "close"]]


def load_d1() -> pd.DataFrame:
    """Back-compat alias → broker-aligned D1 (was UTC-bucketed XAUUSD_DAILY)."""
    return load("D1", "JM_EET")


def swings(tf: str = "D1", swing_window: int = 3, venue: str = "JM_EET"
           ) -> tuple[pd.DataFrame, list[SwingPointInfo]]:
    """Load `tf` bars + detect swings at `swing_window` (default 3 = live EA).
    Returns (df, swings). Any TF in arctic_io.TF_RULE."""
    df = load(tf, venue)
    swings_ = detect_swings(df, DetectionConfig(swing_window=swing_window))
    return df, swings_


def swings_d1(swing_window: int = 3) -> tuple[pd.DataFrame, list[SwingPointInfo]]:
    """Back-compat alias → swings('D1')."""
    return swings("D1", swing_window=swing_window)
