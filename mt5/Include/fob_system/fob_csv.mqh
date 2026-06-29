//+------------------------------------------------------------------+
//|                                                       fob_csv.mqh  |
//|  FOB capture CSV writer — ONE wide row per classified breakout.   |
//|                                                                    |
//|  Path-A capture contract (spec §6.1, APPROVED 2026-06-29). One CSV,|
//|  one row per event (event↔zone is 1:1 at emit). ingest_fob derives |
//|  fob_events / fob_zones / fob_cycles from it (cycle linkage rebuilt |
//|  by grouping (setup_tf, seq) — the EA assigns NO surrogate keys).  |
//|                                                                    |
//|  Columns are tiered:                                               |
//|    TIER A — wire now (detection + FobReplayZoneLife).              |
//|    TIER B — cheap add this task (same replay walk + label-derived).|
//|    TIER C — HEADER emitted, VALUE deferred to phase-2 / ingest.    |
//|  See spec §6.1 for the full column rationale + 3 frozen decisions. |
//|                                                                    |
//|  UTF-8, header row, comma-delimited (ASCII subset = valid UTF-8,   |
//|  no BOM). htf_state is JSON → RFC4180-quoted ("" escapes internal  |
//|  quotes) so its commas don't split the row. Python ingest reads    |
//|  with pd.read_csv(..., encoding='utf-8').                          |
//|                                                                    |
//|  File: <MT5>/Common/Files/FOB/fob_capture_<symbol>_<runid>.csv     |
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
   string path = "FOB\\fob_capture_" + symbol + "_" + runid + ".csv";
   int fh = FileOpen(path, FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_COMMON);
   if(fh == INVALID_HANDLE)
     {
      PrintFormat("[FOB] FATAL cannot open %s (err %d)", path, GetLastError());
      return INVALID_HANDLE;
     }
   FileWriteString(fh,
      //--- TIER A — identity + 4-pointer zone + lifecycle (level = L1)
      "event_id,setup_tf,seq,cf_idx,label,event_tf,direction,"
      "swing_time,bar_time,level,bar_close,"
      "l2,mid,p1_time,p1_price,p3_time,p3_price,zone_valid,"
      "t1_time,t2_time,t3_time,rt_count,rt_time,alive_at_end,invalidation_time,"
      //--- TIER B — cheap behaviour adds (same replay walk + label-derived)
      "bars_alive,n_l1_touches,n_mid_touches,n_l2_touches,"
      "body_clears,risk_class,vr_zone_broken,vr_fresh,vr_made_first_tf,htf_state,"
      //--- TIER C — header emitted, VALUE deferred to phase-2 / ingest-derived
      "confirm_time,confirm_price,continued,mfe_r,mae_r,realized_r,"
      "zone_key,is_primary,superseded_by\r\n");
   return fh;
  }

//+------------------------------------------------------------------+
//| RFC4180-quote a field that may contain commas/quotes (htf_state    |
//| JSON). Wraps in "" and doubles any internal quote. Python's        |
//| pd.read_csv parses this back to the raw string by default.         |
//+------------------------------------------------------------------+
string FobCsvQuote(const string s)
  {
   string e = s;
   StringReplace(e, "\"", "\"\"");
   return "\"" + e + "\"";
  }

//+------------------------------------------------------------------+
//| Append one classified-event row (the wide capture grain). Zone     |
//| lifecycle (mid/Tn/rt/alive/counts/bars_alive/vr_fresh) MUST have   |
//| been replayed onto e.zone by FobReplayZoneLife before this call.   |
//+------------------------------------------------------------------+
void FobCsvWriteEvent(const int fh, const int event_id, const FobEvent &e)
  {
   if(fh == INVALID_HANDLE)
      return;

   bool   isVR = (e.label == FOB_VR);
   //--- risk_class from the role: CF = adjacent TF below (Low-Risk); HRCF = skip a
   //--- TF (High-Risk, currently parked). PBO/VR carry no entry risk class.
   string risk_class = (e.label == FOB_CF) ? "LR" : (e.label == FOB_HRCF ? "HR" : "");
   //--- vr_zone_broken = the zone was invalidated by a close beyond L2 (reversal /
   //--- Full-Margin trigger). Only a valid, now-dead zone counts.
   string vr_broken = (e.zone.valid && !e.zone.alive) ? "1" : "0";
   //--- body_clears: FOB detection is CLOSE-based (a break IS a close beyond the
   //--- level; a wick never triggers), so the breaking body cleared by construction.
   //--- Constant 1 documents that invariant; an open-vs-level "full body" variant is
   //--- a phase-2 refinement (needs the bar open plumbed through). See spec §6.1.
   string body_clears = "1";

   string row =
      //--- TIER A
      IntegerToString(event_id) + "," +
      FobTfName(e.setup_tf) + "," +
      IntegerToString(e.seq) + "," +
      IntegerToString(e.cf_idx) + "," +
      FobLabelName(e.label) + "," +
      FobTfName(e.event_tf) + "," +
      FobDirName(e.dir) + "," +
      FobFmtTime(e.swing_time) + "," +
      FobFmtTime(e.bar_time) + "," +
      FobFmtPrice(e.level) + "," +           // L1 (broken swing / trigger edge)
      FobFmtPrice(e.bar_close) + "," +
      FobFmtPrice(e.zone.l2) + "," +
      FobFmtPrice(e.zone.mid) + "," +
      FobFmtTime(e.zone.p1_time) + "," +
      FobFmtPrice(e.zone.p1_price) + "," +
      FobFmtTime(e.zone.p3_time) + "," +
      FobFmtPrice(e.zone.p3_price) + "," +
      (e.zone.valid ? "1" : "0") + "," +
      FobFmtTime(e.zone.t1_time) + "," +
      FobFmtTime(e.zone.t2_time) + "," +
      FobFmtTime(e.zone.t3_time) + "," +
      IntegerToString(e.zone.rt_count) + "," +
      FobFmtTime(e.zone.rt_time) + "," +
      (e.zone.alive ? "1" : "0") + "," +
      FobFmtTime(e.zone.invalidation_time) + "," +
      //--- TIER B
      IntegerToString(e.zone.bars_alive) + "," +
      IntegerToString(e.zone.n_l1_touches) + "," +
      IntegerToString(e.zone.n_mid_touches) + "," +
      IntegerToString(e.zone.n_l2_touches) + "," +
      body_clears + "," +
      risk_class + "," +
      vr_broken + "," +
      (isVR ? (e.zone.vr_fresh ? "1" : "0") : "") + "," +   // vr_fresh: VR rows only
      (isVR ? FobTfName(e.event_tf) : "") + "," +           // vr_made_first_tf = the TF that made this VR
      FobCsvQuote(e.htf_state) + "," +
      //--- TIER C (headers only; values deferred — spec §6.1)
      ",,,,,,,," + "\r\n";

   FileWriteString(fh, row);
  }

#endif // FOB_CSV_MQH
