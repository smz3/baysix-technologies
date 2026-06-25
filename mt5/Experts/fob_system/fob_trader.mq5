//+------------------------------------------------------------------+
//|                                                    fob_trader.mq5  |
//|        FOB TRADER — the strategy EA (sibling of the emitter).      |
//|                                                                    |
//|  Reuses the emitter's EXACT detection + classification pipeline    |
//|  (fob_swings -> fob_breakouts -> fob_sequence across all 9 TFs, in |
//|  chronological order) so the trade triggers on the SAME PBO/VR/CF  |
//|  events the oracle emits. The emitter stays pristine (read-only);  |
//|  this EA adds orders on top of an identical event stream.          |
//|                                                                    |
//|  FOB-T1 atom (the coin-flip GATE, task 163):                       |
//|    • Trigger : a CF on the chosen setup TF (default H1 -> CF fires |
//|                on M30, the n-1 confirmation TF).                    |
//|    • Entry   : MARKET on CF close (E1), in the PBO/continuation dir.|
//|    • Risk 1R : R = |entry - VR level| (stop back through the VR     |
//|                origin = continuation invalidated).                 |
//|    • Exit    : SYMMETRIC bracket — TP = entry +1R, SL = entry -1R.  |
//|                A symmetric ±1R barrier is a COIN-FLIP by            |
//|                construction (50% null). Win-rate >50% with a       |
//|                binomial z = the CF carries directional content.    |
//|    • One position at a time; native SL/TP do the exit.             |
//|                                                                    |
//|  Trust: the MT5 tester is the arbiter (CLAUDE.md MT5 Trust rule).  |
//|  Run on the M5 chart. GROSS premise = "Open prices only" (fast,    |
//|  deterministic bracket fills); NET tradeability re-runs real-ticks.|
//|  The per-trade ledger (incl. setup_tf / event_tf / cf_idx / seq)   |
//|  is auto-written on deinit -> feeds T2's cf_idx conditioning.      |
//+------------------------------------------------------------------+
#property copyright "Baysix Technologies"
#property version   "1.7.0"         // MUST match FOB_VERSION (fob_types.mqh) — bump together
#property strict

#include <fob_system/fob_swings.mqh>
#include <fob_system/fob_breakouts.mqh>
#include <fob_system/fob_types.mqh>
#include <fob_system/fob_sequence.mqh>

//--- detection (MUST match the emitter so the event stream is identical)
input int    InpSwingWindow   = 3;      // close-based pivot window (odd, >=3)
input int    InpMaxAge        = 0;      // break age filter in bars (<=0 disables)
input bool   InpPboNewestOnly = true;   // PBO = freshest source near CMP

//--- FOB-T1 trade atom
input int    InpSetupTf       = 4;      // setup TF INDEX (M1=0..MN1=8); 4 = H1 -> CF on M30
input int    InpCfIdxFilter   = 0;      // CF ordinal to trade (0 = ALL CFs; T2 will sweep 1/2/3)
input double InpRMultTP       = 1.0;    // TP in R (1.0 = symmetric coin-flip; raise later)
input double InpRMultSL       = 1.0;    // SL in R (1.0 = symmetric coin-flip)
input double InpFixedLot      = 0.01;   // min lot at $50
input ulong  InpMagic         = 3001;   // FOB trader magic
input bool   InpShowTrades     = false; // draw entry/exit arrows (Visual Mode only)

//--- the 9 TFs (index order MUST match FobTfName in fob_types.mqh)
ENUM_TIMEFRAMES g_periods[FOB_N_TF] =
  { PERIOD_M1, PERIOD_M5, PERIOD_M15, PERIOD_M30, PERIOD_H1, PERIOD_H4, PERIOD_D1, PERIOD_W1, PERIOD_MN1 };

//+------------------------------------------------------------------+
//| Per-TF detection state (identical to the emitter's FobTfState).  |
//+------------------------------------------------------------------+
struct FobTfState
  {
   datetime last_time;
   datetime bt[];   double bh[];  double bl[];  double bc[];
   FobSwing swings[];
   int      live_sw[];
   FobBreak breaks[];
  };

//--- one new raw break awaiting chronological classification this tick
struct FobPending
  {
   int      tf;
   datetime swt;
   datetime bt;
   int      dir;
   double   level;
   double   close;
  };

FobTfState    g_tf[FOB_N_TF];
FobSetupState g_setup[FOB_N_TF];
FobEvent      g_events[];
int           g_radius   = 1;
int           g_seen     = 0;        // # events already acted on (watermark into g_events)

//--- one-position state
enum TRADE_STATE { TS_FLAT = 0, TS_INPOS = 1 };
TRADE_STATE g_state = TS_FLAT;

//--- per-trade stash: position_id -> trade context (for the ledger + T2 conditioning)
long   g_pid[];      double g_rw[];
int    g_setuptf[];  int    g_eventtf[];  int g_cfidx[];  int g_seq[];  int g_dir[];

//--- trade-marker prefix (own namespace)
#define FOB_TR_PREFIX "FOB_TR_"

//+------------------------------------------------------------------+
int OnInit()
  {
   g_radius = FobSwingRadius(InpSwingWindow);
   if(g_radius < 0)
      return INIT_PARAMETERS_INCORRECT;
   if(InpSetupTf <= 0 || InpSetupTf >= FOB_N_TF)
     {
      Print("[FOB TRADER] InpSetupTf must be 1..", FOB_N_TF - 1, " (a PBO needs a TF below for its CF).");
      return INIT_PARAMETERS_INCORRECT;
     }

   //--- FULL reset (HARD): MT5 reinits WITHOUT unloading -> globals survive.
   ArrayResize(g_events, 0);
   g_seen  = 0;
   g_state = TS_FLAT;
   for(int i = 0; i < FOB_N_TF; i++)
     {
      g_tf[i].last_time = 0;
      ArrayResize(g_tf[i].bt, 0);     ArrayResize(g_tf[i].bh, 0);
      ArrayResize(g_tf[i].bl, 0);     ArrayResize(g_tf[i].bc, 0);
      ArrayResize(g_tf[i].swings, 0); ArrayResize(g_tf[i].live_sw, 0);
      ArrayResize(g_tf[i].breaks, 0);
      g_setup[i].active     = false;  g_setup[i].seq = 0;
      g_setup[i].vr_locked  = false;  g_setup[i].vr_level = 0.0;
      g_setup[i].cf_count   = 0;      g_setup[i].last_conf_swing = 0;
      g_setup[i].pbo_swing  = 0;
     }
   ArrayResize(g_pid, 0); ArrayResize(g_rw, 0); ArrayResize(g_setuptf, 0);
   ArrayResize(g_eventtf, 0); ArrayResize(g_cfidx, 0); ArrayResize(g_seq, 0); ArrayResize(g_dir, 0);
   ObjectsDeleteAll(0, FOB_TR_PREFIX);

   PrintFormat("[FOB TRADER] v%s init OK — setup_tf=%s -> CF on %s | cf_filter=%d | TP=%.2fR SL=%.2fR | lot=%.2f magic=%I64u",
               FOB_VERSION, FobTfName(InpSetupTf), FobTfName(InpSetupTf - 1),
               InpCfIdxFilter, InpRMultTP, InpRMultSL, InpFixedLot, InpMagic);
   return INIT_SUCCEEDED;
  }

//+------------------------------------------------------------------+
//| Append one closed bar + run swing-confirm + raw-break detection. |
//| Byte-identical to the emitter's FobIngestBar.                    |
//+------------------------------------------------------------------+
void FobIngestBar(FobTfState &s, const datetime bt, const double h, const double l, const double cl)
  {
   int i = ArraySize(s.bt);
   ArrayResize(s.bt, i + 1, 4096); ArrayResize(s.bh, i + 1, 4096);
   ArrayResize(s.bl, i + 1, 4096); ArrayResize(s.bc, i + 1, 4096);
   s.bt[i] = bt; s.bh[i] = h; s.bl[i] = l; s.bc[i] = cl;
   int n = i + 1;

   int p = i - g_radius;
   if(p >= 0)
     {
      FobSwing sw;
      if(FobDetectSwingAt(s.bt, s.bc, n, p, g_radius, sw))
        {
         int si = ArraySize(s.swings);
         ArrayResize(s.swings, si + 1, 512);
         s.swings[si] = sw;
         int li = ArraySize(s.live_sw);
         ArrayResize(s.live_sw, li + 1, 512);
         s.live_sw[li] = si;
        }
     }
   FobDetectBreaksOnBar(s.swings, s.live_sw, i, bt, cl, g_radius, InpMaxAge, s.breaks);
  }

//+------------------------------------------------------------------+
//| Insertion-sort pending breaks: bar_time ASC, ties higher-TF first.|
//+------------------------------------------------------------------+
void FobSortPending(FobPending &p[])
  {
   int n = ArraySize(p);
   for(int i = 1; i < n; i++)
     {
      FobPending key = p[i];
      int j = i - 1;
      while(j >= 0 && (p[j].bt > key.bt || (p[j].bt == key.bt && p[j].tf < key.tf)))
        { p[j + 1] = p[j]; j--; }
      p[j + 1] = key;
     }
  }

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
//| Market entry in `dir` with a symmetric ±R bracket (SL/TP native).|
//| Returns the new position identifier (0 on failure).              |
//+------------------------------------------------------------------+
long FobOpenMarket(const int dir, const double lot, const double r_unit)
  {
   bool   is_long = (dir == FOB_BULL);
   double entry   = is_long ? SymbolInfoDouble(_Symbol, SYMBOL_ASK)
                            : SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double tp_dist = r_unit * InpRMultTP;
   double sl_dist = r_unit * InpRMultSL;
   double sl = is_long ? entry - sl_dist : entry + sl_dist;
   double tp = is_long ? entry + tp_dist : entry - tp_dist;

   MqlTradeRequest req;  MqlTradeResult res;
   ZeroMemory(req);  ZeroMemory(res);
   req.action       = TRADE_ACTION_DEAL;
   req.symbol       = _Symbol;
   req.magic        = InpMagic;
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

   //--- resolve the position identifier (== ticket for a fresh market deal)
   if(PositionSelect(_Symbol))
      return (long)PositionGetInteger(POSITION_IDENTIFIER);
   return (long)res.order;
  }

//+------------------------------------------------------------------+
//| Open position for this EA?                                        |
//+------------------------------------------------------------------+
bool HasPosition()
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong tk = PositionGetTicket(i);
      if(tk == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) == _Symbol &&
         (ulong)PositionGetInteger(POSITION_MAGIC) == InpMagic)
         return true;
     }
   return false;
  }

//+------------------------------------------------------------------+
//| Stash trade context keyed on position id (for the ledger + T2).  |
//+------------------------------------------------------------------+
void StashTrade(const long pid, const double rw, const FobEvent &e)
  {
   int m = ArraySize(g_pid);
   ArrayResize(g_pid, m + 1);     ArrayResize(g_rw, m + 1);
   ArrayResize(g_setuptf, m + 1); ArrayResize(g_eventtf, m + 1);
   ArrayResize(g_cfidx, m + 1);   ArrayResize(g_seq, m + 1);  ArrayResize(g_dir, m + 1);
   g_pid[m] = pid;       g_rw[m] = rw;
   g_setuptf[m] = e.setup_tf;  g_eventtf[m] = e.event_tf;
   g_cfidx[m] = e.cf_idx;      g_seq[m] = e.seq;   g_dir[m] = e.dir;
  }

void DrawTrade(const FobEvent &e, const double entry, const double sl, const double tp)
  {
   if(!InpShowTrades) return;
   bool is_long = (e.dir == FOB_BULL);
   string an = FOB_TR_PREFIX + (string)e.bar_time + "_e";
   if(ObjectFind(0, an) < 0) ObjectCreate(0, an, OBJ_ARROW, 0, e.bar_time, entry);
   ObjectMove(0, an, 0, e.bar_time, entry);
   ObjectSetInteger(0, an, OBJPROP_ARROWCODE, is_long ? 233 : 234);
   ObjectSetInteger(0, an, OBJPROP_COLOR, is_long ? clrAqua : clrMagenta);
   ObjectSetInteger(0, an, OBJPROP_HIDDEN, true);
  }

//+------------------------------------------------------------------+
//| After classification: if FLAT, act on the FIRST unseen CF event  |
//| matching the setup-TF (+ cf_idx) filter.                         |
//+------------------------------------------------------------------+
void ActOnNewEvents()
  {
   int n = ArraySize(g_events);
   for(int k = g_seen; k < n; k++)
     {
      if(g_state == TS_INPOS)
         break;                                  // one position at a time — skip the rest
      FobEvent e = g_events[k];
      if(e.label != FOB_CF)              continue;
      if(e.setup_tf != InpSetupTf)       continue;
      if(InpCfIdxFilter > 0 && e.cf_idx != InpCfIdxFilter) continue;

      double vr_level = g_setup[e.setup_tf].vr_level;
      if(vr_level <= 0.0)                continue;   // no VR ref (shouldn't happen post-lock)

      double entry_ref = (e.dir == FOB_BULL) ? SymbolInfoDouble(_Symbol, SYMBOL_ASK)
                                              : SymbolInfoDouble(_Symbol, SYMBOL_BID);
      double r_unit = MathAbs(entry_ref - vr_level);
      double minstop = (double)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL)
                       * SymbolInfoDouble(_Symbol, SYMBOL_POINT);
      if(r_unit <= 0.0 || r_unit * MathMin(InpRMultTP, InpRMultSL) < minstop)
         continue;                                 // R too tight for a valid bracket — skip

      long pid = FobOpenMarket(e.dir, InpFixedLot, r_unit);
      if(pid > 0)
        {
         StashTrade(pid, r_unit, e);
         g_state = TS_INPOS;
         if(InpShowTrades && PositionSelect(_Symbol))
            DrawTrade(e, PositionGetDouble(POSITION_PRICE_OPEN),
                      PositionGetDouble(POSITION_SL), PositionGetDouble(POSITION_TP));
        }
     }
   g_seen = n;   // every event up to n has now been considered
  }

//+------------------------------------------------------------------+
//| Per tick: ingest newly closed bars (all TFs), classify in order, |
//| reconcile position state, then act on new CF events.             |
//+------------------------------------------------------------------+
void OnTick()
  {
   MqlRates r[];
   ArraySetAsSeries(r, true);
   FobPending pend[];

   for(int t = 0; t < FOB_N_TF; t++)
     {
      int got = CopyRates(_Symbol, g_periods[t], 1, 64, r);
      if(got <= 0) continue;
      int nb0 = ArraySize(g_tf[t].breaks);
      for(int k = got - 1; k >= 0; k--)
        {
         if(r[k].time <= g_tf[t].last_time) continue;
         FobIngestBar(g_tf[t], r[k].time, r[k].high, r[k].low, r[k].close);
         g_tf[t].last_time = r[k].time;
        }
      int nb1 = ArraySize(g_tf[t].breaks);
      for(int b = nb0; b < nb1; b++)
        {
         int pi = ArraySize(pend);
         ArrayResize(pend, pi + 1, 64);
         pend[pi].tf    = t;
         pend[pi].swt   = g_tf[t].breaks[b].swing_time;
         pend[pi].bt    = g_tf[t].breaks[b].bar_time;
         pend[pi].dir   = g_tf[t].breaks[b].dir;
         pend[pi].level = g_tf[t].breaks[b].swing_price;
         pend[pi].close = g_tf[t].breaks[b].bar_close;
        }
     }

   //--- reconcile position state BEFORE classifying new events (bracket may have closed it)
   if(g_state == TS_INPOS && !HasPosition())
      g_state = TS_FLAT;

   int np = ArraySize(pend);
   if(np > 0)
     {
      FobSortPending(pend);
      for(int q = 0; q < np; q++)
         FobClassifyBreak(g_setup, FOB_N_TF, pend[q].tf, pend[q].dir, pend[q].swt, pend[q].bt,
                          pend[q].level, pend[q].close, g_events, InpPboNewestOnly);
     }

   ActOnNewEvents();
  }

//+------------------------------------------------------------------+
//| Human-readable exit reason from the closing deal.                |
//+------------------------------------------------------------------+
string ExitReasonName(const long reason)
  {
   switch((ENUM_DEAL_REASON)reason)
     {
      case DEAL_REASON_SL: return "SL";
      case DEAL_REASON_TP: return "TP";
      case DEAL_REASON_SO: return "SO";
      case DEAL_REASON_EXPERT: return "EXPERT";
     }
   return "OTHER";
  }

//+------------------------------------------------------------------+
//| Map a closed position id -> its stashed trade context.           |
//+------------------------------------------------------------------+
double CtxForPos(const long pid, int &setup_tf, int &event_tf, int &cf_idx, int &seq, int &dir)
  {
   for(int i = ArraySize(g_pid) - 1; i >= 0; i--)
      if(g_pid[i] == pid)
        {
         setup_tf = g_setuptf[i]; event_tf = g_eventtf[i]; cf_idx = g_cfidx[i];
         seq = g_seq[i]; dir = g_dir[i];
         return g_rw[i];
        }
   setup_tf = -1; event_tf = -1; cf_idx = 0; seq = 0; dir = 0;
   return 0.0;
  }

//+------------------------------------------------------------------+
//| Per-trade ledger CSV from the tester's deal history. One row per |
//| closed position with setup_tf / event_tf / cf_idx / seq + R-     |
//| outcome — the input for T2 (cf_idx conditioning). Auto-written   |
//| on deinit (no manual export). Lands in Common\Files\FOB.         |
//+------------------------------------------------------------------+
void WriteTradeLedger()
  {
   if(!HistorySelect(0, TimeCurrent())) return;
   int total = HistoryDealsTotal();
   if(total <= 0) return;

   //--- pass 1: index IN deals by position id
   long in_pid[];  datetime in_time[];  double in_px[];  double in_lot[];  int in_dir[];
   for(int i = 0; i < total; i++)
     {
      ulong tk = HistoryDealGetTicket(i);
      if((long)HistoryDealGetInteger(tk, DEAL_MAGIC) != (long)InpMagic) continue;
      if((ENUM_DEAL_ENTRY)HistoryDealGetInteger(tk, DEAL_ENTRY) != DEAL_ENTRY_IN) continue;
      int n = ArraySize(in_pid);
      ArrayResize(in_pid, n+1); ArrayResize(in_time, n+1); ArrayResize(in_px, n+1);
      ArrayResize(in_lot, n+1); ArrayResize(in_dir, n+1);
      in_pid[n]  = (long)HistoryDealGetInteger(tk, DEAL_POSITION_ID);
      in_time[n] = (datetime)HistoryDealGetInteger(tk, DEAL_TIME);
      in_px[n]   = HistoryDealGetDouble(tk, DEAL_PRICE);
      in_lot[n]  = HistoryDealGetDouble(tk, DEAL_VOLUME);
      in_dir[n]  = (HistoryDealGetInteger(tk, DEAL_TYPE) == DEAL_TYPE_BUY) ? 1 : -1;
     }

   string stamp = TimeToString(TimeCurrent(), TIME_DATE|TIME_MINUTES);
   StringReplace(stamp, ".", ""); StringReplace(stamp, ":", ""); StringReplace(stamp, " ", "_");
   string ver = FOB_VERSION; StringReplace(ver, ".", "");
   string fname = StringFormat("FOB\\fob_trades_%s_v%s_%s_cf%d_%s.csv",
                               _Symbol, ver, FobTfName(InpSetupTf), InpCfIdxFilter, stamp);
   int h = FileOpen(fname, FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON, ',');
   if(h == INVALID_HANDLE)
     { PrintFormat("[FOB TRADER] ledger FileOpen failed (%d) for %s", GetLastError(), fname); return; }
   FileWrite(h, "position_id","direction","setup_tf","event_tf","cf_idx","seq",
             "entry_ts","entry_px","exit_ts","exit_px","exit_reason","lots",
             "range_w","realized_r","realized_pnl_usd","win");

   //--- pass 2: one row per OUT deal, paired to its IN
   int rows = 0, wins = 0;
   for(int i = 0; i < total; i++)
     {
      ulong tk = HistoryDealGetTicket(i);
      if((long)HistoryDealGetInteger(tk, DEAL_MAGIC) != (long)InpMagic) continue;
      if((ENUM_DEAL_ENTRY)HistoryDealGetInteger(tk, DEAL_ENTRY) != DEAL_ENTRY_OUT) continue;

      long     pid     = (long)HistoryDealGetInteger(tk, DEAL_POSITION_ID);
      datetime exit_ts = (datetime)HistoryDealGetInteger(tk, DEAL_TIME);
      double   exit_px = HistoryDealGetDouble(tk, DEAL_PRICE);
      double   pnl     = HistoryDealGetDouble(tk, DEAL_PROFIT)
                         + HistoryDealGetDouble(tk, DEAL_SWAP)
                         + HistoryDealGetDouble(tk, DEAL_COMMISSION);
      string   reason  = ExitReasonName(HistoryDealGetInteger(tk, DEAL_REASON));

      datetime entry_ts = 0; double entry_px = 0, lots = 0; int dir = 0;
      for(int j = ArraySize(in_pid) - 1; j >= 0; j--)
         if(in_pid[j] == pid)
           { entry_ts = in_time[j]; entry_px = in_px[j]; lots = in_lot[j]; dir = in_dir[j]; break; }

      int s_tf, e_tf, cfx, sq, edir;
      double rw = CtxForPos(pid, s_tf, e_tf, cfx, sq, edir);
      double rR = (rw > 0.0) ? (dir * (exit_px - entry_px) / rw) : 0.0;
      int    win = (rR > 0.0) ? 1 : 0;
      wins += win;

      FileWrite(h, (string)pid, (dir > 0 ? "BUY" : "SELL"),
                (s_tf >= 0 ? FobTfName(s_tf) : "?"), (e_tf >= 0 ? FobTfName(e_tf) : "?"),
                (string)cfx, (string)sq,
                TimeToString(entry_ts, TIME_DATE|TIME_SECONDS), DoubleToString(entry_px, _Digits),
                TimeToString(exit_ts,  TIME_DATE|TIME_SECONDS), DoubleToString(exit_px, _Digits),
                reason, DoubleToString(lots, 2), DoubleToString(rw, _Digits),
                DoubleToString(rR, 4), DoubleToString(pnl, 2), (string)win);
      rows++;
     }
   FileClose(h);
   double wr = (rows > 0) ? (100.0 * wins / rows) : 0.0;
   PrintFormat("[FOB TRADER] v%s ledger: %d trades, win-rate %.2f%% (%d/%d) -> Common\\Files\\%s",
               FOB_VERSION, rows, wr, wins, rows, fname);
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   WriteTradeLedger();
   if(InpShowTrades) ObjectsDeleteAll(0, FOB_TR_PREFIX);
  }
//+------------------------------------------------------------------+
