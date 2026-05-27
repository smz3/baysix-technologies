//+------------------------------------------------------------------+
//|                                           RawBreakoutDetector.mqh |
//|                             Copyright 2025, Sigma Trading System |
//+------------------------------------------------------------------+
//| V5.0.4 - Unified Swing Array                                     |
//| L2 = the impulse swing AFTER L1 that starts the move to break L1 |
//| V5.0.5 - Share L2 between same-bar breakouts (same impulse move) |
//+------------------------------------------------------------------+
#ifndef V50_RAWBREAKOUTDETECTOR_MQH
#define V50_RAWBREAKOUTDETECTOR_MQH

#include "../Data/Structures.mqh"
#include "../Common/Defines.mqh"
#include "../Common/Utils.mqh"

class CRawBreakoutDetector
  {
private:
   // CORRECTED LOGIC: Find the impulse swing that starts the move TO break L1
   // This swing occurs AFTER L1 formed, but BEFORE the breakout bar
   // For BULLISH breakout (breaks HIGH) → search for swing LOW AFTER the HIGH
   // For BEARISH breakout (breaks LOW) → search for swing HIGH AFTER the LOW
   double FindImpulseSwingPrice(const SwingPointInfo &broken_swing, 
                                 const SwingPointInfo &swings[], 
                                 const int swings_count,
                                 ENUM_SWING_TYPE target_type,
                                 datetime breakout_bar_time)
     {
      datetime latest_time = 0;
      double found_price = 0.0;

      for(int i = 0; i < swings_count; i++)
        {
         // Must be the correct swing type (opposite of broken swing)
         if(swings[i].type != target_type)
            continue;
            
         // Must occur AFTER the broken swing (L1) formed
         if(swings[i].time <= broken_swing.time)
            continue;
            
         // Must occur BEFORE the breakout bar
         if(swings[i].time >= breakout_bar_time)
            continue;
            
         // We want the MOST RECENT one (closest to the breakout)
         if(swings[i].time > latest_time)
           {
            latest_time = swings[i].time;
            found_price = swings[i].price;
           }
        }
      return found_price;
     }

public:
                     CRawBreakoutDetector(void) {}
                    ~CRawBreakoutDetector(void) {}

   // V5.0.5: Detects breakouts with L2 sharing for same-bar breakouts
   int Detect(
       RawBreakoutInfo &found_breakouts[],
       const MqlRates &bar_to_check,
       const MqlRates &rates_for_tf[],
       const int max_breakout_age_bars,
       SwingPointInfo &swings[],
       const int swings_count,
       ENUM_TIMEFRAMES current_tf,
       const bool log_details,
       const bool is_live_detection)
     {
      ArrayResize(found_breakouts, 0);
      int breakouts_found_count = 0;

      int bar_to_check_idx = FindBarIndexByTime(rates_for_tf, bar_to_check.time, true);
      int rates_count = ArraySize(rates_for_tf);
      if(bar_to_check_idx == -1) return 0;

      // Doctrinal shield: Never check forming bar in live detection
      if(is_live_detection && bar_to_check_idx == 0)
        {
         return 0;
        }

      // V5.0.5: Track L2 per direction to share between same-bar breakouts
      // When multiple swings are broken by same bar, they share the earliest valid L2
      double shared_L2_bullish = 0.0;  // L2 for bullish breakouts (swing LOW)
      double shared_L2_bearish = 0.0;  // L2 for bearish breakouts (swing HIGH)
      datetime earliest_bullish_swing_time = D'3000.01.01';  // Track earliest broken swing
      datetime earliest_bearish_swing_time = D'3000.01.01';

      // FIRST PASS: Find the earliest swing broken for each direction 
      // and calculate shared L2 from that earliest swing
      for(int i = 0; i < swings_count; i++)
        {
         SwingPointInfo current_swing = swings[i];
         
         if(current_swing.time >= bar_to_check.time)
            continue;
         if(current_swing.has_been_broken)
            continue;

         int current_swing_idx = FindBarIndexByTime(rates_for_tf, current_swing.time, true);
         if(current_swing_idx == -1)
            continue;

         int age_in_bars = current_swing_idx - bar_to_check_idx;
         if(max_breakout_age_bars > 0 && age_in_bars > max_breakout_age_bars)
            continue;

         // BULLISH: close > swing HIGH
         if(current_swing.type == SWING_HIGH && bar_to_check.close > current_swing.price)
           {
            if(current_swing.time < earliest_bullish_swing_time)
              {
               earliest_bullish_swing_time = current_swing.time;
               // Calculate L2 from this earliest swing - the impulse swing after it
               shared_L2_bullish = FindImpulseSwingPrice(current_swing, swings, swings_count, 
                                                          SWING_LOW, bar_to_check.time);
              }
           }
         
         // BEARISH: close < swing LOW
         if(current_swing.type == SWING_LOW && bar_to_check.close < current_swing.price)
           {
            if(current_swing.time < earliest_bearish_swing_time)
              {
               earliest_bearish_swing_time = current_swing.time;
               // Calculate L2 from this earliest swing - the impulse swing after it
               shared_L2_bearish = FindImpulseSwingPrice(current_swing, swings, swings_count, 
                                                          SWING_HIGH, bar_to_check.time);
              }
           }
        }

      // SECOND PASS: Create breakouts with shared L2
      for(int i = 0; i < swings_count; i++)
        {
         SwingPointInfo current_swing = swings[i];
         
         if(current_swing.time >= bar_to_check.time)
            continue;
         if(current_swing.has_been_broken)
            continue;

         int current_swing_idx = FindBarIndexByTime(rates_for_tf, current_swing.time, true);
         if(current_swing_idx == -1)
            continue;

         int age_in_bars = current_swing_idx - bar_to_check_idx;
         if(max_breakout_age_bars > 0 && age_in_bars > max_breakout_age_bars)
            continue;

         //=== BULLISH BREAKOUT: Close > Swing HIGH ===
         if(current_swing.type == SWING_HIGH && bar_to_check.close > current_swing.price)
           {
            // Mark swing as broken
            swings[i].has_been_broken = true;
            
            RawBreakoutInfo new_bo;
            new_bo.breakout_bar_time = GetBarCloseTime(bar_to_check.time, current_tf);
            new_bo.breakout_bar_close_price = bar_to_check.close;
            new_bo.direction = DIRECTION_BULLISH;
            new_bo.timeframe_occurred = current_tf;
            new_bo.broken_swing_original_tf = current_swing.original_tf;
            new_bo.broken_swing_price = current_swing.price;
            new_bo.broken_swing_time = current_swing.time;
            new_bo.broken_swing_close_price = current_swing.close_price;
            new_bo.broken_swing_type = current_swing.type;
            new_bo.breakout_age_in_bars = age_in_bars;
            
            // V5.0.5: Use SHARED L2 (from earliest swing in this impulse move)
            new_bo.impulse_start_price = shared_L2_bullish;

            int current_size = ArraySize(found_breakouts);
            ArrayResize(found_breakouts, current_size + 1);
            found_breakouts[current_size] = new_bo;
            breakouts_found_count++;
           }
         
         //=== BEARISH BREAKOUT: Close < Swing LOW ===
         if(current_swing.type == SWING_LOW && bar_to_check.close < current_swing.price)
           {
            // Mark swing as broken
            swings[i].has_been_broken = true;
            
            RawBreakoutInfo new_bo;
            new_bo.breakout_bar_time = GetBarCloseTime(bar_to_check.time, current_tf);
            new_bo.breakout_bar_close_price = bar_to_check.close;
            new_bo.direction = DIRECTION_BEARISH;
            new_bo.timeframe_occurred = current_tf;
            new_bo.broken_swing_original_tf = current_swing.original_tf;
            new_bo.broken_swing_price = current_swing.price;
            new_bo.broken_swing_time = current_swing.time;
            new_bo.broken_swing_close_price = current_swing.close_price;
            new_bo.broken_swing_type = current_swing.type;
            new_bo.breakout_age_in_bars = age_in_bars;
            
            // V5.0.5: Use SHARED L2 (from earliest swing in this impulse move)
            new_bo.impulse_start_price = shared_L2_bearish;

            int current_size = ArraySize(found_breakouts);
            ArrayResize(found_breakouts, current_size + 1);
            found_breakouts[current_size] = new_bo;
            breakouts_found_count++;
           }
        }

      return breakouts_found_count;
     }
  };

#endif // V50_RAWBREAKOUTDETECTOR_MQH
