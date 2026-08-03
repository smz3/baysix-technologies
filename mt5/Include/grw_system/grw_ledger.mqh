//+------------------------------------------------------------------+
//|                                                     grw_ledger.mqh |
//|  GRW-001 — the run's output contract. Two UTF-8 CSVs per pass,      |
//|  written from OnTester into the COMMON files folder:                |
//|                                                                     |
//|    grw_run_<tag>.csv     one row  — the pass summary. Columns map   |
//|                          1:1 onto grw_passes so the Python side     |
//|                          copies values instead of interpreting them.|
//|    grw_trades_<tag>.csv  one row per closed round-trip -> the shared |
//|                          tester_trades spine.                       |
//|                                                                     |
//|  Nothing here writes to research.db. A pass row is RAW MATERIAL,    |
//|  not a finding (spec §2.3), and the only sanctioned path into the   |
//|  DB is the code layer — grw.log_pass() — which CLAUDE.md rule 10    |
//|  and the protocol_guard hook both enforce. The EA hands over a file;|
//|  Python decides whether it is worth a row.                          |
//|                                                                     |
//|  `params` is emitted as JSON and hashed. config_hash is what lets   |
//|  the multiplicity ledger count DISTINCT configs, so re-running the  |
//|  identical config does not silently inflate the trial count.        |
//+------------------------------------------------------------------+
#ifndef GRW_LEDGER_MQH
#define GRW_LEDGER_MQH
#property strict

#include "grw_types.mqh"
#include "grw_exit.mqh"
#include "grw_fitness.mqh"

//+------------------------------------------------------------------+
//| The config, as JSON. This is the authoritative record of WHAT RAN  |
//| — it is serialised from the same GrwCfg the modules read, so it    |
//| cannot describe a different EA than the one that traded.           |
//+------------------------------------------------------------------+
string GrwCfgJson(const GrwCfg &c)
  {
   return StringFormat(
      "{\"entry_type\":\"%s\",\"filter_mask\":%d,\"filters\":\"%s\",\"exit_type\":\"%s\","
      "\"risk_frac\":%.6f,\"tf\":\"%s\",\"htf\":\"%s\",\"lookback\":%d,\"ext_k\":%.4f,"
      "\"sl_buf_k\":%.4f,\"retest_bars\":%d,\"sess_start\":%d,\"sess_end\":%d,"
      "\"vol_floor_pts\":%.2f,\"cost_mult\":%.2f,\"rollover_hr\":%d,\"rr\":%.4f,"
      "\"arm_r\":%.4f,\"trail_atr\":%.4f,\"time_stop_bars\":%d,\"atr_period\":%d,"
      "\"magic\":%I64u}",
      GrwEntryName(c.entry_type), c.filter_mask, GrwFilterMaskName(c.filter_mask),
      GrwExitName(c.exit_type), c.risk_frac,
      EnumToString(c.tf), EnumToString(c.htf), c.lookback, c.ext_k,
      c.sl_buf_k, c.retest_bars, c.sess_start, c.sess_end,
      c.vol_floor_pts, c.cost_mult, c.rollover_hr, c.rr,
      c.arm_r, c.trail_atr, c.time_stop_bars, c.atr_period, c.magic);
  }

//+------------------------------------------------------------------+
//| Deterministic hash of the config JSON -> grw_passes.config_hash.  |
//| SHA256 via CryptEncode; falls back to a cheap rolling hash only   |
//| if the crypt call fails, and SAYS SO in the value so a fallback   |
//| hash can never be mistaken for a real one.                       |
//+------------------------------------------------------------------+
string GrwConfigHash(const string json)
  {
   uchar src[], dst[], key[];
   StringToCharArray(json, src, 0, StringLen(json));   // no trailing NUL in the digest
   if(CryptEncode(CRYPT_HASH_SHA256, src, key, dst) > 0)
     {
      string hex = "";
      for(int i = 0; i < ArraySize(dst); i++)
         hex += StringFormat("%02x", dst[i]);
      return hex;
     }
   ulong h = 1469598103934665603;                      // FNV-1a fallback
   for(int i = 0; i < ArraySize(src); i++)
     { h ^= (ulong)src[i];  h *= 1099511628211; }
   return StringFormat("fnv1a:%I64x", h);
  }

//+------------------------------------------------------------------+
//| Run tag used in both filenames. Symbol + version + window start,  |
//| so two passes of the same batch never collide.                    |
//+------------------------------------------------------------------+
string GrwRunTag(const string suffix)
  {
   datetime t0 = (datetime)SeriesInfoInteger(_Symbol, PERIOD_M1, SERIES_FIRSTDATE);
   string   ts = TimeToString(t0, TIME_DATE);
   StringReplace(ts, ".", "");
   string tail = (StringLen(suffix) > 0) ? ("_" + suffix) : "";
   return StringFormat("%s_v%s_%s%s", _Symbol, GRW_VERSION, ts, tail);
  }

//+------------------------------------------------------------------+
//| PARAMS — written to its OWN .json file, never into the CSV.       |
//|                                                                    |
//| MQL5's FileWrite does not quote a field containing the separator,  |
//| and the config JSON is full of commas, so embedding it shredded    |
//| the summary row into phantom columns (MEASURED, smoke run          |
//| 2026-08-03). A separate artifact removes the escaping problem      |
//| rather than papering over it.                                      |
//+------------------------------------------------------------------+
bool GrwWriteParams(const string tag, const string cfg_json)
  {
   string fname = "grw_params_" + tag + ".json";
   int h = FileOpen(fname, FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON);
   if(h == INVALID_HANDLE)
     {
      PrintFormat("[GRW] params FileOpen failed (%d) for %s", GetLastError(), fname);
      return false;
     }
   FileWriteString(h, cfg_json);
   FileClose(h);
   return true;
  }

//+------------------------------------------------------------------+
//| PASS SUMMARY — one header row + one data row.                     |
//+------------------------------------------------------------------+
bool GrwWriteRunSummary(const string tag, const GrwCfg &c, const GrwStats &st,
                        const GrwFitness &f, const string batch_id)
  {
   string fname = "grw_run_" + tag + ".csv";
   int h = FileOpen(fname, FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON, ',');
   if(h == INVALID_HANDLE)
     {
      PrintFormat("[GRW] run-summary FileOpen failed (%d) for %s", GetLastError(), fname);
      return false;
     }

   string cfg_json = GrwCfgJson(c);

   FileWrite(h,
      "batch_id","ea_name","ea_version","fitness_version","git_sha","git_dirty",
      "symbol","tf","period_start","period_end",
      "fitness","growth","unrankable","n_trades","net_usd","max_dd_pct",
      "profit_factor","win_rate","initial_deposit","final_equity",
      "n_signals","n_gated","n_skipped","n_orders","n_clamp_up","n_clamp_down",
      "clamp_up_frac","mean_risk_pct","max_risk_pct","sizing_valid",
      "config_hash","params_file");

   FileWrite(h,
      batch_id, "grw_meta", GRW_VERSION, GRW_FITNESS_VERSION,
      GRW_GIT_SHA, (GRW_GIT_DIRTY ? "1" : "0"),
      _Symbol, EnumToString(c.tf),
      TimeToString((datetime)SeriesInfoInteger(_Symbol, PERIOD_M1, SERIES_FIRSTDATE), TIME_DATE),
      TimeToString(TimeCurrent(), TIME_DATE),
      DoubleToString(f.fitness, 8), DoubleToString(f.growth, 8),
      (f.unrankable ? "1" : "0"), (string)f.n_trades,
      DoubleToString(f.net_usd, 2), DoubleToString(f.max_dd_pct, 4),
      DoubleToString(f.profit_factor, 4), DoubleToString(f.win_rate, 4),
      DoubleToString(f.initial_deposit, 2), DoubleToString(f.final_equity, 2),
      (string)st.n_signals, (string)st.n_gated, (string)st.n_skipped,
      (string)st.n_orders, (string)st.n_clamp_up, (string)st.n_clamp_down,
      DoubleToString(f.clamp_up_frac, 6), DoubleToString(f.mean_risk_pct, 4),
      DoubleToString(f.max_risk_pct, 4), (f.sizing_valid ? "1" : "0"),
      GrwConfigHash(cfg_json), "grw_params_" + tag + ".json");

   FileClose(h);
   GrwWriteParams(tag, cfg_json);
   PrintFormat("[GRW] run summary -> %s", fname);
   return true;
  }

//+------------------------------------------------------------------+
//| TRADE LEDGER — walks the deal history and pairs IN/OUT deals by   |
//| POSITION_ID. realized_R uses the risk FROZEN AT FILL (g_grw_record)|
//| never a risk re-derived from the exit, which would make R mean a  |
//| different thing on every row.                                     |
//+------------------------------------------------------------------+
int GrwWriteTrades(const string tag, const ulong magic)
  {
   if(!HistorySelect(0, TimeCurrent()))
     {
      Print("[GRW] HistorySelect failed — no trade ledger written");
      return 0;
     }

   string fname = "grw_trades_" + tag + ".csv";
   int h = FileOpen(fname, FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON, ',');
   if(h == INVALID_HANDLE)
     {
      PrintFormat("[GRW] trade-ledger FileOpen failed (%d) for %s", GetLastError(), fname);
      return 0;
     }
   FileWrite(h, "position_id","direction","tag","entry_ts","entry_px","exit_ts","exit_px",
                "lots","risk_unit","realized_R","realized_pnl_usd","commission","swap");

   int total = HistoryDealsTotal();
   int rows  = 0;
   //--- one pass per position id, driven off its OUT deals; IN deals supply the entry.
   for(int i = 0; i < total; i++)
     {
      ulong d = HistoryDealGetTicket(i);
      if(d == 0) continue;
      if(HistoryDealGetString(d, DEAL_SYMBOL) != _Symbol) continue;
      if((ENUM_DEAL_ENTRY)HistoryDealGetInteger(d, DEAL_ENTRY) != DEAL_ENTRY_OUT) continue;

      long pos_id = (long)HistoryDealGetInteger(d, DEAL_POSITION_ID);

      //--- OWNERSHIP IS BY POSITION, NOT BY MAGIC (bug found 2026-08-03, $20 smoke run).
      //--- A broker STOP-OUT closes the position with a deal whose magic is 0, so a
      //--- DEAL_MAGIC filter drops precisely the trade that blew the account up: the
      //--- ledger summed to +$47.44 while the tester reported net -$17.37. The EA's own
      //--- append-only record is the authority on which positions are ours.
      if(GrwRecordRisk(pos_id) <= 0.0 && GrwRecordTag(pos_id) == "") continue;

      //--- find this position's entry deal.
      double   entry_px = 0.0;  datetime entry_ts = 0;  long dir = 0;
      for(int j = 0; j < total; j++)
        {
         ulong e = HistoryDealGetTicket(j);
         if(e == 0) continue;
         if((long)HistoryDealGetInteger(e, DEAL_POSITION_ID) != pos_id) continue;
         if((ENUM_DEAL_ENTRY)HistoryDealGetInteger(e, DEAL_ENTRY) != DEAL_ENTRY_IN) continue;
         entry_px = HistoryDealGetDouble(e, DEAL_PRICE);
         entry_ts = (datetime)HistoryDealGetInteger(e, DEAL_TIME);
         dir      = (HistoryDealGetInteger(e, DEAL_TYPE) == DEAL_TYPE_BUY) ? 1 : -1;
         break;
        }
      if(entry_ts == 0) continue;                       // orphan OUT — skip rather than guess

      double exit_px = HistoryDealGetDouble(d, DEAL_PRICE);
      double lots    = HistoryDealGetDouble(d, DEAL_VOLUME);
      double pnl     = HistoryDealGetDouble(d, DEAL_PROFIT);
      double comm    = HistoryDealGetDouble(d, DEAL_COMMISSION);
      double swap    = HistoryDealGetDouble(d, DEAL_SWAP);
      double risk    = GrwRecordRisk(pos_id);
      double r_mult  = (risk > 0.0) ? (dir * (exit_px - entry_px) / risk) : 0.0;

      //--- exit_reason: a stop-out is the one exit the strategy did not choose, so it is
      //--- labelled rather than left to look like an ordinary close.
      string exit_reason = ((ulong)HistoryDealGetInteger(d, DEAL_MAGIC) == magic)
                           ? "strategy" : "broker_stopout";

      FileWrite(h, (string)pos_id, (dir > 0 ? "BUY" : "SELL"), GrwRecordTag(pos_id) + "|" + exit_reason,
                TimeToString(entry_ts, TIME_DATE|TIME_SECONDS),
                DoubleToString(entry_px, _Digits),
                TimeToString((datetime)HistoryDealGetInteger(d, DEAL_TIME), TIME_DATE|TIME_SECONDS),
                DoubleToString(exit_px, _Digits),
                DoubleToString(lots, 2), DoubleToString(risk, _Digits),
                DoubleToString(r_mult, 6), DoubleToString(pnl, 2),
                DoubleToString(comm, 2), DoubleToString(swap, 2));
      rows++;
     }

   FileClose(h);
   PrintFormat("[GRW] trade ledger -> %s (%d round-trips)", fname, rows);
   return rows;
  }

#endif // GRW_LEDGER_MQH
