from typing import List, Optional
from dataclasses import dataclass
import pandas as pd
from ..models.structures import B2BZoneInfo, SignalDirection
from .orchestrator import StrategyOrchestrator

@dataclass
class TradeSignal:
    zone_id: str
    tf: str
    symbol: str
    direction: SignalDirection
    entry_price: float
    structure_sl: float # RAW L2 (No Buffer)
    tp_price: float
    reason: str
    timestamp: pd.Timestamp
    origin_id: str = "" # V6.0 Redundancy Filter

class SignalScanner:
    """
    The EYES of the Strategy.
    Replaces TradeSignalGenerator.mqh
    
    Now PURE: Reports Structural Levels Only.
    """
    
    def __init__(self, orchestrator: StrategyOrchestrator):
        self.brain = orchestrator
        
    def scan(self, symbol: str, zones: List[B2BZoneInfo], bar_low: float, bar_high: float, current_close: float, current_time: pd.Timestamp, active_zone_ids: set) -> List[TradeSignal]:
        signals = []
        
        for z in zones:
            if not z.is_valid: continue
            
            # Intersection Filter: Is ANY part of the current bar (wick) inside or near the L1-L2 range?
            zone_max = max(z.L1_price, z.L2_price)
            zone_min = min(z.L1_price, z.L2_price)
            buffer = current_close * 0.002
            
            # Check if bar High hit zone Min, or bar Low hit zone Max
            bar_hit = (bar_high >= zone_min - buffer) and (bar_low <= zone_max + buffer)
            
            if not bar_hit:
                continue

            # === TIER 2 MULTI-LEVEL EXECUTION (H4, H1, M30) ===
            triggers = []
            
            # T1 Trigger: L1 Touched NOW and Not Traded
            if z.L1_touched and not z.L1_traded and z.L1_touch_time == current_time:
                triggers.append(('T1', z.L1_price))
            
            # T2 Trigger: 50% Touched NOW and Not Traded
            if z.fifty_touched and not z.fifty_traded and z.fifty_touch_time == current_time:
                triggers.append(('T2', z.fifty_percent))
                
            # T3 Trigger: L2 Touched NOW and Not Traded
            if z.L2_touched and not z.L2_traded and z.L2_touch_time == current_time:
                triggers.append(('T3', z.L2_price)) 
                
            for trigger_type, entry_p in triggers:
                # 2. Ask Brain
                # Wick-Aware: 
                # BULLISH zone (Demand): We check if bar LOW hit the core.
                # BEARISH zone (Supply): We check if bar HIGH hit the core.
                probe = bar_low if z.direction == SignalDirection.BULLISH else bar_high
                
                allowed, reason, target, origin_id = self.brain.is_trade_allowed(
                    z.timeframe, z.direction, z, current_close, current_time, probe_price=probe, trigger_type=trigger_type
                )
                
                if allowed:
                    # Update Specific Flag
                    if trigger_type == 'T1': z.L1_traded = True
                    if trigger_type == 'T2': z.fifty_traded = True
                    if trigger_type == 'T3': z.L2_traded = True
                    
                    z.was_traded = True # Mark generic flag too for safety/visuals
                    
                    sig = TradeSignal(
                        zone_id=z.zone_id,
                        tf=z.timeframe,
                        symbol=symbol,
                        direction=z.direction,
                        entry_price=entry_p,
                        structure_sl=z.L2_price, # Always Structure L2
                        tp_price=target,
                        reason=f"{reason} [{trigger_type}]",
                        timestamp=current_time,
                        origin_id=origin_id # V6.0 Redundancy
                    )
                    signals.append(sig)
                
        return signals
