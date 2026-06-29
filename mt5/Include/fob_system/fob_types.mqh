//+------------------------------------------------------------------+
//|                                                     fob_types.mqh  |
//|        FOB (First Opposite Breakout) — FOB's OWN types.           |
//|                                                                    |
//|  FOB-001 owns its full detection stack — swing pivots, raw break-  |
//|  outs, and its own data types — with NOTHING shared from           |
//|  brc_system. On top it adds the cross-timeframe classifier that    |
//|  walks every raw breakout in chronological order and labels each   |
//|  as PBO / VR / HRCF / CF.                                          |
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
//+------------------------------------------------------------------+
#ifndef FOB_TYPES_MQH
#define FOB_TYPES_MQH
#property strict

//--- single source of truth for the FOB code version (bump on behaviour change)
#define FOB_VERSION "1.20.0"

//--- the 9 TFs in the FOB ladder (index order MUST match g_periods in the emitter)
#define FOB_N_TF 9

//--- FOB OWNS its primitive types — NOTHING shared from brc_system.
enum FOB_DIR
  {
   FOB_BULL = 0,   // close broke ABOVE a swing high
   FOB_BEAR = 1    // close broke BELOW a swing low
  };

enum FOB_SWING_TYPE
  {
   FOB_SWING_HIGH = 0,
   FOB_SWING_LOW  = 1
  };

//--- one confirmed close-based swing pivot
struct FobSwing
  {
   datetime  time;       // pivot bar time
   double    price;      // pivot bar CLOSE (close-based detection)
   int       type;       // FOB_SWING_TYPE
   int       bar_index;  // absolute series index of the pivot
   bool      broken;     // has a later close crossed it?
  };

//--- 4-POINTER ZONE (v1.14.0) — a B2B-style structural band around ANY break,
//--- adapted from BRC's 5-pointer (P5 dropped: the break IS the confirmation).
//--- Geometry (bull break = broke a HIGH; bear = mirror):
//---   P2 = the broken swing (= L1, the trigger/entry edge) — lives on the
//---        owning FobBreak/FobEvent as swing_time/level (NOT duplicated here).
//---   P1 = nearest OPPOSITE-type swing BEFORE  P2 (origin / launch pivot).
//---   P3 = first   OPPOSITE-type swing AFTER   P2, before the break (pullback).
//---   P4 = the break bar (bar_time/bar_close).
//---   L2 = extreme(P1,P3): MIN(lows) for a bull, MAX(highs) for a bear — the
//---        far / invalidation edge. Stop sits beyond L2 (the deeper of the two).
//--- valid = P1+P3 both found AND BRC freshness (no swing strictly in (P3,P4))
//--- AND gap-val (L2 not closed-through in (P3,P4]) pass. valid=false -> NO trade
//--- (foolproof, no fallback — Syafiq 2026-06-26).
struct FobZone
  {
   datetime  p1_time;   double p1_price;   // origin pivot (before the broken swing)
   datetime  p3_time;   double p3_price;   // pullback pivot (after it, before break)
   double    l2;                           // extreme(P1,P3) — far/invalidation edge
   bool      valid;                        // P1+P3 found AND freshness+gap-val pass
   //--- LIFECYCLE (v1.14.1, task 178) — BRC-parity retest ladder + invalidation,
   //--- recomputed STATELESSLY at draw time by FobReplayZoneLife (fob_lifecycle.mqh)
   //--- walking the event-TF bars after the break. L1 (= owning event's `level`)
   //--- and L2 frame the band; mid = (L1+L2)/2. T1=L1, T2=mid, T3=L2 first-touch
   //--- (wick); invalidation = first CLOSE beyond L2 in the anti-break direction.
   double    mid;                          // (L1+L2)/2 — 50% line + T2 retest level
   datetime  t1_time;                      // first wick touch of L1 (0 = untouched)
   datetime  t2_time;                      // first wick touch of mid
   datetime  t3_time;                      // first wick touch of L2
   bool      alive;                        // false once a close breaks beyond L2
   datetime  invalidation_time;            // bar that killed the zone (0 if alive)
   //--- RT — RETOUCH (v1.18.0, VR-only). After a VR is INVALIDATED (close broke
   //--- through L2), price returning to that broken L2 edge = a retouch = the
   //--- break-and-retest entry trigger. rt_count = number of distinct returns to
   //--- L2 (0 = none yet), rt_time = first one (the dot). Stamped only when the
   //--- caller passes track_rt (FOB_VR) into FobReplayZoneLife.
   int       rt_count;                     // distinct L2 retouches after invalidation
   datetime  rt_time;                      // first retouch bar (0 = none) — RT dot anchor
  };

//--- one raw breakout (a close crossing an unbroken swing)
struct FobBreak
  {
   datetime  swing_time;   // broken swing pivot time
   double    swing_price;  // broken swing pivot price (the level taken)
   int       swing_type;   // FOB_SWING_TYPE of the broken swing
   int       dir;          // FOB_DIR of the break
   datetime  bar_time;     // breaking bar time
   double    bar_close;    // breaking bar close (beyond the level)
   int       bar_index;    // absolute series index of the breaking bar
   FobZone   zone;         // 4-pointer structural band (computed at detection)
  };

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
   int       cf_idx;     // CF ordinal WITHIN this cycle (1=1st CF, 2=2nd CF, ...; 0 for PBO/VR)
   int       label;      // FOB_LABEL
   int       event_tf;   // TF index where THIS break actually fired
   int       dir;        // FOB_BULL | FOB_BEAR of this break
   datetime  swing_time; // broken swing TIME — the dot's x (drawn AT the swingpoint, like BRC)
   datetime  bar_time;   // break bar time (the close that crossed the level; chain ordering)
   double    level;      // broken swing price — the dot's y (the level that was taken) = L1
   double    bar_close;  // break bar close (beyond the level)
   FobZone   zone;       // 4-pointer band (P1/P3/L2 + valid) — same break geometry, every role
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
   datetime  pbo_time;   // bar_time of the active PBO (when the break FIRED)
   datetime  pbo_swing;  // swing_time of the active PBO's broken structure (CMP-freshness watermark).
   // CMP rule (task PBO-newest): the PBO marks the SOURCE of the current leg nearest CMP.
   // A reversal (opp dir / no live PBO) is always a fresh source. A SAME-direction break only
   // supersedes if it breaks a NEWER swing (swt > pbo_swing); a same-dir reach-back to OLDER
   // structure (e.g. a Jun-2026 break taking a Nov-2025 low) is stale context, NOT a new PBO.
   bool      vr_locked;  // has the (one-and-only) VR been found?
   datetime  vr_time;    // bar_time of the locked VR
   datetime  vr_swing;   // swing_time of the locked VR's broken structure (NEWEST-swing watermark).
   // SAME-BAR VR pick (mirror of PBO freshness): a single bar can break SEVERAL opposite swings at
   // once. The first one fed is the OLDEST (furthest) swing; the structurally-correct VR is the
   // NEWEST (nearest the turn). On the VR's own bar, a fresher opposite break (swt > vr_swing)
   // REPLACES the VR in place — same dot, no second event (fob_sequence). Cross-bar opposite breaks
   // are NOT the VR (the first bar to retrace owns the VR timing); only same-bar (bt == vr_time) ties.
   int       vr_ev_idx;  // index of the emitted VR event in ev[] (-1 if none) — lets the same-bar
   // upgrade rewrite that one row instead of emitting a duplicate VR. Stable: events never removed.
   double    vr_level;   // broken-swing PRICE of the locked VR (the retracement structure).
   // Set once on VR lock (fob_sequence). The EMITTER never reads it (CSV byte-identical);
   // the TRADER uses it as the structural 1R reference: R = |CF entry - vr_level| (stop back
   // through the VR origin = continuation invalidated). FOB-T1 risk unit.
   int       cf_count;   // CFs emitted SO FAR in the active cycle (1st-CF entry vs Nth-CF layering)
   datetime  last_conf_swing; // swing_time WATERMARK for the confirming chain (task 159).
   // NOTE: no cf_done — a cycle allows MULTIPLE CFs (2nd-CF layering, task 156).
   // Every same-dir continuation after the VR is a fresh CF until superseded.
   // cf_count is the ordinal counter: reset to 0 on each new PBO, +1 per CF emit.
   // last_conf_swing (task 159): a CF must break a swing NEWER than the VR (for
   // CF1) then newer than the prior CF (CF2+). Seeded = VR swing_time on VR lock;
   // each accepted CF requires swt > last_conf_swing then advances it. Blocks a
   // same-dir break that reaches BACK to a pre-VR / already-taken old structure
   // from counting as a confirmation (the 05:45 reach-back bug).
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
      case FOB_BULL: return "BUY";
      case FOB_BEAR: return "SELL";
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
