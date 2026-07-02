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
   z.rt1_time = 0; z.rt2_time = 0; z.rt3_time = 0;
   z.n_l1_touches = 0; z.n_mid_touches = 0; z.n_l2_touches = 0;
   z.bars_alive = 0;   z.vr_fresh = true;
   if(!z.valid)
     { z.alive = false; z.vr_fresh = false; return; }  // no zone -> no life (foolproof)

   bool   bull = (dir == FOB_BULL);
   double l2   = z.l2;                            // far / invalidation edge
   double mid  = (l1 + l2) * 0.5;
   z.mid       = mid;
   double bandLo = MathMin(l1, l2);               // [L1,L2] band for the vr_fresh test
   double bandHi = MathMax(l1, l2);

   bool invalidated = false;                      // RT phase begins after this
   bool in1 = false, in2 = false, in3 = false;    // rising-edge state for touch COUNTS

   for(int i = 0; i < nb; i++)
     {
      if(bt[i] <= brk)
         continue;                                // only bars after the break

      if(!invalidated)
        {
         z.bars_alive++;                          // this bar lived under the zone

         //--- retest ladder (wick) — stamped FIRST, so the death bar's wick can
         //--- still set T3 before invalidation kills the zone (BRC parity).
         double probe = bull ? bl[i] : bh[i];
         bool   h1 = bull ? (probe <= l1)  : (probe >= l1);
         bool   h2 = bull ? (probe <= mid) : (probe >= mid);
         bool   h3 = bull ? (probe <= l2)  : (probe >= l2);
         if(z.t1_time == 0 && h1) z.t1_time = bt[i];
         if(z.t2_time == 0 && h2) z.t2_time = bt[i];
         if(z.t3_time == 0 && h3) z.t3_time = bt[i];
         //--- COUNTS: rising-edge (one episode per distinct return to the level).
         if(h1 && !in1) z.n_l1_touches++;   in1 = h1;
         if(h2 && !in2) z.n_mid_touches++;  in2 = h2;
         if(h3 && !in3) z.n_l2_touches++;   in3 = h3;

         //--- vr_fresh: a CLOSE landing back inside the band = "structured", not fresh.
         if(z.vr_fresh && bc[i] >= bandLo && bc[i] <= bandHi) z.vr_fresh = false;

         //--- invalidation (close-only): close beyond L2 in the anti-break dir.
         bool dead = bull ? (bc[i] < l2) : (bc[i] > l2);
         if(dead)
           {
            z.alive = false; z.invalidation_time = bt[i];
            if(!track_rt) break;                  // CF/PBO: stop at death (old behaviour)
            invalidated = true;                   // VR: open the RT phase from next bar
           }
        }
      else
        {
         //--- RT MIRROR LADDER (VR-only): the VR broke through L2, so price RETURNS
         //--- and re-touches L2 -> mid -> L1 in mirror order/side of the T-ladder.
         //--- A bull VR broke DOWN, so the return is a wick back UP (probe = high);
         //--- a bear VR broke UP, so the return is a wick back DOWN (probe = low).
         //--- Stamp the FIRST bar to reach each level (first-touch times, no counts).
         if(bull)
           {
            if(z.rt1_time == 0 && bh[i] >= l2)  z.rt1_time = bt[i];
            if(z.rt2_time == 0 && bh[i] >= mid) z.rt2_time = bt[i];
            if(z.rt3_time == 0 && bh[i] >= l1)  z.rt3_time = bt[i];
           }
         else
           {
            if(z.rt1_time == 0 && bl[i] <= l2)  z.rt1_time = bt[i];
            if(z.rt2_time == 0 && bl[i] <= mid) z.rt2_time = bt[i];
            if(z.rt3_time == 0 && bl[i] <= l1)  z.rt3_time = bt[i];
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
                  const datetime bt, const double h, const double l,
                  const bool track_rt = false)
  {
   if(!z.valid || bt <= brk)
      return false;

   bool   bull = (dir == FOB_BULL);
   double l2   = z.l2;

   //--- RT live (VR-only): an INVALIDATED VR whose broken zone is re-touched by the
   //--- FORMING wick stamps the RT mirror ladder live, so [RTn] + the entry dots flip
   //--- intrabar exactly like [Tn]. Runs BEFORE the alive-guard (the zone is dead by
   //--- definition here). Mirror of the T-ladder on the RETURN path: bull returns UP
   //--- (probe = high) to L2 -> mid -> L1, bear returns DOWN (probe = low).
   if(track_rt && !z.alive)
     {
      double midRt = z.mid;
      double probe = bull ? h : l;
      bool   hit   = false;
      if(z.rt1_time == 0 && (bull ? (probe >= l2)   : (probe <= l2)))   { z.rt1_time = bt; hit = true; }
      if(z.rt2_time == 0 && (bull ? (probe >= midRt): (probe <= midRt))) { z.rt2_time = bt; hit = true; }
      if(z.rt3_time == 0 && (bull ? (probe >= l1)   : (probe <= l1)))   { z.rt3_time = bt; hit = true; }
      return hit;
     }

   if(!z.alive)
      return false;                               // dead non-RT zone -> no live touch

   double probe = bull ? l : h;                   // bull retests DOWN (low), bear UP (high)
   double mid   = z.mid;
   bool   hit   = false;

   if(z.t1_time == 0 && (bull ? (probe <= l1)  : (probe >= l1)))  { z.t1_time = bt; hit = true; }
   if(z.t2_time == 0 && (bull ? (probe <= mid) : (probe >= mid))) { z.t2_time = bt; hit = true; }
   if(z.t3_time == 0 && (bull ? (probe <= l2)  : (probe >= l2)))  { z.t3_time = bt; hit = true; }

   return hit;
  }

//+------------------------------------------------------------------+
//| TRUE-TICK ACCUMULATOR (v1.24.0, task 197) — the EMITTER's lifecycle |
//| source. Unlike FobReplayZoneLife (stateless, recomputed from CLOSED |
//| bars at OnDeinit and therefore blind to intra-bar ORDER), this is   |
//| STATEFUL and CAUSAL: the zone's touch ladder / counts / RT advance  |
//| tick-by-tick in true stream order, and invalidation / vr_fresh /    |
//| bars_alive advance on each CLOSED bar. Because MT5 reveals a closed  |
//| bar on the FIRST tick of the next bar, every tick of bar N is        |
//| processed by FobAccOnTick BEFORE bar N's close is judged by          |
//| FobAccOnClose — so "tapped the zone then broke it" vs "broke then    |
//| tapped" is recorded correctly, with no look-ahead.                  |
//|                                                                    |
//| Logic is the SAME geometry as FobReplayZoneLife (bull retests DOWN, |
//| bear UP; T1=L1,T2=mid,T3=L2 wick; counts = rising-edge episodes;    |
//| invalidation = CLOSE beyond L2; RT = mirror retouch ladder L2->mid  |
//| ->L1 on the return path) — only the CLOCK differs (live price/close |
//| instead of bar high/low). The per-zone hysteresis state that used   |
//| to be locals in the replay (in1/in2/in3, invalidated) now persists  |
//| in FobZoneAcc, held parallel to the event ledger.                  |
//+------------------------------------------------------------------+
struct FobZoneAcc
  {
   bool in1, in2, in3;     // rising-edge "currently inside the level" — distinct-touch counts
   bool invalidated;       // close has broken L2 -> RT phase (VR only); also true for invalid zones
  };

//+------------------------------------------------------------------+
//| Seed one zone's lifecycle + accumulator at the moment its event is |
//| appended. Resets the SAME fields FobReplayZoneLife reset (so a CSV  |
//| from the accumulator and one from the replay describe the same      |
//| schema), computes mid, and arms the hysteresis state. An invalid    |
//| zone is terminal (no life) — flagged invalidated so it is never     |
//| added to the live watch list.                                      |
//+------------------------------------------------------------------+
void FobAccInit(FobZone &z, FobZoneAcc &a, const int dir, const double l1)
  {
   z.t1_time = 0; z.t2_time = 0; z.t3_time = 0;
   z.alive = true; z.invalidation_time = 0;
   z.rt1_time = 0; z.rt2_time = 0; z.rt3_time = 0;
   z.n_l1_touches = 0; z.n_mid_touches = 0; z.n_l2_touches = 0;
   z.bars_alive = 0;   z.vr_fresh = true;
   a.in1 = false; a.in2 = false; a.in3 = false;
   a.invalidated = false;
   if(!z.valid)
     { z.alive = false; z.vr_fresh = false; a.invalidated = true; return; }  // no zone -> no life
   z.mid = (l1 + z.l2) * 0.5;
  }

//+------------------------------------------------------------------+
//| ONE tick against ONE watched zone. Pre-invalidation: advance the   |
//| touch ladder + distinct-touch counts off the live price `px`.       |
//| Post-invalidation (VR with track_rt): count distinct returns to the |
//| broken L2 edge. The caller must only feed ticks STRICTLY AFTER the  |
//| break bar (a zone enters the watch list when its break bar is        |
//| revealed closed, i.e. on the next bar's first tick) — so no break-   |
//| bar guard is needed here.                                          |
//+------------------------------------------------------------------+
void FobAccOnTick(FobZone &z, FobZoneAcc &a, const int dir, const double l1,
                  const double px, const datetime ttime, const bool track_rt)
  {
   if(!z.valid)
      return;
   bool   bull = (dir == FOB_BULL);
   double l2   = z.l2;
   double mid  = z.mid;

   if(!a.invalidated)
     {
      bool h1 = bull ? (px <= l1)  : (px >= l1);
      bool h2 = bull ? (px <= mid) : (px >= mid);
      bool h3 = bull ? (px <= l2)  : (px >= l2);
      if(z.t1_time == 0 && h1) z.t1_time = ttime;
      if(z.t2_time == 0 && h2) z.t2_time = ttime;
      if(z.t3_time == 0 && h3) z.t3_time = ttime;
      if(h1 && !a.in1) z.n_l1_touches++;   a.in1 = h1;
      if(h2 && !a.in2) z.n_mid_touches++;  a.in2 = h2;
      if(h3 && !a.in3) z.n_l2_touches++;   a.in3 = h3;
     }
   else if(track_rt)
     {
      //--- RT MIRROR LADDER (VR-only): the VR broke through L2, so price RETURNS and
      //--- re-touches L2 -> mid -> L1 in mirror order/side of the T-ladder. A bull VR
      //--- broke DOWN, so the return is a move back UP (px >= level); bear mirrors.
      //--- Stamp the FIRST tick that reaches each level off the live price.
      if(bull)
        {
         if(z.rt1_time == 0 && px >= l2)  z.rt1_time = ttime;
         if(z.rt2_time == 0 && px >= mid) z.rt2_time = ttime;
         if(z.rt3_time == 0 && px >= l1)  z.rt3_time = ttime;
        }
      else
        {
         if(z.rt1_time == 0 && px <= l2)  z.rt1_time = ttime;
         if(z.rt2_time == 0 && px <= mid) z.rt2_time = ttime;
         if(z.rt3_time == 0 && px <= l1)  z.rt3_time = ttime;
        }
     }
  }

//+------------------------------------------------------------------+
//| ONE newly-CLOSED event-TF bar against ONE watched zone. Advances   |
//| bars_alive, the vr_fresh flag (a close back inside [L1,L2] = the    |
//| zone "structured"), and invalidation (a close beyond L2 in the     |
//| anti-break direction). Returns TRUE when the zone is now dead AND   |
//| done (CF/PBO) so the caller drops it from the watch list; a VR      |
//| stays (returns FALSE) to keep counting RT on later ticks. Skips     |
//| the zone's own break bar (btime <= brk) — BRC parity.              |
//+------------------------------------------------------------------+
bool FobAccOnClose(FobZone &z, FobZoneAcc &a, const int dir, const double l1,
                   const datetime brk, const double bclose, const datetime btime,
                   const bool track_rt)
  {
   if(!z.valid)
      return true;                                 // terminal — should never be watched
   if(a.invalidated)
      return false;                                // VR already in RT phase — close path done
   if(btime <= brk)
      return false;                                // only bars STRICTLY after the break

   bool   bull   = (dir == FOB_BULL);
   double l2     = z.l2;
   double bandLo = MathMin(l1, l2);
   double bandHi = MathMax(l1, l2);

   z.bars_alive++;
   if(z.vr_fresh && bclose >= bandLo && bclose <= bandHi)
      z.vr_fresh = false;                          // a close re-entered the band -> "structured"

   bool dead = bull ? (bclose < l2) : (bclose > l2);
   if(dead)
     {
      z.alive = false; z.invalidation_time = btime;
      if(!track_rt)
         return true;                              // CF/PBO: stop here, drop from watch
      a.invalidated = true;                        // VR: open the RT phase from next tick
     }
   return false;
  }

//+------------------------------------------------------------------+
//| DRAW-TIME LADDER BACKFILL (v1.27.1, task 217) — LIVE chart only.   |
//| The causal tick accumulator (FobAcc*) is blind to pre-attach       |
//| history: on a fresh attach it never saw the ticks that touched a    |
//| historical zone, so [Tn] reads T0 even where price clearly swept    |
//| the band. This restores the pre-v1.24.0 behaviour (a bar-wick       |
//| replay backfilled the ladder) but NON-DESTRUCTIVELY: it only FILLS  |
//| a still-empty t1/t2/t3_time (never resets), and touches NOTHING     |
//| else — invalidation / RT ladder / vr_fresh / the distinct-touch     |
//| COUNTS all stay owned by the causal accumulator. So a zone that     |
//| formed live keeps its tick-accurate ladder; only genuinely-empty    |
//| (pre-attach) zones get bar-resolution first-touch times.            |
//|                                                                    |
//| Safe to run every redraw: returns instantly once all three are      |
//| stamped. Walks the CHART-TF bar buffer (bt/bh/bl, index 0 oldest,   |
//| length nb) STRICTLY AFTER the break. Because a close beyond L2 (the |
//| death) puts the whole bar past L1/mid/L2, the death bar's own wick  |
//| fills every remaining Tn — so no post-invalidation touch leaks in.  |
//+------------------------------------------------------------------+
void FobBackfillLadderTimes(FobZone &z, const int dir, const double l1, const datetime brk,
                            const datetime &bt[], const double &bh[], const double &bl[], const int nb)
  {
   if(!z.valid)
      return;
   if(z.t1_time != 0 && z.t2_time != 0 && z.t3_time != 0)
      return;                                       // already fully stamped (live or prior backfill)

   bool   bull = (dir == FOB_BULL);
   double l2   = z.l2;
   double mid  = z.mid;
   for(int i = 0; i < nb; i++)
     {
      if(bt[i] <= brk)
         continue;                                  // only bars strictly after the break
      double probe = bull ? bl[i] : bh[i];          // bull retests DOWN (low), bear UP (high)
      if(z.t1_time == 0 && (bull ? (probe <= l1)  : (probe >= l1)))  z.t1_time = bt[i];
      if(z.t2_time == 0 && (bull ? (probe <= mid) : (probe >= mid))) z.t2_time = bt[i];
      if(z.t3_time == 0 && (bull ? (probe <= l2)  : (probe >= l2)))  z.t3_time = bt[i];
      if(z.t1_time != 0 && z.t2_time != 0 && z.t3_time != 0)
         return;                                    // deepest touch reached -> done
     }
  }

//+------------------------------------------------------------------+
//| DRAW-TIME RT-LADDER BACKFILL (v1.29.0, task 219) — LIVE chart only. |
//| Sibling of FobBackfillLadderTimes for the RETURN path. A VR that    |
//| invalidated BEFORE attach has its RT phase opened by the close-path  |
//| replay (invalidation_time set), but the tick accumulator saw no      |
//| pre-attach ticks, so the mirror ladder rt1/rt2/rt3 stays empty ->    |
//| the zone reads [RT0] forever. This restores bar-resolution RT the    |
//| same NON-DESTRUCTIVE way the T backfill does: fills only a still-     |
//| empty rt1/rt2/rt3_time (never resets), touches NOTHING else.         |
//|                                                                    |
//| Mirror geometry: the VR broke THROUGH L2, so the return re-touches   |
//| L2 -> mid -> L1 on the opposite side of the T-ladder — a bull VR     |
//| broke DOWN so the return is a wick back UP (probe = high); bear      |
//| mirrors (probe = low). Walks the chart-TF bar buffer STRICTLY AFTER  |
//| invalidation_time (the RT phase start). No-op on a live/still-alive  |
//| zone (inval == 0) or one already fully stamped. Safe every redraw.   |
//+------------------------------------------------------------------+
void FobBackfillRtTimes(FobZone &z, const int dir, const double l1, const datetime inval,
                        const datetime &bt[], const double &bh[], const double &bl[], const int nb)
  {
   if(!z.valid || inval == 0)
      return;                                       // no zone / not invalidated -> no RT phase
   if(z.rt1_time != 0 && z.rt2_time != 0 && z.rt3_time != 0)
      return;                                       // already fully stamped (live or prior backfill)

   bool   bull = (dir == FOB_BULL);
   double l2   = z.l2;
   double mid  = z.mid;
   for(int i = 0; i < nb; i++)
     {
      if(bt[i] <= inval)
         continue;                                  // RT phase begins STRICTLY after invalidation
      double probe = bull ? bh[i] : bl[i];          // return path: bull back UP (high), bear DOWN (low)
      if(z.rt1_time == 0 && (bull ? (probe >= l2)  : (probe <= l2)))  z.rt1_time = bt[i];
      if(z.rt2_time == 0 && (bull ? (probe >= mid) : (probe <= mid))) z.rt2_time = bt[i];
      if(z.rt3_time == 0 && (bull ? (probe >= l1)  : (probe <= l1)))  z.rt3_time = bt[i];
      if(z.rt1_time != 0 && z.rt2_time != 0 && z.rt3_time != 0)
         return;                                    // full return reached -> done
     }
  }

#endif // FOB_LIFECYCLE_MQH
