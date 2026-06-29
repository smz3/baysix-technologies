//+------------------------------------------------------------------+
//|                                                     fob_entry.mqh  |
//|  The SWAPPABLE entry module (trader-only). Market entry on a CF,   |
//|  anchored to the CF zone:                                          |
//|    entry = market (Ask/Bid)                                        |
//|    SL    = beyond the zone FAR edge (L2) by slBufferK * band,      |
//|            band = |L1-L2| (structural, scale-free; close beyond L2 |
//|            = breakout invalidated).                                |
//|    TP    = entry +/- risk * rMultTP                                |
//|                                                                    |
//|  Extracted from fob_trader 2026-06-29. MQL5 note: inputs can't be  |
//|  seen from an include, so slBufferK/rMultTP/magic are PARAMETERS.  |
//|  Logic is unchanged from the in-EA version.                        |
//+------------------------------------------------------------------+
#ifndef FOB_ENTRY_MQH
#define FOB_ENTRY_MQH
#property strict

#include "fob_types.mqh"

//+------------------------------------------------------------------+
//| Broker filling mode.                                             |
//+------------------------------------------------------------------+
ENUM_ORDER_TYPE_FILLING FobFilling()
  {
   long mode = (long)SymbolInfoInteger(_Symbol, SYMBOL_FILLING_MODE);
   if((mode & SYMBOL_FILLING_FOK) != 0) return ORDER_FILLING_FOK;
   if((mode & SYMBOL_FILLING_IOC) != 0) return ORDER_FILLING_IOC;
   return ORDER_FILLING_RETURN;
  }

//+------------------------------------------------------------------+
//| Market entry on a CF, anchored to the CF zone. Returns the new    |
//| position id (0 on failure); sets out_rw = risk. HEDGING-safe id   |
//| capture: read POSITION_ID off the entry deal so each concurrent   |
//| position is keyed uniquely.                                       |
//+------------------------------------------------------------------+
long FobOpenMarket(const FobEvent &e, const double lot, const double slBufferK,
                   const double rMultTP, const ulong magic, double &out_rw)
  {
   out_rw = 0.0;
   if(!e.zone.valid) return 0;                            // no measurable band -> no trade
   bool   is_long = (e.dir == FOB_BULL);
   double entry   = is_long ? SymbolInfoDouble(_Symbol, SYMBOL_ASK)
                            : SymbolInfoDouble(_Symbol, SYMBOL_BID);
   //--- SL = beyond the zone FAR edge (L2) by slBufferK * band height.
   double l1     = e.level;                               // broken swing (near edge)
   double l2     = e.zone.l2;                             // far/invalidation edge
   double band   = MathAbs(l1 - l2);                      // zone height (scale-free)
   double buffer = slBufferK * band;
   double sl     = is_long ? l2 - buffer : l2 + buffer;
   double risk   = MathAbs(entry - sl);
   if(risk <= 0.0)
      return 0;
   double minstop = (double)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL)
                    * SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   if(risk < minstop || risk * rMultTP < minstop)
      return 0;                                          // bracket too tight for the broker

   double tp = is_long ? entry + risk * rMultTP : entry - risk * rMultTP;

   MqlTradeRequest req;  MqlTradeResult res;
   ZeroMemory(req);  ZeroMemory(res);
   req.action       = TRADE_ACTION_DEAL;
   req.symbol       = _Symbol;
   req.magic        = magic;
   req.type         = is_long ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   req.volume       = lot;
   req.price        = NormalizeDouble(entry, _Digits);
   req.sl           = NormalizeDouble(sl, _Digits);
   req.tp           = NormalizeDouble(tp, _Digits);
   req.deviation    = 50;
   req.type_filling = FobFilling();
   if(!OrderSend(req, res))
      return 0;
   if(res.retcode != TRADE_RETCODE_DONE && res.retcode != TRADE_RETCODE_PLACED)
      return 0;

   out_rw = risk;
   //--- HEDGING: many positions share the symbol, so PositionSelect(_Symbol) is
   //--- ambiguous. The entry deal's POSITION_ID is the unique key for this fill.
   if(res.deal > 0 && HistorySelect(0, TimeCurrent()) && HistoryDealSelect(res.deal))
      return (long)HistoryDealGetInteger(res.deal, DEAL_POSITION_ID);
   return (long)res.order;
  }

#endif // FOB_ENTRY_MQH
