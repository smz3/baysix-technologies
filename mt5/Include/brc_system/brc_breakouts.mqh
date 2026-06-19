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
//| Scan UNBROKEN swings against ONE just-closed bar; mark newly-broken|
//| swings and append their break events to `breaks[]`.               |
//|   swings[]   : chronological, mutated (broken flag set).          |
//|   live[]     : indices into swings[] of still-unbroken swings,     |
//|                kept chronological; broken swings are compacted out |
//|                in place (order-preserving — NOT swap-remove, so    |
//|                the break-append order is byte-identical to the old |
//|                full 0..n scan). O(live) not O(all-ever).          |
//|   breaks[]   : persistent event log, appended in-place.           |
//| Returns the number of breaks appended on this bar.                |
//+------------------------------------------------------------------+
int BrcDetectBreaksOnBar(BrcSwing &swings[], int &live[],
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

#endif // BRC_BREAKOUTS_MQH
