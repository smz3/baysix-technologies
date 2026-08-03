//+------------------------------------------------------------------+
//|                                                      grw_entry.mqh |
//|  GRW-001 — the four ENTRY primitives (InpEntryType dispatch).       |
//|                                                                     |
//|  All detection is CLOSE-ONLY on the signal TF and reads bar shift   |
//|  1 (the last CLOSED bar) or older. Never shift 0. A forming bar is  |
//|  not information yet, and reading it is how a backtest quietly      |
//|  acquires look-ahead — the ORB family died of exactly that          |
//|  ([[orb_unsorted_tick_lookahead]]).                                 |
//|                                                                     |
//|  Every stop here is STRUCTURAL: it comes from the level whose       |
//|  violation falsifies the mechanism, offset by sl_buf_k * ATR. Risk  |
//|  is then measured off that stop. It is never chosen to make an      |
//|  R-multiple look good — a tighter stop inflates E[R] while shrinking|
//|  dollars ([[er_denominator_illusion]]).                             |
//+------------------------------------------------------------------+
#ifndef GRW_ENTRY_MQH
#define GRW_ENTRY_MQH
#property strict

#include "grw_types.mqh"

//+------------------------------------------------------------------+
//| Armed-break state for GRW_E_BREAK_RETEST. A break arms a level;    |
//| the entry fires later, on the first retouch, or the arm expires.   |
//| Module-level (one strategy instance per chart) and RESET IN OnInit |
//| by the EA — MT5 globals survive a recompile/period switch and a    |
//| stale arm would fire a phantom entry ([[mt5_oninit_full_reset]]).  |
//+------------------------------------------------------------------+
struct GrwArm
  {
   bool     active;
   bool     is_long;
   double   level;      // the broken Donchian edge = the retest price
   datetime armed_at;
   int      bars_left;
  };
GrwArm g_grw_arm;

void GrwEntryReset()
  {
   g_grw_arm.active    = false;
   g_grw_arm.is_long   = false;
   g_grw_arm.level     = 0.0;
   g_grw_arm.armed_at  = 0;
   g_grw_arm.bars_left = 0;
  }

//+------------------------------------------------------------------+
//| Age the armed break. Called on EVERY new signal-TF bar, before    |
//| any max-open or filter gate.                                      |
//|                                                                    |
//| It has to live outside the entry evaluation: while a position is  |
//| open the EA does not evaluate entries at all, so an arm aged only |
//| inside GrwEntryBreakRetest would FREEZE for the life of the trade |
//| and then fire on a level that is hours or days stale. The retest  |
//| window is wall-clock bars since the break, not bars in which we   |
//| happened to be looking.                                           |
//+------------------------------------------------------------------+
void GrwEntryOnNewBar()
  {
   if(!g_grw_arm.active) return;
   g_grw_arm.bars_left--;
   if(g_grw_arm.bars_left <= 0)
      GrwEntryReset();
  }

//+------------------------------------------------------------------+
//| Donchian edges over `n` bars ENDING AT shift 2, i.e. the range as  |
//| it stood BEFORE the bar we are judging. Including bar 1 in its own |
//| range makes a break arithmetically impossible.                    |
//+------------------------------------------------------------------+
bool GrwDonchian(const ENUM_TIMEFRAMES tf, const int n, double &up, double &dn)
  {
   if(n < 2) return false;
   int ih = iHighest(_Symbol, tf, MODE_HIGH, n, 2);
   int il = iLowest(_Symbol, tf, MODE_LOW,  n, 2);
   if(ih < 0 || il < 0) return false;
   up = iHigh(_Symbol, tf, ih);
   dn = iLow(_Symbol, tf, il);
   return (up > 0.0 && dn > 0.0);
  }

//+------------------------------------------------------------------+
//| 1 — DONCHIAN BREAK. Close beyond the prior N-bar extreme.          |
//| MECHANISM: stops rest just past a well-observed edge; tripping     |
//| them forces a short-horizon cascade in the break direction.        |
//| Invalidation = closing back inside the range, so the stop sits a   |
//| buffer beyond the broken edge.                                     |
//+------------------------------------------------------------------+
void GrwEntryDonchian(const GrwCfg &c, const double atr, GrwSignal &s)
  {
   double up, dn;
   if(!GrwDonchian(c.tf, c.lookback, up, dn)) return;
   double cl = iClose(_Symbol, c.tf, 1);
   double buf = c.sl_buf_k * atr;

   if(cl > up)
     {
      s.valid = true;  s.is_long = true;
      s.entry = cl;    s.sl = up - buf;
      s.tag   = "DON_BRK_UP";
     }
   else if(cl < dn)
     {
      s.valid = true;  s.is_long = false;
      s.entry = cl;    s.sl = dn + buf;
      s.tag   = "DON_BRK_DN";
     }
  }

//+------------------------------------------------------------------+
//| 2 — BREAK then RETEST. The break ARMS a level; the entry fires on  |
//| the first bar that trades back to it, within retest_bars.          |
//| MECHANISM: same cascade thesis as (1), but filled against passive  |
//| liquidity at the reclaimed level, which cuts adverse excursion.    |
//| A retest that never comes is a MISSED trade, deliberately — that   |
//| is the real cost of the mechanic and the tester must pay it.       |
//+------------------------------------------------------------------+
void GrwEntryBreakRetest(const GrwCfg &c, const double atr, GrwSignal &s)
  {
   double up, dn;
   if(!GrwDonchian(c.tf, c.lookback, up, dn)) return;
   double cl  = iClose(_Symbol, c.tf, 1);
   double hi  = iHigh(_Symbol, c.tf, 1);
   double lo  = iLow(_Symbol, c.tf, 1);
   double buf = c.sl_buf_k * atr;

   //--- fire first: an armed level that price has just come back to. Ageing/expiry is
   //--- handled by GrwEntryOnNewBar(), which runs on every bar whether or not we are
   //--- in a position — so an arm cannot outlive its window by sitting out a trade.
   if(g_grw_arm.active)
     {
      bool touched = g_grw_arm.is_long ? (lo <= g_grw_arm.level) : (hi >= g_grw_arm.level);
      if(touched)
        {
         s.valid   = true;
         s.is_long = g_grw_arm.is_long;
         s.entry   = g_grw_arm.level;
         s.sl      = g_grw_arm.is_long ? g_grw_arm.level - buf : g_grw_arm.level + buf;
         s.tag     = g_grw_arm.is_long ? "RETEST_UP" : "RETEST_DN";
         GrwEntryReset();
         return;
        }
     }

   //--- then arm on a fresh break. Re-arming replaces the old level: the newest
   //--- break is the one price is actually reacting to.
   if(cl > up)
     {
      g_grw_arm.active    = true;  g_grw_arm.is_long = true;
      g_grw_arm.level     = up;    g_grw_arm.armed_at = iTime(_Symbol, c.tf, 1);
      g_grw_arm.bars_left = c.retest_bars;
     }
   else if(cl < dn)
     {
      g_grw_arm.active    = true;  g_grw_arm.is_long = false;
      g_grw_arm.level     = dn;    g_grw_arm.armed_at = iTime(_Symbol, c.tf, 1);
      g_grw_arm.bars_left = c.retest_bars;
     }
  }

//+------------------------------------------------------------------+
//| 3 — ATR REVERSION. Fade a close ext_k ATRs away from the anchor.   |
//| MECHANISM: liquidity vacuum — whoever absorbed the impulse is left |
//| holding unwanted inventory and works it back toward the anchor.    |
//| Invalidation = the impulse simply continues, so the stop sits      |
//| beyond the extreme of the bar that made it.                        |
//+------------------------------------------------------------------+
void GrwEntryAtrReversion(const GrwCfg &c, const GrwCtx &ctx, const double atr, GrwSignal &s)
  {
   double anchor;
   if(!GrwBuf(ctx.h_anchor, 1, anchor) || anchor <= 0.0 || atr <= 0.0) return;
   double cl  = iClose(_Symbol, c.tf, 1);
   double hi  = iHigh(_Symbol, c.tf, 1);
   double lo  = iLow(_Symbol, c.tf, 1);
   double ext = (cl - anchor) / atr;
   double buf = c.sl_buf_k * atr;

   if(ext >= c.ext_k)                       // stretched UP -> fade SHORT
     {
      s.valid = true;  s.is_long = false;
      s.entry = cl;    s.sl = hi + buf;
      s.tag   = "REV_FADE_DN";
     }
   else if(ext <= -c.ext_k)                 // stretched DOWN -> fade LONG
     {
      s.valid = true;  s.is_long = true;
      s.entry = cl;    s.sl = lo - buf;
      s.tag   = "REV_FADE_UP";
     }
  }

//+------------------------------------------------------------------+
//| 4 — MOMENTUM PULLBACK. In an established trend, enter when a       |
//| pullback touches the anchor and the bar closes back on the trend   |
//| side. MECHANISM: large orders are worked in slices (VWAP/TWAP);    |
//| execution resumes after each pullback, so the anchor keeps getting |
//| defended. Invalidation = the pullback bar's own extreme giving way.|
//+------------------------------------------------------------------+
void GrwEntryMomoPullback(const GrwCfg &c, const GrwCtx &ctx, const double atr, GrwSignal &s)
  {
   double a1, a2;
   if(!GrwBuf(ctx.h_anchor, 1, a1)) return;
   if(!GrwBuf(ctx.h_anchor, 1 + c.lookback, a2)) return;
   if(a1 <= 0.0 || a2 <= 0.0) return;

   double cl  = iClose(_Symbol, c.tf, 1);
   double hi  = iHigh(_Symbol, c.tf, 1);
   double lo  = iLow(_Symbol, c.tf, 1);
   double buf = c.sl_buf_k * atr;
   bool   up_trend = (a1 > a2);
   bool   dn_trend = (a1 < a2);

   if(up_trend && lo <= a1 && cl > a1)      // dipped to the anchor, closed above it
     {
      s.valid = true;  s.is_long = true;
      s.entry = cl;    s.sl = lo - buf;
      s.tag   = "MOMO_PB_UP";
     }
   else if(dn_trend && hi >= a1 && cl < a1)
     {
      s.valid = true;  s.is_long = false;
      s.entry = cl;    s.sl = hi + buf;
      s.tag   = "MOMO_PB_DN";
     }
  }

//+------------------------------------------------------------------+
//| Dispatch. Returns a cleared (invalid) signal when nothing fires.  |
//| ATR is read ONCE here and carried on the signal, so the filter,   |
//| the stop and the trail all reason about the same volatility.      |
//+------------------------------------------------------------------+
void GrwEntryEvaluate(const GrwCfg &c, const GrwCtx &ctx, GrwSignal &s)
  {
   GrwSignalClear(s);
   double atr;
   if(!GrwBuf(ctx.h_atr, 1, atr) || atr <= 0.0)
      return;                                 // no volatility read -> no structural stop
   s.atr = atr;

   switch(c.entry_type)
     {
      case GRW_E_DONCHIAN_BREAK: GrwEntryDonchian(c, atr, s);              break;
      case GRW_E_BREAK_RETEST:   GrwEntryBreakRetest(c, atr, s);           break;
      case GRW_E_ATR_REVERSION:  GrwEntryAtrReversion(c, ctx, atr, s);     break;
      case GRW_E_MOMO_PULLBACK:  GrwEntryMomoPullback(c, ctx, atr, s);     break;
     }

   //--- a signal whose stop is on the wrong side of its own entry is a coding fault,
   //--- not a trade. Drop it loudly rather than sending a rejectable order.
   if(s.valid)
     {
      bool bad = s.is_long ? (s.sl >= s.entry) : (s.sl <= s.entry);
      if(bad)
        {
         PrintFormat("[GRW] BUG: %s produced sl=%.5f on the wrong side of entry=%.5f — dropped",
                     s.tag, s.sl, s.entry);
         GrwSignalClear(s);
        }
     }
  }

#endif // GRW_ENTRY_MQH
