//+------------------------------------------------------------------+
//|                                                     brc_zones.mqh  |
//|  Path-B 5-pointer pairing + accuracy gates — port of zones.py.    |
//|                                                                    |
//|  A BRC zone confirms when the rawbreakout stream lands the SECOND  |
//|  same-direction break (the break of P5). The break IS the trigger: |
//|  this module is called once per new break event (the candidate     |
//|  P4 / 2nd break) and tries to reconstruct a valid 5-pointer behind |
//|  it. SELL geometry (BUY = mirror):                                 |
//|                                                                    |
//|     P5 (old swing LOW)  = 2nd barrier  — the swing this break broke |
//|     P1 (swing HIGH)     = L2 origin    — extreme high before P2     |
//|     P2 (swing LOW)      = L1 entry     — the 1st-break target       |
//|     P3 (swing HIGH<P1)  = context gate — last swing before P4       |
//|     P4 (break bar)      = confirmation — the bar that broke P5      |
//|                                                                    |
//|  Levels:  L1 = P2.price · L2 = extreme(P1,P3) (==P1 under gate) ·   |
//|           mid = (L1+L2)/2 · invalidation = CLOSE beyond L2.         |
//|                                                                    |
//|  ── CHRONOLOGICAL (no look-ahead) reconstruction ──────────────────|
//|  zones.py runs a vectorized FULL-array scan ("first ... after P1")  |
//|  over the FINAL swing list, which lets swings confirmed AFTER the   |
//|  breakout leak into the freshness gate. This emitter is the         |
//|  ORACLE: it only ever sees swings confirmed up to the current bar,  |
//|  so it reconstructs the skeleton BACKWARDS from P4 ("last ... before|
//|  ...") — the freshness gate then collapses to "P3 = the last swing  |
//|  before P4", which is automatically satisfied. The (expected) delta |
//|  vs the Python is exactly the look-ahead the fidelity-diff measures.|
//+------------------------------------------------------------------+
#ifndef BRC_ZONES_MQH
#define BRC_ZONES_MQH
#property strict

#include "brc_types.mqh"

//+------------------------------------------------------------------+
//| extreme(a,b): MAX for SELL (L2 sits above), MIN for BUY.          |
//+------------------------------------------------------------------+
double BrcExtreme(const double a, const double b, const bool sell)
  {
   return sell ? MathMax(a, b) : MathMin(a, b);
  }

//+------------------------------------------------------------------+
//| Last swing STRICTLY before `before_time`, scanning newest->oldest.|
//| any_type=true ignores the type filter (used for P3 = last swing   |
//| before P4 of ANY type). Returns array index, or -1.               |
//+------------------------------------------------------------------+
int BrcLastSwingBefore(const BrcSwing &swings[], const datetime before_time,
                       const int type_filter, const bool any_type)
  {
   for(int k = ArraySize(swings) - 1; k >= 0; k--)
     {
      if(swings[k].time >= before_time)
         continue;
      if(any_type || swings[k].type == type_filter)
         return k;
     }
   return -1;
  }

//+------------------------------------------------------------------+
//| Find the break event for a given broken-swing time (a swing       |
//| breaks at most once, so swing_time is a unique key). -1 if none.  |
//+------------------------------------------------------------------+
int BrcFindBreakBySwingTime(const BrcBreak &breaks[], const datetime swing_time)
  {
   for(int k = ArraySize(breaks) - 1; k >= 0; k--)
      if(breaks[k].swing_time == swing_time)
         return k;
   return -1;
  }

//+------------------------------------------------------------------+
//| Gap-validation (zones.py _passes_gap, EA B2BDetector.mqh:647-659):|
//| reject if L2 was CLOSED through in (P3, P4] — the zone died before |
//| its 2nd break ever landed. Window is by bar index on the TF series |
//| (c[] chronological, index 0 = oldest).                            |
//+------------------------------------------------------------------+
bool BrcPassesGap(const double &c[], const int n,
                  const int p3_index, const int p4_index,
                  const double l2, const bool sell)
  {
   for(int k = p3_index + 1; k <= p4_index && k < n; k++)
     {
      if(sell ? (c[k] > l2) : (c[k] < l2))
         return false;
     }
   return true;
  }

//+------------------------------------------------------------------+
//| Try to confirm a Path-B 5-pointer behind the just-landed break.   |
//|   b         : the new break event (the candidate P4 / 2nd break). |
//|   swings[]  : chronological per-TF swing buffer.                  |
//|   breaks[]  : chronological per-TF break event log.              |
//|   c[],n     : TF close series (index 0 = oldest) for gap-check.   |
//|   out       : filled with the confirmed zone geometry on success. |
//| Returns true and fills `out` iff a valid zone confirms. Lifecycle |
//| fields are left zeroed (BrcLifecycle fills them post-confirm).    |
//|                                                                    |
//| Each P5 swing breaks exactly once, so this fires at most once per  |
//| P5 — the one-zone-per-P5 dedup is structural here (no overwrite    |
//| map needed), and "freshest P1" falls out of the backward scan.    |
//+------------------------------------------------------------------+
bool BrcTryConfirmZone(const BrcBreak &b,
                       const BrcSwing &swings[], const BrcBreak &breaks[],
                       const double &c[], const int n,
                       BrcZone &out)
  {
   bool sell = (b.dir == BRC_BEAR);
   int  p1_type = sell ? BRC_SWING_HIGH : BRC_SWING_LOW;   // P1 / P3 type
   int  p2_type = sell ? BRC_SWING_LOW  : BRC_SWING_HIGH;  // P2 / P5 type

   //--- P5 = the swing this break broke (type == p2_type by construction:
   //    a bear break breaks a LOW, a bull break breaks a HIGH). P4 = break bar.
   if(b.swing_type != p2_type)
      return false;                              // direction/type mismatch
   datetime p5_time  = b.swing_time;
   double   p5_price = b.swing_price;
   datetime p4_time  = b.bar_time;
   double   p4_close = b.bar_close;
   int      p4_index = b.bar_index;

   //--- P3 = last swing before P4 of ANY type (freshness-collapsed); it MUST
   //    be a p1_type swing, else the freshness gate would reject the pattern.
   int ip3 = BrcLastSwingBefore(swings, p4_time, 0, true);
   if(ip3 < 0 || swings[ip3].type != p1_type)
      return false;
   double   p3_price = swings[ip3].price;
   datetime p3_time  = swings[ip3].time;
   int      p3_index = swings[ip3].bar_index;

   //--- P2 = last p2_type swing before P3 (= "first p2_type after P1"); the L1.
   int ip2 = BrcLastSwingBefore(swings, p3_time, p2_type, false);
   if(ip2 < 0)
      return false;
   double   p2_price = swings[ip2].price;
   datetime p2_time  = swings[ip2].time;

   //--- P1 = last p1_type swing before P2 (the freshest valid L2 origin).
   int ip1 = BrcLastSwingBefore(swings, p2_time, p1_type, false);
   if(ip1 < 0)
      return false;
   double   p1_price = swings[ip1].price;
   datetime p1_time  = swings[ip1].time;

   //--- P3<P1 context gate (RESTORED 2026-06-17): the context swing must stay
   //    inside the structure.  SELL -> P3 < P1 ;  BUY -> P3 > P1.
   if(sell ? (p3_price >= p1_price) : (p3_price <= p1_price))
      return false;

   //--- P5 must be MORE EXTREME than P2 (the 2nd barrier sits beyond L1) and
   //    OLDER than P1 (it seeds the structure from behind).
   if(sell ? (p5_price >= p2_price) : (p5_price <= p2_price))
      return false;
   if(p5_time >= p1_time)
      return false;

   //--- Levels.
   double l1 = p2_price;
   double l2 = BrcExtreme(p1_price, p3_price, sell);   // == p1_price under the gate
   double mid = 0.5 * (l1 + l2);

   //--- Gap-validation (freshness is already guaranteed by P3 = last-before-P4).
   if(!BrcPassesGap(c, n, p3_index, p4_index, l2, sell))
      return false;

   //--- break_kind: same_bar if the bar that broke P2 (the 1st break) is the
   //    same bar that broke P5; sequential if P2 broke earlier. If P2 has no
   //    recorded break (absorbed on the same impulse), treat as same_bar
   //    (zones.py: b_p2 is None -> same).
   int break_kind = BRC_SAME_BAR;
   int ib2 = BrcFindBreakBySwingTime(breaks, p2_time);
   if(ib2 >= 0)
      break_kind = (breaks[ib2].bar_index == p4_index) ? BRC_SAME_BAR : BRC_SEQUENTIAL;

   //--- Emit (geometry only; lifecycle filled later).
   out.direction = sell ? BRC_BEAR : BRC_BULL;
   out.l1 = l1;  out.l2 = l2;  out.mid = mid;
   out.p1_time = p1_time;  out.p1_price = p1_price;
   out.p2_time = p2_time;  out.p2_price = p2_price;
   out.p3_time = p3_time;  out.p3_price = p3_price;
   out.p4_time = p4_time;  out.p4_price = p4_close;
   out.p5_time = p5_time;  out.p5_price = p5_price;
   out.break_kind = break_kind;

   //--- lifecycle defaults (BrcLifecycle overwrites) -----------------
   out.t1_time = 0;  out.t2_time = 0;  out.t3_time = 0;
   out.invalidation_time = 0;
   out.alive = true;  out.continued = false;
   out.mfe_r = 0.0;  out.mae_r = 0.0;  out.realized_r = 0.0;
   out.bars_alive = 0;
   out.entry = l1;  out.r_unit = MathAbs(l1 - l2);  out.entered = false;
   return true;
  }

#endif // BRC_ZONES_MQH
