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
  };

TfState g_tf[];
int     g_radius   = 1;
string  g_runid    = "";

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

   PrintFormat("[BRC] brc_baysix v%s init OK — %d TFs, swing_window=%d radius=%d runid=%s",
               BRC_VERSION, n, InpSwingWindow, g_radius, g_runid);
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
        }
     }

   //--- 2. raw breaks on this bar (mutates swing.broken, appends events).
   int before = ArraySize(s.breaks);
   BrcDetectBreaksOnBar(s.swings, i, bt, cl, g_radius, InpMaxAge, s.breaks);
   int after = ArraySize(s.breaks);

   //--- 3. each NEW break is a candidate P4 (2nd break) -> try to confirm a zone.
   for(int k = before; k < after; k++)
     {
      BrcZone z;
      if(BrcTryConfirmZone(s.breaks[k], s.swings, s.breaks, s.bc, n, z))
        {
         int zi = ArraySize(s.zones);
         ArrayResize(s.zones, zi + 1, 256);
         s.zones[zi] = z;
        }
     }

   //--- 4. advance every alive zone by this bar, but only STRICTLY AFTER its P4
   //    (a zone confirmed on bar i has p4_time == bt and must not self-advance).
   int nz = ArraySize(s.zones);
   for(int z = 0; z < nz; z++)
      if(s.zones[z].alive && s.zones[z].p4_time < bt)
         BrcAdvanceZone(s.zones[z], bt, h, l, cl);
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
  }

//+------------------------------------------------------------------+
//| Dump every confirmed zone (alive + dead) to the run CSV.          |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
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
