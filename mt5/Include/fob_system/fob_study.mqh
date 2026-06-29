//+------------------------------------------------------------------+
//|                                                     fob_study.mqh  |
//|  STUDY MODE (T-170) — forward-excursion measurement, NO orders.   |
//|  Per CF on the setup TF, anchor at the CF mid price and track      |
//|  running MFE/MAE/terminal on REAL TICKS until the NEXT CF (any     |
//|  cf_idx) or a cap. COST-FREE: measured on MID (zero spread) —      |
//|  DISCOVERY, pure direction geometry; cost enters at G2, NEVER here.|
//|  Reported in RAW PRICE POINTS (v1.13.0: ATR removed).             |
//|                                                                    |
//|  Extracted from fob_trader 2026-06-29. State is bundled into       |
//|  FobStudyState (an include can't see the .mq5 globals); functions  |
//|  take it by ref + setup_tf/capBars/cfIdxFilter as params. Logic    |
//|  unchanged.                                                        |
//+------------------------------------------------------------------+
#ifndef FOB_STUDY_MQH
#define FOB_STUDY_MQH
#property strict

#include "fob_types.mqh"
#include "fob_engine.mqh"   // FobPeriods[]

//--- one open forward-excursion window + the flushed ledger rows. RAW POINTS.
struct FobStudyState
  {
   bool     sw_open;        // is a window currently being measured?
   datetime sw_cf_time;     // anchor CF bar_time
   datetime sw_open_ts;     // server time at anchor (cap clock)
   int      sw_dir;         // FOB_BULL | FOB_BEAR (continuation dir)
   int      sw_cfidx;       // anchor CF ordinal
   int      sw_seq;         // anchor PBO sequence
   double   sw_entry;       // entry-side fill (mid, cost-free) at anchor
   double   sw_mfe;         // running max favorable excursion (pts)
   double   sw_mae;         // running max adverse  excursion (pts)
   double   sw_term;        // last favorable excursion (-> terminal at close)
   //--- ledger rows (flushed on deinit)
   datetime sr_time[];  int sr_dir[];  int sr_cfidx[];  int sr_seq[];
   double   sr_entry[]; double sr_mfe[]; double sr_mae[]; double sr_term[];
   double   sr_winbars[]; int sr_nextdir[];   // window length (setup-TF bars) + next CF dir (-1 = capped)
  };

//+------------------------------------------------------------------+
//| HARD reset (globals survive reinit).                             |
//+------------------------------------------------------------------+
void FobResetStudy(FobStudyState &st)
  {
   st.sw_open = false; st.sw_cf_time = 0; st.sw_open_ts = 0; st.sw_dir = 0;
   st.sw_cfidx = 0; st.sw_seq = 0; st.sw_entry = 0.0;
   st.sw_mfe = 0.0; st.sw_mae = 0.0; st.sw_term = 0.0;
   ArrayResize(st.sr_time, 0); ArrayResize(st.sr_dir, 0); ArrayResize(st.sr_cfidx, 0); ArrayResize(st.sr_seq, 0);
   ArrayResize(st.sr_entry, 0); ArrayResize(st.sr_mfe, 0); ArrayResize(st.sr_mae, 0);
   ArrayResize(st.sr_term, 0); ArrayResize(st.sr_winbars, 0); ArrayResize(st.sr_nextdir, 0);
  }

//--- Append the just-closed window to the study ledger arrays.
//--- next_dir: FOB_BULL/FOB_BEAR of the CF that ended it, or -1 if capped.
void CloseStudyWindow(FobStudyState &st, const int next_dir, const int setup_tf)
  {
   if(!st.sw_open) return;
   int bars = (int)((TimeCurrent() - st.sw_open_ts) / PeriodSeconds(FobPeriods[setup_tf]));

   int m = ArraySize(st.sr_time);
   ArrayResize(st.sr_time, m+1);   ArrayResize(st.sr_dir, m+1);    ArrayResize(st.sr_cfidx, m+1);
   ArrayResize(st.sr_seq, m+1);    ArrayResize(st.sr_entry, m+1);
   ArrayResize(st.sr_mfe, m+1);    ArrayResize(st.sr_mae, m+1);    ArrayResize(st.sr_term, m+1);
   ArrayResize(st.sr_winbars, m+1);ArrayResize(st.sr_nextdir, m+1);
   st.sr_time[m]   = st.sw_cf_time; st.sr_dir[m]    = st.sw_dir;     st.sr_cfidx[m] = st.sw_cfidx;
   st.sr_seq[m]    = st.sw_seq;     st.sr_entry[m]  = st.sw_entry;
   st.sr_mfe[m]    = st.sw_mfe;     st.sr_mae[m]    = st.sw_mae;     st.sr_term[m]  = st.sw_term;
   st.sr_winbars[m]= bars;          st.sr_nextdir[m] = next_dir;

   st.sw_open = false;
  }

//--- Update the open window with the CURRENT tick (real-ticks model). Captures
//--- intrabar MFE/MAE in TRADEABLE terms (exit-side price), RAW POINTS.
void UpdateStudyWindow(FobStudyState &st, const int setup_tf, const int capBars)
  {
   if(!st.sw_open) return;
   //--- COST-FREE measurement: mid price, NO spread. T-170 is DISCOVERY, not a G2 net ledger.
   double mid = 0.5 * (SymbolInfoDouble(_Symbol, SYMBOL_ASK) + SymbolInfoDouble(_Symbol, SYMBOL_BID));
   double fav = (st.sw_dir == FOB_BULL) ? (mid - st.sw_entry) : (st.sw_entry - mid);
   if(fav  > st.sw_mfe) st.sw_mfe = fav;
   if(-fav > st.sw_mae) st.sw_mae = -fav;
   st.sw_term = fav;                                               // last seen -> terminal at close
   //--- cap: force-close after capBars setup-TF bars with no follow-up CF
   if((long)(TimeCurrent() - st.sw_open_ts) >= (long)capBars * PeriodSeconds(FobPeriods[setup_tf]))
      CloseStudyWindow(st, -1, setup_tf);
  }

//--- Open a fresh window anchored at this CF (mid fill, cost-free).
void OpenStudyWindow(FobStudyState &st, const FobEvent &e, const int setup_tf, const int capBars)
  {
   st.sw_open    = true;
   st.sw_cf_time = e.bar_time;
   st.sw_open_ts = TimeCurrent();
   st.sw_dir     = e.dir;
   st.sw_cfidx   = e.cf_idx;
   st.sw_seq     = e.seq;
   st.sw_entry   = 0.5 * (SymbolInfoDouble(_Symbol, SYMBOL_ASK) + SymbolInfoDouble(_Symbol, SYMBOL_BID)); // mid, cost-free
   st.sw_mfe = 0.0; st.sw_mae = 0.0; st.sw_term = 0.0;
   UpdateStudyWindow(st, setup_tf, capBars);                       // seed t=0
  }

//--- After classification: chain windows. Each new CF on the setup TF closes the
//--- prior window (ended BY that CF) and opens its own ("until next CF").
void StudyOnNewEvents(FobStudyState &st, const FobEvent &events[], int &seen,
                      const int setup_tf, const int cfIdxFilter, const int capBars)
  {
   int n = ArraySize(events);
   for(int k = seen; k < n; k++)
     {
      FobEvent e = events[k];
      if(e.label != FOB_CF)              continue;
      if(e.setup_tf != setup_tf)         continue;
      if(cfIdxFilter > 0 && e.cf_idx != cfIdxFilter) continue;
      if(st.sw_open) CloseStudyWindow(st, e.dir, setup_tf);   // prior window ends at this CF
      OpenStudyWindow(st, e, setup_tf, capBars);
     }
   seen = n;
  }

//--- Flush the study ledger (CSV) — one row per measured CF window. RAW POINTS.
void WriteStudyLedger(FobStudyState &st, const int setup_tf, const int cfIdxFilter)
  {
   if(st.sw_open) CloseStudyWindow(st, -1, setup_tf);   // close the final open window (capped at end-of-data)
   int rows = ArraySize(st.sr_time);

   string stamp = TimeToString(TimeCurrent(), TIME_DATE|TIME_MINUTES);
   StringReplace(stamp, ".", ""); StringReplace(stamp, ":", ""); StringReplace(stamp, " ", "_");
   string ver = FOB_VERSION; StringReplace(ver, ".", "");
   string fname = StringFormat("FOB\\fob_excursion_%s_v%s_%s_cf%d_%s.csv",
                               _Symbol, ver, FobTfName(setup_tf), cfIdxFilter, stamp);
   int h = FileOpen(fname, FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON, ',');
   if(h == INVALID_HANDLE)
     { PrintFormat("[FOB STUDY] ledger FileOpen failed (%d) for %s", GetLastError(), fname); return; }
   FileWrite(h, "cf_time","direction","cf_idx","seq","entry_px",
             "mfe_pts","mae_pts","terminal_pts","bars_to_next_cf","next_cf_dir");

   for(int i = 0; i < rows; i++)
     {
      string nd_s = (st.sr_nextdir[i] == FOB_BULL) ? "BUY" : (st.sr_nextdir[i] == FOB_BEAR) ? "SELL" : "CAP";
      FileWrite(h,
                TimeToString(st.sr_time[i], TIME_DATE|TIME_SECONDS),
                (st.sr_dir[i] == FOB_BULL ? "BUY" : "SELL"),
                (string)st.sr_cfidx[i], (string)st.sr_seq[i],
                DoubleToString(st.sr_entry[i], _Digits),
                DoubleToString(st.sr_mfe[i], _Digits), DoubleToString(st.sr_mae[i], _Digits),
                DoubleToString(st.sr_term[i], _Digits),
                (string)st.sr_winbars[i], nd_s);
     }
   FileClose(h);
   PrintFormat("[FOB STUDY] v%s ledger: %d windows (raw points) -> Common\\Files\\%s",
               FOB_VERSION, rows, fname);
  }

#endif // FOB_STUDY_MQH
