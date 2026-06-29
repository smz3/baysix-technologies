//+------------------------------------------------------------------+
//|                                                    fob_trader.mq5  |
//|        FOB TRADER — the strategy EA (sibling of the emitter).      |
//|                                                                    |
//|  Reuses the emitter's EXACT detection pipeline via the SHARED      |
//|  fob_engine.mqh (same FobIngestBar/FobSortPending the oracle runs) |
//|  so the trade triggers on the SAME PBO/VR/CF events. The emitter   |
//|  stays read-only; this EA adds orders.                             |
//|                                                                    |
//|  Modules (extracted 2026-06-29, v1.23.0):                          |
//|    fob_engine  — shared detection runtime (structs + ingest+sort)  |
//|    fob_entry   — the swappable market-entry module (SL/TP)         |
//|    fob_ledger  — per-trade stash (FobTradeBook) + the trades CSV   |
//|    fob_study   — T-170 forward-excursion study mode (no orders)    |
//|  This file = inputs + globals + OnInit/OnTick orchestration +      |
//|  ActOnNewEvents (the strategy glue).                               |
//|                                                                    |
//|  PURE PRICE-ACTION (v1.13.0): ZERO indicators.                     |
//|  Trade atom: trigger = every CF on g_setup_tf; entry = MARKET on   |
//|  CF detection; SL = beyond zone L2 by InpSlBufferK*band; TP =      |
//|  InpRMultTP*risk. MULTI-POSITION (v1.13.0): every CF opens its own |
//|  independent position (HEDGING). Higher-TF alignment is AWARENESS, |
//|  NOT a trade gate (removed v1.22.0, result_id 18).                 |
//|                                                                    |
//|  Trust: the MT5 tester is the arbiter. Run on the M5 chart; trader |
//|  backtests on REAL TICKS. Native trade-level bands disabled; the   |
//|  fob_visual sequence dots render so fills can be eyeballed.        |
//+------------------------------------------------------------------+
#property copyright "Baysix Technologies"
#property version   "1.23.0"        // MUST match FOB_VERSION (fob_types.mqh) — bump together
#property strict

#include <fob_system/fob_types.mqh>
#include <fob_system/fob_version.mqh>   // AUTO-GEN git provenance — run gen_version.py fob before compile
#include <fob_system/fob_engine.mqh>    // SHARED detection runtime (with the emitter)
#include <fob_system/fob_sequence.mqh>
#include <fob_system/fob_entry.mqh>     // FobOpenMarket / FobFilling
#include <fob_system/fob_ledger.mqh>    // FobTradeBook + StashTrade/CtxForPos/CollectLiveCycles/WriteTradeLedger
#include <fob_system/fob_study.mqh>     // T-170 forward-excursion study mode
#include <fob_system/fob_visual.mqh>    // sequence dots + InpVisualize master toggle

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

//--- trade atom. SL = beyond the zone FAR edge (L2), pushed by k*band.
input FOB_TF_PAIR InpTfPair   = FOB_TF_H1_M30; // setup TF -> CF on the TF one below
input int      InpCfIdxFilter = 0;            // CF ordinal to trade (0 = ALL CFs; T2 sweeps 1/2/3)
input double   InpSlBufferK   = 0.25;         // SL beyond zone L2 by k*band, band=|L1-L2| (0 = at L2)
input double   InpRMultTP      = 1.0;         // TP = RR * risk (1.0 = 1:1, the coin-flip null)
input double   InpFixedLot      = 0.01;       // min lot at $50
input ulong    InpMagic         = 3001;       // FOB trader magic

//--- NOTE: the full-stack STORYLINE ALIGNMENT GATE (task 188) was REMOVED 2026-06-29.
//--- It was REJECTED (result_id 18): in FOB, higher-TF alignment is AWARENESS, not a trade
//--- gate. The awareness snapshot now lives on the EMITTER (fob_events.htf_state).

//--- forward-excursion STUDY mode (T-170). NO orders: per CF on g_setup_tf, anchor at the
//--- CF mid price and track running MFE/MAE/terminal on REAL TICKS until the NEXT CF on the
//--- setup TF (any cf_idx) — or a cap. COST-FREE (mid price). Reported in RAW PRICE POINTS.
input bool     InpStudyMode    = false;       // [study] forward-excursion measurement (no trades)
input int      InpStudyCapBars = 48;          // [study] force-close window after this many setup-TF bars

//--- detection state (FobTfState/FobPending/FobIngestBar/FobSortPending live in fob_engine.mqh)
FobTfState    g_tf[FOB_N_TF];
FobSetupState g_setup[FOB_N_TF];
FobEvent      g_events[];
int           g_radius   = 1;
int           g_seen     = 0;           // # events already acted on (watermark into g_events)
int           g_ingest[];               // ONLY the TF indices we ingest = {setup_tf-1, setup_tf}
int           g_setup_tf   = 4;         // setup TF index, derived from InpTfPair in OnInit
CFobVisual    g_vis;
ulong         g_last_sig = 0;           // last-drawn zone-state hash -> repaint only on change

//--- trade bookkeeping (fob_ledger.mqh) + study state (fob_study.mqh)
FobTradeBook  g_book;
FobStudyState g_study;

//--- live-cycle scratch (rebuilt each redraw): (setup_tf, seq) pairs that still
//--- have an OPEN position — their sequence dots must survive supersession.
int    g_live_tf[];  int g_live_seq[];

//+------------------------------------------------------------------+
int OnInit()
  {
   g_radius = FobSwingRadius(InpSwingWindow);
   if(g_radius < 0)
      return INIT_PARAMETERS_INCORRECT;
   g_setup_tf = (int)InpTfPair + 1;   // M5_M1=0->M5=1, ... D1_H4=5->D1=6

   //--- ingest ONLY the setup TF and its n-1 (CF) TF: byte-identical to the full
   //--- classifier for this setup's events (a break on TF t only sets PBO(t) and
   //--- VR/CF(t+1)) — so {setup_tf-1, setup_tf} fully determines every setup_tf event.
   ArrayResize(g_ingest, 2);
   g_ingest[0] = g_setup_tf - 1;
   g_ingest[1] = g_setup_tf;

   //--- FULL reset (HARD): MT5 reinits WITHOUT unloading -> globals survive.
   ArrayResize(g_events, 0);
   g_seen = 0;
   for(int i = 0; i < FOB_N_TF; i++)
     {
      FobResetTfState(g_tf[i]);
      FobResetSetup(g_setup[i]);
     }
   //--- trade book + live-cycle scratch + study state
   ArrayResize(g_book.pid, 0);     ArrayResize(g_book.rw, 0);      ArrayResize(g_book.setuptf, 0);
   ArrayResize(g_book.eventtf, 0); ArrayResize(g_book.cfidx, 0);   ArrayResize(g_book.seq, 0);
   ArrayResize(g_book.dir, 0);
   ArrayResize(g_live_tf, 0);      ArrayResize(g_live_seq, 0);
   FobResetStudy(g_study);

   //--- kill MT5's native trade-level bands + bid/ask/OHLC lines for focus; our dots stay.
   ChartSetInteger(0, CHART_SHOW_TRADE_LEVELS, false);
   ChartSetInteger(0, CHART_SHOW_ASK_LINE, false);
   ChartSetInteger(0, CHART_SHOW_BID_LINE, false);
   ChartSetInteger(0, CHART_SHOW_OHLC, false);
   g_vis.SyncChartTF();
   g_vis.ClearAll();

   string ingest_lo = FobTfName(g_ingest[0]);
   string ingest_hi = FobTfName(g_ingest[ArraySize(g_ingest) - 1]);
   PrintFormat("[FOB TRADER] v%s | git %s%s | built %s",
               FOB_VERSION, FOB_GIT_SHA,
               (FOB_GIT_DIRTY ? "-DIRTY(exploratory)" : ""), FOB_BUILD_TIME);
   PrintFormat("[FOB TRADER] v%s init OK — setup_tf=%s -> CF on %s (ingest %s..%s, %d TF) | cf_filter=%d | CF_ZONE SLbuf=%.2f TP=%.2fR | lot=%.2f magic=%I64u | MULTI-POSITION",
               FOB_VERSION, FobTfName(g_setup_tf), FobTfName(g_setup_tf - 1),
               ingest_lo, ingest_hi, ArraySize(g_ingest),
               InpCfIdxFilter, InpSlBufferK, InpRMultTP, InpFixedLot, InpMagic);
   if(InpStudyMode)
      PrintFormat("[FOB TRADER] *** STUDY MODE (T-170) *** NO ORDERS — per CF: MFE/MAE/terminal (RAW POINTS) until next CF, cap=%d %s bars",
                  InpStudyCapBars, FobTfName(g_setup_tf));
   return INIT_SUCCEEDED;
  }

//+------------------------------------------------------------------+
//| MULTI-POSITION: act on EVERY unseen CF matching the setup-TF (+   |
//| cf_idx) filter. No one-at-a-time gate — each CF opens its own     |
//| independent position so the 2nd+ CFs of a cycle all fire. Higher- |
//| TF alignment is NOT a gate (rejected, result_id 18) — awareness   |
//| lives on the emitter's htf_state snapshot instead.                |
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
      long pid = FobOpenMarket(e, InpFixedLot, InpSlBufferK, InpRMultTP, InpMagic, rw);
      if(pid > 0)
         StashTrade(g_book, pid, rw, e);
     }
   g_seen = n;   // every event up to n has now been considered
  }

//+------------------------------------------------------------------+
//| Per tick: ingest newly closed bars (the 2 relevant TFs only) via |
//| the shared engine, classify in order, dispatch study vs trade.   |
//+------------------------------------------------------------------+
void OnTick()
  {
   FobPending pend[];
   for(int gi = 0; gi < ArraySize(g_ingest); gi++)
     {
      int t = g_ingest[gi];
      FobIngestTf(g_tf[t], _Symbol, FobPeriods[t], t, g_radius, InpMaxAge, pend);
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
      if(g_study.sw_open) UpdateStudyWindow(g_study, g_setup_tf, InpStudyCapBars);  // measure THIS tick first
      StudyOnNewEvents(g_study, g_events, g_seen, g_setup_tf, InpCfIdxFilter, InpStudyCapBars);
     }
   else
      ActOnNewEvents();

   //--- unified zone layer (PBO/VR/CF bands + dots) so fills can be eyeballed.
   //--- LIVE: repaint EVERY tick so the forming-bar touch shows; TESTER: only when
   //--- a new event classified (np>0) — keeps the visual replay fast.
   bool live = !MQLInfoInteger(MQL_TESTER);
   if(InpVisualize && (np > 0 || live))
     {
      CollectLiveCycles(g_book, InpMagic, g_live_tf, g_live_seq);
      int ci = g_vis.ChartIdx();
      if(ci >= 0)                                          // stamp T-touches FIRST (zone [Tn] + alive)
        {
         g_vis.UpdateZoneLifecycles(g_events, ArraySize(g_events),
                                    g_tf[ci].bt, g_tf[ci].bh, g_tf[ci].bl, g_tf[ci].bc, ArraySize(g_tf[ci].bt));
         MqlRates f[];
         if(live && CopyRates(_Symbol, FobPeriods[ci], 0, 1, f) == 1)
            g_vis.LiveTouchForming(g_events, ArraySize(g_events), f[0].time, f[0].high, f[0].low);
        }
      //--- repaint ONLY on a real change (new event, new touch, or a live-cycle open/close).
      ulong sig = g_vis.StateSignature(g_events, ArraySize(g_events))
                  ^ ((ulong)ArraySize(g_live_tf) * 2654435761ULL);
      if(np > 0 || sig != g_last_sig)
        {
         g_vis.DrawZones(g_events, ArraySize(g_events), g_live_tf, g_live_seq, ArraySize(g_live_tf));
         if(ci >= 0)
            g_vis.DrawStructure(g_tf[ci].swings, g_tf[ci].breaks);
         g_last_sig = sig;
        }
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
   CollectLiveCycles(g_book, InpMagic, g_live_tf, g_live_seq);
   int ci = g_vis.ChartIdx();
   if(ci >= 0)                                          // stamp T-touches FIRST (zone [Tn] + alive)
      g_vis.UpdateZoneLifecycles(g_events, ArraySize(g_events),
                                 g_tf[ci].bt, g_tf[ci].bh, g_tf[ci].bl, g_tf[ci].bc, ArraySize(g_tf[ci].bt));
   g_vis.DrawZones(g_events, ArraySize(g_events), g_live_tf, g_live_seq, ArraySize(g_live_tf));
   if(ci >= 0)
      g_vis.DrawStructure(g_tf[ci].swings, g_tf[ci].breaks);
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   if(InpStudyMode) WriteStudyLedger(g_study, g_setup_tf, InpCfIdxFilter);
   else             WriteTradeLedger(g_book, InpMagic, g_setup_tf, InpSlBufferK, InpRMultTP, InpCfIdxFilter);
   g_vis.ClearAll();
  }
//+------------------------------------------------------------------+
