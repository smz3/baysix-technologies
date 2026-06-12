//+------------------------------------------------------------------+
//|  orb_trade_csv.mqh                                               |
//|  Buffered per-trade fidelity CSV writer — "Feed B".             |
//|                                                                  |
//|  The AUTHORITATIVE per-trade record for the MT5 <-> research.db  |
//|  fidelity flow. Contract: braindump/mt5_fidelity_flow.md.        |
//|                                                                  |
//|  Delimiter ';'  — chosen so JSON commas inside `meta` need no    |
//|  escaping. Ingest reads with sep=';' then json.loads(meta).      |
//|  Columns (header written on Init):                               |
//|    ticket;session_date;direction;entry_ts;entry_px;exit_ts;      |
//|    exit_px;exit_reason;lots;risk_unit;realized_R;                |
//|    realized_pnl_usd;meta                                         |
//|                                                                  |
//|  Buffered: rows accumulate in memory and flush every `flush_n`   |
//|  + on Close() (call from OnDeinit). Mandatory for scale —        |
//|  open/close-per-trade would crawl at 100s of trades/day.         |
//|  File lives in <Common>\Files\ (FILE_COMMON) — the Python bridge.|
//+------------------------------------------------------------------+
#property strict

class CTradeCSV
  {
private:
   string   m_file;
   int      m_flags;
   string   m_buf;        // pending (un-flushed) rows
   int      m_pending;    // rows currently buffered
   int      m_flush_n;    // flush threshold
   long     m_written;    // total rows flushed (diagnostic)
   bool     m_on;         // enabled

   bool FlushImpl()
     {
      if(!m_on || m_pending == 0)
         return(true);
      // Append: open R/W, seek end, write buffer, close. Retry w/ backoff on a
      // share violation (Excel / Python may briefly hold the file).
      for(int attempt = 0; attempt < 5; attempt++)
        {
         int h = FileOpen(m_file, m_flags);
         if(h != INVALID_HANDLE)
           {
            FileSeek(h, 0, SEEK_END);
            FileWriteString(h, m_buf);
            FileClose(h);
            m_written += m_pending;
            m_buf = "";
            m_pending = 0;
            return(true);
           }
         Sleep(20 * (attempt + 1));
        }
      PrintFormat("[trade_csv] FLUSH FAILED after retries: %s (err=%d)", m_file, GetLastError());
      return(false);
     }

public:
            CTradeCSV() : m_pending(0), m_flush_n(50), m_written(0), m_on(false) {}

   //--- fresh=true recreates the file with a header (Common\Files persists across runs)
   void Init(const string filename, const int flush_n = 50, const bool fresh = true)
     {
      m_file    = filename;
      m_flags   = FILE_READ | FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_COMMON;
      m_buf     = "";
      m_pending = 0;
      m_flush_n = (flush_n < 1 ? 1 : flush_n);
      m_written = 0;
      m_on      = true;
      if(fresh)
        {
         FileDelete(m_file, FILE_COMMON);
         int h = FileOpen(m_file, m_flags);
         if(h != INVALID_HANDLE)
           {
            FileWriteString(h,
               "ticket;session_date;direction;entry_ts;entry_px;exit_ts;exit_px;"
               "exit_reason;lots;risk_unit;realized_R;realized_pnl_usd;meta\n");
            FileClose(h);
           }
         else
            PrintFormat("[trade_csv] could not create %s (err=%d)", m_file, GetLastError());
        }
     }

   //--- buffer one closed round-trip; meta_json is a ready-built JSON string
   void WriteTrade(const ulong ticket, const string session_date, const string direction,
                   const datetime entry_ts, const double entry_px,
                   const datetime exit_ts, const double exit_px, const string exit_reason,
                   const double lots, const double risk_unit, const double realized_R,
                   const double realized_pnl_usd, const string meta_json)
     {
      if(!m_on)
         return;
      string row =
         (string)ticket + ";" +
         session_date + ";" +
         direction + ";" +
         TimeToString(entry_ts, TIME_DATE | TIME_SECONDS) + ";" +
         DoubleToString(entry_px, _Digits) + ";" +
         TimeToString(exit_ts, TIME_DATE | TIME_SECONDS) + ";" +
         DoubleToString(exit_px, _Digits) + ";" +
         exit_reason + ";" +
         DoubleToString(lots, 2) + ";" +
         DoubleToString(risk_unit, _Digits) + ";" +
         DoubleToString(realized_R, 4) + ";" +
         DoubleToString(realized_pnl_usd, 2) + ";" +
         meta_json + "\n";
      m_buf += row;
      m_pending++;
      if(m_pending >= m_flush_n)
         FlushImpl();
     }

   void Close() { FlushImpl(); }            // final flush (call from OnDeinit)
   long Written() { return(m_written + m_pending); }
  };
//+------------------------------------------------------------------+
