//+------------------------------------------------------------------+
//|                                                     brc_zones.mqh  |
//|  B2B-PARITY 5-pointer detection — 1:1 port of Sigma's              |
//|  CB2BDetector::DetectB2B_5Pointer (forward scan), run inside the   |
//|  event-driven emitter where the swing buffer only ever holds       |
//|  swings confirmed up to the current bar (so the forward scan       |
//|  carries NO look-ahead — the Python vectorized full-array scan     |
//|  was the only thing that leaked). SELL geometry (BUY = mirror):    |
//|                                                                    |
//|     P1 (swing HIGH)     = L2 origin    — anchor, newest valid wins  |
//|     P2 (swing LOW)      = L1 entry     — FIRST low AFTER P1         |
//|     P3 (swing HIGH)     = context      — FIRST high AFTER P2        |
//|     P5 (old swing LOW)  = 2nd barrier  — first low before P1, <P2   |
//|     P4 (break bar)      = confirmation — the bar that broke P5      |
//|                                                                    |
//|  Levels:  L1 = P2.price · L2 = extreme(P1,P3) · mid = (L1+L2)/2 ·   |
//|           invalidation = CLOSE beyond L2.                          |
//|                                                                    |
//|  ── B2B parity rules (CB2BDetector) ───────────────────────────────|
//|   · FORWARD selection: P2 = first opposite AFTER P1, P3 = first     |
//|     same-type AFTER P2  (B2BDetector.mqh:595/605).                  |
//|   · NO P3<P1 gate — L2 may resolve to P3 (B2BDetector.mqh:395).     |
//|   · winner-per-P5 = NEWEST P1 (B2BDetector.mqh:781).                |
//|   · freshness: no swing strictly in (P3,P4) (B2BDetector.mqh:636).  |
//|   · gap-val: L2 not closed-through in (P3,P4] (B2BDetector.mqh:651).|
//|   · IsSwingUsedInZones: a swing used by an ALIVE same-direction     |
//|     zone cannot seed another (B2BDetector.mqh:498).                 |
//|   · duplicate check on (dir,L1,L2) (B2BDetector.mqh:849).           |
//|                                                                    |
//|  Triggered once per new break (the candidate P4 / P5-break), so the |
//|  newest-P1 winner falls out of a newest->oldest P1 scan, and the    |
//|  one-zone-per-P5 dedup is structural (a swing breaks once).         |
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
//| FIRST swing STRICTLY after `after_time` of `type_filter`,         |
//| scanning oldest->newest. Returns array index, or -1.              |
//| (B2B "first low after P1" / "first high after P2".)               |
//+------------------------------------------------------------------+
int BrcFirstSwingAfter(const BrcSwing &swings[], const datetime after_time,
                       const int type_filter)
  {
   int cnt = ArraySize(swings);
   //--- swings[] is strictly chronological (append order) -> binary-search the
   //    first index with time > after_time (upper_bound), then forward-scan that
   //    short tail for the type. Byte-identical to the old 0..cnt linear scan,
   //    but O(log n + k) not O(n) — this is the per-break hot path.
   int lo = 0, hi = cnt;
   while(lo < hi)
     {
      int mid = (lo + hi) >> 1;
      if(swings[mid].time <= after_time) lo = mid + 1;
      else                               hi = mid;
     }
   for(int k = lo; k < cnt; k++)
      if(swings[k].type == type_filter)
         return k;
   return -1;
  }

//+------------------------------------------------------------------+
//| B2B FindP5_OlderBarrier: first p2_type swing STRICTLY before P1   |
//| (newest->oldest) whose price is BEYOND P2 (SELL: < P2 ; BUY: > P2)|
//| Returns index or -1. Used to verify the broken swing IS the P5    |
//| this P1 maps to (else a closer barrier would win -> skip).        |
//+------------------------------------------------------------------+
int BrcFindP5ForP1(const BrcSwing &swings[], const datetime p1_time,
                   const double p2_price, const int p2_type, const bool sell)
  {
   int cnt = ArraySize(swings);
   //--- binary-search the first index with time >= p1_time, then walk strictly
   //    BEFORE it newest->oldest. Identical set+order to the old full backward
   //    scan that `continue`d every time >= p1_time, but skips that dead prefix.
   int lo = 0, hi = cnt;
   while(lo < hi)
     {
      int mid = (lo + hi) >> 1;
      if(swings[mid].time < p1_time) lo = mid + 1;
      else                           hi = mid;
     }
   for(int k = lo - 1; k >= 0; k--)
     {
      if(swings[k].type != p2_type)
         continue;
      if(sell ? (swings[k].price < p2_price) : (swings[k].price > p2_price))
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
//| Gap-validation (B2BDetector.mqh:647-659): reject if L2 was CLOSED |
//| through in (P3, P4] — the zone died before its 2nd break landed.  |
//| Window is by bar index on the TF series (c[] chronological, 0=old)|
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
//| L2-source swing time for a zone (the P1-or-P3 that became L2).    |
//| B2B's "swing_between" anchor for swing-usage checks.              |
//+------------------------------------------------------------------+
datetime BrcL2SrcTime(const BrcZone &z)
  {
   return (MathAbs(z.p1_price - z.l2) <= MathAbs(z.p3_price - z.l2)) ? z.p1_time : z.p3_time;
  }

//+------------------------------------------------------------------+
//| IsSwingUsedInZones (B2BDetector.mqh:498) — a (price,time) swing   |
//| is "used" iff it is the P2, P5, or L2-source of an ALIVE zone of  |
//| the SAME direction (dead zones free their swings, matching B2B's  |
//| skip-invalidated). BUY/SELL never block each other.               |
//+------------------------------------------------------------------+
bool BrcSwingUsedInZones(const BrcZone &zones[], const double price,
                         const datetime time, const int dir)
  {
   double tol = _Point / 2;
   int cnt = ArraySize(zones);
   for(int i = 0; i < cnt; i++)
     {
      if(!zones[i].alive)               continue;   // dead zones free their swings
      if(zones[i].direction != dir)     continue;   // same direction only

      if(MathAbs(zones[i].p2_price - price) < tol && zones[i].p2_time == time)
         return true;                                // L1 / first_barrier (P2)
      if(MathAbs(zones[i].p5_price - price) < tol && zones[i].p5_time == time)
         return true;                                // second_barrier (P5)

      double   l2src_price = zones[i].l2;
      datetime l2src_time  = BrcL2SrcTime(zones[i]);
      if(MathAbs(l2src_price - price) < tol && l2src_time == time)
         return true;                                // swing_between (L2 source)
     }
   return false;
  }

//+------------------------------------------------------------------+
//| Duplicate check (B2BDetector.mqh:849): a same-direction zone with |
//| matching L1 and L2 already exists. Checks ALL zones (alive+dead). |
//+------------------------------------------------------------------+
bool BrcZoneDuplicate(const BrcZone &zones[], const int dir,
                      const double l1, const double l2)
  {
   double tol = _Point / 2;
   int cnt = ArraySize(zones);
   for(int i = 0; i < cnt; i++)
      if(zones[i].direction == dir &&
         MathAbs(zones[i].l1 - l1) < tol &&
         MathAbs(zones[i].l2 - l2) < tol)
         return true;
   return false;
  }

//+------------------------------------------------------------------+
//| Try to confirm a B2B-parity 5-pointer behind the just-landed break|
//|   b         : the new break event (the candidate P4 / P5-break).  |
//|   swings[]  : chronological per-TF swing buffer.                  |
//|   breaks[]  : chronological per-TF break event log (break_kind).  |
//|   c[],n     : TF close series (index 0 = oldest) for gap-check.   |
//|   existing[]: zones already confirmed on this TF (dedup target).  |
//|   out       : filled with the confirmed zone geometry on success. |
//| Returns true iff a valid zone confirms.                           |
//|                                                                    |
//| PASS 1+2 are folded: scanning P1 candidates NEWEST->OLDEST and     |
//| taking the FIRST that clears freshness+gap+P5-map yields exactly   |
//| B2B's "newest P1 per P5" winner. PASS 3 dedup (swing-usage + dup)  |
//| is applied to that winner only — a blocked winner is dropped, B2B  |
//| does NOT fall back to an older P1 for the same P5.                 |
//+------------------------------------------------------------------+
bool BrcTryConfirmZone(const BrcBreak &b,
                       const BrcSwing &swings[], const BrcBreak &breaks[],
                       const double &c[], const int n,
                       const BrcZone &existing[],
                       BrcZone &out)
  {
   bool sell    = (b.dir == BRC_BEAR);
   int  p1_type = sell ? BRC_SWING_HIGH : BRC_SWING_LOW;   // P1 / P3 type
   int  p2_type = sell ? BRC_SWING_LOW  : BRC_SWING_HIGH;  // P2 / P5 type

   //--- P5 = the swing this break broke (a bear break breaks a LOW, a bull
   //    break breaks a HIGH). P4 = break bar.
   if(b.swing_type != p2_type)
      return false;
   datetime p5_time  = b.swing_time;
   double   p5_price = b.swing_price;
   datetime p4_time  = b.bar_time;
   double   p4_close = b.bar_close;
   int      p4_index = b.bar_index;

   //==================================================================
   // PASS 1+2: find the NEWEST-P1 winner for this P5.
   //==================================================================
   bool     found = false;
   datetime w_p1_time = 0, w_p2_time = 0, w_p3_time = 0;
   double   w_p1_price = 0, w_p2_price = 0, w_p3_price = 0;
   double   w_l1 = 0, w_l2 = 0;

   int swing_count = ArraySize(swings);

   //--- freshness pre-bound (O(1) per P1 candidate instead of an inner O(n) scan):
   //    the LATEST swing strictly before P4. Swings are chronological, so a swing
   //    lies strictly in (P3,P4) for a given candidate IFF this latest-before-P4
   //    swing's time > p3_time (it dominates the open interval's upper end).
   //    Equivalent to the old "any swing with p3_time < t < p4_time" scan.
   int last_before_p4 = -1;
   for(int q = swing_count - 1; q >= 0; q--)
      if(swings[q].time < p4_time)
        { last_before_p4 = q; break; }

   for(int i = swing_count - 1; i >= 0; i--)
     {
      if(swings[i].type != p1_type)
         continue;
      datetime p1_time = swings[i].time;
      if(p1_time >= p4_time)            // P1 must precede P4
         continue;
      if(p1_time <= p5_time)            // P1 must be NEWER than P5 (older can't map here)
         break;
      double p1_price = swings[i].price;

      //--- P2 = first p2_type swing AFTER P1 (B2B forward).
      int ip2 = BrcFirstSwingAfter(swings, p1_time, p2_type);
      if(ip2 < 0 || swings[ip2].time >= p4_time)
         continue;
      datetime p2_time  = swings[ip2].time;
      double   p2_price = swings[ip2].price;

      //--- P5 mapping: the broken swing must BE "first p2_type before P1 beyond
      //    P2" — else B2B would pick a closer barrier as P5 for this P1.
      int ip5map = BrcFindP5ForP1(swings, p1_time, p2_price, p2_type, sell);
      if(ip5map < 0 || swings[ip5map].time != p5_time)
         continue;

      //--- P3 = first p1_type swing AFTER P2 (B2B forward).
      int ip3 = BrcFirstSwingAfter(swings, p2_time, p1_type);
      if(ip3 < 0 || swings[ip3].time >= p4_time)
         continue;
      datetime p3_time  = swings[ip3].time;
      double   p3_price = swings[ip3].price;
      int      p3_index = swings[ip3].bar_index;

      //--- FRESHNESS (B2B): no swing strictly between P3 and P4 (pre-bounded above).
      if(last_before_p4 >= 0 && swings[last_before_p4].time > p3_time)
         continue;

      //--- Levels (NO P3<P1 gate — B2B parity; L2 may be P3).
      double l1  = p2_price;
      double l2  = BrcExtreme(p1_price, p3_price, sell);

      //--- GAP-VAL (B2B): L2 not closed-through in (P3, P4].
      if(!BrcPassesGap(c, n, p3_index, p4_index, l2, sell))
         continue;

      //--- Winner = newest P1 (first hit in the newest->oldest scan).
      found = true;
      w_p1_time = p1_time;  w_p1_price = p1_price;
      w_p2_time = p2_time;  w_p2_price = p2_price;
      w_p3_time = p3_time;  w_p3_price = p3_price;
      w_l1 = l1;            w_l2 = l2;
      break;
     }

   if(!found)
      return false;

   //==================================================================
   // PASS 3: dedup the winner (swing-usage + duplicate). Blocked -> drop.
   //==================================================================
   if(BrcSwingUsedInZones(existing, w_p1_price, w_p1_time, b.dir) ||
      BrcSwingUsedInZones(existing, w_p2_price, w_p2_time, b.dir) ||
      BrcSwingUsedInZones(existing, w_p3_price, w_p3_time, b.dir) ||
      BrcSwingUsedInZones(existing, p5_price,  p5_time,  b.dir))
      return false;
   if(BrcZoneDuplicate(existing, b.dir, w_l1, w_l2))
      return false;

   //--- break_kind: same_bar if the bar that broke P2 (1st break) is the same
   //    bar that broke P5; sequential if earlier. No recorded P2 break (absorbed
   //    on one impulse) -> same_bar (zones.py: b_p2 is None -> same).
   int break_kind = BRC_SAME_BAR;
   int ib2 = BrcFindBreakBySwingTime(breaks, w_p2_time);
   if(ib2 >= 0)
      break_kind = (breaks[ib2].bar_index == p4_index) ? BRC_SAME_BAR : BRC_SEQUENTIAL;

   //--- Emit (geometry only; lifecycle filled later).
   out.direction = b.dir;
   out.l1 = w_l1;  out.l2 = w_l2;  out.mid = 0.5 * (w_l1 + w_l2);
   out.p1_time = w_p1_time;  out.p1_price = w_p1_price;
   out.p2_time = w_p2_time;  out.p2_price = w_p2_price;
   out.p3_time = w_p3_time;  out.p3_price = w_p3_price;
   out.p4_time = p4_time;    out.p4_price = p4_close;
   out.p5_time = p5_time;    out.p5_price = p5_price;
   out.break_kind = break_kind;

   //--- lifecycle defaults (BrcLifecycle overwrites) -----------------
   out.t1_time = 0;  out.t2_time = 0;  out.t3_time = 0;
   out.invalidation_time = 0;
   out.alive = true;  out.continued = false;
   out.mfe_r = 0.0;  out.mae_r = 0.0;  out.realized_r = 0.0;
   out.bars_alive = 0;
   out.entry = w_l1;  out.r_unit = MathAbs(w_l1 - w_l2);  out.entered = false;
   return true;
  }

#endif // BRC_ZONES_MQH
