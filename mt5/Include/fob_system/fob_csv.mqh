//+------------------------------------------------------------------+
//|                                                       fob_csv.mqh  |
//|  FOB event-ledger CSV writer — one row per classified breakout.   |
//|                                                                    |
//|  UTF-8, header row, comma-delimited (ASCII subset = valid UTF-8,   |
//|  no BOM) — same contract as brc_csv. Python ingest reads with      |
//|  pd.read_csv(..., encoding='utf-8').                               |
//|                                                                    |
//|  File: <MT5>/Common/Files/FOB/fob_events_<symbol>_<runid>.csv      |
//+------------------------------------------------------------------+
#ifndef FOB_CSV_MQH
#define FOB_CSV_MQH
#property strict

#include "fob_types.mqh"

#define FOB_CSV_PRICE_DIGITS 3

string FobFmtTime(const datetime t)
  {
   if(t == 0)
      return "";
   return TimeToString(t, TIME_DATE | TIME_MINUTES | TIME_SECONDS);
  }

string FobFmtPrice(const double p)
  {
   return DoubleToString(p, FOB_CSV_PRICE_DIGITS);
  }

//+------------------------------------------------------------------+
//| Open the run CSV in Common/Files/FOB and write the header row.    |
//| Returns the file handle (INVALID_HANDLE on failure).              |
//+------------------------------------------------------------------+
int FobCsvOpen(const string symbol, const string runid)
  {
   string path = "FOB\\fob_events_" + symbol + "_" + runid + ".csv";
   int fh = FileOpen(path, FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_COMMON);
   if(fh == INVALID_HANDLE)
     {
      PrintFormat("[FOB] FATAL cannot open %s (err %d)", path, GetLastError());
      return INVALID_HANDLE;
     }
   FileWriteString(fh,
      "event_id,setup_tf,setup_seq,cf_idx,label,event_tf,direction,swing_time,bar_time,level,bar_close,"
      "l2,p1_time,p1_price,p3_time,p3_price,zone_valid\r\n");   // level = L1; 4-pointer zone (v1.14.0)
   return fh;
  }

//+------------------------------------------------------------------+
//| Append one classified-event row.                                  |
//+------------------------------------------------------------------+
void FobCsvWriteEvent(const int fh, const int event_id, const FobEvent &e)
  {
   if(fh == INVALID_HANDLE)
      return;

   string dir = (e.dir == FOB_BEAR) ? "SELL" : "BUY";

   string row =
      IntegerToString(event_id) + "," +
      FobTfName(e.setup_tf) + "," +
      IntegerToString(e.seq) + "," +
      IntegerToString(e.cf_idx) + "," +
      FobLabelName(e.label) + "," +
      FobTfName(e.event_tf) + "," +
      dir + "," +
      FobFmtTime(e.swing_time) + "," +
      FobFmtTime(e.bar_time) + "," +
      FobFmtPrice(e.level) + "," +
      FobFmtPrice(e.bar_close) + "," +
      //--- 4-pointer zone (L1 = level above; L2 = extreme(P1,P3))
      FobFmtPrice(e.zone.l2) + "," +
      FobFmtTime(e.zone.p1_time) + "," +
      FobFmtPrice(e.zone.p1_price) + "," +
      FobFmtTime(e.zone.p3_time) + "," +
      FobFmtPrice(e.zone.p3_price) + "," +
      (e.zone.valid ? "1" : "0") + "\r\n";

   FileWriteString(fh, row);
  }

#endif // FOB_CSV_MQH
