//+------------------------------------------------------------------+
//|                                                  fob_sequence.mqh  |
//|   FOB cross-timeframe classifier — the ONE new thing in FOB.       |
//|                                                                    |
//|  Feed it raw breakouts in STRICT chronological order (bar_time     |
//|  ascending; ties broken higher-TF-first so a PBO is established    |
//|  before any same-instant lower-TF role is judged). It maintains a  |
//|  per-setup-TF state machine and emits FobEvent(s) for each break.  |
//|                                                                    |
//|  Look-ahead-free: a break's label depends ONLY on breaks already   |
//|  fed (earlier-or-equal bar_time). That is the whole point — the    |
//|  ORB unsorted-tick lesson is that ordering IS the edge guard.      |
//|                                                                    |
//|  Supersede rule (locked 2026-06-25): a fresh break on setup-TF n   |
//|  (any direction) becomes the new PBO for n, voids the prior VR and |
//|  starts a NEW cycle. So a PBO is the "current price" read on its   |
//|  TF, and only the latest (active) cycle per setup TF is alive.     |
//|  VR locks once; CF can fire MANY times within a cycle (task 156).  |
//+------------------------------------------------------------------+
#ifndef FOB_SEQUENCE_MQH
#define FOB_SEQUENCE_MQH
#property strict

#include "fob_types.mqh"

//+------------------------------------------------------------------+
//| Append one classified event to out[]. Returns 1 (events made).    |
//+------------------------------------------------------------------+
int FobAppendEvent(FobEvent &out[], const int setup_tf, const int seq, const int label,
                   const int event_tf, const int dir, const datetime swing_time,
                   const datetime bar_time, const double level, const double bar_close,
                   const int cf_idx = 0)
  {
   int k = ArraySize(out);
   ArrayResize(out, k + 1, 1024);
   out[k].setup_tf   = setup_tf;
   out[k].seq        = seq;
   out[k].cf_idx     = cf_idx;
   out[k].label      = label;
   out[k].event_tf   = event_tf;
   out[k].dir        = dir;
   out[k].swing_time = swing_time;
   out[k].bar_time   = bar_time;
   out[k].level      = level;
   out[k].bar_close  = bar_close;
   return 1;
  }

//+------------------------------------------------------------------+
//| Classify ONE raw break (event-TF `etf`, direction `dir`, at       |
//| bar_time `bt`, level=broken swing price, close=break close).      |
//| Mutates st[] (the per-setup-TF state machine), appends every      |
//| role this break plays to ev[]. Returns the number appended (0-3). |
//|                                                                    |
//| MUST be called in chronological bar_time order.                   |
//+------------------------------------------------------------------+
int FobClassifyBreak(FobSetupState &st[], const int n_tf,
                     const int etf, const int dir, const datetime swt, const datetime bt,
                     const double level, const double close,
                     FobEvent &ev[], const bool pbo_newest_only = true)
  {
   int made = 0;

   //--- ROLE 1: PBO for its own setup TF (the SOURCE of the current leg near CMP).
   //--- SKIP the lowest TF (etf==0, M1): a PBO needs a TF below to ever
   //--- supply its VR/CF, and there is none under M1, so an M1 PBO could
   //--- never develop. M1 breaks still play ROLE 2 (VR/CF for M5) below.
   if(etf > 0)
     {
      //--- CMP-freshness gate (task PBO-newest): a reversal (opp dir, or no
      //--- live PBO) is always a fresh source -> supersede. A SAME-direction
      //--- break supersedes ONLY if it breaks a NEWER swing than the current
      //--- PBO; a same-dir reach-back to OLDER structure is stale context and
      //--- must NOT become the PBO (it still plays ROLE 2 below). Legacy
      //--- "latest-always-wins" behaviour kept under pbo_newest_only=false.
      bool reversal = (!st[etf].active) || (dir != st[etf].pbo_dir);
      bool fresher  = (swt > st[etf].pbo_swing);
      bool supersede = pbo_newest_only ? (reversal || fresher) : true;
      if(supersede)
        {
         st[etf].active    = true;
         st[etf].seq      += 1;
         st[etf].pbo_dir   = dir;
         st[etf].pbo_time  = bt;
         st[etf].pbo_swing = swt;
         st[etf].vr_locked = false;
         st[etf].vr_time   = 0;
         st[etf].vr_swing  = 0;   // new cycle -> clear the same-bar VR watermark
         st[etf].vr_ev_idx = -1;  // new cycle -> no live VR row to rewrite
         st[etf].cf_count  = 0;   // new cycle -> CF ordinal restarts
         st[etf].last_conf_swing = 0;   // new cycle -> confirming-chain watermark clears
         made += FobAppendEvent(ev, etf, st[etf].seq, FOB_PBO, etf, dir, swt, bt, level, close);
        }
     }

   //--- ROLE 2: VR or CF for the setup TF one above (n = etf+1) ------
   int up1 = etf + 1;
   if(up1 < n_tf && st[up1].active)
     {
      if(!st[up1].vr_locked)
        {
         //--- first OPPOSITE break after that PBO = the (single) VR
         if(dir != st[up1].pbo_dir && bt > st[up1].pbo_time)
           {
            st[up1].vr_locked = true;
            st[up1].vr_time   = bt;
            st[up1].vr_swing  = swt;      // remember VR structure for the same-bar newest-swing pick
            st[up1].vr_level  = level;   // VR's broken-swing price = the trader's structural 1R ref
            //--- seed the confirming-chain watermark at the VR's own structure:
            //--- the first CF must break something NEWER than this (task 159).
            st[up1].last_conf_swing = swt;
            st[up1].vr_ev_idx = ArraySize(ev);   // the row we may rewrite on a same-bar fresher tie
            made += FobAppendEvent(ev, up1, st[up1].seq, FOB_VR, etf, dir, swt, bt, level, close);
           }
        }
      //--- SAME-BAR VR upgrade (newest-swing wins, mirrors PBO freshness): one bar
      //--- can break SEVERAL opposite swings at once; the VR must sit on the NEWEST
      //--- (nearest the turn), not the first (oldest) one fed. A later opposite break
      //--- on the SAME bar with a fresher swing REWRITES the VR row in place — same
      //--- dot, no duplicate event. Cross-bar opposite breaks are NOT the VR (the
      //--- first bar to retrace owns the timing), so this is gated to bt == vr_time.
      else if(dir != st[up1].pbo_dir && bt == st[up1].vr_time
              && swt > st[up1].vr_swing && st[up1].vr_ev_idx >= 0)
        {
         st[up1].vr_swing        = swt;
         st[up1].vr_level        = level;
         st[up1].last_conf_swing = swt;
         int vi = st[up1].vr_ev_idx;
         ev[vi].swing_time = swt;     // dot's x -> the newest broken swing (the real VR)
         ev[vi].level      = level;   // dot's y / structural 1R ref -> that swing's price
         ev[vi].bar_close  = close;
        }
      else
        {
         //--- VR locked: EVERY SAME-direction continuation break = a CF.
         //--- Multiple CFs per cycle (2nd-CF layering, task 156) — no lock;
         //--- the cycle only ends when a fresh setup-TF break supersedes it.
         //--- cf_count++ stamps the per-cycle ordinal (1st CF, 2nd CF, ...)
         //--- so the entry test can separate 1st-CF vs Nth-CF accuracy.
         //--- task 159: the broken swing MUST be newer than the confirming-chain
         //--- watermark (= VR swing for CF1, then prior CF swing). A same-dir break
         //--- that reaches back to a pre-VR / already-confirmed OLD structure is NOT
         //--- a continuation and is dropped (no event, ordinal not advanced).
         if(dir == st[up1].pbo_dir && bt > st[up1].vr_time && swt > st[up1].last_conf_swing)
           {
            st[up1].cf_count += 1;
            st[up1].last_conf_swing = swt;   // advance the watermark to this CF's structure
            made += FobAppendEvent(ev, up1, st[up1].seq, FOB_CF, etf, dir, swt, bt, level, close,
                                   st[up1].cf_count);
           }
        }
     }

   //--- HRCF (setup TF two above) REMOVED 2026-06-25: it labelled the
   //--- faster n-2 TF independently of CF, so HRCF could print AFTER CF
   //--- (backwards vs its "early confirmation" intent). Parked for a
   //--- future overlay edge-test; core is now PBO -> VR -> CF (2-TF pair).
   return made;
  }

#endif // FOB_SEQUENCE_MQH
