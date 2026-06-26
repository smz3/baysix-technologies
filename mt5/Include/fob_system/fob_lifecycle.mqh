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
                       const double &bl[], const double &bc[], const int nb)
  {
   //--- reset lifecycle state (stateless recompute)
   z.t1_time = 0; z.t2_time = 0; z.t3_time = 0;
   z.alive = true; z.invalidation_time = 0;
   if(!z.valid)
     { z.alive = false; return; }                // no zone -> no life (foolproof)

   bool   bull = (dir == FOB_BULL);
   double l2   = z.l2;                            // far / invalidation edge
   double mid  = (l1 + l2) * 0.5;
   z.mid       = mid;

   for(int i = 0; i < nb; i++)
     {
      if(bt[i] <= brk)
         continue;                                // only bars after the break

      //--- retest ladder (wick) — stamped FIRST, so the death bar's wick can
      //--- still set T3 before invalidation kills the zone (BRC parity).
      double probe = bull ? bl[i] : bh[i];
      if(z.t1_time == 0 && (bull ? (probe <= l1)  : (probe >= l1)))  z.t1_time = bt[i];
      if(z.t2_time == 0 && (bull ? (probe <= mid) : (probe >= mid))) z.t2_time = bt[i];
      if(z.t3_time == 0 && (bull ? (probe <= l2)  : (probe >= l2)))  z.t3_time = bt[i];

      //--- invalidation (close-only): close beyond L2 in the anti-break dir.
      bool dead = bull ? (bc[i] < l2) : (bc[i] > l2);
      if(dead)
        { z.alive = false; z.invalidation_time = bt[i]; break; }
     }
  }

#endif // FOB_LIFECYCLE_MQH
