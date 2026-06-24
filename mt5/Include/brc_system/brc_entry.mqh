//+------------------------------------------------------------------+
//|                                                    brc_entry.mqh   |
//|  BRC trader — ENTRY module (swappable strategy logic).            |
//|                                                                    |
//|  Turns an alive, post-P4 zone into a concrete entry PLAN: order    |
//|  type, entry price, stop price, risk unit. The host EA owns order  |
//|  sending + one-position state; this module owns ONLY the "what to  |
//|  enter and where" decision, so iterations swap modes here without  |
//|  touching the EA.                                                  |
//|                                                                    |
//|  Fills are LEVEL-BASED by design: entry is a pending LIMIT at the  |
//|  chosen zone level, so the fill price is the level itself — no     |
//|  intrabar guess, trustworthy under the Open-prices tester model    |
//|  (matches the emitter's close-only / open-prices doctrine).        |
//|                                                                    |
//|  IS-01 = BRC_ENTRY_L1 + BRC_CONTINUATION (buy the pullback to the  |
//|  near edge, in the break direction, stop at invalidation).         |
//+------------------------------------------------------------------+
#ifndef BRC_ENTRY_MQH
#define BRC_ENTRY_MQH
#property strict

#include "brc_types.mqh"

//--- pullback DEPTH into the zone the entry waits for (NOT repeated retests):
//    L1 = near edge (shallowest, full stop room) · MID = midpoint · L2 = far
//    edge (deepest, ~zero stop room). Deeper = better price, tighter R.
enum BRC_ENTRY_TOUCH
  {
   BRC_ENTRY_L1  = 0,   // IS-01
   BRC_ENTRY_MID = 1,   // H_alt-2 (task 132)
   BRC_ENTRY_L2  = 2    // H_alt-2 (task 132)
  };

//--- which side of the level to take.
enum BRC_ENTRY_SIDE
  {
   BRC_CONTINUATION = 0,   // IS-01: trade WITH the break (buy pullback / sell rally)
   BRC_FADE         = 1    // H_alt-1 (task 131) — NOT yet specified, EA rejects
  };

//--- which ZONE FEEDS the entry plan (the IS-03 build, task 146).
//    SINGLE      : IS-01 — trade the chart-TF (H1) zone directly.
//    M15_CONFIRM : IS-03 — a retested H1 zone must be confirmed by a FRESH same-dir
//                  M15 BRC (M15.confirm > H1.t1); the entry plan is built on that M15
//                  zone (limit M15.l1 / stop M15.l2+buf), validity = parent H1 alive.
enum BRC_ENTRY_MODE
  {
   BRC_MODE_SINGLE      = 0,   // IS-01
   BRC_MODE_M15_CONFIRM = 1    // IS-03 (task 146)
  };

//+------------------------------------------------------------------+
//| A concrete, send-ready entry plan for one zone.                  |
//+------------------------------------------------------------------+
struct BrcEntryPlan
  {
   bool             valid;       // false -> do not trade this zone (reason set)
   ENUM_ORDER_TYPE  type;        // ORDER_TYPE_BUY_LIMIT / ORDER_TYPE_SELL_LIMIT
   double           entry;       // pending limit price (the chosen zone level)
   double           sl;          // stop price = invalidation level (L2)
   double           r_unit;      // |entry - sl| (the realised risk for THIS entry)
   string           reason;      // human note when !valid
  };

//+------------------------------------------------------------------+
//| Pick the entry level for the chosen pullback depth.              |
//+------------------------------------------------------------------+
double BrcEntryLevelFor(const BrcZone &z, const BRC_ENTRY_TOUCH touch)
  {
   switch(touch)
     {
      case BRC_ENTRY_MID: return z.mid;
      case BRC_ENTRY_L2:  return z.l2;
      default:            return z.l1;   // BRC_ENTRY_L1
     }
  }

//+------------------------------------------------------------------+
//| Build the entry plan. Continuation only for now; fade is a        |
//| declared-but-unspecified mode (task 131) and returns !valid so we |
//| never silently invent its stop structure.                         |
//+------------------------------------------------------------------+
BrcEntryPlan BrcBuildEntryPlan(const BrcZone &z,
                               const BRC_ENTRY_TOUCH touch,
                               const BRC_ENTRY_SIDE  side,
                               const double          sl_buffer_k)
  {
   BrcEntryPlan p;
   p.valid  = false;
   p.type   = ORDER_TYPE_BUY_LIMIT;
   p.entry  = 0.0;
   p.sl     = 0.0;
   p.r_unit = 0.0;
   p.reason = "";

   if(side == BRC_FADE)
     {
      p.reason = "fade mode not yet specified (task 131)";
      return p;
     }

   bool   bull  = (z.direction == BRC_BULL);   // broke UP -> buy the pullback
   double entry = BrcEntryLevelFor(z, touch);
   //--- stop = invalidation edge (L2) pushed a buffer BEYOND it, away from entry,
   //    scaled by zone width. k=0 reproduces the legacy stop-on-L2. The buffer
   //    (a) gives noise/spread room before genuine invalidation and (b) makes the
   //    deep L2 entry (T3) non-degenerate (r_unit = k*width instead of 0).
   double w     = MathAbs(z.l1 - z.l2);
   double sl    = bull ? (z.l2 - sl_buffer_k * w)    // bull: L2 is the low edge -> stop below
                       : (z.l2 + sl_buffer_k * w);   // bear: L2 is the high edge -> stop above
   double r     = MathAbs(entry - sl);

   if(r <= 0.0)
     {
      p.reason = "degenerate R (entry == stop; need sl_buffer_k>0 for L2 entry)";
      return p;
     }

   // Continuation: price pulls back TO the level, so the entry is a LIMIT.
   // bull -> price comes down to entry -> BUY LIMIT (sl below at L2)
   // bear -> price comes up   to entry -> SELL LIMIT (sl above at L2)
   p.type   = bull ? ORDER_TYPE_BUY_LIMIT : ORDER_TYPE_SELL_LIMIT;
   p.entry  = entry;
   p.sl     = sl;
   p.r_unit = r;
   p.valid  = true;
   return p;
  }

#endif // BRC_ENTRY_MQH
