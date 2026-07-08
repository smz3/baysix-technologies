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
                   const double rMultTP, const ulong magic, double &out_rw,
                   const bool no_tp = false)
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
   if(risk < minstop || (!no_tp && risk * rMultTP < minstop))
      return 0;                                          // bracket too tight for the broker

   //--- no_tp (trail-only): no fixed TP -> the trailing stop is the sole profit exit.
   double tp = no_tp ? 0.0 : (is_long ? entry + risk * rMultTP : entry - risk * rMultTP);

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

//+------------------------------------------------------------------+
//| CF_L1_LIMIT entry: a pending LIMIT at the CF zone's L1 (near edge  |
//| / T1) instead of market-on-confirm. Fills ONLY on a pullback to L1 |
//| -> premium price, tighter R. SL is IDENTICAL to the market path    |
//| (beyond L2 by slBufferK*band); TP = entry +/- risk*rMultTP with    |
//| entry = L1, so risk = |L1-SL| = band*(1+slBufferK). Returns the    |
//| PENDING ORDER ticket (0 on failure); out_rw = risk. Cancellation   |
//| of a runaway winner (never pulled back) is the caller's job on a    |
//| new setup-TF PBO. GTC -> no time expiry.                           |
//+------------------------------------------------------------------+
long FobPlaceLimit(const FobEvent &e, const double lot, const double slBufferK,
                   const double rMultTP, const ulong magic, double &out_rw,
                   const bool no_tp = false)
  {
   out_rw = 0.0;
   if(!e.zone.valid) return 0;                            // no measurable band -> no trade
   bool   is_long = (e.dir == FOB_BULL);
   double l1     = e.level;                               // near edge = the limit price (T1)
   double l2     = e.zone.l2;                             // far/invalidation edge
   double band   = MathAbs(l1 - l2);                      // zone height (scale-free)
   double buffer = slBufferK * band;
   double entry  = l1;
   double sl     = is_long ? l2 - buffer : l2 + buffer;
   double risk   = MathAbs(entry - sl);
   if(risk <= 0.0)
      return 0;

   //--- LIMIT-side validity: a BUY LIMIT must sit BELOW the Ask, a SELL LIMIT
   //--- ABOVE the Bid, and both at least STOPS_LEVEL away. A CF is a continuation
   //--- break so price sits BEYOND L1 already; skip the rare too-close case.
   double ask     = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid     = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double minstop = (double)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL)
                    * SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   if(is_long)  { if(entry >= ask - minstop) return 0; }
   else         { if(entry <= bid + minstop) return 0; }
   if(risk < minstop || (!no_tp && risk * rMultTP < minstop))
      return 0;                                          // bracket too tight for the broker

   //--- no_tp (trail-only): no fixed TP -> the trailing stop is the sole profit exit.
   double tp = no_tp ? 0.0 : (is_long ? entry + risk * rMultTP : entry - risk * rMultTP);

   MqlTradeRequest req;  MqlTradeResult res;
   ZeroMemory(req);  ZeroMemory(res);
   req.action       = TRADE_ACTION_PENDING;
   req.symbol       = _Symbol;
   req.magic        = magic;
   req.type         = is_long ? ORDER_TYPE_BUY_LIMIT : ORDER_TYPE_SELL_LIMIT;
   req.volume       = lot;
   req.price        = NormalizeDouble(entry, _Digits);
   req.sl           = NormalizeDouble(sl, _Digits);
   req.tp           = NormalizeDouble(tp, _Digits);
   req.type_time    = ORDER_TIME_GTC;                     // cancelled by a new setup-TF PBO, not time
   req.type_filling = FobFilling();
   if(!OrderSend(req, res))
      return 0;
   if(res.retcode != TRADE_RETCODE_DONE && res.retcode != TRADE_RETCODE_PLACED)
      return 0;

   out_rw = risk;
   return (long)res.order;                                // the pending order ticket
  }

//+------------------------------------------------------------------+
//| PBO_LIMIT entry (v1.34.0): a pending LIMIT into the PARENT PBO's   |
//| zone at a chosen depth, ARMED when the cycle's VR confirms (pre-CF |
//| — the pullback-then-continue thesis). Anchored to the PBO zone,    |
//| NOT the CF zone: T1 = L1 (near/trigger edge), T2 = mid, T3 = L2    |
//| (far). SL = beyond the PBO's L2 by slBufferK*band (band=|L1-L2|),  |
//| identical formula to the CF path but on the PBO geometry. Risk     |
//| SHRINKS as entry deepens (T1 = band*(1+k), T3 = buffer only) — so  |
//| rank the depth sweep on $/trade + survival, never R-multiple.      |
//| Fills ONLY on a pullback into the zone (BUY LIMIT below Ask / SELL |
//| LIMIT above Bid); a level price already passed is skipped (missed  |
//| fill = realistic, the tester measures it). Runaway (no pullback)   |
//| cancelled by the parent cycle's next PBO (CancelPendingsForNewPbo).|
//| `p` is the cached PBO event; `level` 0=T1 1=T2 2=T3. GTC, no time  |
//| expiry. Returns the PENDING ticket (0 on failure); out_rw = risk.  |
//+------------------------------------------------------------------+
long FobPlacePboLimit(const FobEvent &p, const int level, const double lot,
                      const double slBufferK, const double rMultTP,
                      const ulong magic, double &out_rw, const bool no_tp = false)
  {
   out_rw = 0.0;
   if(!p.zone.valid) return 0;                            // no measurable band -> no trade
   bool   is_long = (p.dir == FOB_BULL);
   double l1     = p.level;                               // near edge (T1)
   double l2     = p.zone.l2;                             // far/invalidation edge (T3)
   double mid    = p.zone.mid;                            // 50% line (T2)
   double entry  = (level <= 0) ? l1 : (level == 1) ? mid : l2;   // T1 / T2 / T3
   double band   = MathAbs(l1 - l2);                      // zone height (scale-free)
   double buffer = slBufferK * band;
   double sl     = is_long ? l2 - buffer : l2 + buffer;
   double risk   = MathAbs(entry - sl);
   if(risk <= 0.0)
      return 0;

   //--- pullback INTO the zone: BUY LIMIT must sit BELOW the Ask, SELL LIMIT ABOVE
   //--- the Bid, both >= STOPS_LEVEL away. If price already dipped past this depth
   //--- the level is a missed fill -> skip (don't turn it into a stop order).
   double ask     = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid     = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double minstop = (double)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL)
                    * SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   if(is_long)  { if(entry >= ask - minstop) return 0; }
   else         { if(entry <= bid + minstop) return 0; }
   if(risk < minstop || (!no_tp && risk * rMultTP < minstop))
      return 0;                                          // bracket too tight for the broker

   //--- no_tp (trail-only): no fixed TP -> the trailing stop is the sole profit exit.
   double tp = no_tp ? 0.0 : (is_long ? entry + risk * rMultTP : entry - risk * rMultTP);

   MqlTradeRequest req;  MqlTradeResult res;
   ZeroMemory(req);  ZeroMemory(res);
   req.action       = TRADE_ACTION_PENDING;
   req.symbol       = _Symbol;
   req.magic        = magic;
   req.type         = is_long ? ORDER_TYPE_BUY_LIMIT : ORDER_TYPE_SELL_LIMIT;
   req.volume       = lot;
   req.price        = NormalizeDouble(entry, _Digits);
   req.sl           = NormalizeDouble(sl, _Digits);
   req.tp           = NormalizeDouble(tp, _Digits);
   req.type_time    = ORDER_TIME_GTC;                     // cancelled by a new setup-TF PBO, not time
   req.type_filling = FobFilling();
   if(!OrderSend(req, res))
      return 0;
   if(res.retcode != TRADE_RETCODE_DONE && res.retcode != TRADE_RETCODE_PLACED)
      return 0;

   out_rw = risk;
   return (long)res.order;                                // the pending order ticket
  }

#endif // FOB_ENTRY_MQH
