"""
SIGMA 5-Pointer B2B Engine
Port of B2BDetector.mqh → Python.
Implements the 3-pass candidate selection with strict structural constraints.
"""
import numpy as np
import pandas as pd
import hashlib
from datetime import datetime
from core.models.structures import (
    SwingPointInfo, RawBreakoutInfo, B2BZoneInfo,
    SwingType, SignalDirection, DetectionConfig, generate_zone_id
)

def detect_b2b_zones(
    df: pd.DataFrame,
    swings: list[SwingPointInfo],
    tf: str = "D1",
    config: DetectionConfig = None
) -> list[B2BZoneInfo]:
    """
    Core B2B Detection Pipeline.
    1. Scan for all potential 5-pointer patterns.
    2. Filter out patterns that were interrupted by new swings.
    3. Filter out patterns where L2 was broken before confirmation (Early Fade).
    4. Select winners (Freshest pattern per P5 anchor).
    """
    if config is None:
        config = DetectionConfig()

    closes = df['close'].values
    times = df['time'].values
    n = len(closes)
    
    # Pre-render timestamps for performance
    py_times = [pd.Timestamp(t).to_pydatetime() for t in times]
    
    candidates = []

    # =========================================================================
    # PASS 1: SCAN FOR CANDIDATES (SELL & BUY)
    # =========================================================================
    
    # 1A. SELL CANDIDATES
    for i in range(len(swings) - 2):
        p1 = swings[i]
        if p1.type != SwingType.HIGH: continue
        
        # Find P2 (Low after P1)
        p2 = None
        p2_idx = -1
        for j in range(i + 1, len(swings)):
            if swings[j].time > p1.time and swings[j].type == SwingType.LOW:
                p2 = swings[j]
                p2_idx = j
                break
        if not p2: continue

        # Find P3 (High after P2)
        p3 = None
        p3_idx = -1
        for j in range(p2_idx + 1, len(swings)):
            if swings[j].time > p2.time and swings[j].type == SwingType.HIGH:
                p3 = swings[j]
                p3_idx = j
                break
        if not p3: continue

        # Find P5 (Older Low before P1 with price < P2)
        p5 = None
        for j in range(i - 1, -1, -1):
            if swings[j].time < p1.time and swings[j].type == SwingType.LOW and swings[j].price < p2.price:
                p5 = swings[j]
                break
        if not p5: continue

        # Find P4 (Confirmation Bar: Close < P5 PRICE after P3 TIME)
        p4_time = None
        p4_bar_idx = -1
        
        c_p4_search = closes[p3.bar_index + 1:]
        p4_hits = np.where(c_p4_search < p5.price)[0]
            
        if len(p4_hits) > 0:
            p4_bar_idx = p3.bar_index + 1 + p4_hits[0]
            p4_time = py_times[p4_bar_idx]
        
        if not p4_time: continue

        # V5.1.2: No Interruption Check (No new swings between P3 and P4)
        # Optimized: Only check swings whose index is between p3 and p4
        interrupted = False
        # We can use the index in the swings list to quickly check
        # But for robustness, we use the timestamp logic with NumPy if swings were converted
        # For now, let's keep it simple but faster
        for s in swings[i+1:]: # Only check swings AFTER P1
            if s.time > p3.time and s.time < p4_time:
                interrupted = True
                break
        if interrupted: continue

        # Early Fade Check: L2 price must not be broken (close-based) between P3 and P4
        l2_price = max(p1.price, p3.price)
        
        early_fade_slice = closes[p3.bar_index + 1 : p4_bar_idx + 1]
        early_fade = np.any(early_fade_slice > l2_price)
            
        if early_fade: continue

        candidates.append({
            'p1': p1, 'p2': p2, 'p3': p3, 'p5': p5, 
            'p4_time': p4_time, 'p4_idx': p4_bar_idx,
            'direction': SignalDirection.BEARISH
        })

    # 1B. BUY CANDIDATES
    for i in range(len(swings) - 2):
        p1 = swings[i]
        if p1.type != SwingType.LOW: continue
        
        # Find P2 (High after P1)
        p2 = None
        p2_idx = -1
        for j in range(i + 1, len(swings)):
            if swings[j].time > p1.time and swings[j].type == SwingType.HIGH:
                p2 = swings[j]
                p2_idx = j
                break
        if not p2: continue

        # Find P3 (Low after P2)
        p3 = None
        p3_idx = -1
        for j in range(p2_idx + 1, len(swings)):
            if swings[j].time > p2.time and swings[j].type == SwingType.LOW:
                p3 = swings[j]
                p3_idx = j
                break
        if not p3: continue

        # Find P5 (Older High before P1 with price > P2)
        p5 = None
        for j in range(i - 1, -1, -1):
            if swings[j].time < p1.time and swings[j].type == SwingType.HIGH and swings[j].price > p2.price:
                p5 = swings[j]
                break
        if not p5: continue

        # Find P4 (Confirmation Bar: Close > P5 PRICE after P3 TIME)
        p4_time = None
        p4_bar_idx = -1
        
        c_p4_search = closes[p3.bar_index + 1:]
        p4_hits = np.where(c_p4_search > p5.price)[0]
            
        if len(p4_hits) > 0:
            p4_bar_idx = p3.bar_index + 1 + p4_hits[0]
            p4_time = py_times[p4_bar_idx]
        
        if not p4_time: continue

        # V5.1.2: No Interruption Check
        interrupted = False
        for s in swings[i+1:]:
            if s.time > p3.time and s.time < p4_time:
                interrupted = True
                break
        if interrupted: continue

        # Early Fade Check: L2 (min of P1, P3) must not be broken between P3 and P4
        l2_price = min(p1.price, p3.price)
        
        early_fade_slice = closes[p3.bar_index + 1 : p4_bar_idx + 1]
        early_fade = np.any(early_fade_slice < l2_price)
            
        if early_fade: continue

        candidates.append({
            'p1': p1, 'p2': p2, 'p3': p3, 'p5': p5, 
            'p4_time': p4_time, 'p4_idx': p4_bar_idx,
            'direction': SignalDirection.BULLISH
        })

    # =========================================================================
    # PASS 2: GENERATE B2B ZONE OBJECTS (NO GLOBAL SELECTION)
    # =========================================================================
    zones = []
    for c in candidates:
        p1, p2, p3, p5 = c['p1'], c['p2'], c['p3'], c['p5']
        direction = c['direction']
        
        # Calculate L2 (The Stop level)
        l2_price = max(p1.price, p3.price) if direction == SignalDirection.BEARISH else min(p1.price, p3.price)
        l2_time = p1.time if (direction == SignalDirection.BEARISH and p1.price >= p3.price) or \
                            (direction == SignalDirection.BULLISH and p1.price <= p3.price) else p3.time
                            
        l1_price = p2.price
        
        zone = B2BZoneInfo(
            zone_id=generate_zone_id(l1_price, l2_price, tf, direction, l2_time),
            timeframe=tf,
            direction=direction,
            L1_price=l1_price,
            L2_price=l2_price,
            fifty_percent=(l1_price + l2_price) / 2.0,
            first_barrier_price=p2.price,
            first_barrier_time=p2.time,
            first_barrier_bar_index=p2.bar_index,
            second_barrier_price=p5.price,
            second_barrier_time=p5.time,
            second_barrier_bar_index=p5.bar_index,
            swing_between_price=l2_price,
            swing_between_time=l2_time,
            zone_created_time=c['p4_time'],
            created_bar_index=c['p4_idx']
        )
        zones.append(zone)

    # Final Sort: Chronological by creation
    zones.sort(key=lambda x: x.zone_created_time)
    return zones
