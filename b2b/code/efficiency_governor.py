import pandas as pd
from typing import Tuple, Dict
from core.models.structures import B2BZoneInfo, SignalDirection

class EfficiencyGovernor:
    """
    Manages Tactical Tier Gating, Temporal Muting, and Structural Gaskets.
    """
    
    # Global registry for structural blocks: {(symbol, timeframe, direction): True}
    # [INTERNAL NOTE]: Part of Phase 12D Structural Memory. Remove if reverting to timer-based.
    _structural_blocks: Dict[Tuple[str, str, SignalDirection], bool] = {}

    @staticmethod
    def is_tier_allowed(tf: str, trigger_type: str) -> bool:
        """
        PILLAR 1: Tactical Tier Gating.
        Enforces depth-based entry based on timeframe importance.
        """
        # H4: High Conviction. All tiers (L1, 50%, L2) allowed.
        if tf == 'H4':
            return True
            
        # H1: Validation. Mute L1 (T1). Require Core (T2) or Depth (T3).
        if tf == 'H1':
            return trigger_type in ['T2', 'T3']
            
        # M30: Efficiency. Mute L1 (T1) and Core (T2). Require Deep Depth (T3/L2) ONLY.
        if tf == 'M30':
            return trigger_type == 'T3'
            
        # Default: Allow other TFs (HTF shouldn't be triggering anyway in V6.7)
        return True

    @staticmethod
    def is_temporally_clean(tf: str, symbol: str, direction: SignalDirection, current_time: pd.Timestamp) -> bool:
        """
        PILLAR 2: Structural Memory (Cooldown).
        Checks if the timeframe is currently restricted due to a previous failure.
        This block persists UNTIL a new structure is formed (reset_cooldown).
        """
        key = (symbol, tf, direction)
        return not EfficiencyGovernor._structural_blocks.get(key, False)

    @staticmethod
    def report_trade_failure(symbol: str, tf: str, direction: SignalDirection, current_time: pd.Timestamp):
        """
        Registers a trade failure and activates the Structural Block.
        [INTERNAL NOTE]: Phase 12D Structural Memory - Mutes until reset.
        """
        key = (symbol, tf, direction)
        EfficiencyGovernor._structural_blocks[key] = True

    @staticmethod
    def reset_cooldown(symbol: str, tf: str, direction: SignalDirection):
        """
        Clears the structural block for a specific TF/Dir.
        Called when a NEW structure forms (Safety Interrupt).
        """
        key = (symbol, tf, direction)
        if key in EfficiencyGovernor._structural_blocks:
            del EfficiencyGovernor._structural_blocks[key]

    @staticmethod
    def is_spatially_efficient(current_price: float, zone: B2BZoneInfo) -> Tuple[bool, str]:
        """
        PILLAR 3: Structural Gasket (Anti-Chase).
        Veto entry if the price has moved too far from the anchor (Elasticity).
        Target: Block entries > 3.0x the zone depth (L1-L2).
        """
        depth = abs(zone.L1_price - zone.L2_price)
        
        # Avoid division by zero for thin zones
        if depth <= 0:
            return True, ""
            
        dist = abs(current_price - zone.L1_price)
        
        if dist > (3.0 * depth):
            ratio = dist / depth
            return False, f"Structural Gasket: Elasticity Exhausted ({ratio:.1f}x Depth)"
            
        return True, ""
