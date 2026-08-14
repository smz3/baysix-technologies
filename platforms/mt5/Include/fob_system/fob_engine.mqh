//+------------------------------------------------------------------+
//|                                                    fob_engine.mqh  |
//|  SHARED detection runtime — the ONE copy of FOB's per-TF bar       |
//|  ingest + raw-break collection, consumed by BOTH the emitter       |
//|  (fob_baysix) and the trader (fob_trader). Extracted 2026-06-29    |
//|  to kill the copy-paste drift: the two EAs MUST detect identical   |
//|  zones, so the detection code lives in exactly one place.          |
//|                                                                    |
//|  MQL5 note: includes are pasted ABOVE the .mq5's input/globals, so |
//|  these functions take radius/maxAge as PARAMETERS (they cannot see |
//|  g_radius / InpMaxAge by name). Behaviour is identical to the old  |
//|  in-EA copies — same swing-confirm, same break detection, same     |
//|  chronological sort (bar_time asc, ties higher-TF-first).          |
//+------------------------------------------------------------------+
#ifndef FOB_ENGINE_MQH
#define FOB_ENGINE_MQH
#property strict

#include "fob_types.mqh"
#include "fob_swings.mqh"      // FobSwingRadius / FobDetectSwingAt
#include "fob_breakouts.mqh"   // FobDetectBreaksOnBar

//--- the 9 TFs (index order MUST match FobTfName in fob_types.mqh). Single copy,
//--- shared by both EAs (each EA is its own compilation unit -> no multi-def).
ENUM_TIMEFRAMES FobPeriods[FOB_N_TF] =
  { PERIOD_M1, PERIOD_M5, PERIOD_M15, PERIOD_M30, PERIOD_H1, PERIOD_H4, PERIOD_D1, PERIOD_W1, PERIOD_MN1 };

//+------------------------------------------------------------------+
//| Per-TF detection state (own clock, own buffers). FOB needs swings |
//| + raw breaks only, no 5-point zones.                             |
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
   FobBreak breaks[];      // full raw-break log for this TF
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
   FobZone  zone;         // 4-pointer band carried from the break (v1.14.0)
  };

//+------------------------------------------------------------------+
//| Append one closed bar to a TF buffer and run swing-confirm +      |
//| raw-break detection. New breaks are left appended to s.breaks[];  |
//| the caller reads the [before,after) range for classification.     |
//+------------------------------------------------------------------+
void FobIngestBar(FobTfState &s, const datetime bt, const double op, const double h,
                  const double l, const double cl, const int radius, const int maxAge)
  {
   int i = ArraySize(s.bt);
   ArrayResize(s.bt, i + 1, 4096);
   ArrayResize(s.bh, i + 1, 4096);
   ArrayResize(s.bl, i + 1, 4096);
   ArrayResize(s.bc, i + 1, 4096);
   s.bt[i] = bt;  s.bh[i] = h;  s.bl[i] = l;  s.bc[i] = cl;
   int n = i + 1;

   //--- swing confirm: pivot at p = i - radius now has `radius` right neighbours
   int p = i - radius;
   if(p >= 0)
     {
      FobSwing sw;
      if(FobDetectSwingAt(s.bt, s.bc, n, p, radius, sw))
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
   //--- s.bc/n feed the 4-pointer gap-val (v1.14.0).
   FobDetectBreaksOnBar(s.swings, s.live_sw, i, bt, op, cl, radius, maxAge, s.bt, s.bc, n, s.breaks);
  }

//+------------------------------------------------------------------+
//| Pull this tick's newly-CLOSED bars for ONE TF, ingest them, and   |
//| QUEUE the new raw breaks (tagged with tfIdx) onto pend[]. Returns  |
//| the number of breaks queued. Byte-identical to the old per-TF     |
//| ingest loop both EAs ran inline.                                  |
//+------------------------------------------------------------------+
int FobIngestTf(FobTfState &s, const string sym, const ENUM_TIMEFRAMES period,
                const int tfIdx, const int radius, const int maxAge, FobPending &pend[])
  {
   MqlRates r[];
   ArraySetAsSeries(r, true);
   int got = CopyRates(sym, period, 1, 64, r);
   if(got <= 0)
      return 0;

   int nb0 = ArraySize(s.breaks);
   //--- oldest -> newest so the buffer stays chronological
   for(int k = got - 1; k >= 0; k--)
     {
      if(r[k].time <= s.last_time)
         continue;
      FobIngestBar(s, r[k].time, r[k].open, r[k].high, r[k].low, r[k].close, radius, maxAge);
      s.last_time = r[k].time;
     }
   int nb1 = ArraySize(s.breaks);

   //--- queue this TF's new raw breaks for chronological classification
   int added = 0;
   for(int b = nb0; b < nb1; b++)
     {
      int pi = ArraySize(pend);
      ArrayResize(pend, pi + 1, 64);
      pend[pi].tf    = tfIdx;
      pend[pi].swt   = s.breaks[b].swing_time;
      pend[pi].bt    = s.breaks[b].bar_time;
      pend[pi].dir   = s.breaks[b].dir;
      pend[pi].level = s.breaks[b].swing_price;
      pend[pi].close = s.breaks[b].bar_close;
      pend[pi].zone  = s.breaks[b].zone;
      added++;
     }
   return added;
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
//| FULL reset of one TF's detection buffers (HARD: MT5 reinits       |
//| WITHOUT unloading, so globals survive — clear EVERYTHING).        |
//+------------------------------------------------------------------+
void FobResetTfState(FobTfState &s)
  {
   s.last_time = 0;
   ArrayResize(s.bt,      0);
   ArrayResize(s.bh,      0);
   ArrayResize(s.bl,      0);
   ArrayResize(s.bc,      0);
   ArrayResize(s.swings,  0);
   ArrayResize(s.live_sw, 0);
   ArrayResize(s.breaks,  0);
  }

//+------------------------------------------------------------------+
//| Reset one setup-TF state machine (mirrors the exact field set     |
//| both EAs cleared inline — no more, no less, to stay identical).   |
//+------------------------------------------------------------------+
void FobResetSetup(FobSetupState &st)
  {
   st.active          = false;
   st.seq             = 0;
   st.vr_locked       = false;
   st.vr_level        = 0.0;
   st.vr_swing        = 0;
   st.vr_ev_idx       = -1;
   st.cf_count        = 0;
   st.last_conf_swing = 0;
   st.pbo_swing       = 0;
  }

#endif // FOB_ENGINE_MQH
