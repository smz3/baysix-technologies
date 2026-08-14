//+------------------------------------------------------------------+
//|                                                       grw_exit.mqh |
//|  GRW-001 — the InpExitType branches, plus the open-position book.   |
//|                                                                     |
//|  Every exit reasons off state FROZEN AT FILL (GrwOpen.sl0/risk/atr0)|
//|  never off the current stop or the current ATR. Re-deriving R from  |
//|  a stop that has already been trailed silently redefines 1R halfway |
//|  through the trade, and then every R-multiple in the ledger means a |
//|  different thing.                                                   |
//|                                                                     |
//|  Stops only ever move in the FAVOURABLE direction. A trail that can |
//|  loosen is not a trail, it is a martingale.                         |
//+------------------------------------------------------------------+
#ifndef GRW_EXIT_MQH
#define GRW_EXIT_MQH
#property strict

#include "grw_types.mqh"

//--- The open book. One entry per live position (hedging-safe: keyed by POSITION_ID).
GrwOpen g_grw_open[];

//--- APPEND-ONLY record of every fill, never pruned. The open book loses a position the
//--- moment it closes, taking the frozen 1R with it — and 1R is exactly what the ledger
//--- needs to express the result in R. This is that memory.
GrwOpen g_grw_record[];

void GrwExitReset()
  {
   ArrayResize(g_grw_open, 0);
   ArrayResize(g_grw_record, 0);
  }

int GrwOpenFind(const long pos_id)
  {
   for(int i = 0; i < ArraySize(g_grw_open); i++)
      if(g_grw_open[i].pos_id == pos_id)
         return i;
   return -1;
  }

void GrwOpenAdd(const GrwOpen &o)
  {
   int n = ArraySize(g_grw_open);
   ArrayResize(g_grw_open, n + 1);
   g_grw_open[n] = o;

   int m = ArraySize(g_grw_record);
   ArrayResize(g_grw_record, m + 1);
   g_grw_record[m] = o;
  }

//--- Frozen 1R for a closed position, looked up by id. Returns 0.0 if unknown.
double GrwRecordRisk(const long pos_id)
  {
   for(int i = ArraySize(g_grw_record) - 1; i >= 0; i--)
      if(g_grw_record[i].pos_id == pos_id)
         return g_grw_record[i].risk;
   return 0.0;
  }

string GrwRecordTag(const long pos_id)
  {
   for(int i = ArraySize(g_grw_record) - 1; i >= 0; i--)
      if(g_grw_record[i].pos_id == pos_id)
         return g_grw_record[i].tag;
   return "";
  }

void GrwOpenRemoveAt(const int idx)
  {
   int n = ArraySize(g_grw_open);
   if(idx < 0 || idx >= n) return;
   for(int i = idx; i < n - 1; i++)
      g_grw_open[i] = g_grw_open[i + 1];
   ArrayResize(g_grw_open, n - 1);
  }

//--- Drop book entries whose position no longer exists (TP/SL/manual close).
void GrwOpenPrune()
  {
   for(int i = ArraySize(g_grw_open) - 1; i >= 0; i--)
      if(!PositionSelectByTicket((ulong)g_grw_open[i].pos_id))
         GrwOpenRemoveAt(i);
  }

//+------------------------------------------------------------------+
//| Move a position's stop, but ONLY toward profit and only if the    |
//| broker's stops level allows it. Returns true if the stop moved.   |
//+------------------------------------------------------------------+
bool GrwModifySL(const long pos_id, const double new_sl)
  {
   if(!PositionSelectByTicket((ulong)pos_id)) return false;
   double cur_sl = PositionGetDouble(POSITION_SL);
   double tp     = PositionGetDouble(POSITION_TP);
   bool   is_long = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY);

   //--- favourable-only. cur_sl == 0 means "no stop", so any stop is an improvement.
   if(cur_sl != 0.0)
     {
      if(is_long  && new_sl <= cur_sl) return false;
      if(!is_long && new_sl >= cur_sl) return false;
     }

   //--- respect STOPS_LEVEL against the live price, else the modify is rejected.
   double mkt     = is_long ? SymbolInfoDouble(_Symbol, SYMBOL_BID)
                            : SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double minstop = GrwStopsLevel();
   if(is_long  && new_sl > mkt - minstop) return false;
   if(!is_long && new_sl < mkt + minstop) return false;

   MqlTradeRequest req;  MqlTradeResult res;
   ZeroMemory(req);  ZeroMemory(res);
   req.action   = TRADE_ACTION_SLTP;
   req.symbol   = _Symbol;
   req.position = (ulong)pos_id;
   req.sl       = NormalizeDouble(new_sl, _Digits);
   req.tp       = NormalizeDouble(tp, _Digits);
   if(!OrderSend(req, res)) return false;
   return (res.retcode == TRADE_RETCODE_DONE || res.retcode == TRADE_RETCODE_PLACED);
  }

//+------------------------------------------------------------------+
//| Close a position at market.                                       |
//+------------------------------------------------------------------+
bool GrwClosePosition(const long pos_id, const ulong magic)
  {
   if(!PositionSelectByTicket((ulong)pos_id)) return false;
   bool   is_long = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY);
   double vol     = PositionGetDouble(POSITION_VOLUME);

   MqlTradeRequest req;  MqlTradeResult res;
   ZeroMemory(req);  ZeroMemory(res);
   req.action    = TRADE_ACTION_DEAL;
   req.symbol    = _Symbol;
   req.position  = (ulong)pos_id;
   req.magic     = magic;
   req.volume    = vol;
   req.type      = is_long ? ORDER_TYPE_SELL : ORDER_TYPE_BUY;
   req.price     = is_long ? SymbolInfoDouble(_Symbol, SYMBOL_BID)
                           : SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   req.deviation = 50;
   long mode = (long)SymbolInfoInteger(_Symbol, SYMBOL_FILLING_MODE);
   req.type_filling = ((mode & SYMBOL_FILLING_FOK) != 0) ? ORDER_FILLING_FOK
                    : ((mode & SYMBOL_FILLING_IOC) != 0) ? ORDER_FILLING_IOC
                                                         : ORDER_FILLING_RETURN;
   if(!OrderSend(req, res)) return false;
   return (res.retcode == TRADE_RETCODE_DONE || res.retcode == TRADE_RETCODE_PLACED);
  }

//+------------------------------------------------------------------+
//| Per-tick exit management for one open position.                   |
//|                                                                    |
//| FIXED_RR needs nothing here — the TP was attached at entry and the |
//| broker owns it. The other three actively manage, and all three     |
//| measure progress in R using the FROZEN risk from the fill.         |
//+------------------------------------------------------------------+
void GrwExitManageOne(const GrwCfg &c, const int idx)
  {
   if(idx < 0 || idx >= ArraySize(g_grw_open)) return;
   if(!PositionSelectByTicket((ulong)g_grw_open[idx].pos_id)) return;

   double risk = g_grw_open[idx].risk;
   if(risk <= 0.0) return;

   bool   is_long = g_grw_open[idx].is_long;
   double px      = is_long ? SymbolInfoDouble(_Symbol, SYMBOL_BID)
                            : SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double moved   = is_long ? (px - g_grw_open[idx].entry)
                            : (g_grw_open[idx].entry - px);
   double r_now   = moved / risk;                       // progress in FROZEN R units

   switch(c.exit_type)
     {
      case GRW_X_FIXED_RR:
         break;                                          // broker-side TP; nothing to do

      case GRW_X_ATR_TRAIL:
        {
         if(r_now < c.arm_r) break;                      // not armed yet
         g_grw_open[idx].armed = true;
         double dist   = c.trail_atr * g_grw_open[idx].atr0;   // frozen ATR: constant trail
         double new_sl = is_long ? px - dist : px + dist;
         GrwModifySL(g_grw_open[idx].pos_id, new_sl);
         break;
        }

      case GRW_X_BREAKEVEN_ATR:
        {
         if(r_now < c.arm_r) break;
         if(!g_grw_open[idx].armed)
           {
            //--- first arm: jump to breakeven, then behave as a trail from there.
            g_grw_open[idx].armed = true;
            GrwModifySL(g_grw_open[idx].pos_id, g_grw_open[idx].entry);
            break;
           }
         double dist2   = c.trail_atr * g_grw_open[idx].atr0;
         double new_sl2 = is_long ? px - dist2 : px + dist2;
         GrwModifySL(g_grw_open[idx].pos_id, new_sl2);
         break;
        }

      case GRW_X_TIME_STOP:
         //--- bars_held is advanced by the EA on each new signal-TF bar; the close
         //--- itself happens there too, so nothing tick-driven is needed.
         break;
     }
  }

void GrwExitManageAll(const GrwCfg &c)
  {
   GrwOpenPrune();
   for(int i = ArraySize(g_grw_open) - 1; i >= 0; i--)
      GrwExitManageOne(c, i);
  }

//+------------------------------------------------------------------+
//| New-bar housekeeping: age every open position and close the ones  |
//| that have outlived the mechanism's horizon (GRW_X_TIME_STOP).     |
//| Called ONCE per closed signal-TF bar.                             |
//+------------------------------------------------------------------+
void GrwExitOnNewBar(const GrwCfg &c)
  {
   GrwOpenPrune();
   for(int i = ArraySize(g_grw_open) - 1; i >= 0; i--)
     {
      g_grw_open[i].bars_held++;
      if(c.exit_type == GRW_X_TIME_STOP && c.time_stop_bars > 0
         && g_grw_open[i].bars_held >= c.time_stop_bars)
        {
         if(GrwClosePosition(g_grw_open[i].pos_id, c.magic))
            GrwOpenRemoveAt(i);
        }
     }
  }

//+------------------------------------------------------------------+
//| Flatten the book. Called ONCE, when the barrier episode resolves  |
//| (grw_fitness.mqh v2.0.0): the target is a DOLLAR target read off  |
//| open P&L, so hitting it means banking it, and hitting the floor   |
//| means the shot is spent. Leaving a position open past resolution  |
//| would let post-episode P&L land in the same pass row.             |
//| Returns how many positions were closed.                           |
//+------------------------------------------------------------------+
int GrwCloseAll(const ulong magic)
  {
   int n = 0;
   for(int i = ArraySize(g_grw_open) - 1; i >= 0; i--)
     {
      if(GrwClosePosition(g_grw_open[i].pos_id, magic))
        {
         GrwOpenRemoveAt(i);
         n++;
        }
     }
   return n;
  }

#endif // GRW_EXIT_MQH
