import pandas as pd
from typing import List, Optional, Dict
from ...models.structures import B2BZoneInfo, SignalDirection, FlowState

class FractureEngine:
    """
    Handles the identification and validation of structural fractures (Origins, Outposts, Magnets).
    """
    
    @staticmethod
    def get_zone_by_id(zone_id: str, zones: List[B2BZoneInfo]) -> Optional[B2BZoneInfo]:
        for z in zones:
            if z.zone_id == zone_id:
                return z
        return None

    @staticmethod
    def get_latest_outpost(tf: str, direction: SignalDirection, current_price: float, after_time: pd.Timestamp, zones: List[B2BZoneInfo]) -> Optional[str]:
        best_zone = None
        best_time = after_time
        for z in zones:
            if z.timeframe != tf or z.direction != direction or not z.is_valid:
                continue
            if z.zone_created_time > best_time:
                best_time = z.zone_created_time
                best_zone = z
        if best_zone:
            is_broken = (direction == SignalDirection.BULLISH and current_price < best_zone.L2_price) or \
                        (direction == SignalDirection.BEARISH and current_price > best_zone.L2_price)
            if is_broken: return None
            return best_zone.zone_id
        return None

    @staticmethod
    def is_inside_opposing_zone(tf: str, direction: SignalDirection, price: float, zones: List[B2BZoneInfo], siege_magnet_id: str = "") -> str:
        opp_dir = SignalDirection.BEARISH if direction == SignalDirection.BULLISH else SignalDirection.BULLISH
        
        # MN1 Trade: Ignores everything
        if tf == 'MN1': return ""
        
        check_mn1 = True
        check_w1 = (tf == 'D1') # Standard Hierarchy
        # If lower TF, check all superiors
        if tf in ['H4', 'H1', 'M30']:
            check_w1 = True

        for z in zones:
            if not z.is_valid or z.direction != opp_dir: 
                continue

            tf_match = False
            if check_mn1 and z.timeframe == 'MN1': tf_match = True
            if check_w1 and z.timeframe == 'W1': tf_match = True
            
            if not tf_match: continue
                
            if z.L2_touched: continue # Zone is pierced

            high = max(z.L1_price, z.L2_price)
            low = min(z.L1_price, z.L2_price)
            
            if low <= price <= high:
                if siege_magnet_id != "" and z.zone_id == siege_magnet_id:
                    continue
                return z.zone_id
                
        return ""

    @staticmethod
    def update_magnet_info(tf: str, state: FlowState, current_price: float, zones: List[B2BZoneInfo]):
        """Finds the nearest opposing zone for the current flow."""
        best_magnet = None
        min_dist = float('inf')
        target_dir = SignalDirection.BEARISH if state.origin_dir == SignalDirection.BULLISH else SignalDirection.BULLISH
        
        for z in zones:
            if z.timeframe != tf or not z.is_valid or z.direction != target_dir: 
                continue
            
            dist = float('inf')
            if state.origin_dir == SignalDirection.BULLISH:
                if z.L1_price > current_price: dist = z.L1_price - current_price
            else:
                if z.L1_price < current_price: dist = current_price - z.L1_price
            
            if dist < min_dist:
                min_dist = dist
                best_magnet = z
        
        if best_magnet:
            state.magnet_id = best_magnet.zone_id
            state.magnet_dir = best_magnet.direction 
            state.details_magnet_price = best_magnet.L1_price
            state.details_magnet_L2 = best_magnet.L2_price
            state.magnet_touch_time = best_magnet.L1_touch_time or pd.Timestamp.min
            state.magnet_fifty_touched = best_magnet.fifty_touched
            state.magnet_L2_touched = best_magnet.L2_touched
            
            # Check Structural Supremacy
            state.is_magnet_extreme = True
            for z in zones:
                if z.timeframe == tf and z.direction == state.magnet_dir and z.is_valid:
                    if state.magnet_dir == SignalDirection.BEARISH:
                        if z.L1_price > state.details_magnet_price:
                             state.is_magnet_extreme = False
                             break
                    else:
                        if z.L1_price < state.details_magnet_price:
                             state.is_magnet_extreme = False
                             break
        else:
            state.magnet_id = ""
            state.details_magnet_L2 = 0.0
            state.magnet_fifty_touched = False
            state.magnet_L2_touched = False
            state.is_magnet_extreme = False
