"""
SIGMA B2B Zone Status Tracker
Port of B2BZoneStatus.mqh → Python.
Handles T1 (L1), T2 (50%), T3 (L2) touch tracking and structural invalidation.
"""
import numpy as np
import pandas as pd
from core.models.structures import B2BZoneInfo, SignalDirection

def update_active_zones(current_low: float, current_high: float, current_close: float, current_time: pd.Timestamp, active_zones: list[B2BZoneInfo]):
    """
    STRICT SERIAL update for active zones.
    Checks for T1, T2, T3 touches and L2 invalidation based on the CURRENT bar only.
    """
    for zone in active_zones:
        if not zone.is_valid:
            continue

        # 1. Check Invalidation (Close past L2)
        invalidated = False
        if zone.direction == SignalDirection.BEARISH:
            if current_close > zone.L2_price:
                invalidated = True
        else:
            if current_close < zone.L2_price:
                invalidated = True

        if invalidated:
            zone.is_invalidated = True
            zone.is_valid = False
            zone.invalidation_time = current_time
            continue

        # 2. Check Touches (Internal Structural Progression)
        if zone.direction == SignalDirection.BEARISH: # Sell Zone
            # T1: High >= L1
            if not zone.L1_touched and current_high >= zone.L1_price:
                zone.L1_touched = True
                zone.L1_touch_time = current_time
                zone.touch_count = 1
                
            # T2: High >= 50% (Must be after or same bar as T1)
            if zone.L1_touched and not zone.fifty_touched and current_high >= zone.fifty_percent:
                zone.fifty_touched = True
                zone.fifty_touch_time = current_time
                zone.touch_count = 2
                
            # T3: High >= L2 (Must be after or same bar as T2)
            if zone.fifty_touched and not zone.L2_touched and current_high >= zone.L2_price:
                zone.L2_touched = True
                zone.L2_touch_time = current_time
                zone.touch_count = 3
        else: # Buy Zone
            # T1: Low <= L1
            if not zone.L1_touched and current_low <= zone.L1_price:
                zone.L1_touched = True
                zone.L1_touch_time = current_time
                zone.touch_count = 1
                
            if zone.L1_touched and not zone.fifty_touched and current_low <= zone.fifty_percent:
                zone.fifty_touched = True
                zone.fifty_touch_time = current_time
                zone.touch_count = 2
                
            if zone.fifty_touched and not zone.L2_touched and current_low <= zone.L2_price:
                zone.L2_touched = True
                zone.L2_touch_time = current_time
                zone.touch_count = 3

        # Update Age
        zone.zone_age_bars += 1

def update_zone_statuses(df: pd.DataFrame, zones: list[B2BZoneInfo]):
    """
    Vectorized Audit Update: Calculates T1, T2, T3 touches for a list of zones
    based on the historical data in df. Used for one-shot Audit visualizations.
    """
    highs = df['high'].values
    lows = df['low'].values
    closes = df['close'].values
    times = df.index.values # Assuming index is time or mapped correctly
    
    if len(df) == 0: return

    for zone in zones:
        if not zone.is_valid: continue
        
        # Determine the slice of data after zone creation
        start_idx = zone.created_bar_index
        if start_idx == -1: 
            # Fallback to time-based search if index is missing
            try: start_idx = df.index.get_loc(zone.zone_created_time)
            except: continue
        
        if start_idx >= len(df) - 1: continue
        
        h_slice = highs[start_idx+1:]
        l_slice = lows[start_idx+1:]
        c_slice = closes[start_idx+1:]
        t_slice = df.index[start_idx+1:]

        if zone.direction == SignalDirection.BEARISH: # Sell Zone
            # 1. Invalidation Check (Close > L2)
            inv_hits = np.where(c_slice > zone.L2_price)[0]
            if len(inv_hits) > 0:
                inv_idx = inv_hits[0]
                zone.is_invalidated = True
                zone.is_valid = False
                zone.invalidation_time = t_slice[inv_idx]
                # Trim slices to invalidation point for touch checks
                h_slice = h_slice[:inv_idx+1]
                l_slice = l_slice[:inv_idx+1]
                t_slice = t_slice[:inv_idx+1]

            # 2. Touch Detection (Serial progression T1 -> T2 -> T3)
            # T1: High >= L1
            t1_hits = np.where(h_slice >= zone.L1_price)[0]
            if len(t1_hits) > 0:
                t1_idx = t1_hits[0]
                zone.L1_touched = True
                zone.L1_touch_time = t_slice[t1_idx]
                zone.touch_count = 1
                
                # T2: High >= 50% (Must be on or after T1)
                t2_hits = np.where(h_slice[t1_idx:] >= zone.fifty_percent)[0]
                if len(t2_hits) > 0:
                    t2_idx = t1_idx + t2_hits[0]
                    zone.fifty_touched = True
                    zone.fifty_touch_time = t_slice[t2_idx]
                    zone.touch_count = 2
                    
                    # T3: High >= L2 (Must be on or after T2)
                    t3_hits = np.where(h_slice[t2_idx:] >= zone.L2_price)[0]
                    if len(t3_hits) > 0:
                        t3_idx = t2_idx + t3_hits[0]
                        zone.L2_touched = True
                        zone.L2_touch_time = t_slice[t3_idx]
                        zone.touch_count = 3

        else: # Buy Zone
            # 1. Invalidation Check (Close < L2)
            inv_hits = np.where(c_slice < zone.L2_price)[0]
            if len(inv_hits) > 0:
                inv_idx = inv_hits[0]
                zone.is_invalidated = True
                zone.is_valid = False
                zone.invalidation_time = t_slice[inv_idx]
                h_slice = h_slice[:inv_idx+1]
                l_slice = l_slice[:inv_idx+1]
                t_slice = t_slice[:inv_idx+1]

            # 2. Touch Detection
            t1_hits = np.where(l_slice <= zone.L1_price)[0]
            if len(t1_hits) > 0:
                t1_idx = t1_hits[0]
                zone.L1_touched = True
                zone.L1_touch_time = t_slice[t1_idx]
                zone.touch_count = 1
                
                t2_hits = np.where(l_slice[t1_idx:] <= zone.fifty_percent)[0]
                if len(t2_hits) > 0:
                    t2_idx = t1_idx + t2_hits[0]
                    zone.fifty_touched = True
                    zone.fifty_touch_time = t_slice[t2_idx]
                    zone.touch_count = 2
                    
                    t3_hits = np.where(l_slice[t2_idx:] <= zone.L2_price)[0]
                    if len(t3_hits) > 0:
                        t3_idx = t2_idx + t3_hits[0]
                        zone.L2_touched = True
                        zone.L2_touch_time = t_slice[t3_idx]
                        zone.touch_count = 3

