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
//|  (any direction) becomes the new PBO for n and resets its VR/CF/   |
//|  HRCF progress. So a PBO is the "current price" read on its TF.    |
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
                   const datetime bar_time, const double level, const double bar_close)
  {
   int k = ArraySize(out);
   ArrayResize(out, k + 1, 1024);
   out[k].setup_tf   = setup_tf;
   out[k].seq        = seq;
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
                     FobEvent &ev[])
  {
   int made = 0;

   //--- ROLE 1: PBO for its own setup TF (supersede — always fires) --
   st[etf].active    = true;
   st[etf].seq      += 1;
   st[etf].pbo_dir   = dir;
   st[etf].pbo_time  = bt;
   st[etf].vr_locked = false;
   st[etf].vr_time   = 0;
   st[etf].cf_done   = false;
   st[etf].hrcf_done = false;
   made += FobAppendEvent(ev, etf, st[etf].seq, FOB_PBO, etf, dir, swt, bt, level, close);

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
            made += FobAppendEvent(ev, up1, st[up1].seq, FOB_VR, etf, dir, swt, bt, level, close);
           }
        }
      else
        {
         //--- VR locked: first SAME-direction (continuation) break = CF
         if(dir == st[up1].pbo_dir && !st[up1].cf_done && bt > st[up1].vr_time)
           {
            st[up1].cf_done = true;
            made += FobAppendEvent(ev, up1, st[up1].seq, FOB_CF, etf, dir, swt, bt, level, close);
           }
        }
     }

   //--- ROLE 3: HRCF for the setup TF two above (n = etf+2, skip one) -
   int up2 = etf + 2;
   if(up2 < n_tf && st[up2].active && st[up2].vr_locked)
     {
      if(dir == st[up2].pbo_dir && !st[up2].hrcf_done && bt > st[up2].vr_time)
        {
         st[up2].hrcf_done = true;
         made += FobAppendEvent(ev, up2, st[up2].seq, FOB_HRCF, etf, dir, swt, bt, level, close);
        }
     }

   return made;
  }

#endif // FOB_SEQUENCE_MQH
