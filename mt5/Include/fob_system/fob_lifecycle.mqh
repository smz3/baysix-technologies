//+------------------------------------------------------------------+
//|                                                 fob_lifecycle.mqh  |
//|  FOB zone lifecycle — BRC-parity retest ladder + invalidation,    |
//|  mirror of brc_lifecycle.mqh's BrcAdvanceZone, but STATELESS:      |
//|  recomputed from scratch each redraw by walking the event-TF bar   |
//|  buffer forward from the break bar. No persistent per-zone state — |
//|  the picture is a pure PROJECTION of (event log x bar buffer) and  |
//|  can never drift from the detector (the FOB visual contract).      |
//|                                                                    |
//|  Geometry (set by FobComputeBreakZone):                            |
//|    L1 = the broken swing price (= owning event's `level`, P2).     |
//|    L2 = extreme(P1,P3): MIN below for a bull break / MAX above for |
//|         a bear break — the far / invalidation edge.                |
//|    mid = (L1+L2)/2.                                                 |
//|  A bull break (broke a HIGH) zones the pullback BELOW: price comes  |
//|  DOWN to retest — touched when low <= level. Bear mirror (high>=).  |
//|                                                                    |
//|  Tracked over every event-TF bar STRICTLY AFTER the break bar:     |
//|    • RETEST LADDER (wick): T1=L1, T2=mid, T3=L2 — first intrabar    |
//|      touch of each. Stamped on EVERY post-break bar INCLUDING the   |
//|      death bar (BRC parity: a close-through of L2 legitimately sets |
//|      T3 — the wick did cross it).                                  |
//|    • INVALIDATION (close-only): first bar whose CLOSE breaks beyond |
//|      L2 in the anti-break direction kills the zone.                |
//+------------------------------------------------------------------+
#ifndef FOB_LIFECYCLE_MQH
#define FOB_LIFECYCLE_MQH
#property strict

#include "fob_types.mqh"

//+------------------------------------------------------------------+
//| Replay ONE zone's lifecycle over the event-TF OHLC buffer. Resets |
//| the touch ladder + alive/invalidation, then walks the bars        |
//| (bt/bh/bl/bc, index 0 = OLDEST, length nb) STRICTLY AFTER the      |
//| break bar `brk`. Idempotent: same inputs -> same stamps. Operates  |
//| on the FobZone + the owning break's (dir, L1, bar_time) so the     |
//| SAME stamped zone feeds both the dot label [Tn] and the geometry.  |
//| An invalid zone has no life (alive=false, no touches).            |
//+------------------------------------------------------------------+
void FobReplayZoneLife(FobZone &z, const int dir, const double l1, const datetime brk,
                       const datetime &bt[], const double &bh[],
                       const double &bl[], const double &bc[], const int nb,
                       const bool track_rt = false)
  {
   //--- reset lifecycle state (stateless recompute)
   z.t1_time = 0; z.t2_time = 0; z.t3_time = 0;
   z.alive = true; z.invalidation_time = 0;
   z.rt_count = 0; z.rt_time = 0;
   if(!z.valid)
     { z.alive = false; return; }                // no zone -> no life (foolproof)

   bool   bull = (dir == FOB_BULL);
   double l2   = z.l2;                            // far / invalidation edge
   double mid  = (l1 + l2) * 0.5;
   z.mid       = mid;

   bool invalidated = false;                      // RT phase begins after this
   bool armed       = false;                      // price currently on the broken side

   for(int i = 0; i < nb; i++)
     {
      if(bt[i] <= brk)
         continue;                                // only bars after the break

      if(!invalidated)
        {
         //--- retest ladder (wick) — stamped FIRST, so the death bar's wick can
         //--- still set T3 before invalidation kills the zone (BRC parity).
         double probe = bull ? bl[i] : bh[i];
         if(z.t1_time == 0 && (bull ? (probe <= l1)  : (probe >= l1)))  z.t1_time = bt[i];
         if(z.t2_time == 0 && (bull ? (probe <= mid) : (probe >= mid))) z.t2_time = bt[i];
         if(z.t3_time == 0 && (bull ? (probe <= l2)  : (probe >= l2)))  z.t3_time = bt[i];

         //--- invalidation (close-only): close beyond L2 in the anti-break dir.
         bool dead = bull ? (bc[i] < l2) : (bc[i] > l2);
         if(dead)
           {
            z.alive = false; z.invalidation_time = bt[i];
            if(!track_rt) break;                  // CF/PBO: stop at death (old behaviour)
            invalidated = true; armed = true;     // VR: open the RT phase from next bar
           }
        }
      else
        {
         //--- RT phase (VR-only): count DISTINCT returns to the broken L2 edge.
         //--- A bull VR broke DOWN through L2 -> a retouch is a wick back UP to L2
         //--- (high >= L2); bear VR mirrors (low <= L2). Hysteresis: price must
         //--- leave L2 (re-arm) before another return counts, so one slow retest
         //--- straddling L2 over several bars is ONE retouch, not many.
         if(bull)
           {
            if(armed && bh[i] >= l2) { z.rt_count++; if(z.rt_time == 0) z.rt_time = bt[i]; armed = false; }
            else if(bh[i] <  l2)       armed = true;
           }
         else
           {
            if(armed && bl[i] <= l2) { z.rt_count++; if(z.rt_time == 0) z.rt_time = bt[i]; armed = false; }
            else if(bl[i] >  l2)       armed = true;
           }
        }
     }
  }

//+------------------------------------------------------------------+
//| LIVE intrabar touch off the still-FORMING bar (mirror of           |
//| BrcLiveTouch). Stamps the FIRST wick cross of each ladder level so  |
//| the [Tn] label flips the instant price touches, not only at bar     |
//| close. TOUCH-ONLY — invalidation stays close-only on CLOSED bars    |
//| (don't let a forming-bar close kill a zone mid-bar). Idempotent:    |
//| only fills a still-empty Tn, on a bar STRICTLY AFTER the break.     |
//| Live-chart nicety; the CALLER must tester-guard it (per-tick        |
//| quadratic blow-up under a real-ticks model).                       |
//+------------------------------------------------------------------+
bool FobLiveTouch(FobZone &z, const int dir, const double l1, const datetime brk,
                  const datetime bt, const double h, const double l)
  {
   if(!z.valid || !z.alive || bt <= brk)
      return false;

   bool   bull  = (dir == FOB_BULL);
   double probe = bull ? l : h;                   // bull retests DOWN (low), bear UP (high)
   double mid   = z.mid;
   double l2    = z.l2;
   bool   hit   = false;

   if(z.t1_time == 0 && (bull ? (probe <= l1)  : (probe >= l1)))  { z.t1_time = bt; hit = true; }
   if(z.t2_time == 0 && (bull ? (probe <= mid) : (probe >= mid))) { z.t2_time = bt; hit = true; }
   if(z.t3_time == 0 && (bull ? (probe <= l2)  : (probe >= l2)))  { z.t3_time = bt; hit = true; }

   return hit;
  }

#endif // FOB_LIFECYCLE_MQH
