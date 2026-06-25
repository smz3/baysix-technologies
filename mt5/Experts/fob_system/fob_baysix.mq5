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
#property version   "0.21"          // keep in lockstep with FOB_VERSION (fob_types.mqh)
#property strict

#include <fob_system/fob_swings.mqh>      // FOB's OWN: FobSwingRadius / FobDetectSwingAt
#include <fob_system/fob_breakouts.mqh>   // FOB's OWN: FobDetectBreaksOnBar
#include <fob_system/fob_types.mqh>
#include <fob_system/fob_sequence.mqh>
#include <fob_system/fob_csv.mqh>
#include <fob_system/fob_visual.mqh>      // InpVisualize master toggle (default on)

input int  InpSwingWindow    = 3;     // close-based pivot window (odd, >=3; live BRC = 3)
input int  InpMaxAge         = 0;     // break age filter in bars (<=0 disables)
input bool InpPboNewestOnly  = true;  // PBO = freshest source near CMP (reject same-dir reach-backs)

//--- the 9 TFs (index order MUST match FobTfName in fob_types.mqh)
ENUM_TIMEFRAMES g_periods[FOB_N_TF] =
  { PERIOD_M1, PERIOD_M5, PERIOD_M15, PERIOD_M30, PERIOD_H1, PERIOD_H4, PERIOD_D1, PERIOD_W1, PERIOD_MN1 };

//+------------------------------------------------------------------+
//| Per-TF detection state (own clock, own buffers). Lean vs BRC —    |
//| FOB needs swings + raw breaks only, no 5-point zones.             |
//+------------------------------------------------------------------+
struct FobTfState
  {
   datetime last_time;     // time of the last closed bar already ingested
   datetime bt[];          // growing bar series (index 0 = OLDEST)
   double   bh[];
   double   bl[];
   double   bc[];
   FobSwing swings[];
   int      live_sw[];     // indices into swings[] of UNBROKEN swings (O(live) scan)
   FobBreak breaks[];       // full raw-break log for this TF
  };

//--- one new raw break awaiting chronological classification this tick
struct FobPending
  {
   int      tf;
   datetime swt;          // broken swing time (dot x-coord)
   datetime bt;
   int      dir;
   double   level;
   double   close;
  };

FobTfState    g_tf[FOB_N_TF];
FobSetupState g_setup[FOB_N_TF];   // per-setup-TF state machine
FobEvent      g_events[];           // every classified event (CSV + redraw source)
int           g_radius = 1;
string        g_runid  = "";
CFobVisual    g_vis;

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
      g_tf[i].last_time     = 0;
      ArrayResize(g_tf[i].bt,      0);
      ArrayResize(g_tf[i].bh,      0);
      ArrayResize(g_tf[i].bl,      0);
      ArrayResize(g_tf[i].bc,      0);
      ArrayResize(g_tf[i].swings,  0);
      ArrayResize(g_tf[i].live_sw, 0);
      ArrayResize(g_tf[i].breaks,  0);
      g_setup[i].active     = false;
      g_setup[i].seq        = 0;
      g_setup[i].vr_locked  = false;
      g_setup[i].cf_count   = 0;
      g_setup[i].last_conf_swing = 0;
      g_setup[i].pbo_swing  = 0;
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
//| Append one closed bar to a TF buffer and run swing-confirm +      |
//| raw-break detection. New breaks are left appended to s.breaks[];  |
//| the caller reads the [before,after) range for classification.     |
//+------------------------------------------------------------------+
void FobIngestBar(FobTfState &s, const datetime bt, const double h, const double l, const double cl)
  {
   int i = ArraySize(s.bt);
   ArrayResize(s.bt, i + 1, 4096);
   ArrayResize(s.bh, i + 1, 4096);
   ArrayResize(s.bl, i + 1, 4096);
   ArrayResize(s.bc, i + 1, 4096);
   s.bt[i] = bt;  s.bh[i] = h;  s.bl[i] = l;  s.bc[i] = cl;
   int n = i + 1;

   //--- swing confirm: pivot at p = i - radius now has `radius` right neighbours
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

   //--- raw breaks on this bar (mutates swing.broken, appends events, compacts live_sw)
   FobDetectBreaksOnBar(s.swings, s.live_sw, i, bt, cl, g_radius, InpMaxAge, s.breaks);
  }

//+------------------------------------------------------------------+
//| Insertion-sort pending breaks: bar_time ASC, ties higher-TF first |
//| (so a PBO is established before any same-instant lower-TF role).  |
//+------------------------------------------------------------------+
void FobSortPending(FobPending &p[])
  {
   int n = ArraySize(p);
   for(int i = 1; i < n; i++)
     {
      FobPending key = p[i];
      int j = i - 1;
      while(j >= 0 && (p[j].bt > key.bt || (p[j].bt == key.bt && p[j].tf < key.tf)))
        {
         p[j + 1] = p[j];
         j--;
        }
      p[j + 1] = key;
     }
  }

//+------------------------------------------------------------------+
//| On each tick: ingest newly CLOSED bars for every TF, collect the  |
//| new raw breaks, sort them globally, then classify in order.       |
//+------------------------------------------------------------------+
void OnTick()
  {
   MqlRates r[];
   ArraySetAsSeries(r, true);

   FobPending pend[];

   for(int t = 0; t < FOB_N_TF; t++)
     {
      int got = CopyRates(_Symbol, g_periods[t], 1, 64, r);
      if(got <= 0)
         continue;

      int nb0 = ArraySize(g_tf[t].breaks);
      //--- oldest -> newest so the buffer stays chronological
      for(int k = got - 1; k >= 0; k--)
        {
         if(r[k].time <= g_tf[t].last_time)
            continue;
         FobIngestBar(g_tf[t], r[k].time, r[k].high, r[k].low, r[k].close);
         g_tf[t].last_time = r[k].time;
        }
      int nb1 = ArraySize(g_tf[t].breaks);

      //--- queue this TF's new raw breaks for chronological classification
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

   int np = ArraySize(pend);
   if(np == 0)
      return;

   FobSortPending(pend);

   //--- classify each break in true chronological order
   for(int q = 0; q < np; q++)
      FobClassifyBreak(g_setup, FOB_N_TF, pend[q].tf, pend[q].dir, pend[q].swt, pend[q].bt,
                       pend[q].level, pend[q].close, g_events, InpPboNewestOnly);

   //--- event-TF lens is a full PROJECTION of the log -> repaint it whole
   //--- (cross-chart pending flips + role merging only work on a replay)
   if(InpVisualize)
     {
      g_vis.RedrawCurrentTF(g_events, ArraySize(g_events));
      int ci = g_vis.ChartIdx();
      if(ci >= 0)
         g_vis.DrawStructure(g_tf[ci].swings, g_tf[ci].breaks);   // swings + raw breaks
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
   g_vis.RedrawCurrentTF(g_events, ArraySize(g_events));
   int ci = g_vis.ChartIdx();
   if(ci >= 0)
      g_vis.DrawStructure(g_tf[ci].swings, g_tf[ci].breaks);   // swings + raw breaks
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
      FobCsvWriteEvent(fh, e + 1, g_events[e]);
   FileClose(fh);

   PrintFormat("[FOB] fob_baysix v%s done — %d events across %d TFs -> Common/Files/FOB/fob_events_%s_%s.csv",
               FOB_VERSION, n, FOB_N_TF, _Symbol, g_runid);
  }
//+------------------------------------------------------------------+
