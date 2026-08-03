//+------------------------------------------------------------------+
//|                                                     grw_filter.mqh |
//|  GRW-001 — the InpFilterMask gates.                                 |
//|                                                                     |
//|  Every selected bit must pass (AND). There is deliberately no OR    |
//|  mode: "A or B" is a DIFFERENT hypothesis about why the edge exists |
//|  and therefore belongs in its own pre-registered config, not in a   |
//|  runtime switch that makes two batches look like one.               |
//|                                                                     |
//|  A filter is a SELECTION claim — "the edge lives here and not       |
//|  there" — so each one is a testable statement on its own, and       |
//|  mask=0 (take everything) is the baseline every mask must beat.     |
//|                                                                     |
//|  All gates read the SIGNAL's own bar (shift 1) or live broker       |
//|  state at decision time. Nothing here may look forward.             |
//+------------------------------------------------------------------+
#ifndef GRW_FILTER_MQH
#define GRW_FILTER_MQH
#property strict

#include "grw_types.mqh"

//+------------------------------------------------------------------+
//| Broker-hour window, INCLUSIVE both ends. start > end wraps past    |
//| midnight (e.g. 22..3 = the Asia/rollover block).                   |
//+------------------------------------------------------------------+
bool GrwInHourWindow(const int hr, const int start, const int end)
  {
   if(start <= end) return (hr >= start && hr <= end);
   return (hr >= start || hr <= end);               // wrapped
  }

//+------------------------------------------------------------------+
//| Apply the mask. `why` receives the FIRST failing gate so a         |
//| rejected signal can be counted by reason instead of vanishing.     |
//+------------------------------------------------------------------+
bool GrwFilterPass(const GrwCfg &c, const GrwCtx &ctx, const GrwSignal &s, string &why)
  {
   why = "";
   if(c.filter_mask == 0)
      return true;                                  // baseline: take everything

   MqlDateTime dt;
   TimeToStruct(iTime(_Symbol, c.tf, 1), dt);        // the SIGNAL's own hour, not "now"

   //--- SESSION: participation regime. The flow that drives the mechanism has hours.
   if((c.filter_mask & GRW_F_SESSION) != 0)
      if(!GrwInHourWindow(dt.hour, c.sess_start, c.sess_end))
        { why = "SESSION"; return false; }

   //--- NO_ROLLOVER: spread blows out at the daily roll, so fills there are not
   //--- representative of anything the strategy could actually get.
   if((c.filter_mask & GRW_F_NO_ROLLOVER) != 0)
      if(dt.hour == c.rollover_hr)
        { why = "ROLLOVER"; return false; }

   //--- TREND_HTF: agree with the higher-TF anchor slope. Not a forecast — a refusal to
   //--- take the side dominant flow is leaning against.
   if((c.filter_mask & GRW_F_TREND_HTF) != 0)
     {
      double h1, h2;
      if(!GrwBuf(ctx.h_htf, 1, h1) || !GrwBuf(ctx.h_htf, 1 + c.lookback, h2))
        { why = "TREND_HTF_NODATA"; return false; }
      bool htf_up = (h1 > h2);
      if(s.is_long != htf_up)
        { why = "TREND_HTF"; return false; }
     }

   //--- VOL_FLOOR: a move must be big enough that the edge is not the same size as the
   //--- spread. This is the volatility half of the cost argument.
   if((c.filter_mask & GRW_F_VOL_FLOOR) != 0)
     {
      double pt = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
      if(pt <= 0.0 || (s.atr / pt) < c.vol_floor_pts)
        { why = "VOL_FLOOR"; return false; }
     }

   //--- COST_RATIO: require the stop distance to be a multiple of the LIVE spread. The
   //--- only structural escape from transaction cost is a payoff materially bigger than
   //--- it (CLAUDE.md rule 16) — this gate makes that requirement explicit and testable
   //--- instead of leaving it to be discovered at G2.
   if((c.filter_mask & GRW_F_COST_RATIO) != 0)
     {
      double sp   = GrwSpread();
      double risk = MathAbs(s.entry - s.sl);
      if(sp <= 0.0 || risk < c.cost_mult * sp)
        { why = "COST_RATIO"; return false; }
     }

   return true;
  }

#endif // GRW_FILTER_MQH
