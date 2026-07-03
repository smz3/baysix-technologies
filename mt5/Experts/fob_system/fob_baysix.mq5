//+------------------------------------------------------------------+
//|                                                     fob_baysix.mq5 |
//|        FOB (First Opposite Breakout) — the SINGLE FOB EA.          |
//|                                                                    |
//|  ONE EA, three modes (InpMode) — merged 2026-07-02 (v1.28.0) so    |
//|  the oracle and the strategy can NEVER drift (they were two EAs    |
//|  with two different lifecycle engines, which is exactly why the     |
//|  live touch ladder disagreed). Detection + zone lifecycle now live  |
//|  in ONE place, run by ONE causal accumulator, for every mode:      |
//|                                                                    |
//|    • EMIT  (default) — READ-ONLY oracle. Ingests ALL 9 TFs, stamps  |
//|      the causal htf_state awareness snapshot, and writes the UTF-8  |
//|      lifecycle CSV -> Python. NO orders. Pristine + re-emittable    |
//|      for OOS (the reason the old standalone emitter existed — kept  |
//|      intact, now just a mode).                                     |
//|    • TRADE — the strategy. Ingests only the setup pair {n-1, n},   |
//|      opens a MARKET position per CF on the setup TF (multi-position,|
//|      hedging), SL beyond zone L2 by k*band, TP = RR*risk. Higher-TF |
//|      alignment is AWARENESS, not a gate (result_id 18).            |
//|    • STUDY — T-170 forward-excursion measurement (no orders): per   |
//|      CF, track MFE/MAE/terminal on real ticks until the next CF.    |
//|                                                                    |
//|  Run on REAL TICKS (Model=4) — FOB is a tick-resolution model and   |
//|  open-prices is BANNED (Syafiq 2026-06-29). Detection (swing/break) |
//|  is CLOSE-only, but the zone LIFECYCLE (touch ladder / counts / RT) |
//|  is accumulated CAUSALLY tick-by-tick (FobAcc*, v1.24.0) so the CSV  |
//|  and the live chart record true intra-bar ORDER.                   |
//|                                                                    |
//|  Modules — FOB owns EVERYTHING, nothing shared with brc_system:    |
//|    fob_types · fob_engine (shared ingest+sort) · fob_sequence ·     |
//|    fob_lifecycle (accumulator) · fob_entry · fob_ledger ·           |
//|    fob_study · fob_csv · fob_visual                                 |
//+------------------------------------------------------------------+
#property copyright "Baysix Technologies"
#property version   "1.32.0"        // MUST match FOB_VERSION (fob_types.mqh) — bump both together
#property strict

#include <fob_system/fob_types.mqh>
#include <fob_system/fob_version.mqh>   // AUTO-GEN git provenance — run gen_version.py fob before compile
#include <fob_system/fob_engine.mqh>    // SHARED detection runtime (ingest + sort)
#include <fob_system/fob_sequence.mqh>
#include <fob_system/fob_lifecycle.mqh> // TRUE-TICK accumulator (FobAccInit/OnTick/OnClose) — the ONE lifecycle engine
#include <fob_system/fob_entry.mqh>     // FobOpenMarket / FobFilling            (TRADE)
#include <fob_system/fob_ledger.mqh>    // FobTradeBook + Stash/CollectLiveCycles/WriteTradeLedger (TRADE)
#include <fob_system/fob_study.mqh>     // T-170 forward-excursion study         (STUDY)
#include <fob_system/fob_csv.mqh>       // event ledger CSV                       (EMIT)
//--- fob_visual.mqh is #included AFTER the input block below (not here) so the MODE +
//--- DETECTION inputs render FIRST on the tester Inputs tab and the drawing toggles LAST.

//--- THE MODE SWITCH — one EA, three jobs (merged 2026-07-02).
enum FOB_MODE
  {
   FOB_EMIT  = 0,   // read-only oracle: all 9 TFs + htf_state + CSV, NO orders (default)
   FOB_TRADE = 1,   // the strategy: market entry per CF on the setup TF
   FOB_STUDY = 2    // T-170 forward-excursion measurement, NO orders
  };
input group          "══════  MODE — pick the job  ══════"
input FOB_MODE InpMode = FOB_EMIT;      // MODE: EMIT=oracle CSV (no orders) · TRADE=orders · STUDY=excursion

input group          "══════  DETECTION — all modes  ══════"
input int    InpSwingWindow   = 3;      // DETECT: close-based pivot window (odd, >=3)
input int    InpMaxAge        = 0;      // DETECT: break age filter in bars (<=0 disables)
input bool   InpPboNewestOnly = true;   // DETECT: PBO = freshest source near CMP (reject same-dir reach-backs)

//--- setup/CF timeframe pair (TRADE + STUDY only). A PBO on the setup TF is confirmed by a
//--- CF on the TF one below it; the CF TF is always (setup TF - 1). EMIT ignores this (all 9 TFs).
enum FOB_TF_PAIR
  {
   FOB_TF_M5_M1   = 0,   // setup M5  -> CF on M1
   FOB_TF_M15_M5  = 1,   // setup M15 -> CF on M5
   FOB_TF_M30_M15 = 2,   // setup M30 -> CF on M15
   FOB_TF_H1_M30  = 3,   // setup H1  -> CF on M30  (baseline)
   FOB_TF_H4_H1   = 4,   // setup H4  -> CF on H1
   FOB_TF_D1_H4   = 5    // setup D1  -> CF on H4
  };
input group          "══════  TRADE / STUDY — setup pair (EMIT ignores: does all 9 TFs)  ══════"
input FOB_TF_PAIR InpTfPair    = FOB_TF_H1_M30; // TRADE/STUDY: setup TF -> CF on the TF one below
input int      InpCfIdxFilter  = 0;             // TRADE/STUDY: CF ordinal to trade (0 = ALL CFs)

input group          "══════  TRADE — orders only  ══════"
input double   InpSlBufferK    = 0.25;          // TRADE: SL beyond zone L2 by k*band, band=|L1-L2| (0 = at L2)
input double   InpRMultTP       = 1.0;          // TRADE: TP = RR * risk (1.0 = 1:1, the coin-flip null)
input double   InpFixedLot       = 0.01;        // TRADE: fixed lot (min lot at $50)
input ulong    InpMagic          = 3001;        // TRADE: FOB magic number

input group          "══════  STUDY — excursion only  ══════"
input int      InpStudyCapBars  = 48;           // STUDY: force-close window after this many setup-TF bars

//--- LIVE-chart tick warm-up (v1.31.0, task 223). On a fresh live attach the causal
//--- accumulator is blind to pre-attach history, so historical zones have empty touch
//--- ladders. We replay this many DAYS of REAL ticks through FobWarmFillTick once, so
//--- live == tester (tick-exact WHEN/WHERE) instead of guessing from bar wicks. 0 =
//--- unbounded (back to the oldest structure bar; slow on EMIT/high-TF attach). Ignored
//--- in the tester (already tick-causal from test-start). 30d covers M5..H4 fully.
input group          "══════  LIVE-chart only — ignored in the tester  ══════"
input int      InpTickWarmDays  = 30;           // LIVE: days of ticks to warm-up the touch ladder (0=unbounded)
input bool     InpDebugRt       = false;        // LIVE: print setup-TF VR t/rt ladder times vs bar_time after warm-up

//--- VISUAL/DRAWING inputs live in fob_visual.mqh; included HERE (after the block above) so
//--- MODE + DETECTION render first on the Inputs tab and the drawing toggles render last.
#include <fob_system/fob_visual.mqh>    // InpVisualize (MASTER draw toggle) + InpShow* toggles

//--- detection state (FobTfState/FobPending/FobIngestBar/FobSortPending/FobPeriods live in fob_engine.mqh)
FobTfState    g_tf[FOB_N_TF];
FobSetupState g_setup[FOB_N_TF];   // per-setup-TF state machine
FobEvent      g_events[];           // every classified event (CSV + redraw + trade source)
int           g_radius = 1;
string        g_runid  = "";
CFobVisual    g_vis;
ulong         g_last_sig = 0;       // last-drawn zone-state hash -> repaint only on change (no twitch)

//--- ONE lifecycle engine (v1.24.0, now every mode). g_acc[] is parallel to g_events[]
//--- (one accumulator per event); g_watch[] holds the indices of zones still LIVE (alive,
//--- or a VR counting RT) so the per-tick inner loop only touches a handful. g_last_form[t]
//--- gates per-TF ingest behind a real new-bar (cheap iTime vs a CopyRates every tick).
FobZoneAcc    g_acc[];              // parallel to g_events — persistent per-zone hysteresis/RT state
int           g_watch[];           // indices into g_events of zones still being watched
datetime      g_last_form[FOB_N_TF];// last seen forming-bar open time per TF (new-bar gate)
double        g_last_px = 0.0;      // last processed tick price (tick decimation)
bool          g_warmed  = false;    // LIVE: has the one-time historical-tick ladder warm-up run? (task 223)
//--- (task 226) chart period/type-switch cache: the globals SURVIVE OnDeinit+OnInit, so a switch
//--- on the SAME symbol can reuse the already-built + warmed state instead of a multi-second rebuild.
int           g_prev_reason   = -1;  // UninitializeReason() from the last OnDeinit (REASON_CHARTCHANGE => reuse candidate)
string        g_cached_symbol = "";  // symbol the cached state was built for (guards a symbol swap under CHARTCHANGE)

//--- INGEST set (mode-gated): EMIT = all 9 TFs (full storyline oracle); TRADE/STUDY = only
//--- {setup_tf-1, setup_tf} (byte-identical to the full classifier for this setup's events —
//--- a break on TF t only sets PBO(t) and VR/CF(t+1)). Populated in OnInit.
int           g_ingest[];
int           g_setup_tf = 4;       // setup TF index, derived from InpTfPair (TRADE/STUDY)

//--- trade + study bookkeeping (only active in the matching mode)
FobTradeBook  g_book;
FobStudyState g_study;
int           g_seen = 0;           // # events already acted on (watermark into g_events)
int           g_live_tf[];  int g_live_seq[];   // (setup_tf, seq) cycles with an OPEN position

//--- mode label for logs
string FobModeName(const FOB_MODE m)
  { return m == FOB_TRADE ? "TRADE" : (m == FOB_STUDY ? "STUDY" : "EMIT"); }

//+------------------------------------------------------------------+
int OnInit()
  {
   g_radius = FobSwingRadius(InpSwingWindow);
   if(g_radius < 0)
      return INIT_PARAMETERS_INCORRECT;
   g_setup_tf = (int)InpTfPair + 1;   // M5_M1=0->M5=1, ... D1_H4=5->D1=6

   //--- (task 226) CACHE FAST-PATH — a chart PERIOD switch (or template) on the SAME symbol re-fires
   //--- OnDeinit+OnInit but the globals SURVIVE. g_events is chart-period-INDEPENDENT (EMIT ingests
   //--- all 9 TFs; TRADE/STUDY key off InpTfPair, an INPUT — never the chart period), so if the
   //--- warm-up already completed we can REUSE the built + warmed ladder and just repaint the new
   //--- chart TF — no wipe, no multi-second re-warm. Guards: reason must be REASON_CHARTCHANGE (a
   //--- recompile=2 / param-change=5 / template=7 all fall through to the full rebuild below), the
   //--- symbol must be unchanged (CHARTCHANGE also fires on a symbol swap -> stale zones), and the
   //--- prior warm-up must have finished (g_warmed). Note: a chart TYPE toggle (candles/line) does
   //--- NOT reinit the EA at all -> it never paid the re-warm cost; only OnChartEvent repaints it.
   bool reuse = (g_prev_reason == REASON_CHARTCHANGE)
                && (g_cached_symbol == _Symbol)
                && g_warmed
                && (ArraySize(g_events) > 0);
   if(reuse)
     {
      g_vis.SyncChartTF();
      if(InpVisualize)
        {
         bool live = !MQLInfoInteger(MQL_TESTER);
         int  ci   = g_vis.ChartIdx();
         g_vis.DrawZones(g_events, ArraySize(g_events), g_live_tf, g_live_seq,
                         ArraySize(g_live_tf), live, g_last_px);
         if(ci >= 0)
            g_vis.DrawStructure(g_tf[ci].swings, g_tf[ci].breaks);
        }
      PrintFormat("[FOB %s] v%s CHART-SWITCH reuse — %d zones cached, no re-warm",
                  FobModeName(InpMode), FOB_VERSION, ArraySize(g_events));
      return INIT_SUCCEEDED;
     }

   //--- INGEST set by mode. EMIT = the full 9-TF oracle; TRADE/STUDY = the setup pair only.
   if(InpMode == FOB_EMIT)
     {
      ArrayResize(g_ingest, FOB_N_TF);
      for(int i = 0; i < FOB_N_TF; i++)
         g_ingest[i] = i;
     }
   else
     {
      ArrayResize(g_ingest, 2);
      g_ingest[0] = g_setup_tf - 1;
      g_ingest[1] = g_setup_tf;
     }

   //--- FULL reset (HARD): MT5 calls OnDeinit+OnInit on every chart period switch / recompile /
   //--- param change WITHOUT unloading, so the global arrays SURVIVE. Clear EVERYTHING so each
   //--- reinit rebuilds cleanly from the 64-bar window ([[mt5_oninit_full_reset]]).
   ArrayResize(g_events, 0);
   ArrayResize(g_acc,    0);
   ArrayResize(g_watch,  0);
   g_last_px = 0.0;
   g_seen    = 0;
   g_warmed  = false;   // re-warm the ladder from ticks on every (re)attach / period switch (task 223)
   g_cached_symbol = _Symbol;   // (task 226) stamp the symbol this fresh build is for -> the next CHARTCHANGE can reuse it
   for(int i = 0; i < FOB_N_TF; i++)
     {
      FobResetTfState(g_tf[i]);
      FobResetSetup(g_setup[i]);
      g_last_form[i] = 0;
     }
   //--- trade book + live-cycle scratch + study state
   ArrayResize(g_book.pid, 0);     ArrayResize(g_book.rw, 0);      ArrayResize(g_book.setuptf, 0);
   ArrayResize(g_book.eventtf, 0); ArrayResize(g_book.cfidx, 0);   ArrayResize(g_book.seq, 0);
   ArrayResize(g_book.dir, 0);
   ArrayResize(g_live_tf, 0);      ArrayResize(g_live_seq, 0);
   FobResetStudy(g_study);

   string ts = TimeToString(TimeCurrent(), TIME_DATE | TIME_MINUTES);
   StringReplace(ts, ".", "");
   StringReplace(ts, " ", "_");
   StringReplace(ts, ":", "");
   g_runid = "v" + FOB_VERSION + "_" + ts;

   g_vis.SyncChartTF();
   g_vis.ClearAll();

   PrintFormat("[FOB %s] v%s | git %s%s | built %s",
               FobModeName(InpMode), FOB_VERSION, FOB_GIT_SHA,
               (FOB_GIT_DIRTY ? "-DIRTY(exploratory)" : ""), FOB_BUILD_TIME);
   if(InpMode == FOB_EMIT)
      PrintFormat("[FOB EMIT] v%s init OK — %d TFs, swing_window=%d radius=%d runid=%s visualize=%s",
                  FOB_VERSION, FOB_N_TF, InpSwingWindow, g_radius, g_runid, (InpVisualize ? "ON" : "off"));
   else
      PrintFormat("[FOB %s] v%s init OK — setup_tf=%s -> CF on %s (ingest %s..%s, %d TF) | cf_filter=%d | SLbuf=%.2f TP=%.2fR | lot=%.2f magic=%I64u%s",
                  FobModeName(InpMode), FOB_VERSION, FobTfName(g_setup_tf), FobTfName(g_setup_tf - 1),
                  FobTfName(g_ingest[0]), FobTfName(g_ingest[ArraySize(g_ingest) - 1]), ArraySize(g_ingest),
                  InpCfIdxFilter, InpSlBufferK, InpRMultTP, InpFixedLot, InpMagic,
                  (InpMode == FOB_STUDY ? " | *** STUDY: NO ORDERS ***" : " | MULTI-POSITION"));
   return INIT_SUCCEEDED;
  }

//+------------------------------------------------------------------+
//| MULTI-POSITION (TRADE): act on EVERY unseen CF matching the       |
//| setup-TF (+ cf_idx) filter. Each CF opens its own independent     |
//| position (HEDGING). Higher-TF alignment is NOT a gate (rejected,  |
//| result_id 18) — awareness lives on the emitter's htf_state.       |
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
//| ONE-TIME LIVE TICK WARM-UP (v1.31.0, task 223). Replaces the       |
//| deleted bar-wick backfills. After the first tick has built the     |
//| historical zone STRUCTURE (structure is bar-close-correct), replay |
//| the real ticks over [now - InpTickWarmDays, now] and hand each to  |
//| FobWarmFillTick, so every pre-attach zone gets a TICK-EXACT touch  |
//| (and VR RT) ladder — the same one the tester builds causally. LIVE |
//| only; the tester replays every tick from test-start already.       |
//|                                                                    |
//| Returns false if the tick history isn't downloaded yet (retry next |
//| tick — don't mark warmed). Fills all TFs at once (not chart-TF     |
//| gated, unlike the old backfill), times-only + fill-only so it can  |
//| never clobber the live accumulator's counts.                      |
//+------------------------------------------------------------------+
bool FobWarmupReplay(const datetime warm_start)
  {
   int n = ArraySize(g_events);
   if(n <= 0)
      return true;                                  // nothing to warm

   MqlTick ticks[];
   ulong from_msc = (ulong)warm_start * 1000;       // 0 -> from the earliest available tick
   ulong to_msc   = (ulong)TimeCurrent() * 1000 + 1000;
   int got = CopyTicksRange(_Symbol, ticks, COPY_TICKS_ALL, from_msc, to_msc);
   if(got <= 0)
      return false;                                 // tick history not ready -> retry next tick

   for(int k = 0; k < got; k++)
     {
      double   px = ticks[k].bid;
      if(px <= 0.0)
         continue;                                  // ask-only tick (no bid) -> skip, matches the live bid path
      datetime tt = ticks[k].time;
      for(int i = 0; i < n; i++)
        {
         if(!g_events[i].zone.valid)
            continue;
         bool track_rt = (g_events[i].label == FOB_VR);
         //--- skip zones already fully stamped (live-formed, or filled earlier this pass)
         bool tdone = (g_events[i].zone.t1_time != 0 && g_events[i].zone.t2_time != 0 && g_events[i].zone.t3_time != 0);
         bool rdone = (!track_rt) || (g_events[i].zone.rt1_time != 0 && g_events[i].zone.rt2_time != 0 && g_events[i].zone.rt3_time != 0);
         if(tdone && rdone)
            continue;
         //--- RT opens only after the invalidating bar CLOSES (bar-open + its TF seconds) — the
         //--- tester boundary. 0 (still alive) -> every tick stays on the T-ladder.
         int tf_sec = PeriodSeconds(FobPeriods[g_events[i].event_tf]);
         datetime inval_close = 0;
         if(g_events[i].zone.invalidation_time > 0)
            inval_close = g_events[i].zone.invalidation_time + tf_sec;
         //--- (task 225b) T-phase starts at the break bar's CLOSE, not its OPEN: the tester seeds
         //--- the accumulator when the break bar CLOSES, so it never counts that bar's own impulse
         //--- plunge through L1/mid/L2 as touches. Starting at bar_time (open) collapsed t1/t2/t3
         //--- onto the break bar -> messed-up historical T-dots. Match the tester boundary.
         datetime brk_close = g_events[i].bar_time + tf_sec;
         FobWarmFillTick(g_events[i].zone, g_events[i].dir, g_events[i].level,
                         brk_close, inval_close, track_rt, px, tt);
        }
     }
   return true;
  }

//+------------------------------------------------------------------+
//| On each tick: ingest newly CLOSED bars for the mode's TF set,     |
//| classify in chronological order, seed accumulators, advance the   |
//| ONE lifecycle engine (close path + tick path), then dispatch the  |
//| mode's job (emit=nothing/CSV-at-deinit, trade=orders, study).     |
//+------------------------------------------------------------------+
void OnTick()
  {
   //--- LIVE flag: the bar-resolution ladder backfill (task 217) + intrabar-dead dimming
   //--- (task 216) are live-chart niceties only. The tester stays pure tick-causal so OOS
   //--- re-emit CSVs are byte-identical.
   bool live = !MQLInfoInteger(MQL_TESTER);

   //--- (1) INGEST — over the mode's TF set, gated per TF behind a REAL new bar. b0[t]
   //--- snapshots each TF's pre-ingest buffer size so the close path (3) sweeps exactly
   //--- the bars that closed this tick.
   int b0[FOB_N_TF];
   FobPending pend[];
   for(int gi = 0; gi < ArraySize(g_ingest); gi++)
     {
      int t = g_ingest[gi];
      b0[t] = ArraySize(g_tf[t].bt);
      datetime ft = iTime(_Symbol, FobPeriods[t], 0);
      if(ft == 0 || ft == g_last_form[t])
         continue;                                  // no new bar closed on this TF
      g_last_form[t] = ft;
      FobIngestTf(g_tf[t], _Symbol, FobPeriods[t], t, g_radius, InpMaxAge, pend);
     }

   //--- (2) CLASSIFY new breaks in true chronological order (bar_time asc, ties higher-TF-
   //--- first). EMIT stamps the causal htf_state awareness snapshot. Then SEED an accumulator
   //--- per newly-emitted event, run cycle-end eviction, and add valid zones to the watch list.
   int np = ArraySize(pend);
   if(np > 0)
     {
      FobSortPending(pend);
      for(int q = 0; q < np; q++)
        {
         int before = ArraySize(g_events);
         FobClassifyBreak(g_setup, FOB_N_TF, pend[q].tf, pend[q].dir, pend[q].swt, pend[q].bt,
                          pend[q].level, pend[q].close, pend[q].zone, g_events, InpPboNewestOnly);
         int after = ArraySize(g_events);
         if(InpMode == FOB_EMIT && after > before)
           {
            string snap = FobBuildHtfState(g_setup);
            for(int z = before; z < after; z++)
               g_events[z].htf_state = snap;
           }
        }
      //--- seed accumulators for the events just appended (g_acc lags g_events).
      int ne = ArraySize(g_events);
      int na = ArraySize(g_acc);
      if(ne > na)
        {
         ArrayResize(g_acc, ne);
         for(int i = na; i < ne; i++)
           {
            FobAccInit(g_events[i].zone, g_acc[i], g_events[i].dir, g_events[i].level);
            //--- CYCLE-END EVICTION (event-driven, NEVER a bar cap — [[fob_event_driven_no_bar_caps]]):
            //--- a new PBO opens cycle S on setup_TF X, so the PRIOR cycle's VR/CF on X are
            //--- storyline-dead -> drop them from g_watch (rows stay in g_events, data intact).
            //--- Bounds g_watch to the live cycle per TF -> linear runtime, kills zombie rt_count.
            //--- Runs BEFORE this PBO is added below; only evicts seq < S (never self-evicts).
            if(g_events[i].label == FOB_PBO)
              {
               int xtf = g_events[i].setup_tf;
               int xsq = g_events[i].seq;
               for(int w = ArraySize(g_watch) - 1; w >= 0; w--)
                 {
                  int wi = g_watch[w];
                  if(g_events[wi].setup_tf == xtf && g_events[wi].seq < xsq)
                    {
                     int last = ArraySize(g_watch) - 1;
                     g_watch[w] = g_watch[last];     // swap-remove (downward scan = safe)
                     ArrayResize(g_watch, last);
                    }
                 }
              }
            if(g_events[i].zone.valid)
              {
               int w = ArraySize(g_watch);
               ArrayResize(g_watch, w + 1, 64);
               g_watch[w] = i;
              }
           }
        }
     }

   //--- (3) CLOSE PATH — for each bar that just closed (per ingested TF, oldest->newest),
   //--- advance invalidation / vr_fresh / bars_alive on every watched zone of that TF. A dead
   //--- CF/PBO is swap-removed; a dead VR stays to count RT on ticks.
   for(int gi = 0; gi < ArraySize(g_ingest); gi++)
     {
      int t  = g_ingest[gi];
      int hi = ArraySize(g_tf[t].bt);
      for(int i = b0[t]; i < hi; i++)
        {
         datetime cbt = g_tf[t].bt[i];
         double   cbc = g_tf[t].bc[i];
         for(int w = ArraySize(g_watch) - 1; w >= 0; w--)
           {
            int idx = g_watch[w];
            if(g_events[idx].event_tf != t)
               continue;
            bool trackRt = (g_events[idx].label == FOB_VR);
            bool drop = FobAccOnClose(g_events[idx].zone, g_acc[idx], g_events[idx].dir,
                                      g_events[idx].level, g_events[idx].bar_time, cbc, cbt, trackRt);
            if(drop)
              {
               int last = ArraySize(g_watch) - 1;
               g_watch[w] = g_watch[last];          // safe: downward scan
               ArrayResize(g_watch, last);
              }
           }
        }
     }

   //--- (4) TICK PATH — advance the touch ladder / counts / RT on every watched zone off the
   //--- LIVE tick price, in true stream order. Skipped when the price is unchanged (XAUUSD
   //--- repeats ticks heavily) — the decimation that keeps a real-ticks run fast.
   MqlTick tk;
   if(SymbolInfoTick(_Symbol, tk) && tk.bid != g_last_px)
     {
      g_last_px = tk.bid;
      //--- (task 225) LIVE stray-dot fix: on a fresh attach this live tick would stamp EVERY
      //--- historical zone's touch/RT slot at NOW (current price already satisfies the level),
      //--- BEFORE the §5 warm-up replays the real ticks — and the warm-up is fill-only so it can
      //--- never overwrite the NOW value. Defer the accumulator loop while a warm-up is still
      //--- pending (live + visualize + not yet warmed). g_last_px is still updated above for the
      //--- price line. Tester (live=false) and live-TRADE-visualize-off (no warm-up) always run
      //--- -> CSV byte-identical, trading unaffected. Once warmed, §4 resumes on genuinely-new ticks.
      if(!(live && InpVisualize && !g_warmed))
        {
         int nw = ArraySize(g_watch);
         for(int w = 0; w < nw; w++)
           {
            int idx = g_watch[w];
            bool trackRt = (g_events[idx].label == FOB_VR);
            FobAccOnTick(g_events[idx].zone, g_acc[idx], g_events[idx].dir,
                         g_events[idx].level, tk.bid, tk.time, trackRt);
           }
        }
     }

   //--- (DISPATCH) the mode's job. EMIT does nothing here (CSV written at OnDeinit).
   if(InpMode == FOB_STUDY)
     {
      if(g_study.sw_open) UpdateStudyWindow(g_study, g_setup_tf, InpStudyCapBars);  // measure THIS tick first
      StudyOnNewEvents(g_study, g_events, g_seen, g_setup_tf, InpCfIdxFilter, InpStudyCapBars);
     }
   else if(InpMode == FOB_TRADE)
      ActOnNewEvents();

   //--- (5) VISUAL (live only in practice; OFF in the capture tester). Zones are already
   //--- stamped by the accumulator across all ingested TFs — just redraw on a state change,
   //--- NO replay (UpdateZoneLifecycles/LiveTouchForming would RESET and clobber it).
   if(InpVisualize)
     {
      if(InpMode == FOB_TRADE)
         CollectLiveCycles(g_book, InpMagic, g_live_tf, g_live_seq);
      int ci = g_vis.ChartIdx();
      //--- ONE-TIME historical-tick warm-up (task 223, v1.31.0) — replaces the deleted wick
      //--- backfills. Replays real ticks through FobWarmFillTick so every pre-attach zone gets
      //--- a TICK-EXACT touch/RT ladder (live == tester). LIVE only; retries each tick until the
      //--- tick history is downloaded. Fills all TFs, not just the chart TF.
      bool just_warmed = false;
      if(live && !g_warmed)
        {
         datetime ws = (InpTickWarmDays > 0) ? TimeCurrent() - (datetime)InpTickWarmDays * 86400 : 0;
         if(FobWarmupReplay(ws))
           {
            g_warmed    = true;
            just_warmed = true;                       // force one repaint so the filled dots appear
            PrintFormat("[FOB %s] tick warm-up complete — %d zones, window=%s",
                        FobModeName(InpMode), ArraySize(g_events),
                        (InpTickWarmDays > 0 ? (string)InpTickWarmDays + "d" : "unbounded"));
            //--- (task 225 verify) dump the low-TF (M1/M5/M15) VR ladders right after warm-up:
            //--- every t*/rt* time MUST be historical (< now), never ≈now. A ≈now stamp = the
            //--- §4 leak this fix closes still firing. Remove once confirmed green.
            if(InpDebugRt)
              {
               int ndbg = ArraySize(g_events);
               for(int i = 0; i < ndbg; i++)
                 {
                  if(g_events[i].label != FOB_VR || g_events[i].event_tf > 2)
                     continue;                          // VRs on M1/M5/M15 only (event_tf 0/1/2)
                  PrintFormat("[FOB RT-DBG] VR %s seq=%d bar=%s | t1=%s t2=%s t3=%s | rt1=%s rt2=%s rt3=%s | inval=%s",
                              FobTfName(g_events[i].event_tf), g_events[i].seq,
                              TimeToString(g_events[i].bar_time, TIME_DATE | TIME_MINUTES),
                              TimeToString(g_events[i].zone.t1_time, TIME_DATE | TIME_MINUTES),
                              TimeToString(g_events[i].zone.t2_time, TIME_DATE | TIME_MINUTES),
                              TimeToString(g_events[i].zone.t3_time, TIME_DATE | TIME_MINUTES),
                              TimeToString(g_events[i].zone.rt1_time, TIME_DATE | TIME_MINUTES),
                              TimeToString(g_events[i].zone.rt2_time, TIME_DATE | TIME_MINUTES),
                              TimeToString(g_events[i].zone.rt3_time, TIME_DATE | TIME_MINUTES),
                              TimeToString(g_events[i].zone.invalidation_time, TIME_DATE | TIME_MINUTES));
                 }
              }
           }
        }

      ulong sig = g_vis.StateSignature(g_events, ArraySize(g_events), g_last_px)
                  ^ ((ulong)ArraySize(g_live_tf) * 2654435761ULL);   // live-cycle open/close flips repaint (TRADE)
      if(np > 0 || sig != g_last_sig || just_warmed)
        {
         g_vis.DrawZones(g_events, ArraySize(g_events), g_live_tf, g_live_seq, ArraySize(g_live_tf),
                         live, g_last_px);                        // ClearAll + zone bands + edge labels
         if(ci >= 0)
            g_vis.DrawStructure(g_tf[ci].swings, g_tf[ci].breaks); // swings + raw breaks on top
         g_last_sig = sig;
        }
     }
  }

//+------------------------------------------------------------------+
//| Live TF switch: rebuild the visual layer for the new chart TF.    |
//+------------------------------------------------------------------+
void OnChartEvent(const int id, const long &lparam, const double &dparam, const string &sparam)
  {
   if(!InpVisualize || id != CHARTEVENT_CHART_CHANGE)
      return;
   g_vis.SyncChartTF();
   if(InpMode == FOB_TRADE)
      CollectLiveCycles(g_book, InpMagic, g_live_tf, g_live_seq);
   bool live = !MQLInfoInteger(MQL_TESTER);
   int ci = g_vis.ChartIdx();
   //--- (v1.31.0, task 223) no per-TF backfill here anymore — the historical-tick warm-up
   //--- (FobWarmupReplay, OnTick) already filled every TF's ladder tick-exact, and a period
   //--- switch re-fires OnInit -> g_warmed=false -> the next tick re-warms. Just redraw.
   g_vis.DrawZones(g_events, ArraySize(g_events), g_live_tf, g_live_seq, ArraySize(g_live_tf),
                   live, g_last_px);
   if(ci >= 0)
      g_vis.DrawStructure(g_tf[ci].swings, g_tf[ci].breaks);
  }

//+------------------------------------------------------------------+
//| On detach/recompile: wipe chart objects, then write the mode's    |
//| output — EMIT = event ledger CSV, STUDY = excursion ledger,       |
//| TRADE = trade ledger.                                            |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   g_prev_reason = reason;   // (task 226) OnInit reads this: REASON_CHARTCHANGE + same symbol -> reuse the cache
   g_vis.ClearAll();         // wipe chart objects before any early-return

   //--- (task 226) a chart period/template switch keeps the globals alive for OnInit to reuse, so
   //--- SKIP the ledger dump here — it is the SAME data and dumping it on every switch is the other
   //--- half of the switch lag. The ledger is still written on a real exit (remove/close/recompile).
   if(reason == REASON_CHARTCHANGE)
      return;

   if(InpMode == FOB_STUDY)
     {
      WriteStudyLedger(g_study, g_setup_tf, InpCfIdxFilter);
      return;
     }
   if(InpMode == FOB_TRADE)
     {
      WriteTradeLedger(g_book, InpMagic, g_setup_tf, InpSlBufferK, InpRMultTP, InpCfIdxFilter);
      return;
     }

   //--- EMIT: dump every classified event to the run CSV. Lifecycle was accumulated CAUSALLY
   //--- tick-by-tick during the run (FobAcc*) — serialize AS-IS, no replay.
   int fh = FobCsvOpen(_Symbol, g_runid);
   if(fh == INVALID_HANDLE)
      return;
   int n = ArraySize(g_events);
   for(int e = 0; e < n; e++)
      FobCsvWriteEvent(fh, e + 1, g_events[e]);
   FileClose(fh);
   PrintFormat("[FOB EMIT] v%s done — %d events across %d TFs -> Common/Files/FOB/fob_capture_%s_%s.csv",
               FOB_VERSION, n, FOB_N_TF, _Symbol, g_runid);
  }
//+------------------------------------------------------------------+
