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
//|  Ladder (this file's TF order, index 0..7):                       |
//|      M5 · M15 · M30 · H1 · H4 · D1 · W1 · MN1                      |
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
#define FOB_VERSION "0.1.0"

//--- the 8 TFs in the FOB ladder (index order MUST match g_periods in the emitter)
#define FOB_N_TF 8

//--- the four cross-TF roles a raw breakout can play
enum FOB_LABEL
  {
   FOB_PBO  = 0,   // Primary BreakOut  (the CMP breakout, the setup anchor)
   FOB_VR   = 1,   // Valid Retracement (first OPPOSITE break, one TF below)
   FOB_HRCF = 2,   // High-Risk Confirmation (continuation, TF n-2 = skip one)
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
   datetime  bar_time;   // break bar time (the close that crossed the level)
   double    level;      // broken swing price (the level that was taken)
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
   bool      cf_done;    // first CF already labeled?
   bool      hrcf_done;  // first HRCF already labeled?
  };

//--- TF index -> name (the FOB ladder; hardcoded to FOB_N_TF=8)
string FobTfName(const int i)
  {
   static string nm[FOB_N_TF] = { "M5","M15","M30","H1","H4","D1","W1","MN1" };
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

//--- confirmed colour scheme (locked 2026-06-25 with Syafiq)
color FobLabelColor(const int label)
  {
   switch(label)
     {
      case FOB_PBO:  return clrDodgerBlue;    // blue  — the anchor
      case FOB_VR:   return clrMediumPurple;  // purple — matches manual's purple zones
      case FOB_HRCF: return clrOrange;        // orange — high-risk caution
      case FOB_CF:   return clrLimeGreen;     // green  — go
     }
   return clrGray;
  }

#endif // FOB_TYPES_MQH
