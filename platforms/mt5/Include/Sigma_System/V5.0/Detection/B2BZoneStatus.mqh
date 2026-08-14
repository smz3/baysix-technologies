//+------------------------------------------------------------------+
//|                                               B2BZoneStatus.mqh |
//|                             Copyright 2025, Sigma Trading System |
//| V5.1: Zone Status Updates and Validation                          |
//| - Touch tracking (L1, 50%, L2)                                    |
//| - Zone invalidation                                               |
//| - Historical validation                                           |
//| V6.0: Phase 0 Zone Logging Integration                            |
//+------------------------------------------------------------------+
#ifndef V50_B2BZONESTATUS_MQH
#define V50_B2BZONESTATUS_MQH

#include "../Data/Structures.mqh"
#include "../Common/CircularBuffer.mqh"
#include "../Data/QuantLogger.mqh"

// Global Quant Logger (instantiated in main EA)
extern CQuantLogger g_QuantLogger;

//+------------------------------------------------------------------+
//| CB2BZoneStatus Class                                              |
//| Handles zone touch tracking and validation                        |
//+------------------------------------------------------------------+
class CB2BZoneStatus
  {
public:
   //=== Real-time Status Updates ===
   // Updates zones in internal m_zones array
   static int  UpdateZoneStatus(B2BZoneInfo &zones[], int zone_count, 
                                 ENUM_TIMEFRAMES tf,
                                 double current_close, double current_high, double current_low);
   
   // Updates zones in external CCircularBuffer
   // V11.0: return bitmask (1=Structural, 2=Metric)
   static int  UpdateZoneStatusInBuffer(B2BZoneInfo &zones[], int zone_count,
                                         double current_close, double current_high, double current_low,
                                         bool is_new_bar = false);
   
   //=== Historical Validation ===
   static int  ValidateZonesInBuffer(B2BZoneInfo &zones[], int zone_count);
   static bool ValidateZoneAgainstHistory(B2BZoneInfo &zone);
  };

//+------------------------------------------------------------------+
//| UpdateZoneStatus - Updates zones in array for specific TF         |
//+------------------------------------------------------------------+
int CB2BZoneStatus::UpdateZoneStatus(B2BZoneInfo &zones[], int zone_count,
                                      ENUM_TIMEFRAMES tf,
                                      double current_close, double current_high, double current_low)
  {
   int zones_changed = 0;
   
   // Get current bar time once for efficiency
   datetime current_bar_time = iTime(_Symbol, tf, 0);

   for(int i = 0; i < zone_count; i++)
     {
      if(zones[i].timeframe != tf)
         continue;
      
      if(zones[i].is_invalidated || !zones[i].is_valid)
         continue;
         
      // V5.2: Prevent self-triggering on Creation Bar (Breakout Bar)
      // We only accept touches on bars AFTER the zone was created
      if(current_bar_time <= zones[i].zone_created_time)
         continue;
      
      bool changed = false;
      
      // Update zone age
      zones[i].zone_age_bars = iBarShift(_Symbol, tf, zones[i].zone_created_time);
      
      //=== L1 TOUCH DETECTION (T1) ===

         bool L1_touched_now = false;
         
         if(zones[i].direction == DIRECTION_BEARISH)
           {
            double entry_level = MathMin(zones[i].L1_price, zones[i].L2_price);
            L1_touched_now = (current_high >= entry_level);
           }
         else
           {
            double entry_level = MathMax(zones[i].L1_price, zones[i].L2_price);
            L1_touched_now = (current_low <= entry_level);
           }
         
         if(L1_touched_now)
           {
            bool was_first_touch = !zones[i].L1_touched;
            
            zones[i].L1_touched = true;
            zones[i].L1_touch_time = TimeCurrent(); // UPDATE EVERY TIME
            zones[i].touch_count++;
            changed = true;
            
            if(was_first_touch)
            {
                zones[i].L1_touch_bar = 0;
                
                // Phase 0: Log T1 touch
                g_QuantLogger.LogZoneTouched(zones[i], "T1");
                
                // Track parent zone touch
                if(!zones[i].is_parent_touched)
                  {
                   bool is_parent_zone = (zones[i].timeframe >= PERIOD_M15);
                   if(is_parent_zone)
                     {
                      zones[i].is_parent_touched = true;
                      zones[i].parent_touched_time = TimeCurrent();
                      zones[i].parent_touch_depth = 1;
                     }
                  }
            }
           }
      
      //=== 50% TOUCH DETECTION (T2) ===
      if(!zones[i].fifty_touched)
        {
         bool fifty_touched_now = false;
         
         if(zones[i].direction == DIRECTION_BEARISH)
            fifty_touched_now = (current_high >= zones[i].fifty_percent);
         else
            fifty_touched_now = (current_low <= zones[i].fifty_percent);
         
         if(fifty_touched_now && zones[i].L1_touched)
           {
            zones[i].fifty_touched = true;
            zones[i].fifty_touch_time = TimeCurrent();
            zones[i].fifty_touch_bar = 0;
            changed = true;
            
            // Phase 0: Log T2 touch
            g_QuantLogger.LogZoneTouched(zones[i], "T2");
           }
        }
      
      //=== L2 WICK TOUCH DETECTION (T3) ===
      if(!zones[i].L2_touched)
        {
         bool L2_touched_now = false;
         
         if(zones[i].direction == DIRECTION_BEARISH)
           {
            double L2_level = MathMax(zones[i].L1_price, zones[i].L2_price);
            L2_touched_now = (current_high >= L2_level);
           }
         else
           {
            double L2_level = MathMin(zones[i].L1_price, zones[i].L2_price);
            L2_touched_now = (current_low <= L2_level);
           }
         
         if(L2_touched_now && zones[i].fifty_touched)
           {
            zones[i].L2_touched = true;
            zones[i].L2_touch_time = TimeCurrent();
            zones[i].L2_touch_bar = 0;
            changed = true;
            
            // Phase 0: Log T3 touch
            g_QuantLogger.LogZoneTouched(zones[i], "T3");
           }
        }
      
      //=== L2 INVALIDATION ===
      if(zones[i].direction == DIRECTION_BEARISH)
        {
         double invalidation_level = MathMax(zones[i].L1_price, zones[i].L2_price);
         if(current_close > invalidation_level)
           {
            zones[i].is_invalidated = true;
            zones[i].invalidation_time = TimeCurrent();
            zones[i].L2_touched = true;
            changed = true;
            
            // Phase 0: Log BULLDOZED
            g_QuantLogger.LogZoneBulldozed(zones[i]);
           }
        }
      else
        {
         double invalidation_level = MathMin(zones[i].L1_price, zones[i].L2_price);
         if(current_close < invalidation_level)
           {
            zones[i].is_invalidated = true;
            zones[i].invalidation_time = TimeCurrent();
            zones[i].L2_touched = true;
            changed = true;
            
            // Phase 0: Log BULLDOZED
            g_QuantLogger.LogZoneBulldozed(zones[i]);
           }
        }
      
      if(changed)
         zones_changed++;
     }
   
   return zones_changed;
  }

//+------------------------------------------------------------------+
//| UpdateZoneStatusInBuffer - Updates zones in CCircularBuffer       |
//| V6.2 FIX: Invalidation ONLY triggers when is_new_bar is true      |
//| Touch detection (T1/T2/T3) still runs every tick for real-time    |
//+------------------------------------------------------------------+
int CB2BZoneStatus::UpdateZoneStatusInBuffer(B2BZoneInfo &zones[], int zone_count,
                                              double current_close, double current_high, double current_low,
                                              bool is_new_bar)
  {
   int total_mask = ZONE_CHANGE_NONE;
   
   // V10.3 OPTIMIZATION: Cache bar times per timeframe to avoid repeated iTime/iBarShift calls
   // This reduces expensive MQL5 API calls from O(zones) to O(timeframes)
   static ENUM_TIMEFRAMES cached_tfs[9] = {PERIOD_M1, PERIOD_M5, PERIOD_M15, PERIOD_M30, PERIOD_H1, PERIOD_H4, PERIOD_D1, PERIOD_W1, PERIOD_MN1};
   static datetime cached_bar_times[9] = {0};
   static datetime last_update_time = 0;
   
   // Refresh cache once per second max (bar times don't change faster than that)
   datetime now = TimeCurrent();
   if(now != last_update_time)
     {
      last_update_time = now;
      for(int t = 0; t < 9; t++)
         cached_bar_times[t] = iTime(_Symbol, cached_tfs[t], 0);
     }
   
   for(int i = 0; i < zone_count; i++)
     {
      B2BZoneInfo zone = zones[i];
      
      if(zone.is_invalidated || !zone.is_valid)
         continue;
      
      // V12 PERFORMANCE: Skip fully-consumed zones (touch lifecycle complete)
      // Once L2 is touched, no further state changes can occur. Skipping these
      // prevents the per-tick loop from growing unbounded over multi-year backtests.
      if(zone.L2_touched)
         continue;
      
      // V5.2: Prevent self-triggering on Creation Bar
      // V10.3: Use cached bar time instead of calling iTime per zone
      datetime bar_time = 0;
      for(int t = 0; t < 9; t++)
        {
         if(cached_tfs[t] == zone.timeframe) { bar_time = cached_bar_times[t]; break; }
        }
      // V11.2: Birth Bar Validation
      // We only skip if the CURRENT candle is the same as the creation candle (intra-bar).
      // If the current candle has advanced (bar_time > zone_created_time), we MUST validate.
      if(bar_time < zone.zone_created_time)
         continue;

      bool structural_changed = false;
      bool metric_changed = false;
      
      //=== V11.1/V12: Delta-Age Sync (State-Driven Invalidation + O(1) Optimization) ===
      int current_age = zone.zone_age_bars;
      
      // V12 PERFORMANCE FIX: iBarShift is expensive. Only call it on new bars or initial load.
      if(is_new_bar || zone.zone_age_bars == 0)
      {
         current_age = iBarShift(_Symbol, zone.timeframe, zone.zone_created_time);
      }
      
      int delta_age = current_age - zone.zone_age_bars;
      bool run_full_validation = (delta_age > 1);
      bool run_fast_check = (delta_age == 1 || is_new_bar);
      
      // We wait until the check is successfully completed before updating zone_age_bars
      // This ensures that if data is missing, we try again on the next tick.
      
      //=== L1 TOUCH ===
      if(!zone.L1_touched)
        {
         bool L1_touched_now = false;
         
         if(zone.direction == DIRECTION_BEARISH)
           {
            double entry_level = MathMin(zone.L1_price, zone.L2_price);
            L1_touched_now = (current_high >= entry_level);
           }
         else
           {
            double entry_level = MathMax(zone.L1_price, zone.L2_price);
            L1_touched_now = (current_low <= entry_level);
           }
         
         if(L1_touched_now)
           {
            zone.L1_touched = true;
            zone.L1_touch_time = TimeCurrent();
            zone.touch_count++;
            
             // Phase 0: Log T1 touch
             g_QuantLogger.LogZoneTouched(zone, "T1");
             
            // V1.3: Signal HTF touch for flip check (performance optimization)
            if(zone.timeframe == PERIOD_W1 || zone.timeframe == PERIOD_D1)
               total_mask |= ZONE_CHANGE_HTF_TOUCHED;
               
            structural_changed = true;
           }
        }
      
      //=== 50% TOUCH ===
      if(!zone.fifty_touched && zone.L1_touched)
        {
         bool fifty_touched_now = false;
         
         if(zone.direction == DIRECTION_BEARISH)
            fifty_touched_now = (current_high >= zone.fifty_percent);
         else
            fifty_touched_now = (current_low <= zone.fifty_percent);
         
         if(fifty_touched_now)
           {
            zone.fifty_touched = true;
            zone.fifty_touch_time = TimeCurrent();
            
              // Phase 0: Log T2 touch
              g_QuantLogger.LogZoneTouched(zone, "T2");
                
             structural_changed = true;
            }
        }
      
      //=== L2 TOUCH ===
      if(!zone.L2_touched && zone.fifty_touched)
        {
         bool L2_touched_now = false;
         
         if(zone.direction == DIRECTION_BEARISH)
           {
            double L2_level = MathMax(zone.L1_price, zone.L2_price);
            L2_touched_now = (current_high >= L2_level);
           }
         else
           {
            double L2_level = MathMin(zone.L1_price, zone.L2_price);
            L2_touched_now = (current_low <= L2_level);
           }
         
         if(L2_touched_now)
           {
            zone.L2_touched = true;
            zone.L2_touch_time = TimeCurrent();
            
              // Phase 0: Log T3 touch
              g_QuantLogger.LogZoneTouched(zone, "T3");
 
                
             structural_changed = true;
            }
        }
      
      //=== MFE/MAE TRACKING (Phase 0.5B) ===
      // V13.2 OPTIMIZATION: Simple price-gate check BEFORE expensive point conversion
      if(zone.L1_touched && zone.L1_touch_time > 0)
        {
         if(zone.direction == DIRECTION_BULLISH)
           {
            // BUY zone: favorable = UP, adverse = DOWN
            if(current_high > zone.L1_price + (zone.max_favorable_excursion * _Point))
              {
               zone.max_favorable_excursion = (current_high - zone.L1_price) / _Point;
               zone.mfe_time = TimeCurrent();
               metric_changed = true;
              }
            if(current_low < zone.L1_price - (zone.max_adverse_excursion * _Point))
              {
               zone.max_adverse_excursion = (zone.L1_price - current_low) / _Point;
               zone.mae_time = TimeCurrent();
               metric_changed = true;
              }
           }
         else
           {
            // SELL zone: favorable = DOWN, adverse = UP
            if(current_low < zone.L1_price - (zone.max_favorable_excursion * _Point))
              {
               zone.max_favorable_excursion = (zone.L1_price - current_low) / _Point;
               zone.mfe_time = TimeCurrent();
               metric_changed = true;
              }
            if(current_high > zone.L1_price + (zone.max_adverse_excursion * _Point))
              {
               zone.max_adverse_excursion = (current_high - zone.L1_price) / _Point;
               zone.mae_time = TimeCurrent();
               metric_changed = true;
              }
           }
        }
      
      //=== INVALIDATION (ONLY ON BAR CLOSE) ===
      // V6.2 FIX: Only check invalidation when is_new_bar is true
      // This prevents zones from being invalidated on wick touches
      //=== INVALIDATION (ONLY ON BAR CLOSE) ===
      // V6.2 FIX: Only check invalidation when is_new_bar is true
      // V11.0: "Strict Fractal Invalidation" - Use specific bar CLOSE, not current tick (Open)
      // This handles gaps correctly: We validate the bar that JUST closed (index 1)
      // V11.2: State-Driven Invalidation
      if(run_full_validation)
        {
         if(ValidateZoneAgainstHistory(zone))
           {
            structural_changed = true;
           }
         else
           {
            zone.zone_age_bars = current_age;
            metric_changed = true;
           }
        }
      else if(run_fast_check)
        {
         double strict_close_price = iClose(_Symbol, zone.timeframe, 1);
         
         bool should_invalidate = false;
         if(zone.direction == DIRECTION_BEARISH)
         {
          double invalidation_level = MathMax(zone.L1_price, zone.L2_price);
          if(strict_close_price > invalidation_level) should_invalidate = true;
         }
         else
         {
          double invalidation_level = MathMin(zone.L1_price, zone.L2_price);
          if(strict_close_price < invalidation_level) should_invalidate = true;
         }

         if(should_invalidate)
         {
          zone.is_invalidated = true;
          zone.invalidation_time = TimeCurrent();
          zone.L2_touched = true;
          structural_changed = true;
          g_QuantLogger.LogZoneBulldozed(zone);
         }
         else
         {
          zone.zone_age_bars = current_age;
          metric_changed = true;
         }
        } // End if(run_fast_check)
      
       if(structural_changed || metric_changed)
        {
         zones[i] = zone;
         if(structural_changed) total_mask |= ZONE_CHANGE_STRUCTURAL;
         if(metric_changed)     total_mask |= ZONE_CHANGE_METRIC;
        }
     }
   
   return total_mask;
  }

//+------------------------------------------------------------------+
//| ValidateZonesInBuffer - Validates zones against history           |
//+------------------------------------------------------------------+
int CB2BZoneStatus::ValidateZonesInBuffer(B2BZoneInfo &zones[], int zone_count)
  {
   int invalidated_count = 0;
   
   for(int i = 0; i < zone_count; i++)
     {
      if(ValidateZoneAgainstHistory(zones[i]))
         invalidated_count++;
     }
   
   return invalidated_count;
  }

//+------------------------------------------------------------------+
//| ValidateZoneAgainstHistory - Historical price check               |
//+------------------------------------------------------------------+
bool CB2BZoneStatus::ValidateZoneAgainstHistory(B2BZoneInfo &zone)
  {
   if(zone.is_invalidated || !zone.is_valid)
      return false;
   
   datetime pattern_complete_time = (datetime)MathMax((double)zone.second_barrier_time, (double)zone.zone_created_time);
   
   MqlRates rates[];
   int bars_loaded = CopyRates(Symbol(), zone.timeframe, pattern_complete_time, TimeCurrent(), rates);
   
   // DEBUG: First BUY zone timing
   static int timing_debug = 0;
   if(timing_debug < 1 && zone.direction == DIRECTION_BULLISH)
     {
      PrintFormat("[BUY TIMING] zone_created=%s, second_barrier=%s, pattern_complete=%s, TimeCurrent=%s, bars_loaded=%d, TF=%d",
                 TimeToString(zone.zone_created_time), TimeToString(zone.second_barrier_time),
                 TimeToString(pattern_complete_time), TimeToString(TimeCurrent()), bars_loaded, zone.timeframe);
      timing_debug++;
     }
   
   if(bars_loaded <= 0)
      return false;
   
   ArraySetAsSeries(rates, false);
   
   double invalidation_level, L1_level, L2_level;
   if(zone.direction == DIRECTION_BEARISH)
     {
      invalidation_level = MathMax(zone.L1_price, zone.L2_price);
      L1_level = MathMin(zone.L1_price, zone.L2_price);
      L2_level = MathMax(zone.L1_price, zone.L2_price);
     }
   else
     {
      invalidation_level = MathMin(zone.L1_price, zone.L2_price);
      L1_level = MathMax(zone.L1_price, zone.L2_price);
      L2_level = MathMin(zone.L1_price, zone.L2_price);
     }
   
   // DEBUG: For first BUY zone, find min_low across ALL bars
   static int buy_comprehensive_debug = 0;
   if(buy_comprehensive_debug < 1 && zone.direction == DIRECTION_BULLISH)
     {
      double min_low = 999999;
      int valid_bars = 0;
      for(int k = 0; k < bars_loaded; k++)
        {
         if(rates[k].time < pattern_complete_time) continue;
         if(rates[k].low < min_low) min_low = rates[k].low;
         valid_bars++;
        }
      PrintFormat("[BUY COMPREHENSIVE] zone L1=%.2f L2=%.2f | bars_checked=%d | min_low=%.2f | L1_level=%.2f | WOULD_TOUCH=%s",
                 zone.L1_price, zone.L2_price, valid_bars, min_low, L1_level, min_low <= L1_level ? "YES" : "NO");
      buy_comprehensive_debug++;
     }
   
   for(int i = 0; i < bars_loaded; i++)
     {
      // V11.2: Include Creation Bar
      // We only skip if the rate bar time is STRICTLY before the pattern creation time.
      // If the rate bar is the same as creation bar, we check its CLOSE.
      if(rates[i].time < pattern_complete_time)
         continue;
      
      // Touch tracking FIRST - before checking invalidation
      // So touches are recorded even on the bar that invalidates
      if(zone.direction == DIRECTION_BEARISH)
        {
         // SELL zone: price comes UP to touch levels
         if(!zone.L1_touched && rates[i].high >= L1_level)
           {
            zone.L1_touched = true;
            zone.L1_touch_time = rates[i].time;
           }
         if(zone.L1_touched && !zone.fifty_touched && rates[i].high >= zone.fifty_percent)
           {
            zone.fifty_touched = true;
            zone.fifty_touch_time = rates[i].time;
           }
         if(zone.fifty_touched && !zone.L2_touched && rates[i].high >= L2_level)
           {
            zone.L2_touched = true;
            zone.L2_touch_time = rates[i].time;
           }
        }
      else
        {
         // BUY zone: price comes DOWN to touch levels
         if(!zone.L1_touched && rates[i].low <= L1_level)
           {
            zone.L1_touched = true;
            zone.L1_touch_time = rates[i].time;
           }
         if(zone.L1_touched && !zone.fifty_touched && rates[i].low <= zone.fifty_percent)
           {
            zone.fifty_touched = true;
            zone.fifty_touch_time = rates[i].time;
           }
         if(zone.fifty_touched && !zone.L2_touched && rates[i].low <= L2_level)
           {
            zone.L2_touched = true;
            zone.L2_touch_time = rates[i].time;
           }
        }
      
      // Check invalidation AFTER touch tracking
      bool invalidated = false;
      if(zone.direction == DIRECTION_BEARISH)
        {
         if(rates[i].close > invalidation_level)
            invalidated = true;
        }
      else
        {
         if(rates[i].close < invalidation_level)
            invalidated = true;
        }
      
      // Phase 0.5B: Track MFE/MAE for touched zones during historical validation
      if(zone.L1_touched && zone.L1_touch_time > 0)
        {
         double entry_price = zone.L1_price;
         double favorable = 0, adverse = 0;
         
         if(zone.direction == DIRECTION_BULLISH)
           {
            // BUY zone: favorable = price UP, adverse = price DOWN
            favorable = (rates[i].high - entry_price) / _Point;
            adverse = (entry_price - rates[i].low) / _Point;
           }
         else
           {
            // SELL zone: favorable = price DOWN, adverse = price UP
            favorable = (entry_price - rates[i].low) / _Point;
            adverse = (rates[i].high - entry_price) / _Point;
           }
         
         if(favorable > 0 && favorable > zone.max_favorable_excursion)
            {
             zone.max_favorable_excursion = favorable;
             zone.mfe_time = rates[i].time;
            }
         if(adverse > 0 && adverse > zone.max_adverse_excursion)
            {
             zone.max_adverse_excursion = adverse;
             zone.mae_time = rates[i].time;
            }
        }
      
      if(invalidated)
        {
         zone.is_invalidated = true;
         zone.invalidation_time = rates[i].time;
         zone.L2_touched = true;
         return true;
        }
     }
   return false;
  }


#endif // V50_B2BZONESTATUS_MQH
