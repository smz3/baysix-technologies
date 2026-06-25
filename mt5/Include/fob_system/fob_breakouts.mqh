//+------------------------------------------------------------------+
//|                                                 fob_breakouts.mqh  |
//|  FOB's OWN raw breakout primitive — copy of the STRUCT-001         |
//|  detector (brc_breakouts.mqh), so FOB owns its detection and is    |
//|  never coupled to brc_system's copy. Logic is identical (faithful  |
//|  port of rawbreakout.py).                                          |
//|                                                                    |
//|  bull = close > swing HIGH ;  bear = close < swing LOW.            |
//|  Eligibility per swing: not broken; swing older than the bar;      |
//|  confirmation gate (bar_index >= swing.bar_index + radius);        |
//|  age filter (max_age<=0 disables). A swing breaks at most once.    |
//|                                                                    |
//|  Types (BrcSwing / BrcBreak / BRC_*) stay shared from brc_types —  |
//|  the STRUCT-001 data primitive, not detection logic.               |
//+------------------------------------------------------------------+
#ifndef FOB_BREAKOUTS_MQH
#define FOB_BREAKOUTS_MQH
#property strict

#include <brc_system/brc_types.mqh>   // BrcSwing, BrcBreak, BRC_BULL/BEAR (STRUCT-001 types)

//+------------------------------------------------------------------+
//| Scan UNBROKEN swings against ONE just-closed bar; mark newly-broken|
//| swings and append their break events to `breaks[]`.               |
//|   swings[]   : chronological, mutated (broken flag set).          |
//|   live[]     : indices into swings[] of still-unbroken swings,     |
//|                kept chronological; broken swings are compacted out |
//|                in place (order-preserving). O(live) not O(all).    |
//|   breaks[]   : persistent event log, appended in-place.           |
//| Returns the number of breaks appended on this bar.                |
//+------------------------------------------------------------------+
int FobDetectBreaksOnBar(BrcSwing &swings[], int &live[],
                         const int bar_index, const datetime bar_time, const double bar_close,
                         const int radius, const int max_age,
                         BrcBreak &breaks[])
  {
   int n_live = ArraySize(live);
   int added  = 0;
   int w      = 0;                                       // survivor write cursor (compaction)

   for(int j = 0; j < n_live; j++)
     {
      int s = live[j];
      //--- temporal / eligibility guards: NOT yet (or never) eligible to break
      //    this bar, but still unbroken -> keep live, re-check on a later bar.
      if(swings[s].time >= bar_time)                       { live[w++] = live[j]; continue; }  // swing must precede bar
      if(bar_index < swings[s].bar_index + radius)         { live[w++] = live[j]; continue; }  // confirmation gate
      if(max_age > 0 && (bar_index - swings[s].bar_index) > max_age) { live[w++] = live[j]; continue; }

      bool is_bull = (swings[s].type == BRC_SWING_HIGH && bar_close > swings[s].price);
      bool is_bear = (swings[s].type == BRC_SWING_LOW  && bar_close < swings[s].price);
      if(!is_bull && !is_bear)
        { live[w++] = live[j]; continue; }                // price didn't cross -> stays live

      //--- swing breaks (permanent) -> emit event, drop it from the live list.
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

   ArrayResize(live, w);                                  // survivors only, original order preserved
   return added;
  }

#endif // FOB_BREAKOUTS_MQH
