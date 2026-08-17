"""
structures.py — STRUCT-001 self-owned structural data models.

Decoupled copy of the swing/breakout types from
b2b/sigma_core/b2b/models/structures.py. STRUCT-001 owns its own primitive
vocabulary so the struct filing system stands alone — it no longer reaches into
the b2b package (no sys.path → b2b hack). Only the types the structure layer
needs live here; the B2B zone/flow types deliberately do NOT.

Parity is a SNAPSHOT property: these dataclasses are field-identical to the b2b
ones at decouple time. A drift guard (research/tests/test_struct_parity.py)
asserts struct's swing detector still matches the audited b2b engine — so this
fork cannot silently diverge.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class SignalDirection(Enum):
    NONE = "NONE"
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"


class SwingType(Enum):
    NONE = "NONE"
    HIGH = "SWING_HIGH"
    LOW = "SWING_LOW"


# Canonical TF order (coarse → fine), mirrors b2b TF_HIERARCHY.
TF_HIERARCHY = ["MN1", "W1", "D1", "H4", "H1", "M30", "M15", "M5", "M1"]
TF_RANK = {tf: i for i, tf in enumerate(TF_HIERARCHY)}


@dataclass
class SwingPointInfo:
    price: float = 0.0
    time: datetime = None
    close_price: float = 0.0
    type: SwingType = SwingType.NONE
    has_been_broken: bool = False
    original_tf: str = ""
    bar_index: int = -1

    def is_valid(self) -> bool:
        return self.time is not None and self.type != SwingType.NONE


@dataclass
class RawBreakoutInfo:
    breakout_bar_time: datetime = None
    breakout_bar_close_price: float = 0.0
    direction: SignalDirection = SignalDirection.NONE
    timeframe: str = ""
    broken_swing_price: float = 0.0
    broken_swing_time: datetime = None
    broken_swing_close_price: float = 0.0
    broken_swing_type: SwingType = SwingType.NONE
    impulse_start_price: float = 0.0
    breakout_bar_index: int = -1
    broken_swing_bar_index: int = -1

    def is_valid(self) -> bool:
        return self.direction != SignalDirection.NONE and self.broken_swing_time is not None


@dataclass
class DetectionConfig:
    swing_window: int = 3
    swing_lookback: int = 20
    max_breakout_age: int = 0
    historical_bars: int = 5000
    min_age_bars: int = 8
    max_zone_age_bars: int = 5000
