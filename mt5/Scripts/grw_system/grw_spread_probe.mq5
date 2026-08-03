//+------------------------------------------------------------------+
//|                                            grw_spread_probe.mq5  |
//|  Measures the REAL Just Markets XAUUSD spread from the terminal's |
//|  own downloaded tick history.                                     |
//|                                                                   |
//|  WHY: brokers/justmarkets.yaml carries spread.typical_pips = 2.0  |
//|  "confirmed from live experience" (an eyeball, not a measurement) |
//|  and leaves stress_pips + news_pips as TO_VERIFY. Every cost      |
//|  number in the GRW mandate divides by that 2.0. On a $20 account  |
//|  at 0.01 lot the round-trip spread IS the entire cost line — Pro  |
//|  charges no commission and JM is swap-free — so a 30% error in    |
//|  this one figure is a 30% error in the whole viability envelope.  |
//|                                                                   |
//|  Emits the spread distribution by server hour and by weekday so   |
//|  the cheap trading windows (if any) become a measured fact.       |
//+------------------------------------------------------------------+
#property script_show_inputs
#property strict

input string InpSymbol      = "XAUUSD.s";  // symbol (JM uses the .s suffix)
input int    InpMonthsBack  = 12;          // months of tick history to scan
input string InpOutFile     = "grw_spread_probe.csv";

// spread histogram, in POINTS (integer) — exact percentiles, tiny memory.
// gold digits=2 -> point=0.01, pip=0.10 = 10 points. 600 bins = 0..60 pips.
#define MAX_POINT_BIN 600
#define PIP_POINTS    10

long g_hist_hour[24][MAX_POINT_BIN + 1];
long g_hist_dow[7][MAX_POINT_BIN + 1];
long g_hist_all[MAX_POINT_BIN + 1];
long g_overflow = 0;   // ticks wider than MAX_POINT_BIN
long g_total    = 0;

//+------------------------------------------------------------------+
double PercentileFromHist(const long &hist[], const long total, const double q)
{
   if(total <= 0) return(0.0);
   long want = (long)MathCeil(q * (double)total);
   if(want < 1) want = 1;
   long cum = 0;
   for(int b = 0; b <= MAX_POINT_BIN; b++)
   {
      cum += hist[b];
      if(cum >= want)
         return((double)b / (double)PIP_POINTS);   // points -> pips
   }
   return((double)MAX_POINT_BIN / (double)PIP_POINTS);
}

double MeanFromHist(const long &hist[], const long total)
{
   if(total <= 0) return(0.0);
   double acc = 0.0;
   for(int b = 0; b <= MAX_POINT_BIN; b++)
      acc += (double)b * (double)hist[b];
   return(acc / (double)total / (double)PIP_POINTS);
}

// share of ticks at or below `pips`
double ShareAtOrBelow(const long &hist[], const long total, const double pips)
{
   if(total <= 0) return(0.0);
   int cap = (int)MathRound(pips * PIP_POINTS);
   if(cap > MAX_POINT_BIN) cap = MAX_POINT_BIN;
   long cum = 0;
   for(int b = 0; b <= cap; b++) cum += hist[b];
   return((double)cum / (double)total);
}

void SliceHour(const int h, long &out[])
{
   ArrayResize(out, MAX_POINT_BIN + 1);
   for(int b = 0; b <= MAX_POINT_BIN; b++) out[b] = g_hist_hour[h][b];
}

void SliceDow(const int d, long &out[])
{
   ArrayResize(out, MAX_POINT_BIN + 1);
   for(int b = 0; b <= MAX_POINT_BIN; b++) out[b] = g_hist_dow[d][b];
}

long HourTotal(const int h)
{
   long t = 0;
   for(int b = 0; b <= MAX_POINT_BIN; b++) t += g_hist_hour[h][b];
   return(t);
}

long DowTotal(const int d)
{
   long t = 0;
   for(int b = 0; b <= MAX_POINT_BIN; b++) t += g_hist_dow[d][b];
   return(t);
}

//+------------------------------------------------------------------+
void OnStart()
{
   string sym = InpSymbol;
   if(!SymbolSelect(sym, true))
   {
      PrintFormat("[spread_probe] symbol '%s' not available — falling back to %s", sym, _Symbol);
      sym = _Symbol;
      if(!SymbolSelect(sym, true))
      { Print("[spread_probe] FATAL: no usable symbol"); return; }
   }

   const double point  = SymbolInfoDouble(sym, SYMBOL_POINT);
   const int    digits = (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);
   if(point <= 0.0)
   { Print("[spread_probe] FATAL: point size is zero"); return; }

   PrintFormat("[spread_probe] %s digits=%d point=%.5f — scanning %d months of ticks",
               sym, digits, point, InpMonthsBack);

   ArrayInitialize(g_hist_all, 0);
   for(int h = 0; h < 24; h++) for(int b = 0; b <= MAX_POINT_BIN; b++) g_hist_hour[h][b] = 0;
   for(int d = 0; d < 7;  d++) for(int b = 0; b <= MAX_POINT_BIN; b++) g_hist_dow[d][b]  = 0;

   const datetime now  = TimeCurrent();
   const datetime from = now - (datetime)((long)InpMonthsBack * 30 * 86400);

   // chunk day-by-day: keeps the tick array bounded and lets us show progress
   MqlTick ticks[];
   int days = (int)((now - from) / 86400) + 1;
   int days_with_data = 0;

   for(int d = 0; d < days; d++)
   {
      datetime day_start = from + (datetime)((long)d * 86400);
      datetime day_end   = day_start + 86400;

      int n = CopyTicksRange(sym, ticks, COPY_TICKS_INFO,
                             (ulong)day_start * 1000, (ulong)day_end * 1000);
      if(n <= 0) continue;
      days_with_data++;

      for(int i = 0; i < n; i++)
      {
         double bid = ticks[i].bid;
         double ask = ticks[i].ask;
         if(bid <= 0.0 || ask <= 0.0) continue;      // one-sided tick, no spread to read
         double sp = ask - bid;
         if(sp < 0.0) continue;                       // crossed quote — data artifact

         int bin = (int)MathRound(sp / point);
         if(bin > MAX_POINT_BIN) { g_overflow++; bin = MAX_POINT_BIN; }
         if(bin < 0) bin = 0;

         MqlDateTime mdt;
         TimeToStruct(ticks[i].time, mdt);

         g_hist_all[bin]++;
         g_hist_hour[mdt.hour][bin]++;
         g_hist_dow[mdt.day_of_week][bin]++;
         g_total++;
      }

      if((d % 30) == 0)
         PrintFormat("[spread_probe] day %d/%d  ticks so far=%I64d", d, days, g_total);
   }

   if(g_total <= 0)
   {
      Print("[spread_probe] NO TICKS. Open the symbol chart and let MT5 download tick history first.");
      return;
   }

   // ---- report -----------------------------------------------------------
   double med_all = PercentileFromHist(g_hist_all, g_total, 0.50);
   double p90_all = PercentileFromHist(g_hist_all, g_total, 0.90);
   double p99_all = PercentileFromHist(g_hist_all, g_total, 0.99);

   PrintFormat("[spread_probe] ==== %s | %d days with data | %I64d ticks ====",
               sym, days_with_data, g_total);
   PrintFormat("[spread_probe] ALL: median=%.2f pips  mean=%.2f  p90=%.2f  p99=%.2f  overflow=%I64d",
               med_all, MeanFromHist(g_hist_all, g_total), p90_all, p99_all, g_overflow);
   PrintFormat("[spread_probe] share <= 2.0 pips (the yaml assumption) = %.1f%%",
               100.0 * ShareAtOrBelow(g_hist_all, g_total, 2.0));
   PrintFormat("[spread_probe] round-trip cost @0.01 lot: median=$%.3f  p90=$%.3f  p99=$%.3f",
               med_all * 0.10, p90_all * 0.10, p99_all * 0.10);

   int fh = FileOpen(InpOutFile, FILE_WRITE | FILE_CSV | FILE_ANSI | FILE_COMMON, ',');
   if(fh == INVALID_HANDLE)
   { PrintFormat("[spread_probe] FileOpen failed err=%d", GetLastError()); return; }

   FileWrite(fh, "bucket_kind", "bucket", "n_ticks", "mean_pips", "p25_pips",
                 "median_pips", "p75_pips", "p90_pips", "p99_pips",
                 "share_le_2pip", "rt_cost_usd_median_001lot");

   FileWrite(fh, "ALL", "all", (string)g_total,
             DoubleToString(MeanFromHist(g_hist_all, g_total), 3),
             DoubleToString(PercentileFromHist(g_hist_all, g_total, 0.25), 2),
             DoubleToString(med_all, 2),
             DoubleToString(PercentileFromHist(g_hist_all, g_total, 0.75), 2),
             DoubleToString(p90_all, 2),
             DoubleToString(p99_all, 2),
             DoubleToString(ShareAtOrBelow(g_hist_all, g_total, 2.0), 4),
             DoubleToString(med_all * 0.10, 3));

   long slice[];
   for(int h = 0; h < 24; h++)
   {
      long tot = HourTotal(h);
      if(tot <= 0) continue;
      SliceHour(h, slice);
      double med = PercentileFromHist(slice, tot, 0.50);
      FileWrite(fh, "HOUR_SERVER", (string)h, (string)tot,
                DoubleToString(MeanFromHist(slice, tot), 3),
                DoubleToString(PercentileFromHist(slice, tot, 0.25), 2),
                DoubleToString(med, 2),
                DoubleToString(PercentileFromHist(slice, tot, 0.75), 2),
                DoubleToString(PercentileFromHist(slice, tot, 0.90), 2),
                DoubleToString(PercentileFromHist(slice, tot, 0.99), 2),
                DoubleToString(ShareAtOrBelow(slice, tot, 2.0), 4),
                DoubleToString(med * 0.10, 3));
      PrintFormat("[spread_probe] hour %02d  n=%-10I64d median=%.2f  p90=%.2f  rt=$%.3f",
                  h, tot, med, PercentileFromHist(slice, tot, 0.90), med * 0.10);
   }

   for(int d = 0; d < 7; d++)
   {
      long tot = DowTotal(d);
      if(tot <= 0) continue;
      SliceDow(d, slice);
      double med = PercentileFromHist(slice, tot, 0.50);
      FileWrite(fh, "DOW", (string)d, (string)tot,
                DoubleToString(MeanFromHist(slice, tot), 3),
                DoubleToString(PercentileFromHist(slice, tot, 0.25), 2),
                DoubleToString(med, 2),
                DoubleToString(PercentileFromHist(slice, tot, 0.75), 2),
                DoubleToString(PercentileFromHist(slice, tot, 0.90), 2),
                DoubleToString(PercentileFromHist(slice, tot, 0.99), 2),
                DoubleToString(ShareAtOrBelow(slice, tot, 2.0), 4),
                DoubleToString(med * 0.10, 3));
   }

   FileClose(fh);
   PrintFormat("[spread_probe] wrote %s to the COMMON Files folder", InpOutFile);
}
//+------------------------------------------------------------------+
