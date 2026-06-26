//+------------------------------------------------------------------+
//|                                                    fob_trader.mq5  |
//|        FOB TRADER — the strategy EA (sibling of the emitter).      |
//|                                                                    |
//|  Reuses the emitter's EXACT detection + classification pipeline    |
//|  (fob_swings -> fob_breakouts -> fob_sequence) so the trade        |
//|  triggers on the SAME PBO/VR/CF events the oracle emits. The       |
//|  emitter stays pristine (read-only); this EA adds orders.          |
//|                                                                    |
//|  PURE PRICE-ACTION (v1.13.0): ZERO indicators. ATR fully removed   |
//|  — even study-mode MFE/MAE is now raw price points.                |
//|                                                                    |
//|  Trade atom:                                                       |
//|    • Trigger : every CF on g_setup_tf (default H1 -> CF on M30).   |
//|    • Entry   : MARKET on CF detection, PBO/continuation dir.       |
//|    • SL      : beyond the CF ZONE — the CF's broken swing level     |
//|                (reclaim it = breakout failed) ± InpSlBufferK*pen.   |
//|    • TP      : InpRMultTP * risk.                                  |
//|                                                                    |
//|  MULTI-POSITION (v1.13.0, task 176): NO one-at-a-time gate. EVERY   |
//|  CF opens its own independent position (HEDGING account) — the 1st  |
//|  CF no longer locks the cycle, so the 2nd CF (the paper's best      |
//|  entry) and beyond all fire. Each position carries its own SL/TP;   |
//|  the ledger pairs by position_id.                                  |
//|                                                                    |
//|  Per-TF iteration (task 163): ingest ONLY {setup_tf-1, setup_tf}   |
//|  — byte-identical to the full classifier for this setup's events,  |
//|  far faster on real ticks.                                         |
//|                                                                    |
//|  Trust: the MT5 tester is the arbiter. Run on the M5 chart. Native |
//|  trade-level bands are DISABLED (CHART_SHOW_TRADE_LEVELS off); the  |
//|  fob_visual sequence dots (PBO/VR/CF) render so fills can be        |
//|  eyeballed against the sequence. MT5 draws the trade arrows itself. |
//|  A cycle with a LIVE position keeps its sequence dots even after a  |
//|  newer cycle supersedes it (task: visual retention).               |
//+------------------------------------------------------------------+
#property copyright "Baysix Technologies"
#property version   "1.14.0"        // MUST match FOB_VERSION (fob_types.mqh) — bump together
#property strict

#include <fob_system/fob_swings.mqh>
#include <fob_system/fob_breakouts.mqh>
#include <fob_system/fob_types.mqh>
#include <fob_system/fob_sequence.mqh>
#include <fob_system/fob_visual.mqh>     // sequence dots + InpVisualize master toggle

//--- detection (MUST match the emitter so the event stream is identical)
input int    InpSwingWindow   = 3;      // close-based pivot window (odd, >=3)
input int    InpMaxAge        = 0;      // break age filter in bars (<=0 disables)
input bool   InpPboNewestOnly = true;   // PBO = freshest source near CMP

//--- setup/CF timeframe pair. A PBO on the setup TF is confirmed by a CF on the TF one
//--- below it; pick a pair from the dropdown and the CF TF is always (setup TF - 1).
enum FOB_TF_PAIR
  {
   FOB_TF_M5_M1   = 0,   // setup M5  -> CF on M1
   FOB_TF_M15_M5  = 1,   // setup M15 -> CF on M5
   FOB_TF_M30_M15 = 2,   // setup M30 -> CF on M15
   FOB_TF_H1_M30  = 3,   // setup H1  -> CF on M30  (baseline)
   FOB_TF_H4_H1   = 4,   // setup H4  -> CF on H1
   FOB_TF_D1_H4   = 5    // setup D1  -> CF on H4
  };

//--- trade atom. SL = the broken CF swing level (CF_ZONE), pushed beyond by k*penetration.
input FOB_TF_PAIR InpTfPair   = FOB_TF_H1_M30; // setup TF -> CF on the TF one below
input int      InpCfIdxFilter = 0;            // CF ordinal to trade (0 = ALL CFs; T2 sweeps 1/2/3)
input double   InpSlBufferK   = 0.0;          // SL beyond the CF level by k*penetration (0 = at the level)
input double   InpRMultTP      = 1.0;         // TP = RR * risk (1.0 = 1:1, the coin-flip null)
input double   InpFixedLot      = 0.01;       // min lot at $50
input ulong    InpMagic         = 3001;       // FOB trader magic

//--- forward-excursion STUDY mode (T-170). NO orders: per CF on g_setup_tf, anchor at the
//--- CF mid price and track running MFE/MAE/terminal on REAL TICKS until the NEXT CF on the
//--- setup TF (any cf_idx) — or a cap. COST-FREE: measured on MID (zero spread) — this is
//--- DISCOVERY, pure direction geometry; cost enters at G2, NEVER here. Reported in RAW
//--- PRICE POINTS (v1.13.0: ATR removed — FOB is indicator-free).
input bool     InpStudyMode    = false;       // [study] forward-excursion measurement (no trades)
input int      InpStudyCapBars = 48;          // [study] force-close window after this many setup-TF bars

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
   FobZone  zone;         // 4-pointer band carried from the break (v1.14.0)
  };

FobTfState    g_tf[FOB_N_TF];
FobSetupState g_setup[FOB_N_TF];
FobEvent      g_events[];
int           g_radius   = 1;
int           g_seen     = 0;           // # events already acted on (watermark into g_events)
int           g_ingest[];               // ONLY the TF indices we ingest = {setup_tf-1, setup_tf}
int           g_setup_tf   = 4;               // setup TF index, derived from InpTfPair in OnInit
CFobVisual    g_vis;

//--- per-trade stash: position_id -> trade context (for the ledger + T2 conditioning).
//--- These arrays hold EVERY open+closed trade — the trader is now multi-position.
long   g_pid[];      double g_rw[];
int    g_setuptf[];  int    g_eventtf[];  int g_cfidx[];  int g_seq[];  int g_dir[];

//--- live-cycle scratch (rebuilt each redraw): (setup_tf, seq) pairs that still
//--- have an OPEN position — their sequence dots must survive supersession.
int    g_live_tf[];  int g_live_seq[];

//--- STUDY mode (T-170): one open forward-excursion window at a time. RAW POINTS (no ATR).
bool     g_sw_open      = false;        // is a window currently being measured?
datetime g_sw_cf_time   = 0;            // anchor CF bar_time
datetime g_sw_open_ts   = 0;            // server time at anchor (cap clock)
int      g_sw_dir       = 0;            // FOB_BULL | FOB_BEAR (continuation dir)
int      g_sw_cfidx     = 0;            // anchor CF ordinal
int      g_sw_seq       = 0;            // anchor PBO sequence
double   g_sw_entry     = 0.0;          // entry-side fill (mid, cost-free) at anchor
double   g_sw_mfe       = 0.0;          // running max favorable excursion (pts, exit-side)
double   g_sw_mae       = 0.0;          // running max adverse  excursion (pts, exit-side)
double   g_sw_term      = 0.0;          // last favorable excursion (-> terminal at close)

//--- study ledger rows (flushed on deinit) — raw points only
datetime sr_time[];  int sr_dir[];  int sr_cfidx[];  int sr_seq[];
double   sr_entry[]; double sr_mfe[]; double sr_mae[]; double sr_term[];
double   sr_winbars[]; int sr_nextdir[];   // window length (setup-TF bars) + next CF dir (-1 = capped)

//+------------------------------------------------------------------+
int OnInit()
  {
   g_radius = FobSwingRadius(InpSwingWindow);
   if(g_radius < 0)
      return INIT_PARAMETERS_INCORRECT;
   g_setup_tf = (int)InpTfPair + 1;   // M5_M1=0->M5=1, M15_M5=1->M15=2, ... D1_H4=5->D1=6

   //--- ingest ONLY the setup TF and its n-1 (CF) TF: byte-identical to the full
   //--- classifier for this setup's events (a break on TF t only sets PBO(t) and
   //--- VR/CF(t+1)) — so {setup_tf-1, setup_tf} fully determines every setup_tf event.
   ArrayResize(g_ingest, 2);
   g_ingest[0] = g_setup_tf - 1;
   g_ingest[1] = g_setup_tf;

   //--- FULL reset (HARD): MT5 reinits WITHOUT unloading -> globals survive.
   ArrayResize(g_events, 0);
   g_seen  = 0;
   for(int i = 0; i < FOB_N_TF; i++)
     {
      g_tf[i].last_time = 0;
      ArrayResize(g_tf[i].bt, 0);     ArrayResize(g_tf[i].bh, 0);
      ArrayResize(g_tf[i].bl, 0);     ArrayResize(g_tf[i].bc, 0);
      ArrayResize(g_tf[i].swings, 0); ArrayResize(g_tf[i].live_sw, 0);
      ArrayResize(g_tf[i].breaks, 0);
      g_setup[i].active     = false;  g_setup[i].seq = 0;
      g_setup[i].vr_locked  = false;  g_setup[i].vr_level = 0.0;
      g_setup[i].vr_swing   = 0;      g_setup[i].vr_ev_idx = -1;
      g_setup[i].cf_count   = 0;      g_setup[i].last_conf_swing = 0;
      g_setup[i].pbo_swing  = 0;
     }
   ArrayResize(g_pid, 0); ArrayResize(g_rw, 0); ArrayResize(g_setuptf, 0);
   ArrayResize(g_eventtf, 0); ArrayResize(g_cfidx, 0); ArrayResize(g_seq, 0); ArrayResize(g_dir, 0);
   ArrayResize(g_live_tf, 0); ArrayResize(g_live_seq, 0);

   //--- study-mode state (HARD reset — globals survive reinit)
   g_sw_open = false; g_sw_cf_time = 0; g_sw_open_ts = 0; g_sw_dir = 0;
   g_sw_cfidx = 0; g_sw_seq = 0; g_sw_entry = 0.0;
   g_sw_mfe = 0.0; g_sw_mae = 0.0; g_sw_term = 0.0;
   ArrayResize(sr_time, 0); ArrayResize(sr_dir, 0); ArrayResize(sr_cfidx, 0); ArrayResize(sr_seq, 0);
   ArrayResize(sr_entry, 0); ArrayResize(sr_mfe, 0); ArrayResize(sr_mae, 0);
   ArrayResize(sr_term, 0); ArrayResize(sr_winbars, 0); ArrayResize(sr_nextdir, 0);

   //--- kill MT5's native trade-level bands (the red/gray shading) PERMANENTLY;
   //--- the deal arrows MT5 draws on its own are enough. Our sequence dots stay.
   ChartSetInteger(0, CHART_SHOW_TRADE_LEVELS, false);
   //--- the red/gray bands are the Ask (red, upper) + Bid (gray, lower) price
   //--- lines, not trade levels — kill them too (and the OHLC band) for focus.
   ChartSetInteger(0, CHART_SHOW_ASK_LINE, false);
   ChartSetInteger(0, CHART_SHOW_BID_LINE, false);
   ChartSetInteger(0, CHART_SHOW_OHLC, false);
   g_vis.SyncChartTF();
   g_vis.ClearAll();

   PrintFormat("[FOB TRADER] v%s init OK — setup_tf=%s -> CF on %s (ingest %s+%s) | cf_filter=%d | CF_ZONE SLbuf=%.2f TP=%.2fR | lot=%.2f magic=%I64u | MULTI-POSITION",
               FOB_VERSION, FobTfName(g_setup_tf), FobTfName(g_setup_tf - 1),
               FobTfName(g_ingest[0]), FobTfName(g_ingest[1]),
               InpCfIdxFilter, InpSlBufferK, InpRMultTP, InpFixedLot, InpMagic);
   if(InpStudyMode)
      PrintFormat("[FOB TRADER] *** STUDY MODE (T-170) *** NO ORDERS — per CF: MFE/MAE/terminal (RAW POINTS) until next CF, cap=%d %s bars",
                  InpStudyCapBars, FobTfName(g_setup_tf));
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
   FobDetectBreaksOnBar(s.swings, s.live_sw, i, bt, cl, g_radius, InpMaxAge, s.bc, n, s.breaks);
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
//| Market entry on a CF, anchored to the CF zone.                   |
//|   entry = market (Ask/Bid)                                       |
//|   SL    = CF level (the swing the CF broke) pushed BEYOND it by   |
//|           InpSlBufferK * penetration (reclaim = breakout failed)  |
//|   TP    = entry ± risk * InpRMultTP                              |
//| Returns the new position id (0 on failure); sets out_rw = risk.  |
//| HEDGING-safe id capture: read POSITION_ID off the entry deal so  |
//| each concurrent position is keyed uniquely.                      |
//+------------------------------------------------------------------+
long FobOpenMarket(const int dir, const double lot, const double cf_level, double &out_rw)
  {
   out_rw = 0.0;
   bool   is_long = (dir == FOB_BULL);
   double entry   = is_long ? SymbolInfoDouble(_Symbol, SYMBOL_ASK)
                            : SymbolInfoDouble(_Symbol, SYMBOL_BID);
   //--- SL = the broken CF swing level, pushed beyond by InpSlBufferK*penetration.
   double pen    = MathAbs(entry - cf_level);             // breakout penetration
   double buffer = InpSlBufferK * pen;
   double sl     = is_long ? cf_level - buffer : cf_level + buffer;
   double risk   = MathAbs(entry - sl);
   if(risk <= 0.0)
      return 0;
   double minstop = (double)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL)
                    * SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   if(risk < minstop || risk * InpRMultTP < minstop)
      return 0;                                          // bracket too tight for the broker

   double tp = is_long ? entry + risk * InpRMultTP : entry - risk * InpRMultTP;

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

   out_rw = risk;
   //--- HEDGING: many positions share the symbol, so PositionSelect(_Symbol) is
   //--- ambiguous. The entry deal's POSITION_ID is the unique key for this fill.
   if(res.deal > 0 && HistorySelect(0, TimeCurrent()) && HistoryDealSelect(res.deal))
      return (long)HistoryDealGetInteger(res.deal, DEAL_POSITION_ID);
   return (long)res.order;
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

//+------------------------------------------------------------------+
//| MULTI-POSITION: act on EVERY unseen CF matching the setup-TF (+   |
//| cf_idx) filter. No one-at-a-time gate — each CF opens its own     |
//| independent position so the 2nd+ CFs of a cycle all fire.         |
//+------------------------------------------------------------------+
void ActOnNewEvents()
  {
   int n = ArraySize(g_events);
   for(int k = g_seen; k < n; k++)
     {
      FobEvent e = g_events[k];
      if(e.label != FOB_CF)              continue;
      if(e.setup_tf != g_setup_tf)       continue;
      if(InpCfIdxFilter > 0 && e.cf_idx != InpCfIdxFilter) continue;

      double rw = 0.0;
      long pid = FobOpenMarket(e.dir, InpFixedLot, e.level, rw);   // SL anchored to the CF level
      if(pid > 0)
         StashTrade(pid, rw, e);
     }
   g_seen = n;   // every event up to n has now been considered
  }

//+------------------------------------------------------------------+
//| Rebuild g_live_tf/g_live_seq = the (setup_tf, seq) cycles that    |
//| still have an OPEN position. Used so a live cycle's sequence dots  |
//| survive even after a newer cycle supersedes it.                   |
//+------------------------------------------------------------------+
void CollectLiveCycles()
  {
   ArrayResize(g_live_tf, 0);
   ArrayResize(g_live_seq, 0);
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong tk = PositionGetTicket(i);
      if(tk == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      if((ulong)PositionGetInteger(POSITION_MAGIC) != InpMagic) continue;
      long pid = (long)PositionGetInteger(POSITION_IDENTIFIER);
      //--- map this open position back to its stashed cycle (setup_tf, seq)
      for(int j = ArraySize(g_pid) - 1; j >= 0; j--)
         if(g_pid[j] == pid)
           {
            int m = ArraySize(g_live_tf);
            ArrayResize(g_live_tf, m + 1); ArrayResize(g_live_seq, m + 1);
            g_live_tf[m] = g_setuptf[j]; g_live_seq[m] = g_seq[j];
            break;
           }
     }
  }

//==================================================================//
//  STUDY MODE (T-170) — forward-excursion measurement, no orders.  //
//  RAW PRICE POINTS (v1.13.0: ATR removed).                        //
//==================================================================//

//--- Append the just-closed window to the study ledger arrays.
//--- next_dir: FOB_BULL/FOB_BEAR of the CF that ended it, or -1 if capped.
void CloseStudyWindow(const int next_dir)
  {
   if(!g_sw_open) return;
   int bars = (int)((TimeCurrent() - g_sw_open_ts) / PeriodSeconds(g_periods[g_setup_tf]));

   int m = ArraySize(sr_time);
   ArrayResize(sr_time, m+1);   ArrayResize(sr_dir, m+1);    ArrayResize(sr_cfidx, m+1);
   ArrayResize(sr_seq, m+1);    ArrayResize(sr_entry, m+1);
   ArrayResize(sr_mfe, m+1);    ArrayResize(sr_mae, m+1);    ArrayResize(sr_term, m+1);
   ArrayResize(sr_winbars, m+1);ArrayResize(sr_nextdir, m+1);
   sr_time[m]   = g_sw_cf_time; sr_dir[m]    = g_sw_dir;     sr_cfidx[m] = g_sw_cfidx;
   sr_seq[m]    = g_sw_seq;     sr_entry[m]  = g_sw_entry;
   sr_mfe[m]    = g_sw_mfe;     sr_mae[m]    = g_sw_mae;     sr_term[m]  = g_sw_term;
   sr_winbars[m]= bars;         sr_nextdir[m] = next_dir;

   g_sw_open = false;
  }

//--- Update the open window with the CURRENT tick (real-ticks model). Captures
//--- intrabar MFE/MAE in TRADEABLE terms (exit-side price), RAW POINTS.
void UpdateStudyWindow()
  {
   if(!g_sw_open) return;
   //--- COST-FREE measurement: mid price, NO spread. T-170 is DISCOVERY, not a G2 net ledger —
   //--- excursion is pure direction geometry; cost enters later at G2, never here.
   double mid = 0.5 * (SymbolInfoDouble(_Symbol, SYMBOL_ASK) + SymbolInfoDouble(_Symbol, SYMBOL_BID));
   double fav = (g_sw_dir == FOB_BULL) ? (mid - g_sw_entry) : (g_sw_entry - mid);
   if(fav  > g_sw_mfe) g_sw_mfe = fav;
   if(-fav > g_sw_mae) g_sw_mae = -fav;
   g_sw_term = fav;                                               // last seen -> terminal at close
   //--- cap: force-close after InpStudyCapBars setup-TF bars with no follow-up CF
   if((long)(TimeCurrent() - g_sw_open_ts) >= (long)InpStudyCapBars * PeriodSeconds(g_periods[g_setup_tf]))
      CloseStudyWindow(-1);
  }

//--- Open a fresh window anchored at this CF (mid fill, cost-free).
void OpenStudyWindow(const FobEvent &e)
  {
   g_sw_open    = true;
   g_sw_cf_time = e.bar_time;
   g_sw_open_ts = TimeCurrent();
   g_sw_dir     = e.dir;
   g_sw_cfidx   = e.cf_idx;
   g_sw_seq     = e.seq;
   g_sw_entry   = 0.5 * (SymbolInfoDouble(_Symbol, SYMBOL_ASK) + SymbolInfoDouble(_Symbol, SYMBOL_BID)); // mid, cost-free
   g_sw_mfe = 0.0; g_sw_mae = 0.0; g_sw_term = 0.0;
   UpdateStudyWindow();                                           // seed t=0
  }

//--- After classification: chain windows. Each new CF on the setup TF closes the
//--- prior window (ended BY that CF) and opens its own ("until next CF").
void StudyOnNewEvents()
  {
   int n = ArraySize(g_events);
   for(int k = g_seen; k < n; k++)
     {
      FobEvent e = g_events[k];
      if(e.label != FOB_CF)              continue;
      if(e.setup_tf != g_setup_tf)       continue;
      if(InpCfIdxFilter > 0 && e.cf_idx != InpCfIdxFilter) continue;
      if(g_sw_open) CloseStudyWindow(e.dir);   // prior window ends at this CF
      OpenStudyWindow(e);
     }
   g_seen = n;
  }

//--- Flush the study ledger (CSV) — one row per measured CF window. RAW POINTS.
void WriteStudyLedger()
  {
   if(g_sw_open) CloseStudyWindow(-1);          // close the final open window (capped at end-of-data)
   int rows = ArraySize(sr_time);

   string stamp = TimeToString(TimeCurrent(), TIME_DATE|TIME_MINUTES);
   StringReplace(stamp, ".", ""); StringReplace(stamp, ":", ""); StringReplace(stamp, " ", "_");
   string ver = FOB_VERSION; StringReplace(ver, ".", "");
   string fname = StringFormat("FOB\\fob_excursion_%s_v%s_%s_cf%d_%s.csv",
                               _Symbol, ver, FobTfName(g_setup_tf), InpCfIdxFilter, stamp);
   int h = FileOpen(fname, FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON, ',');
   if(h == INVALID_HANDLE)
     { PrintFormat("[FOB STUDY] ledger FileOpen failed (%d) for %s", GetLastError(), fname); return; }
   FileWrite(h, "cf_time","direction","cf_idx","seq","entry_px",
             "mfe_pts","mae_pts","terminal_pts","bars_to_next_cf","next_cf_dir");

   for(int i = 0; i < rows; i++)
     {
      string nd_s = (sr_nextdir[i] == FOB_BULL) ? "BUY" : (sr_nextdir[i] == FOB_BEAR) ? "SELL" : "CAP";
      FileWrite(h,
                TimeToString(sr_time[i], TIME_DATE|TIME_SECONDS),
                (sr_dir[i] == FOB_BULL ? "BUY" : "SELL"),
                (string)sr_cfidx[i], (string)sr_seq[i],
                DoubleToString(sr_entry[i], _Digits),
                DoubleToString(sr_mfe[i], _Digits), DoubleToString(sr_mae[i], _Digits),
                DoubleToString(sr_term[i], _Digits),
                (string)sr_winbars[i], nd_s);
     }
   FileClose(h);
   PrintFormat("[FOB STUDY] v%s ledger: %d windows (raw points) -> Common\\Files\\%s",
               FOB_VERSION, rows, fname);
  }

//+------------------------------------------------------------------+
//| Per tick: ingest newly closed bars (the 2 relevant TFs only),    |
//| classify in order, act on new CFs.                               |
//+------------------------------------------------------------------+
void OnTick()
  {
   MqlRates r[];
   ArraySetAsSeries(r, true);
   FobPending pend[];

   for(int gi = 0; gi < ArraySize(g_ingest); gi++)
     {
      int t = g_ingest[gi];
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
         pend[pi].zone  = g_tf[t].breaks[b].zone;
        }
     }

   int np = ArraySize(pend);
   if(np > 0)
     {
      FobSortPending(pend);
      for(int q = 0; q < np; q++)
         FobClassifyBreak(g_setup, FOB_N_TF, pend[q].tf, pend[q].dir, pend[q].swt, pend[q].bt,
                          pend[q].level, pend[q].close, pend[q].zone, g_events, InpPboNewestOnly);
     }

   if(InpStudyMode)
     {
      if(g_sw_open) UpdateStudyWindow();   // measure THIS tick before a new CF can replace the window
      StudyOnNewEvents();                  // chain windows on any new setup-TF CF
     }
   else
      ActOnNewEvents();

   //--- sequence dots (PBO/VR/CF) so fills can be eyeballed vs the sequence.
   //--- live cycles (open positions) are retained even after supersession.
   if(InpVisualize && np > 0)
     {
      CollectLiveCycles();
      g_vis.RedrawCurrentTF(g_events, ArraySize(g_events), g_live_tf, g_live_seq, ArraySize(g_live_tf));
      int ci = g_vis.ChartIdx();
      if(ci >= 0)
         g_vis.DrawStructure(g_tf[ci].swings, g_tf[ci].breaks);
      g_vis.DrawZones(g_events, ArraySize(g_events));   // 4-pointer L1/L2 bands
     }
  }

//+------------------------------------------------------------------+
//| Live TF switch: rebuild the sequence-dot layer for the new TF.   |
//+------------------------------------------------------------------+
void OnChartEvent(const int id, const long &lparam, const double &dparam, const string &sparam)
  {
   if(!InpVisualize || id != CHARTEVENT_CHART_CHANGE)
      return;
   g_vis.SyncChartTF();
   CollectLiveCycles();
   g_vis.RedrawCurrentTF(g_events, ArraySize(g_events), g_live_tf, g_live_seq, ArraySize(g_live_tf));
   int ci = g_vis.ChartIdx();
   if(ci >= 0)
      g_vis.DrawStructure(g_tf[ci].swings, g_tf[ci].breaks);
   g_vis.DrawZones(g_events, ArraySize(g_events));   // 4-pointer L1/L2 bands
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
//| on deinit. Lands in Common\Files\FOB.                            |
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
   string rmode = "cfz";   // CF_ZONE is the only risk mode
   string fname = StringFormat("FOB\\fob_trades_%s_v%s_%s_%s_cf%d_%s.csv",
                               _Symbol, ver, FobTfName(g_setup_tf), rmode, InpCfIdxFilter, stamp);
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
   if(InpStudyMode) WriteStudyLedger();
   else             WriteTradeLedger();
   g_vis.ClearAll();
  }
//+------------------------------------------------------------------+
