//+------------------------------------------------------------------+
//|                                                 brc_breakouts.mqh  |
//|  Raw breakout primitive — faithful port of rawbreakout.py         |
//|  (RawBreakoutDetector.mqh re-port), TRIMMED for Path B.           |
//|                                                                    |
//|  bull = close > swing HIGH ;  bear = close < swing LOW.            |
//|  Eligibility per swing: not broken; swing older than the bar;      |
//|  confirmation gate (bar_index >= swing.bar_index + radius);        |
//|  age filter (max_age<=0 disables). A swing breaks at most once.    |
//|                                                                    |
//|  OMITTED vs the oracle: PASS-1 shared-L2 (impulse_start_price).    |
//|  Path B never consumes L2, and the PASS-2 break decision does not  |
//|  depend on it — so dropping it changes no break time/price/dir.    |
//+------------------------------------------------------------------+
#ifndef BRC_BREAKOUTS_MQH
#define BRC_BREAKOUTS_MQH
#property strict

#include "brc_types.mqh"

//+------------------------------------------------------------------+
//| Scan all swings against ONE just-closed bar; mark newly-broken    |
//| swings and append their break events to `breaks[]`.               |
//|   swings[]   : chronological, mutated (broken flag set).          |
//|   breaks[]   : persistent event log, appended in-place.           |
//| Returns the number of breaks appended on this bar.                |
//+------------------------------------------------------------------+
int BrcDetectBreaksOnBar(BrcSwing &swings[],
                         const int bar_index, const datetime bar_time, const double bar_close,
                         const int radius, const int max_age,
                         BrcBreak &breaks[])
  {
   int n_sw   = ArraySize(swings);
   int added  = 0;

   for(int s = 0; s < n_sw; s++)
     {
      if(swings[s].broken)                              continue;
      if(swings[s].time >= bar_time)                    continue;   // swing must precede bar
      if(bar_index < swings[s].bar_index + radius)      continue;   // confirmation gate
      if(max_age > 0 && (bar_index - swings[s].bar_index) > max_age) continue;

      bool is_bull = (swings[s].type == BRC_SWING_HIGH && bar_close > swings[s].price);
      bool is_bear = (swings[s].type == BRC_SWING_LOW  && bar_close < swings[s].price);
      if(!is_bull && !is_bear)
         continue;

      swings[s].broken = true;

      int k = ArraySize(breaks);
      ArrayResize(breaks, k + 1);
      breaks[k].swing_time  = swings[s].time;
      breaks[k].swing_price = swings[s].price;
      breaks[k].swing_type  = swings[s].type;
      breaks[k].dir         = is_bull ? BRC_BULL : BRC_BEAR;
      breaks[k].bar_time    = bar_time;
      breaks[k].bar_close   = bar_close;
      breaks[k].bar_index   = bar_index;
      added++;
     }
   return added;
  }

#endif // BRC_BREAKOUTS_MQH
