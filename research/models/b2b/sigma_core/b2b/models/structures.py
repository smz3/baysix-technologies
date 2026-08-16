"""
SIGMA-Crypto-ASCEND Core Data Models
Port of V5.0 Structures.mqh → Python dataclasses.
Only essential fields for detection + backtesting + statistics.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, IntEnum
from typing import Dict, List, Optional
import hashlib
import pandas as pd


class SignalDirection(Enum):
    NONE = "NONE"
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"


class SwingType(Enum):
    NONE = "NONE"
    HIGH = "SWING_HIGH"
    LOW = "SWING_LOW"


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
class B2BZoneInfo:
    zone_id: str = ""
    timeframe: str = ""
    direction: SignalDirection = SignalDirection.NONE

    L1_price: float = 0.0
    L2_price: float = 0.0
    fifty_percent: float = 0.0

    first_barrier_price: float = 0.0
    first_barrier_time: datetime = None
    second_barrier_price: float = 0.0
    second_barrier_time: datetime = None
    swing_between_price: float = 0.0
    swing_between_time: datetime = None

    L1_touched: bool = False
    fifty_touched: bool = False
    L2_touched: bool = False
    L1_traded: bool = False
    fifty_traded: bool = False
    L2_traded: bool = False

    is_valid: bool = True
    is_invalidated: bool = False
    zone_created_time: datetime = None
    invalidation_time: datetime = None

    has_narrative_parent: bool = False
    has_control_parent: bool = False
    parent_zone_id: str = ""
    is_inside_parent: bool = False
    parent_tf: str = ""
    parent_count: int = 0
    tf_rank: int = -1

    first_barrier_bar_index: int = -1
    second_barrier_bar_index: int = -1
    created_bar_index: int = -1
    zone_age_bars: int = 0
    touch_count: int = 0
    L1_touch_time: datetime = None
    fifty_touch_time: datetime = None
    L2_touch_time: datetime = None

    atr_at_creation: float = 0.0
    session_created: str = ""

    was_traded: bool = False
    entry_level_used: str = ""
    entry_price: float = 0.0
    sl_price: float = 0.0
    tp_price: float = 0.0
    exit_price: float = 0.0
    exit_reason: str = ""
    trade_open_time: datetime = None
    trade_close_time: datetime = None
    pnl_points: float = 0.0
    pnl_money: float = 0.0
    rr_planned: float = 0.0
    rr_achieved: float = 0.0
    max_adverse_excursion: float = 0.0
    max_favorable_excursion: float = 0.0


def generate_zone_id(L1: float, L2: float, tf: str, direction: SignalDirection, time: datetime) -> str:
    raw = f"{L1:.8f}_{L2:.8f}_{tf}_{direction.value}_{time}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


@dataclass
class FlowState:
    """
    Snapshot of the Narrative Flow for a specific timeframe.
    Port of MQL5 FlowState struct.
    """
    origin_id: str = "" # zone_id is string (hex) in Python
    origin_dir: SignalDirection = SignalDirection.NONE
    origin_touch_time: pd.Timestamp = pd.Timestamp.min
    details_origin_price: float = 0.0
    details_origin_L2: float = 0.0
    
    magnet_id: str = ""
    magnet_dir: SignalDirection = SignalDirection.NONE
    details_magnet_price: float = 0.0
    details_magnet_L2: float = 0.0
    magnet_touch_time: pd.Timestamp = pd.Timestamp.min # V6.5 Freshness Baseline for Faders
    magnet_fifty_touched: bool = False
    magnet_L2_touched: bool = False
    is_magnet_extreme: bool = False # V5.8
    
    outpost_id: str = ""
    outpost_touch_time: pd.Timestamp = pd.Timestamp.min
    details_outpost_price: float = 0.0
    
    roadblock_id: str = ""
    anchor_is_traded: bool = False # V5.7: Safety Trigger
    is_siege_active: bool = False # V5.5
    is_valid: bool = False
    
    # V6.7: Inertial Flow (Structural Memory)
    latch_dir: SignalDirection = SignalDirection.NONE
    
    last_update_time: pd.Timestamp = pd.Timestamp.min

    def reset(self):
        """Resets the state to initial values (keeps the latch)."""
        self.origin_id = ""
        self.origin_dir = SignalDirection.NONE
        self.origin_touch_time = pd.Timestamp.min
        self.details_origin_price = 0.0
        self.details_origin_L2 = 0.0
        self.magnet_id = ""
        self.magnet_dir = SignalDirection.NONE
        self.details_magnet_price = 0.0
        self.details_magnet_L2 = 0.0
        self.magnet_fifty_touched = False
        self.magnet_L2_touched = False
        self.is_magnet_extreme = False
        self.outpost_id = ""
        self.outpost_touch_time = pd.Timestamp.min
        self.details_outpost_price = 0.0
        self.roadblock_id = ""
        self.anchor_is_traded = False
        self.is_siege_active = False
        self.is_valid = False
        # V6.7: Latch persists through resets to maintain the "Storyline"
        self.last_update_time = pd.Timestamp.min


@dataclass
class DetectionConfig:
    swing_window: int = 3
    swing_lookback: int = 20
    max_breakout_age: int = 0
    historical_bars: int = 5000
    min_age_bars: int = 8
    max_zone_age_bars: int = 5000


class DetectionContext:
    """
    Holds all accumulated state during left-to-right historical processing.
    Python equivalent of MT5's global arrays and CCircularBuffer.
    """
    def __init__(self, config: DetectionConfig = None):
        self.config = config or DetectionConfig()
        self.swings: Dict[str, List[SwingPointInfo]] = {}
        self.breakouts: Dict[str, List[RawBreakoutInfo]] = {}
        self.zones: Dict[str, List[B2BZoneInfo]] = {}
        self._next_display_number = 1

    def get_swings(self, tf: str) -> List[SwingPointInfo]:
        if tf not in self.swings:
            self.swings[tf] = []
        return self.swings[tf]

    def get_breakouts(self, tf: str) -> List[RawBreakoutInfo]:
        if tf not in self.breakouts:
            self.breakouts[tf] = []
        return self.breakouts[tf]

    def get_zones(self, tf: str) -> List[B2BZoneInfo]:
        if tf not in self.zones:
            self.zones[tf] = []
        return self.zones[tf]

    def get_all_zones(self) -> List[B2BZoneInfo]:
        result = []
        for tf in TF_HIERARCHY:
            if tf in self.zones:
                result.extend(self.zones[tf])
        return result

    def next_display_number(self) -> int:
        n = self._next_display_number
        self._next_display_number += 1
        return n
