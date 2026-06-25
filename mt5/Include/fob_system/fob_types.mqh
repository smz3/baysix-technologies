//+------------------------------------------------------------------+
//|                                                     fob_types.mqh  |
//|        FOB (First Opposite Breakout) — shared types.              |
//|                                                                    |
//|  FOB-001 = sibling of BRC-001 under STRUCT-001. It REUSES the      |
//|  STRUCT primitives (swing pivots + raw breakouts) from brc_system  |
//|  and adds ONE new thing: a cross-timeframe classifier that walks   |
//|  every raw breakout in chronological order and labels each as      |
//|  PBO / VR / HRCF / CF.                                             |
//|                                                                    |
//|  SOP : CMP -> BO(PBO) -> VR -> CF -> CONTI.                        |
//|  Ladder (this file's TF order, index 0..8):                       |
//|      M1 · M5 · M15 · M30 · H1 · H4 · D1 · W1 · MN1                 |
//|  For a setup TF n:  VR/CF = TF n-1 (adjacent below),              |
//|                     HRCF  = TF n-2 (skip one below).              |
//|                                                                    |
//|  Roles (per raw break on event-TF `etf`, direction `d`):          |
//|    • PBO  for setup-TF etf      (always — supersede rule)          |
//|    • VR   for setup-TF etf+1    if its PBO active, no VR yet,      |
//|                                 d == OPPOSITE of that PBO          |
//|    • CF   for setup-TF etf+1    if VR locked, d == SAME, no CF yet |
//|    • HRCF for setup-TF etf+2    if VR locked, d == SAME, no HRCF   |
//|                                                                    |
//|  Tech-debt: brc_swings/brc_breakouts/brc_types are really STRUCT   |
//|  primitives; promote to a shared `struct_system` namespace later.  |
//+------------------------------------------------------------------+
#ifndef FOB_TYPES_MQH
#define FOB_TYPES_MQH
#property strict

#include <brc_system/brc_types.mqh>   // BrcSwing, BrcBreak, BRC_DIR (BRC_BULL/BRC_BEAR)

//--- single source of truth for the FOB code version (bump on behaviour change)
#define FOB_VERSION "0.8.0"

//--- the 9 TFs in the FOB ladder (index order MUST match g_periods in the emitter)
#define FOB_N_TF 9

//--- the four cross-TF roles a raw breakout can play
enum FOB_LABEL
  {
   FOB_PBO  = 0,   // Primary BreakOut  (the CMP breakout, the setup anchor)
   FOB_VR   = 1,   // Valid Retracement (first OPPOSITE break, one TF below)
   FOB_HRCF = 2,   // High-Risk Confirmation (continuation, TF n-2) — PARKED 2026-06-25, classifier no longer emits it
   FOB_CF   = 3    // Confirmation       (continuation, TF n-1 = adjacent below)
  };

//+------------------------------------------------------------------+
//| One classified breakout (the FOB ledger row + draw payload).      |
//| A single raw break can produce up to 3 of these (PBO for its own  |
//| TF, VR-or-CF for the TF above, HRCF for two TFs above).           |
//+------------------------------------------------------------------+
struct FobEvent
  {
   int       setup_tf;   // TF index of the governing PBO (the "setup" TF)
   int       seq;        // per-setup_tf PBO sequence id (1-based, increments per new PBO)
   int       label;      // FOB_LABEL
   int       event_tf;   // TF index where THIS break actually fired
   int       dir;        // BRC_BULL | BRC_BEAR of this break
   datetime  swing_time; // broken swing TIME — the dot's x (drawn AT the swingpoint, like BRC)
   datetime  bar_time;   // break bar time (the close that crossed the level; chain ordering)
   double    level;      // broken swing price — the dot's y (the level that was taken)
   double    bar_close;  // break bar close (beyond the level)
  };

//+------------------------------------------------------------------+
//| Live state for one setup TF (its currently-active PBO + progress).|
//| Reset whenever a fresh break on that same TF supersedes the PBO.  |
//+------------------------------------------------------------------+
struct FobSetupState
  {
   bool      active;     // is there a live PBO on this setup TF?
   int       seq;        // running PBO counter for this setup TF
   int       pbo_dir;    // direction of the active PBO
   datetime  pbo_time;   // bar_time of the active PBO
   bool      vr_locked;  // has the (one-and-only) VR been found?
   datetime  vr_time;    // bar_time of the locked VR
   // NOTE: no cf_done — a cycle allows MULTIPLE CFs (2nd-CF layering, task 156).
   // Every same-dir continuation after the VR is a fresh CF until superseded.
  };

//--- TF index -> name (the FOB ladder; hardcoded to FOB_N_TF=8)
string FobTfName(const int i)
  {
   static string nm[FOB_N_TF] = { "M1","M5","M15","M30","H1","H4","D1","W1","MN1" };
   if(i < 0 || i >= FOB_N_TF)
      return "?";
   return nm[i];
  }

string FobLabelName(const int label)
  {
   switch(label)
     {
      case FOB_PBO:  return "PBO";
      case FOB_VR:   return "VR";
      case FOB_HRCF: return "HRCF";
      case FOB_CF:   return "CF";
     }
   return "?";
  }

//--- thesis direction word (the PBO's direction, stamped on every role of a chain)
string FobDirName(const int dir)
  {
   switch(dir)
     {
      case BRC_BULL: return "BUY";
      case BRC_BEAR: return "SELL";
     }
   return "?";
  }

//--- confirmed colour scheme (locked 2026-06-25 with Syafiq)
color FobLabelColor(const int label)
  {
   switch(label)
     {
      case FOB_PBO:  return clrDodgerBlue;    // blue  — the anchor
      case FOB_VR:   return clrYellow;        // yellow (VR highlight, set 2026-06-25)
      case FOB_HRCF: return clrOrange;        // orange — high-risk caution
      case FOB_CF:   return clrLimeGreen;     // green  — go
     }
   return clrGray;
  }

#endif // FOB_TYPES_MQH
