//+------------------------------------------------------------------+
//|                                                     fob_baysix.mq5 |
//|        FOB (First Opposite Breakout) classifier EMITTER.          |
//|                                                                    |
//|  ONE job: across 9 TFs (M1..MN1), detect raw breakouts (FOB's OWN  |
//|  swing + breakout detection, fob_swings/fob_breakouts) and CLASSIFY|
//|  chronological order as PBO / VR / HRCF / CF, then (a) draw them   |
//|  colour-coded and (b) emit a UTF-8 event ledger to CSV. NO orders, |
//|  NO money — this is the read-only oracle that feeds Python.        |
//|                                                                    |
//|  Run on REAL TICKS (Model=4) — FOB is a tick-resolution model and   |
//|  open-prices is BANNED (Syafiq 2026-06-29). Detection (swing/break) |
//|  is CLOSE-only, but the zone LIFECYCLE (touch ladder / counts / RT) |
//|  is now accumulated CAUSALLY tick-by-tick (FobAcc*, v1.24.0 task    |
//|  197) so the CSV records true intra-bar ORDER. Per tick: each TF's  |
//|  newly-closed bars are ingested (new-bar-gated), the new breaks are |
//|  merged + sorted (bar_time asc, ties higher-TF-first) and fed to    |
//|  the classifier in chronological order — the ordering guard that    |
//|  kills the ORB unsorted-tick look-ahead — then the close path and   |
//|  tick path advance each watched zone's lifecycle.                  |
//|                                                                    |
//|  Modules — FOB owns EVERYTHING, nothing shared with brc_system:    |
//|    fob_types (own swing/break/dir types) · fob_swings · fob_break-  |
//|    outs · fob_sequence · fob_csv · fob_visual                      |
//+------------------------------------------------------------------+
#property copyright "Baysix Technologies"
#property version   "1.24.0"        // MUST match FOB_VERSION (fob_types.mqh) — bump both together
#property strict

#include <fob_system/fob_types.mqh>
#include <fob_system/fob_engine.mqh>      // SHARED detection runtime (structs + ingest+sort) — with the trader
#include <fob_system/fob_sequence.mqh>
#include <fob_system/fob_lifecycle.mqh>   // TRUE-TICK accumulator (FobAccInit/OnTick/OnClose) — zone lifecycle source
#include <fob_system/fob_csv.mqh>
#include <fob_system/fob_visual.mqh>      // InpVisualize master toggle (default on)

input int  InpSwingWindow    = 3;     // close-based pivot window (odd, >=3; live BRC = 3)
input int  InpMaxAge         = 0;     // break age filter in bars (<=0 disables)
input bool InpPboNewestOnly  = true;  // PBO = freshest source near CMP (reject same-dir reach-backs)

//--- detection state (FobTfState/FobPending/FobIngestBar/FobSortPending/FobPeriods
//--- all live in fob_engine.mqh, shared byte-identically with the trader)
FobTfState    g_tf[FOB_N_TF];
FobSetupState g_setup[FOB_N_TF];   // per-setup-TF state machine
FobEvent      g_events[];           // every classified event (CSV + redraw source)
int           g_radius = 1;
string        g_runid  = "";
CFobVisual    g_vis;
ulong         g_last_sig = 0;       // last-drawn zone-state hash -> repaint only on change (no twitch)

//--- TRUE-TICK accumulator state (v1.24.0, task 197). g_acc[] is parallel to
//--- g_events[] (one accumulator per event); g_watch[] holds the indices of
//--- zones still LIVE (alive, or a VR counting RT) so the per-tick inner loop
//--- only touches a handful, never the full ledger. g_last_form[t] gates per-TF
//--- ingest behind a real new-bar (cheap iTime vs a CopyRates every tick).
FobZoneAcc    g_acc[];              // parallel to g_events — persistent per-zone hysteresis/RT state
int           g_watch[];           // indices into g_events of zones still being watched
datetime      g_last_form[FOB_N_TF];// last seen forming-bar open time per TF (new-bar gate)
double        g_last_px = 0.0;      // last processed tick price (tick decimation)

//+------------------------------------------------------------------+
int OnInit()
  {
   g_radius = FobSwingRadius(InpSwingWindow);
   if(g_radius < 0)
      return INIT_PARAMETERS_INCORRECT;

   //--- FULL reset (HARD): MT5 calls OnDeinit+OnInit on every chart period
   //--- switch / recompile / param change WITHOUT unloading the program, so
   //--- the global arrays SURVIVE. If we only zero last_time+g_setup (the old
   //--- bug), the next tick re-ingests all 64 bars into the already-populated
   //--- buffers -> duplicate bars (corrupt pivots -> dots misplaced) and a
   //--- restarted seq piled onto a stale g_events (seq dupes -> visual never
   //--- locks the active cycle -> "pending" stuck). Clear EVERYTHING so each
   //--- reinit rebuilds cleanly from the 64-bar window.
   ArrayResize(g_events, 0);
   ArrayResize(g_acc,    0);
   ArrayResize(g_watch,  0);
   g_last_px = 0.0;
   for(int i = 0; i < FOB_N_TF; i++)
     {
      FobResetTfState(g_tf[i]);
      FobResetSetup(g_setup[i]);
      g_last_form[i] = 0;
     }

   string ts = TimeToString(TimeCurrent(), TIME_DATE | TIME_MINUTES);
   StringReplace(ts, ".", "");
   StringReplace(ts, " ", "_");
   StringReplace(ts, ":", "");
   g_runid = "v" + FOB_VERSION + "_" + ts;

   g_vis.SyncChartTF();
   g_vis.ClearAll();

   PrintFormat("[FOB] fob_baysix v%s init OK — %d TFs, swing_window=%d radius=%d runid=%s visualize=%s",
               FOB_VERSION, FOB_N_TF, InpSwingWindow, g_radius, g_runid, (InpVisualize ? "ON" : "off"));
   return INIT_SUCCEEDED;
  }

//+------------------------------------------------------------------+
//| On each tick: ingest newly CLOSED bars for every TF, collect the  |
//| new raw breaks, sort them globally, then classify in order.       |
//| Ingest + sort are the SHARED engine (fob_engine.mqh).             |
//+------------------------------------------------------------------+
void OnTick()
  {
   //--- (1) INGEST — gated per TF behind a REAL new bar (cheap iTime vs a CopyRates
   //--- every tick). b0[t] snapshots each TF's pre-ingest buffer size so the close
   //--- path (3) can sweep exactly the bars that closed this tick.
   int b0[FOB_N_TF];
   FobPending pend[];
   for(int t = 0; t < FOB_N_TF; t++)
     {
      b0[t] = ArraySize(g_tf[t].bt);
      datetime ft = iTime(_Symbol, FobPeriods[t], 0);
      if(ft == 0 || ft == g_last_form[t])
         continue;                                  // no new bar closed on this TF
      g_last_form[t] = ft;
      FobIngestTf(g_tf[t], _Symbol, FobPeriods[t], t, g_radius, InpMaxAge, pend);
     }

   //--- (2) CLASSIFY new breaks in true chronological order (bar_time asc, ties higher-
   //--- TF-first), stamp the causal htf_state snapshot, then SEED an accumulator per
   //--- newly-emitted event and add the valid zones to the live watch list.
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
         if(after > before)
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
            if(g_events[i].zone.valid)
              {
               int w = ArraySize(g_watch);
               ArrayResize(g_watch, w + 1, 64);
               g_watch[w] = i;
              }
           }
        }
     }

   //--- (3) CLOSE PATH — for each bar that just closed (per TF, oldest->newest), advance
   //--- invalidation / vr_fresh / bars_alive on every watched zone of that TF. A dead
   //--- CF/PBO is swap-removed from the watch list; a dead VR stays to count RT on ticks.
   for(int t = 0; t < FOB_N_TF; t++)
     {
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
               g_watch[w] = g_watch[last];          // safe: downward scan, swapped-in was already done
               ArrayResize(g_watch, last);
              }
           }
        }
     }

   //--- (4) TICK PATH — advance the touch ladder / counts / RT on every watched zone off
   //--- the LIVE tick price, in true stream order (this is the intra-bar ORDER the old
   //--- closed-bar replay could not resolve). Skipped when the price is unchanged
   //--- (XAUUSD repeats ticks heavily) — the decimation that keeps a real-ticks run fast.
   MqlTick tk;
   if(SymbolInfoTick(_Symbol, tk) && tk.bid != g_last_px)
     {
      g_last_px = tk.bid;
      int nw = ArraySize(g_watch);
      for(int w = 0; w < nw; w++)
        {
         int idx = g_watch[w];
         bool trackRt = (g_events[idx].label == FOB_VR);
         FobAccOnTick(g_events[idx].zone, g_acc[idx], g_events[idx].dir,
                      g_events[idx].level, tk.bid, tk.time, trackRt);
        }
     }

   //--- (5) VISUAL (live only; OFF in the capture tester). Zones are already stamped by
   //--- the accumulator across ALL TFs, so we just redraw on a state change — NO replay
   //--- (UpdateZoneLifecycles/LiveTouchForming would RESET and clobber the accumulator).
   if(InpVisualize)
     {
      ulong sig = g_vis.StateSignature(g_events, ArraySize(g_events));
      if(np > 0 || sig != g_last_sig)
        {
         g_vis.DrawZones(g_events, ArraySize(g_events));           // ClearAll + zone bands + edge labels
         int ci = g_vis.ChartIdx();
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
   //--- zones are kept current by the tick accumulator (all TFs) — just redraw for the
   //--- new chart TF; NO replay (UpdateZoneLifecycles would reset the accumulated life).
   g_vis.DrawZones(g_events, ArraySize(g_events));              // ClearAll + zone bands + edge labels
   int ci = g_vis.ChartIdx();
   if(ci >= 0)
      g_vis.DrawStructure(g_tf[ci].swings, g_tf[ci].breaks);   // swings + raw breaks on top
  }

//+------------------------------------------------------------------+
//| Dump every classified event to the run CSV.                       |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   g_vis.ClearAll();   // wipe chart objects on detach/recompile (before the CSV early-return)

   int fh = FobCsvOpen(_Symbol, g_runid);
   if(fh == INVALID_HANDLE)
      return;

   int n = ArraySize(g_events);
   for(int e = 0; e < n; e++)
      //--- zone lifecycle was accumulated CAUSALLY tick-by-tick during the run
      //--- (FobAccInit/FobAccOnTick/FobAccOnClose) — serialize it AS-IS, no replay.
      //--- mid/Tn/counts/rt/alive/invalidation/bars_alive/vr_fresh are already stamped.
      FobCsvWriteEvent(fh, e + 1, g_events[e]);
   FileClose(fh);

   PrintFormat("[FOB] fob_baysix v%s done — %d events across %d TFs -> Common/Files/FOB/fob_capture_%s_%s.csv",
               FOB_VERSION, n, FOB_N_TF, _Symbol, g_runid);
  }
//+------------------------------------------------------------------+
