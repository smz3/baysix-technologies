//+------------------------------------------------------------------+
//|                                                       Utils.mqh |
//|                            Copyright 2025, Sigma Trading System |
//|                                       sigmatrading.ai@gmail.com |
//+------------------------------------------------------------------+
//| V5.0 CLEAN SLATE - B2B ONLY                                      |
//| Stripped of sequence-related utilities                           |
//+------------------------------------------------------------------+
#ifndef V50_UTILS_MQH
#define V50_UTILS_MQH

#include "Defines.mqh"
#include "../Data/Structures.mqh"

#property copyright "Copyright 2025, Sigma Trading System"
#property link      "sigmatrading.ai@gmail.com"
#property version   "5.00"
#property strict

//+------------------------------------------------------------------+
//| Font Enum to String                                              |
//+------------------------------------------------------------------+
string FontEnumToString(ENUM_DISPLAY_FONT font_enum)
  {
   switch(font_enum)
     {
      case FONT_COURIER: return "Courier New";
      case FONT_ARIAL:   return "Arial";
      case FONT_TIMES:   return "Times New Roman";
      case FONT_CALIBRI_LIGHT: return "Calibri Light";
     }
   return "Courier New"; // Default
  }

//+------------------------------------------------------------------+
//| Finds the index of a bar in a cached array by its timestamp      |
//| Works with MQL5 descending-sorted arrays (newest at index 0)    |
//+------------------------------------------------------------------+
int FindBarIndexByTime(const MqlRates &rates_array[], datetime target_time, bool find_later_bar)
  {
   int size = ArraySize(rates_array);
   if(size == 0) 
     {
      return -1; // Guard against empty array
     }

   // Binary search for descending-sorted MQL5 rates arrays
   int low = 0, high = size - 1;
   while(low <= high)
     {
      int mid = low + (high - low) / 2;
      if(rates_array[mid].time == target_time)
        {
         return mid; // Exact match found
        }
      else if(rates_array[mid].time < target_time)
        {
         high = mid - 1;
        }
      else
        {
         low = mid + 1;
        }
     }

   // Fallback: No exact match - find nearest bar based on preference
   if(find_later_bar)
     {
      if(low >= 0 && low < size)
        {
         return low;
        }
      return -1;
     }
   else
     {
      if(high >= 0 && high < size)
        {
         return high;
        }
      return -1;
     }
  }

//+------------------------------------------------------------------+
//| SwingType to SignalDirection                                     |
//+------------------------------------------------------------------+
ENUM_SIGNAL_DIRECTION SwingTypeToSignalDirection(ENUM_SWING_TYPE swing_type)
  {
   if(swing_type == SWING_HIGH)
      return DIRECTION_BEARISH;
   else if(swing_type == SWING_LOW)
      return DIRECTION_BULLISH;
   return DIRECTION_NONE;
  }

//+------------------------------------------------------------------+
//| Add Swing to Local History Array                                 |
//+------------------------------------------------------------------+
void AddSwingToLocalHistory(SwingPointInfo &local_swing_array[], const SwingPointInfo &new_swing)
  {
   int current_size = ArraySize(local_swing_array);
   ArrayResize(local_swing_array, current_size + 1);
   local_swing_array[current_size] = new_swing;
  }

//+------------------------------------------------------------------+
//| Sort Breakouts by Time (ascending)                               |
//+------------------------------------------------------------------+
void SortBreakoutsByTime(RawBreakoutInfo &breakouts[])
  {
   int size = ArraySize(breakouts);
   if(size <= 1) return;

   // Simple bubble sort
   for(int i = 0; i < size - 1; i++)
     {
      for(int j = 0; j < size - i - 1; j++)
        {
         if(breakouts[j].breakout_bar_time > breakouts[j+1].breakout_bar_time)
           {
            RawBreakoutInfo temp = breakouts[j];
            breakouts[j] = breakouts[j+1];
            breakouts[j+1] = temp;
           }
        }
     }
  }

//+------------------------------------------------------------------+
//| TimeframeToIndex - wrapper for TFEnumToIndex                     |
//+------------------------------------------------------------------+
int TimeframeToIndex(ENUM_TIMEFRAMES tf)
  {
   return TFEnumToIndex(tf);
  }

//+------------------------------------------------------------------+
//| GetBarCloseTime                                                  |
//| Calculates the closing time of a bar given its opening time      |
//+------------------------------------------------------------------+
datetime GetBarCloseTime(datetime bar_open_time, ENUM_TIMEFRAMES tf)
  {
   int period_seconds = PeriodSeconds(tf);
   if(period_seconds == 0) return bar_open_time;

   // Subtract one second for official closing timestamp
   return bar_open_time + period_seconds - 1;
  }

//+------------------------------------------------------------------+
//| Direction To String                                              |
//+------------------------------------------------------------------+
string DirectionToString(ENUM_SIGNAL_DIRECTION dir)
  {
   switch(dir)
     {
      case DIRECTION_BULLISH: return "BULLISH";
      case DIRECTION_BEARISH: return "BEARISH";
      default:                return "NONE";
     }
  }

//+------------------------------------------------------------------+
//| Swing Type To String                                             |
//+------------------------------------------------------------------+
string SwingTypeToString(ENUM_SWING_TYPE type)
  {
   switch(type)
     {
      case SWING_HIGH: return "HIGH";
      case SWING_LOW:  return "LOW";
      default:         return "NONE";
     }
  }

//+------------------------------------------------------------------+
//| Timeframe To String (short form)                                 |
//+------------------------------------------------------------------+
string TFToString(ENUM_TIMEFRAMES tf)
  {
   switch(tf)
     {
      case PERIOD_M1:  return "M1";
      case PERIOD_M5:  return "M5";
      case PERIOD_M15: return "M15";
      case PERIOD_M30: return "M30";
      case PERIOD_H1:  return "H1";
      case PERIOD_H4:  return "H4";
      case PERIOD_D1:  return "D1";
      case PERIOD_W1:  return "W1";
      case PERIOD_MN1: return "MN1";
      default:         return "??";
     }
  }

//+------------------------------------------------------------------+
//| Ensure History Loaded (Force Tester Sync)                        |
//+------------------------------------------------------------------+
bool EnsureHistoryLoaded(string symbol, ENUM_TIMEFRAMES tf, int target_bars=100)
{
   // Reset error
   ResetLastError();
   
   // Retry loop (up to 3 seconds)
   for(int k=0; k<30; k++)
   {
      // 1. Check if we have bars available via Bars()
      int bars = Bars(symbol, tf);
      if(bars >= target_bars) return true; // Success
      
      // 2. Force load attempt via iTime (deepest required bar)
      datetime t = iTime(symbol, tf, target_bars);
      
      // 3. Force load via CopyRates
      MqlRates rates[];
      int copied = CopyRates(symbol, tf, 0, target_bars, rates);
      
      if(copied >= target_bars) return true;
      
      // Wait slightly for Tester to fetch data (blocking)
      Sleep(100);
   }
   
   PrintFormat("WARNING: Data Sync Timed Out for %s. Got %d/%d bars.", 
               TFToString(tf), Bars(symbol, tf), target_bars);
               
   return false;
}

#endif // V50_UTILS_MQH
