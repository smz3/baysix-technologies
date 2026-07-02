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
#define FOB_VERSION "1.30.0"   // 1.30.0: VR-BEFORE-PBO CAUSALITY FIX (task 221) — the VR lock gate compared bar OPEN times (bt > pbo_time), but a PBO is only a KNOWN fact at its bar CLOSE. A higher-TF PBO bar spans a long window, so a lower-TF opposite break that fired INSIDE the still-forming PBO bar was stamped VR before the PBO ever confirmed = look-ahead (VR predating its own cause). Fix: gate on CONFIRMATION time (bar_open + FobTfSeconds(TF)); the VR's break must CLOSE strictly after the PBO closed. Added FobTfSeconds(i) ladder helper. CF-vs-VR gate needs NO change (CF+VR share the same TF, so open-order == close-order); fixing VR cascades correct causality to CF. Contaminates ALL prior emit CSVs -> re-emit + re-test both modes (task 220) BEFORE trusting any VR-conditioned screen. 1.29.1: LIVE-chart RT backfill (task 219 follow-up) — a VR that invalidated BEFORE attach had its RT phase opened by the close-path replay but no ticks to stamp the mirror ladder, so it read [RT0] forever. Added FobBackfillRtTimes + CFobVisual::BackfillChartRt: the sibling of the T backfill for the return path (L2->mid->L1), fill-only + bar-resolution + LIVE-only (tester stays tick-causal, CSV byte-identical). T backfill left as-is: already bar-res truthful (a single bar that sweeps all 3 levels genuinely stamps them together — spreading that would invent data). 1.29.0: RT-LADDER REDEFINE (task 219, human dec call_id 93) — the single L2-only rt_count/rt_time is replaced by a MIRROR retouch ladder rt1/rt2/rt3_time (L2 -> mid -> L1), stamped OnTick/replay exactly like the T-ladder but on the RETURN path after invalidation (opposite side/sequence). A bull VR that broke DOWN through L2 stamps rt1 when price wicks back UP to L2, rt2 at mid, rt3 at L1 (the full return to the trigger); bear mirrors. Distinct-return COUNT + re-arm hysteresis dropped (FobZoneAcc.armed removed). CSV cols rt_count,rt_time -> rt1_time,rt2_time,rt3_time (fob_zones + ingest_fob loader migrated in lockstep); re-emit + re-test both modes. 1.28.0: MERGE — emitter + trader collapse into ONE EA (fob_baysix.mq5) with InpMode = EMIT | TRADE | STUDY. Root cause of the live touch-ladder disagreement was TWO EAs running TWO different lifecycle engines (emitter=causal tick accumulator, trader=stateless bar replay); now ONE causal accumulator (FobAcc*) is the single lifecycle engine for every mode, so oracle and strategy can never drift. EMIT ingests all 9 TFs + htf_state + CSV (byte-identical to the old standalone emitter); TRADE/STUDY ingest the setup pair only. fob_trader.mq5 RETIRED. RT-ladder redefinition (RT1/RT2/RT3 mirror ladder, human dec call_id 93) deferred to the next commit. Overrides the old two-EA-per-system rule (Syafiq 2026-07-02); 1.27.1: FIX task 217 — the v1.27.0 close-path backfill only stamped zones still in g_watch (cycle-end eviction drops superseded zones first) so historical [Tn] stayed T0. Replaced with a DRAW-TIME, chart-TF, FILL-ONLY ladder backfill (FobBackfillLadderTimes via CFobVisual::BackfillChartLadder) — the pre-v1.24.0 bar-wick replay, but non-destructive: fills only empty t1/t2/t3, never resets, never touches counts/rt/invalidation. LIVE-only, tester byte-identical; 1.27.0: live-chart fidelity — (216) intrabar-dead dimming: a higher-TF zone dims the instant price is beyond L2, not only at bar close (z.alive stays close-only for CSV); (217) touch-ladder backfill [superseded by 1.27.1]; 1.26.0: zone always draws — P3 = raw deepest pullback close (not a lagging fractal), P1 optional, freshness+gap-val REJECTS removed (were BRC trade filters, not geometry). Fixes messy/no-box VR bug (task 210). CHANGES L2 -> trader SL/1R -> re-emit + re-test both EAs; 1.25.0: emitter cycle-end eviction — new PBO retires prior cycle's VR/CF from g_watch (event-driven, NO bar cap) -> linear runtime + fixes zombie rt_count; 1.24.0: emitter lifecycle = TRUE-TICK accumulator (intra-bar order; replaces OnDeinit closed-bar replay), real-ticks only; 1.23.0: modularize trader + shared fob_engine.mqh

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
//---   P1 = nearest OPPOSITE-type fractal swing BEFORE P2 (origin) — OPTIONAL.
//---   P3 = deepest OPPOSITE-direction CLOSE in (P2, break) — the raw pullback
//---        extreme (v1.26.0; was the first fractal swing, which lagged a bar
//---        and vanished on sharp V-pullbacks -> "no box drawn", task 210).
//---   P4 = the break bar (bar_time/bar_close).
//---   L2 = extreme(P1,P3): MIN(lows) for a bull, MAX(highs) for a bear — the
//---        far / invalidation edge. Stop sits beyond L2 (the deeper of the two).
//--- valid = at least ONE of P1/P3 exists (v1.26.0). The old freshness + gap-val
//--- REJECTS were BRC TRADE-quality filters, NOT geometry -> REMOVED so a messy/
//--- pre-touched VR still draws its full box; gate trades on quality in the trader.
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
   //--- RT — RETOUCH MIRROR LADDER (v1.29.0, task 219, VR-only). After a VR is
   //--- INVALIDATED (close broke through L2), price RETURNS to the broken zone and
   //--- re-touches L2 -> mid -> L1 in MIRROR order of the T-ladder (same 3 levels,
   //--- opposite side/sequence): a bull VR broke DOWN through L2 so the return is a
   //--- move back UP (L2 nearest, L1 the full return to the trigger); bear mirrors.
   //--- rt1/rt2/rt3_time = first wick/tick touch of L2/mid/L1 (0 = not yet reached),
   //--- the break-and-retest entry ladder. Stamped only when the caller passes
   //--- track_rt (FOB_VR) into FobReplayZoneLife/FobAcc*. Replaced the old single
   //--- L2-only rt_count/rt_time (human ruling call_id 93).
   datetime  rt1_time;                     // first retouch of L2  (0 = none) — RT dot anchor
   datetime  rt2_time;                     // first retouch of mid
   datetime  rt3_time;                     // first retouch of L1  (full return to the trigger edge)
   //--- CAPTURE round-1 (v1.21.0, task 193) — also recomputed STATELESSLY inside
   //--- FobReplayZoneLife (same walk as the touch ladder), so the CSV emit and the
   //--- chart never disagree. Counts use rising-edge hysteresis (one episode per
   //--- distinct return to the level), NOT a per-bar tally.
   int       n_l1_touches;                 // distinct wick touches of L1  (pre-invalidation)
   int       n_mid_touches;                // distinct wick touches of mid
   int       n_l2_touches;                 // distinct wick touches of L2
   int       bars_alive;                   // event-TF bars from break to invalidation (or run end)
   bool      vr_fresh;                     // true = NO post-break bar CLOSED back inside [L1,L2]
                                           // (price left clean → "fresh", layer in). false =
                                           // a close re-entered the band → "structured" (ride trend).
   double    bar_open;                     // the BREAKING bar's OPEN — recorded raw (v1.21.0).
                                           // Rides on the zone because the zone payload travels
                                           // intact through the classifier (no extra plumbing).
                                           // Lets us flag a full-body impulse break (opened already
                                           // beyond L1) vs a closing break (opened inside, closed out).
  };

//--- one raw breakout (a close crossing an unbroken swing)
struct FobBreak
  {
   datetime  swing_time;   // broken swing pivot time
   double    swing_price;  // broken swing pivot price (the level taken)
   int       swing_type;   // FOB_SWING_TYPE of the broken swing
   int       dir;          // FOB_DIR of the break
   datetime  bar_time;     // breaking bar time
   double    bar_open;     // breaking bar open (for the full-body-clear flag)
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
   //--- per-TF awareness snapshot (v1.21.0, task 193) — the RAW live-cycle standing of
   //--- all 9 TFs AT this event's bar, stamped CAUSALLY right after FobClassifyBreak
   //--- (so it sees only data ≤ bar_time). JSON: {"M1":{"dir":"","cf":0},...}. The model's
   //--- awareness mapping (a TF reads from the cycle one below it) is applied in ANALYSIS,
   //--- never baked here — keeps it lossless if the rule sharpens (frozen decision #2).
   string    htf_state;
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
   // Set once on VR lock (fob_sequence). The EMITTER never reads it (CSV byte-identical).
   // NOTE: this is NOT the R unit. The live TRADER's risk unit is R = |entry - SL| where SL
   // sits beyond the zone FAR edge L2 by InpSlBufferK*band (fob_trader OpenCfTrade) — measured
   // to L2, NOT to vr_level. vr_level is kept as the VR origin reference only.
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

//--- TF index -> bar duration in SECONDS (the FOB ladder). Used to convert a
//--- break's bar_time (bar OPEN) into its CONFIRMATION time (open + duration):
//--- a break is only a KNOWN fact at its bar close, so cross-TF causality
//--- (VR must confirm AFTER its PBO confirms) is judged on confirm times, not
//--- opens (task 221 — a lower-TF opposite break inside a still-forming higher-
//--- TF PBO bar must NOT be stamped VR). W1/MN1 use nominal 7/30-day lengths;
//--- exactness there is immaterial (they sit at the top of the ladder).
long FobTfSeconds(const int i)
  {
   static long sc[FOB_N_TF] =
     {
      60,            // M1
      300,           // M5
      900,           // M15
      1800,          // M30
      3600,          // H1
      14400,         // H4
      86400,         // D1
      604800,        // W1  (7d nominal)
      2592000        // MN1 (30d nominal)
     };
   if(i < 0 || i >= FOB_N_TF)
      return 0;
   return sc[i];
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

//+------------------------------------------------------------------+
//| RAW per-TF awareness snapshot (frozen decision #2, task 193).      |
//| For each of the 9 TFs, its CURRENT live-cycle standing: dir = the  |
//| active PBO's direction (BUY/SELL, "" if no live cycle), cf = CFs   |
//| deep so far. Snapshot only (current standing), NOT sequence        |
//| history. The "X reads from cycle-on-(X-1)" mapping is an ANALYSIS  |
//| derivation layered on this raw form, never baked here.             |
//+------------------------------------------------------------------+
string FobBuildHtfState(const FobSetupState &st[])
  {
   string s = "{";
   for(int i = 0; i < FOB_N_TF; i++)
     {
      if(i > 0)
         s += ",";
      string dir = st[i].active ? ((st[i].pbo_dir == FOB_BEAR) ? "SELL" : "BUY") : "";
      int    cf  = st[i].active ? st[i].cf_count : 0;
      s += "\"" + FobTfName(i) + "\":{\"dir\":\"" + dir + "\",\"cf\":" + IntegerToString(cf) + "}";
     }
   s += "}";
   return s;
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
