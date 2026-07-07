//+------------------------------------------------------------------+
//|                                                    fob_ledger.mqh  |
//|  Trade bookkeeping + the per-trade ledger CSV (trader-only).       |
//|  The per-trade stash is bundled into FobTradeBook so these         |
//|  functions can live in an include (an include can't see the .mq5   |
//|  globals declared below it). Extracted from fob_trader 2026-06-29; |
//|  logic unchanged.                                                  |
//+------------------------------------------------------------------+
#ifndef FOB_LEDGER_MQH
#define FOB_LEDGER_MQH
#property strict

#include "fob_types.mqh"

//--- per-trade stash keyed by position id (parallel arrays). Holds EVERY
//--- open+closed trade — the trader is multi-position. Feeds the ledger + T2.
struct FobTradeBook
  {
   long   pid[];      double rw[];
   int    setuptf[];  int eventtf[];  int cfidx[];  int seq[];  int dir[];
  };

//+------------------------------------------------------------------+
//| Stash trade context keyed on position id (for the ledger + T2).  |
//+------------------------------------------------------------------+
void StashTrade(FobTradeBook &book, const long pid, const double rw, const FobEvent &e)
  {
   int m = ArraySize(book.pid);
   ArrayResize(book.pid, m + 1);     ArrayResize(book.rw, m + 1);
   ArrayResize(book.setuptf, m + 1); ArrayResize(book.eventtf, m + 1);
   ArrayResize(book.cfidx, m + 1);   ArrayResize(book.seq, m + 1);  ArrayResize(book.dir, m + 1);
   book.pid[m] = pid;       book.rw[m] = rw;
   book.setuptf[m] = e.setup_tf;  book.eventtf[m] = e.event_tf;
   book.cfidx[m] = e.cf_idx;      book.seq[m] = e.seq;   book.dir[m] = e.dir;
  }

//+------------------------------------------------------------------+
//| Map a closed position id -> its stashed trade context.           |
//+------------------------------------------------------------------+
double CtxForPos(const FobTradeBook &book, const long pid,
                 int &setup_tf, int &event_tf, int &cf_idx, int &seq, int &dir)
  {
   for(int i = ArraySize(book.pid) - 1; i >= 0; i--)
      if(book.pid[i] == pid)
        {
         setup_tf = book.setuptf[i]; event_tf = book.eventtf[i]; cf_idx = book.cfidx[i];
         seq = book.seq[i]; dir = book.dir[i];
         return book.rw[i];
        }
   setup_tf = -1; event_tf = -1; cf_idx = 0; seq = 0; dir = 0;
   return 0.0;
  }

//+------------------------------------------------------------------+
//| (CF_L1_LIMIT) per-PENDING-ORDER stash, keyed by the order ticket. |
//| A pending limit carries its cycle context BEFORE it fills; on a   |
//| fill the ledger recovers it via the IN-deal's DEAL_ORDER. Parallel|
//| to FobTradeBook (which is keyed by position id, for market fills).|
//+------------------------------------------------------------------+
struct FobPendingBook
  {
   long   ticket[];   double rw[];
   int    setuptf[];  int eventtf[];  int cfidx[];  int seq[];  int dir[];
  };

//--- stash a placed pending limit's context, keyed on its order ticket.
void StashPending(FobPendingBook &pb, const long ticket, const double rw, const FobEvent &e)
  {
   int m = ArraySize(pb.ticket);
   ArrayResize(pb.ticket, m + 1);   ArrayResize(pb.rw, m + 1);
   ArrayResize(pb.setuptf, m + 1);  ArrayResize(pb.eventtf, m + 1);
   ArrayResize(pb.cfidx, m + 1);    ArrayResize(pb.seq, m + 1);  ArrayResize(pb.dir, m + 1);
   pb.ticket[m] = ticket;      pb.rw[m] = rw;
   pb.setuptf[m] = e.setup_tf; pb.eventtf[m] = e.event_tf;
   pb.cfidx[m] = e.cf_idx;     pb.seq[m] = e.seq;   pb.dir[m] = e.dir;
  }

//--- map a filled pending's originating ORDER ticket -> its stashed context.
double CtxForPending(const FobPendingBook &pb, const long ticket,
                     int &setup_tf, int &event_tf, int &cf_idx, int &seq, int &dir)
  {
   for(int i = ArraySize(pb.ticket) - 1; i >= 0; i--)
      if(pb.ticket[i] == ticket)
        {
         setup_tf = pb.setuptf[i]; event_tf = pb.eventtf[i]; cf_idx = pb.cfidx[i];
         seq = pb.seq[i]; dir = pb.dir[i];
         return pb.rw[i];
        }
   setup_tf = -1; event_tf = -1; cf_idx = 0; seq = 0; dir = 0;
   return 0.0;
  }

//+------------------------------------------------------------------+
//| Cancel-on-parent-PBO: a NEW PBO on the setup TF (seq = new_seq)   |
//| ends the current cycle, so any STILL-PENDING L1 limit from a PRIOR|
//| cycle (seq < new_seq) is a runaway winner that never pulled back  |
//| -> delete it. A FILLED limit has left the orders pool (OrderSelect|
//| fails) -> untouched: its SL/TP own it and its context stays booked|
//| for the ledger. Only touches this setup TF's pendings.            |
//+------------------------------------------------------------------+
void CancelPendingsForNewPbo(const FobPendingBook &pb, const ulong magic,
                             const int setup_tf, const int new_seq)
  {
   for(int i = ArraySize(pb.ticket) - 1; i >= 0; i--)
     {
      if(pb.setuptf[i] != setup_tf) continue;
      if(pb.seq[i] >= new_seq)      continue;
      long tk = pb.ticket[i];
      if(!OrderSelect(tk))                                  continue;  // filled/gone -> leave booked
      if((ulong)OrderGetInteger(ORDER_MAGIC) != magic)      continue;
      MqlTradeRequest req;  MqlTradeResult res;
      ZeroMemory(req);  ZeroMemory(res);
      req.action = TRADE_ACTION_REMOVE;
      req.order  = (ulong)tk;
      if(!OrderSend(req, res))
         continue;                                          // delete failed (already filled/gone) — leave booked
     }
  }

//+------------------------------------------------------------------+
//| Rebuild live_tf/live_seq = the (setup_tf, seq) cycles that still  |
//| have an OPEN position, so a live cycle's sequence dots survive    |
//| even after a newer cycle supersedes it.                          |
//+------------------------------------------------------------------+
void CollectLiveCycles(const FobTradeBook &book, const ulong magic, int &live_tf[], int &live_seq[])
  {
   ArrayResize(live_tf, 0);
   ArrayResize(live_seq, 0);
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong tk = PositionGetTicket(i);
      if(tk == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      if((ulong)PositionGetInteger(POSITION_MAGIC) != magic) continue;
      long pid = (long)PositionGetInteger(POSITION_IDENTIFIER);
      //--- map this open position back to its stashed cycle (setup_tf, seq)
      for(int j = ArraySize(book.pid) - 1; j >= 0; j--)
         if(book.pid[j] == pid)
           {
            int m = ArraySize(live_tf);
            ArrayResize(live_tf, m + 1); ArrayResize(live_seq, m + 1);
            live_tf[m] = book.setuptf[j]; live_seq[m] = book.seq[j];
            break;
           }
     }
  }

//+------------------------------------------------------------------+
//| Human-readable exit reason from the closing deal.                |
//+------------------------------------------------------------------+
string ExitReasonName(const long reason)
  {
   switch((ENUM_DEAL_REASON)reason)
     {
      case DEAL_REASON_SL: return "SL";
      case DEAL_REASON_TP: return "TP";
      case DEAL_REASON_SO: return "SO";
      case DEAL_REASON_EXPERT: return "EXPERT";
     }
   return "OTHER";
  }

//+------------------------------------------------------------------+
//| Per-trade ledger CSV from the tester's deal history. One row per |
//| closed position with setup_tf / event_tf / cf_idx / seq + R-     |
//| outcome — the input for T2 (cf_idx conditioning). Auto-written   |
//| on deinit. Lands in Common\Files\FOB.                            |
//+------------------------------------------------------------------+
void WriteTradeLedger(const FobTradeBook &book, const FobPendingBook &pbook, const ulong magic,
                      const int setup_tf, const double slBufferK, const double rMultTP,
                      const int cfIdxFilter, const int entryMode, const int pboLevel = -1)
  {
   if(!HistorySelect(0, TimeCurrent())) return;
   int total = HistoryDealsTotal();
   if(total <= 0) return;

   //--- pass 1: index IN deals by position id
   long in_pid[];  datetime in_time[];  double in_px[];  double in_lot[];  int in_dir[];  long in_order[];
   for(int i = 0; i < total; i++)
     {
      ulong tk = HistoryDealGetTicket(i);
      if((long)HistoryDealGetInteger(tk, DEAL_MAGIC) != (long)magic) continue;
      if((ENUM_DEAL_ENTRY)HistoryDealGetInteger(tk, DEAL_ENTRY) != DEAL_ENTRY_IN) continue;
      int n = ArraySize(in_pid);
      ArrayResize(in_pid, n+1); ArrayResize(in_time, n+1); ArrayResize(in_px, n+1);
      ArrayResize(in_lot, n+1); ArrayResize(in_dir, n+1); ArrayResize(in_order, n+1);
      in_pid[n]   = (long)HistoryDealGetInteger(tk, DEAL_POSITION_ID);
      in_time[n]  = (datetime)HistoryDealGetInteger(tk, DEAL_TIME);
      in_px[n]    = HistoryDealGetDouble(tk, DEAL_PRICE);
      in_lot[n]   = HistoryDealGetDouble(tk, DEAL_VOLUME);
      in_dir[n]   = (HistoryDealGetInteger(tk, DEAL_TYPE) == DEAL_TYPE_BUY) ? 1 : -1;
      in_order[n] = (long)HistoryDealGetInteger(tk, DEAL_ORDER);   // originating order (pending ticket for a limit fill)
     }

   string stamp = TimeToString(TimeCurrent(), TIME_DATE|TIME_MINUTES);
   StringReplace(stamp, ".", ""); StringReplace(stamp, ":", ""); StringReplace(stamp, " ", "_");
   string ver = FOB_VERSION; StringReplace(ver, ".", "");
   string rmode = "cfz";   // CF_ZONE is the only risk mode
   //--- K & RR in the name so an OPTIMIZATION sweep writes one CSV per combo
   //    (else every pass clobbers the same file). k025=SLbuf 0.25, rr200=RR 2.00.
   string ktok  = StringFormat("k%03d",  (int)MathRound(slBufferK * 100));
   string rrtok = StringFormat("rr%03d", (int)MathRound(rMultTP  * 100));
   //--- entry mechanic in the name so CF_MARKET / CF_L1_LIMIT / PBO_LIMIT (per depth)
   //--- never clobber each other. 2==PBO_LIMIT -> pbot1/pbot2/pbot3 by pboLevel.
   string emtok;
   if(entryMode == 2)      emtok = StringFormat("pbot%d", pboLevel + 1);  // 0->t1,1->t2,2->t3
   else if(entryMode == 1) emtok = "l1";
   else                    emtok = "cf";
   string fname = StringFormat("FOB\\fob_trades_%s_v%s_%s_%s_%s_%s_%s_cf%d_%s.csv",
                               _Symbol, ver, FobTfName(setup_tf), rmode,
                               emtok, ktok, rrtok, cfIdxFilter, stamp);
   int h = FileOpen(fname, FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON, ',');
   if(h == INVALID_HANDLE)
     { PrintFormat("[FOB TRADER] ledger FileOpen failed (%d) for %s", GetLastError(), fname); return; }
   FileWrite(h, "position_id","direction","setup_tf","event_tf","cf_idx","seq",
             "entry_ts","entry_px","exit_ts","exit_px","exit_reason","lots",
             "range_w","realized_r","realized_pnl_usd","win");

   //--- pass 2: one row per OUT deal, paired to its IN
   int rows = 0, wins = 0;
   for(int i = 0; i < total; i++)
     {
      ulong tk = HistoryDealGetTicket(i);
      if((long)HistoryDealGetInteger(tk, DEAL_MAGIC) != (long)magic) continue;
      if((ENUM_DEAL_ENTRY)HistoryDealGetInteger(tk, DEAL_ENTRY) != DEAL_ENTRY_OUT) continue;

      long     pid     = (long)HistoryDealGetInteger(tk, DEAL_POSITION_ID);
      datetime exit_ts = (datetime)HistoryDealGetInteger(tk, DEAL_TIME);
      double   exit_px = HistoryDealGetDouble(tk, DEAL_PRICE);
      double   pnl     = HistoryDealGetDouble(tk, DEAL_PROFIT)
                         + HistoryDealGetDouble(tk, DEAL_SWAP)
                         + HistoryDealGetDouble(tk, DEAL_COMMISSION);
      string   reason  = ExitReasonName(HistoryDealGetInteger(tk, DEAL_REASON));

      datetime entry_ts = 0; double entry_px = 0, lots = 0; int dir = 0; long entry_ord = 0;
      for(int j = ArraySize(in_pid) - 1; j >= 0; j--)
         if(in_pid[j] == pid)
           { entry_ts = in_time[j]; entry_px = in_px[j]; lots = in_lot[j]; dir = in_dir[j];
             entry_ord = in_order[j]; break; }

      int s_tf, e_tf, cfx, sq, edir;
      //--- limit fills carry cycle context by their originating ORDER (pending-book);
      //--- market fills carry it by POSITION_ID (trade-book). Try pending first.
      double rw = CtxForPending(pbook, entry_ord, s_tf, e_tf, cfx, sq, edir);
      if(s_tf < 0)
         rw = CtxForPos(book, pid, s_tf, e_tf, cfx, sq, edir);
      double rR = (rw > 0.0) ? (dir * (exit_px - entry_px) / rw) : 0.0;
      int    win = (rR > 0.0) ? 1 : 0;
      wins += win;

      FileWrite(h, (string)pid, (dir > 0 ? "BUY" : "SELL"),
                (s_tf >= 0 ? FobTfName(s_tf) : "?"), (e_tf >= 0 ? FobTfName(e_tf) : "?"),
                (string)cfx, (string)sq,
                TimeToString(entry_ts, TIME_DATE|TIME_SECONDS), DoubleToString(entry_px, _Digits),
                TimeToString(exit_ts,  TIME_DATE|TIME_SECONDS), DoubleToString(exit_px, _Digits),
                reason, DoubleToString(lots, 2), DoubleToString(rw, _Digits),
                DoubleToString(rR, 4), DoubleToString(pnl, 2), (string)win);
      rows++;
     }
   FileClose(h);
   double wr = (rows > 0) ? (100.0 * wins / rows) : 0.0;
   PrintFormat("[FOB TRADER] v%s ledger: %d trades, win-rate %.2f%% (%d/%d) -> Common\\Files\\%s",
               FOB_VERSION, rows, wr, wins, rows, fname);
  }

#endif // FOB_LEDGER_MQH
