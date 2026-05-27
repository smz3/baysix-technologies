//+------------------------------------------------------------------+
//| STABLE DETECTION MODULE - DO NOT MODIFY                          |
//| This entire file contains the core swing point detection engine.   |
//| The logic herein is stable, tested, and critical for the correct   |
//| functioning of the entire trading system.                          |
//|                                                                  |
//| DO NOT MODIFY this file without a complete understanding of its    |
//| role and the impact on historical and live signal generation.      |
//+------------------------------------------------------------------+
//| V5.0 CLEAN SLATE - B2B ONLY                                      |
//+------------------------------------------------------------------+

// MQL5 Swing Point Detector for SIGMA V5.0
// Detects swing highs and lows based on a sliding window.

#ifndef V50_SWINGPOINTDETECTOR_MQH
#define V50_SWINGPOINTDETECTOR_MQH

#include "../Data/Structures.mqh"
#include "../Common/Utils.mqh"

//+------------------------------------------------------------------+
//| CSwingPointDetector Class                                        |
//| Scans historical data to find swing points.                      |
//+------------------------------------------------------------------+
class CSwingPointDetector
  {
public:
                     CSwingPointDetector(void);

   // --- Public Methods ---
   SwingPointInfo    DetectLiveSwing(const MqlRates &rates_window[], const int bar_idx_to_check, ENUM_TIMEFRAMES timeframe, const int swing_window_size = 3);
   SwingPointInfo    CheckForSwingHigh(const ENUM_TIMEFRAMES timeframe, const int swing_window, const int swing_lookback, const datetime target_bar_time, const MqlRates &rates[], const int rates_total);
   SwingPointInfo    CheckForSwingLow(const ENUM_TIMEFRAMES timeframe, const int swing_window, const int swing_lookback, const datetime target_bar_time, const MqlRates &rates[], const int rates_total);
   
   // --- Retroactive Validation Methods ---
   bool              ValidateSwingPoint(const SwingPointInfo &swing_point, const MqlRates &rates[], const int rates_total, const int swing_window);
   int               CleanupInvalidatedSwings(SwingPointInfo &swing_array[], int &swing_count, const MqlRates &rates[], const int rates_total, const int swing_window);

private:
   // --- Private Helper Methods ---
   bool              IsSwingHigh(const MqlRates &rates[], const int middle_bar_index, const int window_size, ENUM_TIMEFRAMES timeframe);
   bool              IsSwingLow(const MqlRates &rates[], const int middle_bar_index, const int window_size, ENUM_TIMEFRAMES timeframe);
  };

//+------------------------------------------------------------------+
//| Constructor                                                      |
//+------------------------------------------------------------------+
CSwingPointDetector::CSwingPointDetector(void)
  {
   // Default swing window for live detection is 3 bars.
  }

//+------------------------------------------------------------------+
//| DetectLiveSwing                                                  |
//| Detects a swing point using a provided window of MqlRates.       |
//+------------------------------------------------------------------+
SwingPointInfo CSwingPointDetector::DetectLiveSwing(
    const MqlRates &rates_window[], 
    const int bar_idx_to_check,
    ENUM_TIMEFRAMES timeframe,
    const int swing_window_size
)
  {
   if(ArraySize(rates_window) < swing_window_size || swing_window_size < 3 || swing_window_size % 2 == 0)
     {
      return SwingPointInfo();
     }
   
   if(bar_idx_to_check < (swing_window_size / 2) || bar_idx_to_check >= (ArraySize(rates_window) - (swing_window_size / 2)))
     {
      return SwingPointInfo();
     }

   if(IsSwingHigh(rates_window, bar_idx_to_check, swing_window_size, timeframe))
     {
      MqlRates swing_bar = rates_window[bar_idx_to_check];
      return SwingPointInfo(swing_bar.close, swing_bar.time, swing_bar.close, SWING_HIGH, timeframe);
     }

   if(IsSwingLow(rates_window, bar_idx_to_check, swing_window_size, timeframe))
     {
      MqlRates swing_bar = rates_window[bar_idx_to_check];
      return SwingPointInfo(swing_bar.close, swing_bar.time, swing_bar.close, SWING_LOW, timeframe);
     }

   return SwingPointInfo(0, rates_window[bar_idx_to_check].time, rates_window[bar_idx_to_check].close, SWING_NONE, timeframe);
  }

//+------------------------------------------------------------------+
//| CheckForSwingHigh                                                |
//+------------------------------------------------------------------+
SwingPointInfo CSwingPointDetector::CheckForSwingHigh(
    const ENUM_TIMEFRAMES timeframe,
    const int swing_window,
    const int swing_lookback,
    const datetime target_bar_time,
    const MqlRates &rates[],
    const int rates_total
)
  {
   if(swing_window < 3 || swing_window % 2 == 0) return SwingPointInfo();
   if(swing_lookback <= 0) return SwingPointInfo();

   int target_bar_cache_index = FindBarIndexByTime(rates, target_bar_time, false);
   if(target_bar_cache_index < 0)
     {
      return SwingPointInfo();
     }

   int window_radius = swing_window / 2;
   int window_start_cache_index = target_bar_cache_index - window_radius;

   if(window_start_cache_index < 0 || (window_start_cache_index + swing_window) > rates_total)
     {
      return SwingPointInfo();
     }

   MqlRates rates_window[];
   if(ArrayResize(rates_window, swing_window) < 0) return SwingPointInfo();
   
   for(int i = 0; i < swing_window; i++)
     {
      rates_window[i] = rates[window_start_cache_index + i];
     }
   
   if(IsSwingHigh(rates_window, window_radius, swing_window, timeframe))
     {
      MqlRates swing_bar_candidate = rates_window[window_radius];

      // Calculate full imprint of the swing
      double imprint_top = swing_bar_candidate.high;
      double imprint_bottom = swing_bar_candidate.low;
      for(int k = 0; k < swing_window; k++)
        {
         if(rates_window[k].high > imprint_top) imprint_top = rates_window[k].high;
         if(rates_window[k].low < imprint_bottom) imprint_bottom = rates_window[k].low;
        }

      SwingPointInfo new_swing;
      new_swing.price = swing_bar_candidate.close;
      new_swing.time = swing_bar_candidate.time;
      new_swing.close_price = swing_bar_candidate.close;
      new_swing.type = SWING_HIGH;
      new_swing.original_tf = timeframe;
      new_swing.swing_imprint_top = imprint_top;
      new_swing.swing_imprint_bottom = imprint_bottom;

      return new_swing;
     }
   return SwingPointInfo();
  }

//+------------------------------------------------------------------+
//| CheckForSwingLow                                                 |
//+------------------------------------------------------------------+
SwingPointInfo CSwingPointDetector::CheckForSwingLow(
    const ENUM_TIMEFRAMES timeframe,
    const int swing_window,
    const int swing_lookback,
    const datetime target_bar_time,
    const MqlRates &rates[],
    const int rates_total
)
  {
   if(swing_window < 3 || swing_window % 2 == 0) return SwingPointInfo();
   if(swing_lookback <= 0) return SwingPointInfo();

   int target_bar_cache_index = FindBarIndexByTime(rates, target_bar_time, false);
   if(target_bar_cache_index < 0)
     {
      return SwingPointInfo();
     }

   int window_radius = swing_window / 2;
   int window_start_cache_index = target_bar_cache_index - window_radius;

   if(window_start_cache_index < 0 || (window_start_cache_index + swing_window) > rates_total)
     {
      return SwingPointInfo();
     }

   MqlRates rates_window[];
   if(ArrayResize(rates_window, swing_window) < 0) return SwingPointInfo();

   for(int i = 0; i < swing_window; i++)
     {
      rates_window[i] = rates[window_start_cache_index + i];
     }

   if(IsSwingLow(rates_window, window_radius, swing_window, timeframe))
     {
      MqlRates swing_bar_candidate = rates_window[window_radius];

      // Calculate full imprint of the swing
      double imprint_top = swing_bar_candidate.high;
      double imprint_bottom = swing_bar_candidate.low;
      for(int k = 0; k < swing_window; k++)
        {
         if(rates_window[k].high > imprint_top) imprint_top = rates_window[k].high;
         if(rates_window[k].low < imprint_bottom) imprint_bottom = rates_window[k].low;
        }

      SwingPointInfo new_swing;
      new_swing.price = swing_bar_candidate.close;
      new_swing.time = swing_bar_candidate.time;
      new_swing.close_price = swing_bar_candidate.close;
      new_swing.type = SWING_LOW;
      new_swing.original_tf = timeframe;
      new_swing.swing_imprint_top = imprint_top;
      new_swing.swing_imprint_bottom = imprint_bottom;

      return new_swing;
     }
   return SwingPointInfo();
  }

//+------------------------------------------------------------------+
//| IsSwingHigh                                                      |
//+------------------------------------------------------------------+
bool CSwingPointDetector::IsSwingHigh(const MqlRates &rates[], const int middle_bar_index, const int window_size, ENUM_TIMEFRAMES timeframe)
  {
   MqlRates candidate_bar = rates[middle_bar_index];
   double candidate_close = candidate_bar.close;

   for(int i = 0; i < window_size; i++)
     {
      if(i == middle_bar_index)
         continue;

      MqlRates neighbor_bar = rates[i];
      double neighbor_close = neighbor_bar.close;

      // Swing high must have close STRICTLY GREATER than all neighbors
      if(candidate_close <= neighbor_close)
        {
         return false;
        }
     }

   return true;
  }

//+------------------------------------------------------------------+
//| IsSwingLow                                                       |
//+------------------------------------------------------------------+
bool CSwingPointDetector::IsSwingLow(const MqlRates &rates[], const int middle_bar_index, const int window_size, ENUM_TIMEFRAMES timeframe)
  {
   MqlRates candidate_bar = rates[middle_bar_index];
   double candidate_close = candidate_bar.close;

   for(int i = 0; i < window_size; i++)
     { 
      if(i == middle_bar_index)
         continue;

      MqlRates neighbor_bar = rates[i];
      double neighbor_close = neighbor_bar.close;

      // Swing low must have close STRICTLY LOWER than all neighbors
      if(candidate_close >= neighbor_close)
        {
         return false;
        }
     }

   return true;
  }

//+------------------------------------------------------------------+
//| ValidateSwingPoint                                               |
//+------------------------------------------------------------------+
bool CSwingPointDetector::ValidateSwingPoint(
    const SwingPointInfo &swing_point, 
    const MqlRates &rates[], 
    const int rates_total, 
    const int swing_window)
  {
   if(swing_point.time == 0 || swing_point.type == SWING_NONE) return false;
   
   int actual_rates_size = ArraySize(rates);
   if(actual_rates_size < swing_window) return false;
   
   int swing_bar_idx = FindBarIndexByTime(rates, swing_point.time, false);
   if(swing_bar_idx < 0) return false;
   
   int window_radius = swing_window / 2;
   if(swing_bar_idx < window_radius || swing_bar_idx >= (actual_rates_size - window_radius)) 
      return false;
   
   MqlRates validation_window[];
   if(ArrayResize(validation_window, swing_window) < 0) return false;
   
   int window_start = swing_bar_idx - window_radius;
   int window_end = window_start + swing_window - 1;
   
   if(window_start < 0 || window_end >= actual_rates_size)
      return false;
   
   for(int i = 0; i < swing_window; i++)
     {
      validation_window[i] = rates[window_start + i];
     }
   
   if(swing_point.type == SWING_HIGH)
     {
      return IsSwingHigh(validation_window, window_radius, swing_window, swing_point.original_tf);
     }
   else if(swing_point.type == SWING_LOW)
     {
      return IsSwingLow(validation_window, window_radius, swing_window, swing_point.original_tf);
     }
   
   return false;
  }

//+------------------------------------------------------------------+
//| CleanupInvalidatedSwings                                         |
//+------------------------------------------------------------------+
int CSwingPointDetector::CleanupInvalidatedSwings(
    SwingPointInfo &swing_array[], 
    int &swing_count, 
    const MqlRates &rates[], 
    const int rates_total, 
    const int swing_window)
  {
   int removed_count = 0;
   
   for(int i = swing_count - 1; i >= 0; i--)
     {
      if(!ValidateSwingPoint(swing_array[i], rates, rates_total, swing_window))
        {
         for(int j = i; j < swing_count - 1; j++)
           {
            swing_array[j] = swing_array[j + 1];
           }
         swing_count--;
         removed_count++;
        }
     }
   
   return removed_count;
  }

#endif // V50_SWINGPOINTDETECTOR_MQH
