import pandas as pd
from typing import List, Dict
from ...models.structures import B2BZoneInfo, SignalDirection, FlowState
from .fracture_engine import FractureEngine

class StateManager:
    """
    Manages the persistent states and latches for each timeframe.
    """
    
    def __init__(self, engines: Dict):
        self.fracture = engines.get('fracture', FractureEngine())

    def update_timeframe_flow(self, tf: str, state: FlowState, zones: List[B2BZoneInfo], current_price: float):
        """
        Primary logic for advancing the HTF narrative.
        Ported from StrategyOrchestrator._update_flow.
        """
        # 1. Sticky Validation: Keep current origin if valid and not broken
        if state.is_valid and state.origin_id != "":
            curr = self.fracture.get_zone_by_id(state.origin_id, zones)
            if curr and curr.is_valid:
                is_broken = (curr.direction == SignalDirection.BULLISH and current_price < curr.L2_price) or \
                             (curr.direction == SignalDirection.BEARISH and current_price > curr.L2_price)
                if not is_broken:
                    # Update Anchor Status
                    outpost_id = self.fracture.get_latest_outpost(tf, state.origin_dir, current_price, curr.zone_created_time, zones)
                    state.outpost_id = outpost_id or ""
                    anchor = self.fracture.get_zone_by_id(outpost_id, zones) if outpost_id else curr
                    
                    if outpost_id:
                        state.outpost_touch_time = anchor.L1_touch_time or pd.Timestamp.min
                    
                    state.anchor_is_traded = anchor.L1_touched
                    self.fracture.update_magnet_info(tf, state, current_price, zones)
                    
                    # Siege Logic
                    self._process_siege_state(state, zones)

                    # Successor Promotion
                    if state.magnet_L2_touched:
                        if self._promote_successor(tf, state, curr, zones, current_price):
                            return # Narrative Shifted
                    
                    return

        # 2. Origin Search (When old origin is dead or none exists)
        self._find_new_origin(tf, state, zones, current_price)

    def _process_siege_state(self, state: FlowState, zones: List[B2BZoneInfo]):
        """Handles the Siege Mode activation."""
        if state.magnet_id != "":
            magnet_zone = self.fracture.get_zone_by_id(state.magnet_id, zones)
            if magnet_zone and magnet_zone.L1_touched:
                op_time = state.outpost_touch_time if state.outpost_touch_time is not None else pd.Timestamp.min
                mg_time = magnet_zone.L1_touch_time if magnet_zone.L1_touch_time is not None else pd.Timestamp.min
                
                if op_time > mg_time:
                    state.is_siege_active = True
                else:
                    state.is_siege_active = False
        else:
            state.is_siege_active = False

    def _promote_successor(self, tf: str, state: FlowState, curr: B2BZoneInfo, zones: List[B2BZoneInfo], current_price: float) -> bool:
        """Promotes a successor zone if the magnet has been defeated."""
        successor_id = self.fracture.get_latest_outpost(tf, state.origin_dir, current_price, curr.zone_created_time, zones)
        if successor_id:
            state.origin_id = successor_id
            state.magnet_id = ""
            state.is_siege_active = False
            succ = self.fracture.get_zone_by_id(successor_id, zones)
            state.anchor_is_traded = succ.L1_touched if succ else False
            return True
        else:
            # V5.8 fallback: reset if no successors after magnet touch
            state.is_valid = False
            state.reset()
            return True
        return False

    def _find_new_origin(self, tf: str, state: FlowState, zones: List[B2BZoneInfo], current_price: float):
        """Standard search for the most recent valid origin."""
        best_origin = None
        for z in zones:
            if z.timeframe != tf or not z.is_valid: continue
            
            is_broken = (z.direction == SignalDirection.BULLISH and current_price < z.L2_price) or \
                         (z.direction == SignalDirection.BEARISH and current_price > z.L2_price)
            if is_broken: continue
            
            # In Media Res check
            is_ahead = (z.direction == SignalDirection.BULLISH and current_price > z.L1_price) or \
                        (z.direction == SignalDirection.BEARISH and current_price < z.L1_price)
            
            if not z.L1_touched and not is_ahead: continue
            
            if not best_origin or z.zone_created_time > best_origin.zone_created_time:
                best_origin = z
        
        if not best_origin:
            state.is_valid = False
            return

        state.origin_id = best_origin.zone_id
        state.origin_dir = best_origin.direction
        state.details_origin_price = best_origin.L1_price
        state.details_origin_L2 = best_origin.L2_price
        state.origin_touch_time = best_origin.L1_touch_time or best_origin.zone_created_time
        state.is_valid = True
        
        # V6.7 Storyline Latch: Lock the memory
        state.latch_dir = best_origin.direction
        
        # Initial Anchor Status
        outpost_id = self.fracture.get_latest_outpost(tf, state.origin_dir, current_price, best_origin.zone_created_time, zones)
        state.outpost_id = outpost_id or ""
        anchor = self.fracture.get_zone_by_id(outpost_id, zones) if outpost_id else best_origin
        if outpost_id: 
            state.outpost_touch_time = anchor.L1_touch_time or pd.Timestamp.min

        state.anchor_is_traded = anchor.L1_touched
        state.is_siege_active = False
        self.fracture.update_magnet_info(tf, state, current_price, zones)
