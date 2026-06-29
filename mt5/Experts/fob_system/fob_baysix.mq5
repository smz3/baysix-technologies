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
//|  Run on the M5 chart, tester model "Open prices only" (swing +     |
//|  break detection are CLOSE-only, so each bar is final at its close |
//|  — the open-prices model is exact here and far faster). Per tick,  |
//|  every TF's newly-closed bars are ingested, the new breaks across  |
//|  ALL TFs are merged + sorted (bar_time asc, ties higher-TF-first)  |
//|  and fed to the classifier in true chronological order — the same  |
//|  ordering guard that kills the ORB unsorted-tick look-ahead.       |
//|                                                                    |
//|  Modules — FOB owns EVERYTHING, nothing shared with brc_system:    |
//|    fob_types (own swing/break/dir types) · fob_swings · fob_break-  |
//|    outs · fob_sequence · fob_csv · fob_visual                      |
//+------------------------------------------------------------------+
#property copyright "Baysix Technologies"
#property version   "1.23.0"        // MUST match FOB_VERSION (fob_types.mqh) — bump both together
#property strict

#include <fob_system/fob_types.mqh>
#include <fob_system/fob_engine.mqh>      // SHARED detection runtime (structs + ingest+sort) — with the trader
#include <fob_system/fob_sequence.mqh>
#include <fob_system/fob_lifecycle.mqh>   // FobReplayZoneLife — stamp zone lifecycle onto events for CSV
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
   for(int i = 0; i < FOB_N_TF; i++)
     {
      FobResetTfState(g_tf[i]);
      FobResetSetup(g_setup[i]);
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
   FobPending pend[];
   for(int t = 0; t < FOB_N_TF; t++)
      FobIngestTf(g_tf[t], _Symbol, FobPeriods[t], t, g_radius, InpMaxAge, pend);

   int  np   = ArraySize(pend);
   bool live = !MQLInfoInteger(MQL_TESTER);
   if(np == 0 && !live)
      return;                       // tester: no new event -> skip the repaint (fast)

   if(np > 0)
     {
      FobSortPending(pend);
      //--- classify each break in true chronological order. After each break, stamp the
      //--- RAW per-TF awareness snapshot onto the rows it just emitted — CAUSALLY (the
      //--- snapshot reflects g_setup as-of this bar, never a future state). A same-bar VR
      //--- upgrade rewrites an existing row in place (no append) -> it keeps its earlier
      //--- snapshot (same bar, ~identical state), which is correct.
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
     }

   //--- event-TF lens is a full PROJECTION of the log -> repaint it whole (cross-chart
   //--- pending flips + role merging only work on a replay). LIVE: every tick so the
   //--- forming-bar touch shows; TESTER: only on a new event (np>0), no forming pass.
   if(InpVisualize)
     {
      int ci = g_vis.ChartIdx();
      if(ci >= 0)                                                  // stamp T-touches FIRST (zone [Tn] + alive)
        {
         g_vis.UpdateZoneLifecycles(g_events, ArraySize(g_events),
                                    g_tf[ci].bt, g_tf[ci].bh, g_tf[ci].bl, g_tf[ci].bc, ArraySize(g_tf[ci].bt));
         //--- LIVE intrabar touch off the FORMING bar so [Tn] flips on the wick, not
         //--- only at close. Touch-only; SKIP in tester (per-tick quadratic blow-up).
         MqlRates f[];
         if(live && CopyRates(_Symbol, FobPeriods[ci], 0, 1, f) == 1)
            g_vis.LiveTouchForming(g_events, ArraySize(g_events), f[0].time, f[0].high, f[0].low);
        }
      //--- repaint ONLY on a real change (new event OR a newly-stamped touch) — a
      //--- full ClearAll+redraw every tick is what made the bands TWITCH.
      ulong sig = g_vis.StateSignature(g_events, ArraySize(g_events));
      if(np > 0 || sig != g_last_sig)
        {
         g_vis.DrawZones(g_events, ArraySize(g_events));           // ClearAll + zone bands + edge labels
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
   int ci = g_vis.ChartIdx();
   if(ci >= 0)                                                  // stamp T-touches FIRST (zone [Tn] + alive)
      g_vis.UpdateZoneLifecycles(g_events, ArraySize(g_events),
                                 g_tf[ci].bt, g_tf[ci].bh, g_tf[ci].bl, g_tf[ci].bc, ArraySize(g_tf[ci].bt));
   g_vis.DrawZones(g_events, ArraySize(g_events));              // ClearAll + zone bands + edge labels
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
     {
      //--- STATELESS lifecycle replay over THIS event's own event-TF bar buffer (the same
      //--- FobReplayZoneLife the chart uses), so the CSV carries mid/Tn/counts/rt/alive/
      //--- invalidation/bars_alive/vr_fresh. VR rows track RT (the break-and-retest phase).
      int etf = g_events[e].event_tf;
      bool isVR = (g_events[e].label == FOB_VR);
      FobReplayZoneLife(g_events[e].zone, g_events[e].dir, g_events[e].level, g_events[e].bar_time,
                        g_tf[etf].bt, g_tf[etf].bh, g_tf[etf].bl, g_tf[etf].bc,
                        ArraySize(g_tf[etf].bt), isVR);
      FobCsvWriteEvent(fh, e + 1, g_events[e]);
     }
   FileClose(fh);

   PrintFormat("[FOB] fob_baysix v%s done — %d events across %d TFs -> Common/Files/FOB/fob_capture_%s_%s.csv",
               FOB_VERSION, n, FOB_N_TF, _Symbol, g_runid);
  }
//+------------------------------------------------------------------+
