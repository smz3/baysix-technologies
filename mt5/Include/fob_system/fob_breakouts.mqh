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
//| 4-POINTER ZONE (v1.26.0) — fill b.zone for a just-detected break.  |
//| L1 = P2 = the broken swing (ALWAYS known). L2 = far/invalidation   |
//| edge = extreme(P1,P3):                                             |
//|   P1 = nearest OPPOSITE-type fractal swing before P2 (ORIGIN) —    |
//|        OPTIONAL (no bail if absent; only voids near start-of-      |
//|        history where no prior opposite pivot exists).              |
//|   P3 = deepest OPPOSITE-direction CLOSE strictly between P2's bar  |
//|        and the break bar (the ACTUAL pullback extreme). Replaces   |
//|        the old FIRST fractal-confirmed swing, which lagged one bar |
//|        and vanished on sharp V-pullbacks -> the "no box drawn"     |
//|        bug (task 210). The retrace low is a real printed close.    |
//| valid = at least ONE of P1/P3 exists (a far edge can be placed).   |
//| Freshness + gap-val REJECTS were BRC TRADE-quality filters, NOT    |
//| geometry -> REMOVED (v1.26.0): a choppy / pre-touched zone still   |
//| has a real L1+L2 and MUST draw. Re-home to the trader if ever      |
//| wanted (fob_entry gates trades on zone.valid).                     |
//| Look-ahead-free: every scan reads indices STRICTLY < the break bar.|
//|   times[]  : TF bar-time series (index 0 = oldest), len n_closes.  |
//|   closes[] : TF close series   (index 0 = oldest), len n_closes.   |
//+------------------------------------------------------------------+
void FobComputeBreakZone(const FobSwing &swings[], const datetime &times[],
                         const double &closes[], const int n_closes, FobBreak &b)
  {
   b.zone.valid   = false;
   b.zone.p1_time = 0; b.zone.p1_price = 0;
   b.zone.p3_time = 0; b.zone.p3_price = 0; b.zone.l2 = 0.0;
   //--- lifecycle defaults (recomputed at draw by FobReplayZoneLife)
   b.zone.mid = 0.0; b.zone.alive = true; b.zone.invalidation_time = 0;
   b.zone.t1_time = 0; b.zone.t2_time = 0; b.zone.t3_time = 0;
   b.zone.bar_open = b.bar_open;   // carry the breaking bar's open onto the zone payload

   bool     bull     = (b.dir == FOB_BULL);
   int      opp_type = bull ? FOB_SWING_LOW : FOB_SWING_HIGH;  // P1 type (opposite the broken swing)
   datetime p2_time  = b.swing_time;                           // P2 = the broken swing (= L1)
   int      ns       = ArraySize(swings);

   //--- P2's series index = start of the pullback window (located in the time series).
   int p2_idx = -1;
   for(int idx = b.bar_index - 1; idx >= 0; idx--)
      if(times[idx] == p2_time) { p2_idx = idx; break; }

   //--- P1 = ORIGIN: nearest opposite-type fractal swing STRICTLY BEFORE P2.
   //--- OPTIONAL — a missing origin no longer voids the zone (P3 carries L2).
   int    ip1   = -1;
   for(int k = ns - 1; k >= 0; k--)
      if(swings[k].time < p2_time && swings[k].type == opp_type) { ip1 = k; break; }
   bool   hasP1 = (ip1 >= 0);

   //--- P3 = PULLBACK: deepest opposite-direction CLOSE strictly between P2's bar
   //--- and the break bar. The raw retrace extreme (NOT a fractal) so it never
   //--- lags/vanishes on a sharp V; past-only (idx < break bar) -> no look-ahead.
   int    ip3bar = -1;
   double p3     = 0.0;
   if(p2_idx >= 0)
      for(int idx = p2_idx + 1; idx < b.bar_index && idx < n_closes; idx++)
        {
         double c = closes[idx];
         if(ip3bar < 0 || (bull ? c < p3 : c > p3)) { p3 = c; ip3bar = idx; }
        }
   bool   hasP3 = (ip3bar >= 0);

   //--- need at least one far-edge anchor. Both absent is degenerate (no origin
   //--- AND break bar adjacent to P2 -> no pullback bars) -> no zone.
   if(!hasP1 && !hasP3)
      return;

   double p1 = hasP1 ? swings[ip1].price : 0.0;
   double l2;                                     // extreme(P1,P3) — deeper edge
   if(hasP1 && hasP3) l2 = bull ? MathMin(p1, p3) : MathMax(p1, p3);
   else               l2 = hasP3 ? p3 : p1;       // only one anchor -> use it

   if(hasP1) { b.zone.p1_time = swings[ip1].time; b.zone.p1_price = p1; }
   if(hasP3) { b.zone.p3_time = times[ip3bar];    b.zone.p3_price = p3; }
   b.zone.l2      = l2;
   b.zone.mid     = (b.swing_price + l2) * 0.5;   // L1 = broken swing price
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
                         const int bar_index, const datetime bar_time,
                         const double bar_open, const double bar_close,
                         const int radius, const int max_age,
                         const datetime &times[], const double &closes[], const int n_closes,
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
      breaks[k].bar_open    = bar_open;
      breaks[k].bar_close   = bar_close;
      breaks[k].bar_index   = bar_index;
      FobComputeBreakZone(swings, times, closes, n_closes, breaks[k]);   // 4-pointer band (v1.26.0)
      added++;
     }

   ArrayResize(live, w);                                  // survivors only, original order preserved
   return added;
  }

#endif // FOB_BREAKOUTS_MQH
