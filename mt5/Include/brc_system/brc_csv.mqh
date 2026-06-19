//+------------------------------------------------------------------+
//|                                                       brc_csv.mqh  |
//|  Lifecycle-row CSV writer — one row per confirmed zone per TF.     |
//|                                                                    |
//|  UTF-8, header row, comma-delimited (design spec §3). Every value  |
//|  written is pure ASCII (ISO timestamps + decimals + SELL/BUY), and |
//|  ASCII is a strict subset of UTF-8, so FILE_ANSI bytes ARE valid   |
//|  UTF-8 — no BOM, no UTF-16. This is the deliberate break from the  |
//|  old UTF-16 / headerless QUANT_ZONES format that broke ingestion   |
//|  (reference_mt5_bridge). Python ingest (task 119) reads it with    |
//|  pd.read_csv(..., encoding='utf-8').                               |
//|                                                                    |
//|  File: <MT5>/Common/Files/BRC/brc_zones_<symbol>_<runid>.csv       |
//+------------------------------------------------------------------+
#ifndef BRC_CSV_MQH
#define BRC_CSV_MQH
#property strict

#include "brc_types.mqh"

#define BRC_CSV_PRICE_DIGITS 3

//+------------------------------------------------------------------+
//| datetime -> "YYYY.MM.DD HH:MM:SS", or "" for the 0 sentinel       |
//| (blank = level never touched / zone still alive at data-end).     |
//+------------------------------------------------------------------+
string BrcFmtTime(const datetime t)
  {
   if(t == 0)
      return "";
   return TimeToString(t, TIME_DATE | TIME_MINUTES | TIME_SECONDS);
  }

string BrcFmtPrice(const double p)
  {
   return DoubleToString(p, BRC_CSV_PRICE_DIGITS);
  }

//+------------------------------------------------------------------+
//| Open the run's CSV in Common/Files/BRC and write the header row.  |
//| Returns the file handle (INVALID_HANDLE on failure).              |
//+------------------------------------------------------------------+
int BrcCsvOpen(const string symbol, const string runid)
  {
   string path = "BRC\\brc_zones_" + symbol + "_" + runid + ".csv";
   int fh = FileOpen(path, FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_COMMON);
   if(fh == INVALID_HANDLE)
     {
      PrintFormat("[BRC] FATAL cannot open %s (err %d)", path, GetLastError());
      return INVALID_HANDLE;
     }
   FileWriteString(fh,
      "zone_id,seq,zone_key,is_primary,consolidated_into,tf,direction,"
      "p1_time,p1_price,p2_time,p2_price,p3_time,p3_price,"
      "p4_time,p4_price,p5_time,p5_price,"
      "l1,l2,mid,break_kind,"
      "t1_time,t2_time,t3_time,confirm_time,invalidation_time,"
      "alive_at_end,continued,mfe_r,mae_r,realized_r,bars_alive\r\n");
   return fh;
  }

//+------------------------------------------------------------------+
//| Append one finalized zone-lifecycle row.                          |
//+------------------------------------------------------------------+
void BrcCsvWriteZone(const int fh, const int zone_id, const string tf, const BrcZone &z)
  {
   if(fh == INVALID_HANDLE)
      return;

   string dir  = (z.direction == BRC_BEAR) ? "SELL" : "BUY";
   string kind = (z.break_kind == BRC_SEQUENTIAL) ? "sequential" : "same_bar";

   string row =
      IntegerToString(zone_id) + "," +
      IntegerToString(z.seq) + "," + z.zone_key + "," +
      IntegerToString(z.is_primary ? 1 : 0) + "," + z.consolidated_into + "," +
      tf + "," + dir + "," +
      BrcFmtTime(z.p1_time) + "," + BrcFmtPrice(z.p1_price) + "," +
      BrcFmtTime(z.p2_time) + "," + BrcFmtPrice(z.p2_price) + "," +
      BrcFmtTime(z.p3_time) + "," + BrcFmtPrice(z.p3_price) + "," +
      BrcFmtTime(z.p4_time) + "," + BrcFmtPrice(z.p4_price) + "," +
      BrcFmtTime(z.p5_time) + "," + BrcFmtPrice(z.p5_price) + "," +
      BrcFmtPrice(z.l1) + "," + BrcFmtPrice(z.l2) + "," + BrcFmtPrice(z.mid) + "," +
      kind + "," +
      BrcFmtTime(z.t1_time) + "," + BrcFmtTime(z.t2_time) + "," + BrcFmtTime(z.t3_time) + "," +
      BrcFmtTime(z.p4_time) + "," +                       // confirm_time == p4_time
      BrcFmtTime(z.invalidation_time) + "," +
      IntegerToString(z.alive ? 1 : 0) + "," +
      IntegerToString(z.continued ? 1 : 0) + "," +
      DoubleToString(z.mfe_r, 4) + "," +
      DoubleToString(z.mae_r, 4) + "," +
      DoubleToString(z.realized_r, 4) + "," +
      IntegerToString(z.bars_alive) + "\r\n";

   FileWriteString(fh, row);
  }

#endif // BRC_CSV_MQH
