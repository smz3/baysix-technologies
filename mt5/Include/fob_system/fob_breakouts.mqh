//+------------------------------------------------------------------+
//|                                                 fob_breakouts.mqh  |
//|  FOB's OWN raw breakout primitive — FOB owns its detection, NOTHING |
//|  shared with brc_system (types incl.). Faithful port of            |
//|  rawbreakout.py.                                                    |
//|                                                                    |
//|  bull = close > swing HIGH ;  bear = close < swing LOW.            |
//|  Eligibility per swing: not broken; swing older than the bar;      |
//|  confirmation gate (bar_index >= swing.bar_index + radius);        |
//|  age filter (max_age<=0 disables). A swing breaks at most once.    |
//+------------------------------------------------------------------+
#ifndef FOB_BREAKOUTS_MQH
#define FOB_BREAKOUTS_MQH
#property strict

#include "fob_types.mqh"   // FobSwing, FobBreak, FOB_BULL/BEAR (FOB's own types)

//+------------------------------------------------------------------+
//| 4-POINTER ZONE (v1.14.0) — fill b.zone for a just-detected break.  |
//| BRC's level logic (extreme(P1,P3) + freshness + gap-val), but P2   |
//| is PINNED to the break's own broken swing (no parallel selection   |
//| scan -> can never desync from the FOB event). P5 dropped: the break |
//| itself is the confirmation. Look-ahead-free: P1/P2/P3 all precede   |
//| the break bar, gap-val reads only closes up to it.                  |
//|   closes[] : the TF close series (index 0 = oldest), len n_closes. |
//+------------------------------------------------------------------+
void FobComputeBreakZone(const FobSwing &swings[], const double &closes[], const int n_closes,
                         FobBreak &b)
  {
   b.zone.valid   = false;
   b.zone.p1_time = 0; b.zone.p1_price = 0;
   b.zone.p3_time = 0; b.zone.p3_price = 0; b.zone.l2 = 0.0;

   bool     bull     = (b.dir == FOB_BULL);
   int      opp_type = bull ? FOB_SWING_LOW : FOB_SWING_HIGH;  // P1/P3 type (opposite the broken swing)
   datetime p2_time  = b.swing_time;                           // P2 = the broken swing (= L1)
   int      ns       = ArraySize(swings);

   //--- P1 = nearest opposite-type swing STRICTLY BEFORE P2 (newest->oldest).
   int ip1 = -1;
   for(int k = ns - 1; k >= 0; k--)
      if(swings[k].time < p2_time && swings[k].type == opp_type) { ip1 = k; break; }
   if(ip1 < 0) return;                                         // no origin -> no zone (foolproof)

   //--- P3 = FIRST opposite-type swing STRICTLY AFTER P2 and before the break bar.
   int ip3 = -1;
   for(int k = 0; k < ns; k++)
      if(swings[k].time > p2_time && swings[k].time < b.bar_time && swings[k].type == opp_type)
        { ip3 = k; break; }
   if(ip3 < 0) return;                                         // no pullback pivot -> no zone

   //--- FRESHNESS (BRC): no swing of ANY type strictly between P3 and the break bar.
   for(int k = 0; k < ns; k++)
      if(swings[k].time > swings[ip3].time && swings[k].time < b.bar_time)
         return;                                               // messy structure -> reject

   double p1 = swings[ip1].price, p3 = swings[ip3].price;
   double l2 = bull ? MathMin(p1, p3) : MathMax(p1, p3);       // extreme(P1,P3) = far edge

   //--- GAP-VAL (BRC): L2 not closed-through in (P3, P4]. A break bar can only
   //--- close through L1 (the opposite edge), so including P4 is harmless.
   int p3_idx = swings[ip3].bar_index;
   for(int idx = p3_idx + 1; idx <= b.bar_index && idx < n_closes; idx++)
      if(bull ? (closes[idx] < l2) : (closes[idx] > l2))
         return;                                               // zone died before triggering -> reject

   b.zone.p1_time = swings[ip1].time; b.zone.p1_price = p1;
   b.zone.p3_time = swings[ip3].time; b.zone.p3_price = p3;
   b.zone.l2      = l2;
   b.zone.valid   = true;
  }

//+------------------------------------------------------------------+
//| Scan UNBROKEN swings against ONE just-closed bar; mark newly-broken|
//| swings and append their break events to `breaks[]`.               |
//|   swings[]   : chronological, mutated (broken flag set).          |
//|   live[]     : indices into swings[] of still-unbroken swings,     |
//|                kept chronological; broken swings are compacted out |
//|                in place (order-preserving). O(live) not O(all).    |
//|   closes[]   : TF close series (=s.bc) for the 4-pointer gap-val.  |
//|   breaks[]   : persistent event log, appended in-place.           |
//| Returns the number of breaks appended on this bar.                |
//+------------------------------------------------------------------+
int FobDetectBreaksOnBar(FobSwing &swings[], int &live[],
                         const int bar_index, const datetime bar_time, const double bar_close,
                         const int radius, const int max_age,
                         const double &closes[], const int n_closes,
                         FobBreak &breaks[])
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

      bool is_bull = (swings[s].type == FOB_SWING_HIGH && bar_close > swings[s].price);
      bool is_bear = (swings[s].type == FOB_SWING_LOW  && bar_close < swings[s].price);
      if(!is_bull && !is_bear)
        { live[w++] = live[j]; continue; }                // price didn't cross -> stays live

      //--- swing breaks (permanent) -> emit event, drop it from the live list.
      swings[s].broken = true;

      int k = ArraySize(breaks);
      ArrayResize(breaks, k + 1);
      breaks[k].swing_time  = swings[s].time;
      breaks[k].swing_price = swings[s].price;
      breaks[k].swing_type  = swings[s].type;
      breaks[k].dir         = is_bull ? FOB_BULL : FOB_BEAR;
      breaks[k].bar_time    = bar_time;
      breaks[k].bar_close   = bar_close;
      breaks[k].bar_index   = bar_index;
      FobComputeBreakZone(swings, closes, n_closes, breaks[k]);   // 4-pointer band (v1.14.0)
      added++;
     }

   ArrayResize(live, w);                                  // survivors only, original order preserved
   return added;
  }

#endif // FOB_BREAKOUTS_MQH
