//+------------------------------------------------------------------+
//|                                       import_custom_ticks.mq5      |
//|                          Copyright 2026, Baysix Technologies       |
//+------------------------------------------------------------------+
//| Build an MT5 custom symbol from the EXACT research-parquet ticks   |
//| so the Strategy Tester runs on the SAME data the Python research   |
//| validated on (a VALID Gate-7 FIDELITY test).                       |
//|                                                                    |
//| Reads Common\Files\baysix_XAUUSD_pq_ticks.bin (written by          |
//| research/code/export_ticks_mt5.py):                                |
//|   header int64 n; then n records of int64 time_msc, double bid,    |
//|   double ask, int64 volume  (little-endian, 32 bytes each).        |
//|                                                                    |
//| Creates 'XAUUSD_pq' (3-digit, UTC ticks) and loads it day-by-day   |
//| via CustomTicksReplace (calendar-day ranges tile without overlap). |
//| Run: drag this script onto ANY chart in the JM terminal.           |
//+------------------------------------------------------------------+
#property copyright "Copyright 2026, Baysix Technologies"
#property version   "1.00"
#property script_show_inputs

input string InpSymbol   = "XAUUSD_pq";                  // custom symbol to (re)build
input string InpPath     = "Custom\\Baysix";             // folder in the Symbols tree
input string InpOrigin   = "XAUUSD_dukas";               // copy specs FROM (then override digits)
input string InpBinFile  = "baysix_XAUUSD_pq_ticks.bin"; // in Common\Files
input int    InpDigits   = 3;                            // parquet precision (Dukascopy gold = 3)

const long MS_PER_DAY = 86400000;

//+------------------------------------------------------------------+
void OnStart()
  {
   //--- 1. (re)create the custom symbol -----------------------------------------
   bool is_custom = false;
   if(SymbolExist(InpSymbol, is_custom))
     {
      PrintFormat("[import] '%s' exists -> deleting to rebuild clean", InpSymbol);
      SymbolSelect(InpSymbol, false);
      if(!CustomSymbolDelete(InpSymbol))
         PrintFormat("[import] delete failed: %d (close its charts/tester first)", GetLastError());
     }
   if(!CustomSymbolCreate(InpSymbol, InpPath, InpOrigin))
     { PrintFormat("[import] CustomSymbolCreate failed: %d", GetLastError()); return; }

   // Override ONLY price precision — inherit every TRADE/MARGIN spec from the
   // working origin (XAUUSD_dukas). Forcing CFD calc + XAU margin currency made
   // margin uncomputable in USD (blank usd/lot) -> OrderCalcMargin failed ->
   // tester opened zero trades. Inherited (Forex) calc computes P&L as
   // move*contract*lots (digit-independent), so no tick-value scaling needed.
   CustomSymbolSetInteger(InpSymbol, SYMBOL_DIGITS, InpDigits);
   CustomSymbolSetDouble (InpSymbol, SYMBOL_TRADE_TICK_SIZE,  MathPow(10, -InpDigits));
   CustomSymbolSetDouble (InpSymbol, SYMBOL_POINT,            MathPow(10, -InpDigits));
   // tick value scaled to 3-digit precision (harmless under Forex calc, correct under CFD)
   CustomSymbolSetDouble (InpSymbol, SYMBOL_TRADE_TICK_VALUE, 100.0 * MathPow(10, -InpDigits)); // 0.10
   CustomSymbolSetDouble (InpSymbol, SYMBOL_VOLUME_MIN,  0.01);
   CustomSymbolSetDouble (InpSymbol, SYMBOL_VOLUME_STEP, 0.01);
   SymbolSelect(InpSymbol, true);
   PrintFormat("[import] symbol '%s' ready (digits=%d) — loading ticks ...", InpSymbol, InpDigits);

   //--- 2. open the binary -------------------------------------------------------
   int fh = FileOpen(InpBinFile, FILE_READ|FILE_BIN|FILE_COMMON);
   if(fh == INVALID_HANDLE)
     { PrintFormat("[import] cannot open Common\\Files\\%s: %d", InpBinFile, GetLastError()); return; }
   long n = FileReadLong(fh);
   PrintFormat("[import] %s reports %I64d ticks", InpBinFile, n);

   //--- 3. stream records, flush per calendar day via CustomTicksReplace ---------
   MqlTick day[];
   ArrayResize(day, 300000);
   int    cnt        = 0;
   long   cur_day    = -1;
   long   total      = 0;
   long   total_in   = 0;
   datetime t0 = 0, tN = 0;

   for(long i = 0; i < n; i++)
     {
      long   tmsc = FileReadLong(fh);
      double bid  = FileReadDouble(fh);
      double ask  = FileReadDouble(fh);
      long   vol  = FileReadLong(fh);
      total_in++;
      long d = tmsc / MS_PER_DAY;

      if(cur_day == -1) cur_day = d;
      if(d != cur_day || cnt >= ArraySize(day))
        {
         total += FlushDay(InpSymbol, cur_day, day, cnt);
         cnt = 0;
         cur_day = d;
        }
      if(cnt >= ArraySize(day)) ArrayResize(day, ArraySize(day) + 100000);

      day[cnt].time       = (datetime)(tmsc / 1000);
      day[cnt].time_msc   = tmsc;
      day[cnt].bid        = bid;
      day[cnt].ask        = ask;
      day[cnt].last       = 0.0;
      day[cnt].volume     = (ulong)vol;
      day[cnt].volume_real= (double)vol;
      day[cnt].flags      = TICK_FLAG_BID | TICK_FLAG_ASK;
      cnt++;

      if(t0 == 0) t0 = day[cnt-1].time;
      tN = day[cnt-1].time;
     }
   if(cnt > 0) total += FlushDay(InpSymbol, cur_day, day, cnt);
   FileClose(fh);

   PrintFormat("[import] DONE: read %I64d, replaced %I64d ticks into '%s'", total_in, total, InpSymbol);
   PrintFormat("[import] range %s .. %s — now run the Strategy Tester on '%s' (Every tick based on real ticks)",
               TimeToString(t0, TIME_DATE|TIME_SECONDS), TimeToString(tN, TIME_DATE|TIME_SECONDS), InpSymbol);
  }

//+------------------------------------------------------------------+
//| Replace one calendar day's ticks (range tiles by day, no overlap) |
//+------------------------------------------------------------------+
long FlushDay(const string sym, const long day_idx, MqlTick &ticks[], const int count)
  {
   if(count <= 0) return(0);
   long from_msc = day_idx * MS_PER_DAY;
   long to_msc   = from_msc + MS_PER_DAY - 1;
   int replaced  = CustomTicksReplace(sym, from_msc, to_msc, ticks, count);
   if(replaced < 0)
      PrintFormat("[import] CustomTicksReplace failed day=%s err=%d",
                  TimeToString((datetime)(from_msc/1000), TIME_DATE), GetLastError());
   return(replaced > 0 ? replaced : 0);
  }
//+------------------------------------------------------------------+
