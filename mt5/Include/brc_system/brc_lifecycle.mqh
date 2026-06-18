//+------------------------------------------------------------------+
//|                                                 brc_lifecycle.mqh  |
//|  Per-zone lifecycle tracking — port of lifecycle.py + retest.py +  |
//|  continuation.py, folded into ONE incremental per-bar advance.    |
//|                                                                    |
//|  A zone is born at P4 and is advanced one bar at a time on every   |
//|  TF bar STRICTLY AFTER P4 (P4 closes beyond P5 — more extreme than |
//|  L1 but inside L2 — so it can never self-invalidate; the forward   |
//|  walk starts on the next bar). Three things are tracked:           |
//|                                                                    |
//|   1. INVALIDATION (close-only, lifecycle.py): first bar whose      |
//|      CLOSE breaks beyond L2 in the anti-break direction kills the  |
//|      zone. level = MAX(L1,L2) SELL / MIN(L1,L2) BUY (== L2 under   |
//|      the P3<P1 gate; EA MAX/MIN form kept for robustness).         |
//|                                                                    |
//|   2. RETEST LADDER (wick, retest.py): T1=L1, T2=mid, T3=L2; first  |
//|      intrabar touch of each. SELL touched when high>=level, BUY    |
//|      when low<=level. Recorded on EVERY post-P4 bar INCLUDING the  |
//|      death bar (B2B parity: B2BZoneStatus stamps touches BEFORE    |
//|      invalidation — a close-through of L2 legitimately sets T3).   |
//|                                                                    |
//|   3. CONTINUATION (continuation.py), anchored on the L1 retest     |
//|      ENTRY (T1 touch). entry = L1, R = |L1-L2|.  MFE/MAE use bar   |
//|      extremes over [entry .. death] INCLUSIVE of the death bar;    |
//|      `continued` = a bar CLOSED >= +1R in the break direction      |
//|      before invalidation; realized_r = unmanaged hold (stop L2, no |
//|      TP) signed entry->exit close, exit on death or at data-end    |
//|      (a still-alive entered zone keeps tracking the latest close). |
//|                                                                    |
//|  ⚠️ Death bar is INCLUDED in retest + excursion/realized; only     |
//|  `continued` excludes it (closed +1R must precede invalidation).   |
//+------------------------------------------------------------------+
#ifndef BRC_LIFECYCLE_MQH
#define BRC_LIFECYCLE_MQH
#property strict

#include "brc_types.mqh"
#include "brc_zones.mqh"     // BrcExtreme

//+------------------------------------------------------------------+
//| Advance ONE alive zone by a single post-P4 bar (time bt, OHLC).   |
//| No-op if the zone is already dead. The caller must invoke this    |
//| only for bars STRICTLY AFTER the zone's P4 bar.                   |
//+------------------------------------------------------------------+
void BrcAdvanceZone(BrcZone &z, const datetime bt,
                    const double h, const double l, const double cl)
  {
   if(!z.alive)
      return;

   bool   sell  = (z.direction == BRC_BEAR);
   double level = BrcExtreme(z.l1, z.l2, sell);          // invalidation level (== L2)
   bool   dead  = sell ? (cl > level) : (cl < level);    // close-only

   //--- 2. retest ladder (wick) — recorded on EVERY post-P4 bar INCLUDING the
   //    death bar (B2B parity: B2BZoneStatus records touches FIRST, then checks
   //    invalidation, so a close-through of L2 legitimately stamps T3 — the wick
   //    did cross it — exactly as the live Sigma EA does). A T1 touch arms the
   //    entry on THIS bar, so the excursion below already counts it.
   double probe = sell ? h : l;
   if(z.t1_time == 0 && (sell ? (probe >= z.l1)  : (probe <= z.l1)))
     { z.t1_time = bt; z.entered = true; }            // L1 retest = the entry
   if(z.t2_time == 0 && (sell ? (probe >= z.mid) : (probe <= z.mid)))
      z.t2_time = bt;
   if(z.t3_time == 0 && (sell ? (probe >= z.l2)  : (probe <= z.l2)))
      z.t3_time = bt;

   //--- 3. continuation (only after the L1 entry has fired). MFE/MAE include the
   //    death bar; realized_r tracks the latest close (frozen at the death close
   //    once dead, since the zone stops advancing); `continued` excludes the
   //    death bar (closed +1R BEFORE invalidation).
   if(z.entered)
     {
      double R = z.r_unit;
      if(R > 0.0)
        {
         double fav = sell ? (z.entry - l) : (h - z.entry);   // favourable extreme
         double adv = sell ? (h - z.entry) : (z.entry - l);   // adverse extreme
         if(fav / R > z.mfe_r) z.mfe_r = fav / R;
         if(adv / R > z.mae_r) z.mae_r = adv / R;
         z.realized_r = sell ? (z.entry - cl) / R : (cl - z.entry) / R;
         if(!dead)
           {
            bool reached_R = sell ? (cl <= z.entry - R) : (cl >= z.entry + R);
            if(reached_R) z.continued = true;
           }
        }
     }

   //--- 1. invalidation / bars_alive. bars_alive = post-P4 bars BEFORE the death
   //    bar (or all post-P4 bars if still alive at data-end), matching
   //    lifecycle.py ZoneLife.bars_alive (the 0-based index of the death bar).
   if(dead)
     {
      z.alive = false;
      z.invalidation_time = bt;
     }
   else
      z.bars_alive++;
  }

//+------------------------------------------------------------------+
//| Live INTRABAR touch pass — mirror of B2B's per-tick touch detect  |
//| (B2BZoneStatus.UpdateZoneStatusInBuffer). Stamps t1/t2/t3 off the |
//| FORMING bar's running high/low (h,l) so the [Tn] label flips the  |
//| instant price wicks a level, instead of waiting for the bar close.|
//|                                                                    |
//| Touch-ONLY: invalidation, bars_alive and `continued` stay         |
//| CLOSE-only (BrcAdvanceZone owns them) — a forming-bar wick must    |
//| never kill a zone. Data-neutral for the CSV ledger: the forming   |
//| bar's high/low only grow, so a level a wick crosses is also        |
//| crossed by that same bar's CLOSED extremes — the touch lands on    |
//| the SAME bar (same `bt`) either way; we just stamp it earlier.     |
//| A T1 touch arms the entry (z.entered) exactly as BrcAdvanceZone    |
//| does, so the close-only excursion stays consistent. Returns true   |
//| if any touch time was newly stamped (caller redraws the visual).   |
//+------------------------------------------------------------------+
bool BrcLiveTouch(BrcZone &z, const datetime bt, const double h, const double l)
  {
   if(!z.alive)
      return false;

   bool   sell  = (z.direction == BRC_BEAR);
   double probe = sell ? h : l;
   bool   hit   = false;

   if(z.t1_time == 0 && (sell ? (probe >= z.l1)  : (probe <= z.l1)))
     { z.t1_time = bt; z.entered = true; hit = true; }   // L1 retest = the entry
   if(z.t2_time == 0 && (sell ? (probe >= z.mid) : (probe <= z.mid)))
     { z.t2_time = bt; hit = true; }
   if(z.t3_time == 0 && (sell ? (probe >= z.l2)  : (probe <= z.l2)))
     { z.t3_time = bt; hit = true; }

   return hit;
  }

#endif // BRC_LIFECYCLE_MQH
