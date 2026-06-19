//+------------------------------------------------------------------+
//|                                                     brc_baysix.mq5 |
//|         BRC zone-lifecycle EMITTER — the chronological oracle.     |
//|                                                                    |
//|  ONE job: emit a trustworthy, look-ahead-free zone-lifecycle       |
//|  ledger across 8 TFs (M5..MN1) to a UTF-8 CSV. All inference is    |
//|  downstream in Python (tasks 119 ingest / 120 funnel). NO strategy,|
//|  NO orders, NO money — this is L1 fidelity + the L2 raw material.  |
//|                                                                    |
//|  Run on the M5 chart, tester model "Open prices only" (detection + |
//|  invalidation are close-only, so each bar's OHLC is final at its   |
//|  close — the open-prices model is exact here and far faster).      |
//|  Event-driven, incremental: each TF maintains its own growing bar  |
//|  buffer + swing/break/zone state, advanced one closed bar at a     |
//|  time. The OnBar event structurally kills the vectorized           |
//|  argmax-by-position look-ahead that manufactured the old "edge".   |
//|                                                                    |
//|  Modules (brc_system, self-contained — no Sigma includes):         |
//|    brc_types · brc_swings · brc_breakouts · brc_zones · brc_lifecycle · brc_csv |
//|  ⚠️ COMPILE-UNTESTED (authored without an MT5 toolchain present).   |
//+------------------------------------------------------------------+
#property copyright "Baysix Technologies"
#property version   "1.00"        // keep in lockstep with BRC_VERSION (brc_types.mqh)
#property strict

#include <brc_system/brc_types.mqh>
#include <brc_system/brc_swings.mqh>
#include <brc_system/brc_breakouts.mqh>
#include <brc_system/brc_zones.mqh>
#include <brc_system/brc_lifecycle.mqh>
#include <brc_system/brc_csv.mqh>
#include <brc_system/brc_visual.mqh>   // chart eyeball layer (InpVisualize master toggle, default off)

input int InpSwingWindow = 3;      // close-based pivot window (odd, >=3; live EA = 3)
input int InpMaxAge      = 0;      // break age filter in bars (<=0 disables)

//--- the 8 TFs detected in one run (M5 base .. MN1)
ENUM_TIMEFRAMES g_periods[] =
  { PERIOD_M5, PERIOD_M15, PERIOD_M30, PERIOD_H1, PERIOD_H4, PERIOD_D1, PERIOD_W1, PERIOD_MN1 };
string g_names[] = { "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN1" };

//+------------------------------------------------------------------+
//| Per-TF detection state (own clock, own buffers).                 |
//+------------------------------------------------------------------+
struct TfState
  {
   ENUM_TIMEFRAMES period;
   string          name;
   datetime        last_time;     // time of the last closed bar already ingested
   //--- growing bar series (index 0 = OLDEST, chronological)
   datetime        bt[];
   double          bh[];
   double          bl[];
   double          bc[];
   //--- detection state
   BrcSwing        swings[];
   BrcBreak        breaks[];
   BrcZone         zones[];        // every confirmed zone (alive + dead) — written at end
   //--- live-index free-lists (task 128 prune): hold only still-relevant entries
   //    so the per-bar scans are O(live)/O(alive), not O(all-ever). Both stay
   //    chronological (append + order-preserving compaction) -> byte-identical.
   int             live_sw[];      // indices into swings[] of UNBROKEN swings
   int             alive_idx[];    // indices into zones[]  of ALIVE  zones
  };

TfState    g_tf[];
int        g_radius = 1;
string     g_runid  = "";
CBrcVisual g_vis;          // chart visualizer (no-op unless InpVisualize)

//+------------------------------------------------------------------+
int OnInit()
  {
   g_radius = BrcSwingRadius(InpSwingWindow);
   if(g_radius < 0)
      return INIT_PARAMETERS_INCORRECT;

   int n = ArraySize(g_periods);
   ArrayResize(g_tf, n);
   for(int i = 0; i < n; i++)
     {
      g_tf[i].period    = g_periods[i];
      g_tf[i].name      = g_names[i];
      g_tf[i].last_time = 0;
     }

   string ts = TimeToString(TimeCurrent(), TIME_DATE | TIME_MINUTES);
   StringReplace(ts, ".", "");
   StringReplace(ts, " ", "_");
   StringReplace(ts, ":", "");
   g_runid = "v" + BRC_VERSION + "_" + ts;          // version stamped into every CSV name

   g_vis.SyncChartTF();
   g_vis.ClearAll();                                // wipe any objects from a prior run

   PrintFormat("[BRC] brc_baysix v%s init OK — %d TFs, swing_window=%d radius=%d runid=%s visualize=%s",
               BRC_VERSION, n, InpSwingWindow, g_radius, g_runid, (InpVisualize ? "ON" : "off"));
   return INIT_SUCCEEDED;
  }

//+------------------------------------------------------------------+
//| Append one closed bar to a TF buffer (reserve-amortized) and run  |
//| the full per-bar pipeline: swing confirm -> breaks -> zone        |
//| confirm -> advance alive zones.                                   |
//+------------------------------------------------------------------+
void BrcIngestBar(TfState &s, const datetime bt, const double h, const double l, const double cl)
  {
   int i = ArraySize(s.bt);                              // absolute index of this bar
   ArrayResize(s.bt, i + 1, 4096);
   ArrayResize(s.bh, i + 1, 4096);
   ArrayResize(s.bl, i + 1, 4096);
   ArrayResize(s.bc, i + 1, 4096);
   s.bt[i] = bt;  s.bh[i] = h;  s.bl[i] = l;  s.bc[i] = cl;
   int n = i + 1;

   //--- 1. swing confirm: the pivot at p = i - radius now has `radius` right
   //    neighbours (the just-closed bar i is the last of them).
   int p = i - g_radius;
   if(p >= 0)
     {
      BrcSwing sw;
      if(BrcDetectSwingAt(s.bt, s.bc, n, p, g_radius, sw))
        {
         int si = ArraySize(s.swings);
         ArrayResize(s.swings, si + 1, 512);
         s.swings[si] = sw;
         int li = ArraySize(s.live_sw);                  // register as live (unbroken)
         ArrayResize(s.live_sw, li + 1, 512);
         s.live_sw[li] = si;
         g_vis.OnSwing(s.name, sw);
        }
     }

   //--- 2. raw breaks on this bar (mutates swing.broken, appends events,
   //    compacts s.live_sw down to survivors).
   int before = ArraySize(s.breaks);
   BrcDetectBreaksOnBar(s.swings, s.live_sw, i, bt, cl, g_radius, InpMaxAge, s.breaks);
   int after = ArraySize(s.breaks);
   for(int b = before; b < after; b++)
      g_vis.OnBreak(s.name, s.breaks[b]);

   //--- 3. each NEW break is a candidate P4 (2nd break) -> try to confirm a zone.
   //    existing zones (s.zones) feed B2B's swing-usage + duplicate dedup.
   for(int k = before; k < after; k++)
     {
      BrcZone z;
      if(BrcTryConfirmZone(s.breaks[k], s.swings, s.breaks, s.bc, n, s.zones, z))
        {
         int zi = ArraySize(s.zones);
         ArrayResize(s.zones, zi + 1, 256);
         s.zones[zi] = z;
         int ai = ArraySize(s.alive_idx);                // register as alive
         ArrayResize(s.alive_idx, ai + 1, 256);
         s.alive_idx[ai] = zi;
         g_vis.OnZoneConfirmed(s.name, s.zones[zi]);
        }
     }

   //--- 4. advance every alive zone by this bar, but only STRICTLY AFTER its P4
   //    (a zone confirmed on bar i has p4_time == bt and must not self-advance).
   //    Iterate only s.alive_idx (O(alive)); compact out zones that just died,
   //    order-preserving so the set + per-zone math are byte-identical to the
   //    old 0..nz scan (BrcAdvanceZone touches only its own zone -> order-free).
   int na = ArraySize(s.alive_idx);
   int w  = 0;
   for(int j = 0; j < na; j++)
     {
      int z = s.alive_idx[j];
      if(s.zones[z].p4_time < bt)
        {
         BrcAdvanceZone(s.zones[z], bt, h, l, cl);
         g_vis.OnZoneAdvanced(s.name, s.zones[z]);
        }
      if(s.zones[z].alive)
         s.alive_idx[w++] = s.alive_idx[j];
     }
   ArrayResize(s.alive_idx, w);
  }

//+------------------------------------------------------------------+
//| On each tick, ingest any newly CLOSED bar for every TF. Index 1 = |
//| last closed bar (index 0 = forming). We copy a small recent       |
//| window and ingest bars newer than last_time (1 per TF per tick in |
//| practice; the window covers any catch-up).                        |
//+------------------------------------------------------------------+
void OnTick()
  {
   MqlRates r[];
   ArraySetAsSeries(r, true);

   for(int t = 0; t < ArraySize(g_tf); t++)
     {
      int got = CopyRates(_Symbol, g_tf[t].period, 1, 64, r);
      if(got <= 0)
         continue;
      //--- oldest -> newest so the buffer stays chronological
      for(int k = got - 1; k >= 0; k--)
        {
         if(r[k].time <= g_tf[t].last_time)
            continue;
         BrcIngestBar(g_tf[t], r[k].time, r[k].high, r[k].low, r[k].close);
         g_tf[t].last_time = r[k].time;
        }
     }

   //--- live INTRABAR touch pass: stamp t1/t2/t3 off each TF's FORMING bar
   //    (index 0) so the [Tn] label flips the instant price wicks a level,
   //    instead of only at bar close. Touch-only — invalidation/continuation
   //    stay close-only (BrcAdvanceZone). Data-neutral for the CSV (the touch
   //    lands on the same bar either way; see BrcLiveTouch). It is a purely
   //    live-chart instant-update nicety, so SKIP IT IN THE TESTER: under a
   //    real-ticks model it fires per-tick and loops every accumulated zone
   //    (quadratic, the >24h/8yr blow-up), while adding nothing to the ledger.
   if(MQLInfoInteger(MQL_TESTER))
      return;

   MqlRates f[];
   for(int t = 0; t < ArraySize(g_tf); t++)
     {
      if(CopyRates(_Symbol, g_tf[t].period, 0, 1, f) != 1)   // index 0 = forming bar
         continue;
      int nz = ArraySize(g_tf[t].zones);
      for(int z = 0; z < nz; z++)
         if(g_tf[t].zones[z].alive && g_tf[t].zones[z].p4_time < f[0].time)
            if(BrcLiveTouch(g_tf[t].zones[z], f[0].time, f[0].high, f[0].low))
               g_vis.OnZoneAdvanced(g_tf[t].name, g_tf[t].zones[z]);
     }
  }

//+------------------------------------------------------------------+
//| Live TF switch: when the chart period changes, rebuild the visual |
//| layer for the new TF from stored state (only that TF draws).      |
//+------------------------------------------------------------------+
void OnChartEvent(const int id, const long &lparam, const double &dparam, const string &sparam)
  {
   if(!InpVisualize || id != CHARTEVENT_CHART_CHANGE)
      return;
   g_vis.SyncChartTF();
   string tf = "";
   ENUM_TIMEFRAMES p = (ENUM_TIMEFRAMES)ChartPeriod();
   for(int t = 0; t < ArraySize(g_tf); t++)
      if(g_tf[t].period == p)
        {
         g_vis.RedrawCurrentTF(g_tf[t].name,
                               g_tf[t].swings, ArraySize(g_tf[t].swings),
                               g_tf[t].breaks, ArraySize(g_tf[t].breaks),
                               g_tf[t].zones,  ArraySize(g_tf[t].zones));
         return;
        }
   g_vis.ClearAll();   // chart on a TF the emitter doesn't track
  }

//+------------------------------------------------------------------+
//| Dump every confirmed zone (alive + dead) to the run CSV.          |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   g_vis.ClearAll();   // wipe chart objects on detach/recompile/chart-close (before the CSV early-return)

   int fh = BrcCsvOpen(_Symbol, g_runid);
   if(fh == INVALID_HANDLE)
      return;

   int zone_id = 0;
   int total   = 0;
   for(int t = 0; t < ArraySize(g_tf); t++)
     {
      int nz = ArraySize(g_tf[t].zones);
      for(int z = 0; z < nz; z++)
         BrcCsvWriteZone(fh, ++zone_id, g_tf[t].name, g_tf[t].zones[z]);
      total += nz;
     }
   FileClose(fh);
   PrintFormat("[BRC] brc_baysix v%s done — %d zones across %d TFs -> Common/Files/BRC/brc_zones_%s_%s.csv",
               BRC_VERSION, total, ArraySize(g_tf), _Symbol, g_runid);
  }
//+------------------------------------------------------------------+
