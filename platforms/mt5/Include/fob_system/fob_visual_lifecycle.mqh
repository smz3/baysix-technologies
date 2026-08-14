//+------------------------------------------------------------------+
//|                                         fob_visual_lifecycle.mqh  |
//|  PART of fob_visual.mqh — out-of-line CFobVisual method bodies.    |
//|  DO NOT #include directly: no include guard by design; it is       |
//|  pulled in by fob_visual.mqh AFTER the class declaration.          |
//|                                                                    |
//|  Scope: DATA-ONLY passes (no drawing) — reconstruct per-setup-TF    |
//|  cycle state + stamp the touch/RT ladders + alive/invalidation      |
//|  onto the chart-TF zones. All the "figure out state" work that      |
//|  DrawZones consumes.                                               |
//+------------------------------------------------------------------+

//+------------------------------------------------------------------+
//| PASS 1 — reconstruct each setup TF's ACTIVE (latest) seq, whether  |
//| its VR is locked, and how many CFs it has developed. A PBO resets   |
//| the cycle; VR/CF only advance the cycle they belong to.            |
//+------------------------------------------------------------------+
void CFobVisual::ReconstructState(const FobEvent &ev[], const int n,
                                  int &curSeq[], bool &vrLocked[], int &cfCount[]) const
  {
   for(int i = 0; i < FOB_N_TF; i++) { curSeq[i] = -1; vrLocked[i] = false; cfCount[i] = 0; }
   for(int i = 0; i < n; i++)
     {
      int s  = ev[i].setup_tf;
      int sq = ev[i].seq;
      if(ev[i].label == FOB_PBO)
        { curSeq[s] = sq; vrLocked[s] = false; cfCount[s] = 0; }
      else if(sq == curSeq[s])
        {
         if(ev[i].label == FOB_VR)                                   vrLocked[s] = true;
         else if(ev[i].label == FOB_CF && ev[i].cf_idx > cfCount[s]) cfCount[s] = ev[i].cf_idx;
        }
     }
  }

//+------------------------------------------------------------------+
//| Stamp the retest ladder + alive/invalidation onto every event      |
//| whose break fired on THIS chart TF (data only, no drawing).        |
//+------------------------------------------------------------------+
void CFobVisual::UpdateZoneLifecycles(FobEvent &ev[], const int n,
                                      const datetime &bt[], const double &bh[],
                                      const double &bl[], const double &bc[], const int nb)
  {
   if(m_idx < 0)
      return;
   int E = m_idx;
   for(int i = 0; i < n; i++)
      if(ev[i].event_tf == E)
         FobReplayZoneLife(ev[i].zone, ev[i].dir, ev[i].level, ev[i].bar_time, bt, bh, bl, bc, nb,
                           ev[i].label == FOB_VR);   // track RT (broken-L2 retouch) on VRs only
  }

//--- (v1.31.0, task 223) BackfillChartLadder / BackfillChartRt DELETED — the pre-attach
//--- touch + RT ladders are now filled by a real historical-tick warm-up in the EA
//--- (FobWarmupReplay -> FobWarmFillTick), not by bar-wick guessing. Bars can't recover
//--- intrabar touch TIME (right day/week, wrong minute on low TFs); replaying the ticks
//--- through the same stamping the accumulator uses makes live == tester, tick-exact.

//+------------------------------------------------------------------+
//| LIVE intrabar touch pass — stamp T1/T2/T3 off the chart-TF FORMING |
//| bar (mirror of BRC's OnTick forming-bar pass). Runs AFTER the      |
//| closed-bar UpdateZoneLifecycles (which resets the ladder), so it    |
//| only fills a still-empty Tn from the live wick. Touch-only.        |
//+------------------------------------------------------------------+
void CFobVisual::LiveTouchForming(FobEvent &ev[], const int n,
                                  const datetime fbt, const double fbh, const double fbl)
  {
   if(m_idx < 0)
      return;
   int E = m_idx;
   for(int i = 0; i < n; i++)
      if(ev[i].event_tf == E)
         FobLiveTouch(ev[i].zone, ev[i].dir, ev[i].level, ev[i].bar_time, fbt, fbh, fbl,
                      ev[i].label == FOB_VR);       // live RT on VRs only (parity with closed-bar)
  }
