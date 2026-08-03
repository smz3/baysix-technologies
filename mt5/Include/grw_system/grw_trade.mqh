//+------------------------------------------------------------------+
//|                                                      grw_trade.mqh |
//|  GRW-001 — order placement. Market entry, structural stop, and the |
//|  TP attached only when the exit type actually wants one.           |
//|                                                                     |
//|  The stop is RE-ANCHORED to the live fill price at identical |risk|:|
//|  the signal's stop came off a CLOSED bar, and price has moved since.|
//|  Keeping the raw level would let 1R drift with slippage, so the     |
//|  risk distance measured at signal time is preserved and the stop is |
//|  placed that far from where we actually got in. R then means one    |
//|  thing across every trade in the ledger.                            |
//+------------------------------------------------------------------+
#ifndef GRW_TRADE_MQH
#define GRW_TRADE_MQH
#property strict

#include "grw_types.mqh"
#include "grw_sizing.mqh"
#include "grw_exit.mqh"

ENUM_ORDER_TYPE_FILLING GrwFilling()
  {
   long mode = (long)SymbolInfoInteger(_Symbol, SYMBOL_FILLING_MODE);
   if((mode & SYMBOL_FILLING_FOK) != 0) return ORDER_FILLING_FOK;
   if((mode & SYMBOL_FILLING_IOC) != 0) return ORDER_FILLING_IOC;
   return ORDER_FILLING_RETURN;
  }

//+------------------------------------------------------------------+
//| Send one market order for `s`, sized by the equity fraction.      |
//| Returns the POSITION_ID (0 on any refusal) and registers the      |
//| position in the exit book with its 1R frozen.                     |
//+------------------------------------------------------------------+
long GrwOpenMarket(const GrwCfg &c, const GrwSignal &s, const GRW_UNDERSIZE under,
                   GrwStats &st, double &out_lots, double &out_risk_pct)
  {
   out_lots = 0.0;  out_risk_pct = 0.0;
   if(!s.valid) return 0;

   //--- risk as measured at SIGNAL time — this is the 1R denominator, frozen from here on.
   double risk = MathAbs(s.entry - s.sl);
   if(risk <= 0.0) { st.n_skipped++; return 0; }

   double minstop = GrwStopsLevel();
   if(risk < minstop) { st.n_skipped++; return 0; }      // bracket tighter than the broker allows

   double lots = GrwSizeLots(risk, c.risk_frac, under, st, out_risk_pct);
   if(lots <= 0.0) return 0;                             // GrwSizeLots already counted the skip

   //--- re-anchor to the live fill side, preserving |risk|.
   double entry = s.is_long ? SymbolInfoDouble(_Symbol, SYMBOL_ASK)
                            : SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double sl    = s.is_long ? entry - risk : entry + risk;

   //--- FIXED_RR is the only branch with a broker-side target. The managed exits must NOT
   //--- carry a TP: a fixed TP truncates exactly the right tail they exist to capture
   //--- ([[fob_tail_carried_no_early_exit]]).
   double tp = 0.0;
   if(c.exit_type == GRW_X_FIXED_RR)
     {
      if(risk * c.rr < minstop) { st.n_skipped++; return 0; }
      tp = s.is_long ? entry + risk * c.rr : entry - risk * c.rr;
     }

   MqlTradeRequest req;  MqlTradeResult res;
   ZeroMemory(req);  ZeroMemory(res);
   req.action       = TRADE_ACTION_DEAL;
   req.symbol       = _Symbol;
   req.magic        = c.magic;
   req.type         = s.is_long ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   req.volume       = lots;
   req.price        = NormalizeDouble(entry, _Digits);
   req.sl           = NormalizeDouble(sl, _Digits);
   req.tp           = NormalizeDouble(tp, _Digits);
   req.deviation    = 50;
   req.type_filling = GrwFilling();
   if(!OrderSend(req, res)) { st.n_skipped++; return 0; }
   if(res.retcode != TRADE_RETCODE_DONE && res.retcode != TRADE_RETCODE_PLACED)
     { st.n_skipped++; return 0; }

   //--- HEDGING-safe id: read POSITION_ID off the entry deal, never PositionSelect(_Symbol).
   long pos_id = (long)res.order;
   if(res.deal > 0 && HistorySelect(0, TimeCurrent()) && HistoryDealSelect(res.deal))
      pos_id = (long)HistoryDealGetInteger(res.deal, DEAL_POSITION_ID);

   GrwOpen o;
   o.pos_id    = pos_id;
   o.is_long   = s.is_long;
   o.entry     = entry;
   o.sl0       = sl;
   o.risk      = risk;
   o.lots      = lots;
   o.atr0      = s.atr;
   o.opened_at = TimeCurrent();
   o.bars_held = 0;
   o.armed     = false;
   o.tag       = s.tag;
   GrwOpenAdd(o);

   st.n_orders++;
   out_lots = lots;
   return pos_id;
  }

//+------------------------------------------------------------------+
//| How many positions this EA currently holds (by magic).            |
//+------------------------------------------------------------------+
int GrwCountOpen(const ulong magic)
  {
   int n = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) == _Symbol
         && (ulong)PositionGetInteger(POSITION_MAGIC) == magic)
         n++;
     }
   return n;
  }

#endif // GRW_TRADE_MQH
