//+------------------------------------------------------------------+
//|                                                   Structures.mqh |
//|                        Copyright 2025, SIGMA Systems             |
//|                                         https://www.asksigma.com |
//+------------------------------------------------------------------+
//| V5.0 CLEAN SLATE - B2B ONLY                                      |
//| Contains only: RawBreakoutInfo, SwingPointInfo, TimeFrameDataCache, B2BZoneInfo |
//| Removed: SequenceInfo, CFob, CCf, PBOFullInfo, SequenceBarrier, etc. |
//+------------------------------------------------------------------+
#property strict

#ifndef V50_STRUCTURES_MQH
#define V50_STRUCTURES_MQH

#include "../Common/Defines.mqh"

//+------------------------------------------------------------------+
//| RawBreakoutInfo Structure                                        |
//| Container for detected raw breakout data                         |
//+------------------------------------------------------------------+
struct RawBreakoutInfo
  {
   datetime          breakout_bar_time;        // Time of the bar that broke the swing(s)
   double            breakout_bar_close_price; // Close price of the breakout bar
   ENUM_SIGNAL_DIRECTION direction;            // BULLISH or BEARISH
   ENUM_TIMEFRAMES   timeframe_occurred;       // Timeframe the breakout happened on
   ENUM_TIMEFRAMES   broken_swing_original_tf; // The original TF of the defining swing
   double            broken_swing_price;       // Price of the defining swing that was broken
   datetime          broken_swing_time;        // Time of the defining swing that was broken
   double            broken_swing_close_price; // Close price of the defining swing bar
   ENUM_SWING_TYPE   broken_swing_type;        // Type of the defining swing (HIGH or LOW)
   double            impulse_start_price;      // The price of the swing that started the impulse wave
   int               breakout_age_in_bars;     // Age of the broken swing in bars
   int               breakout_bar_idx;         // The index of the breakout bar on its own timeframe

   //--- Constructor
   RawBreakoutInfo(void) { Reset(); }

   //--- Copy Constructor
   RawBreakoutInfo(const RawBreakoutInfo &other)
     {
      breakout_bar_time = other.breakout_bar_time;
      breakout_bar_close_price = other.breakout_bar_close_price;
      direction = other.direction;
      timeframe_occurred = other.timeframe_occurred;
      broken_swing_original_tf = other.broken_swing_original_tf;
      broken_swing_price = other.broken_swing_price;
      broken_swing_time = other.broken_swing_time;
      broken_swing_close_price = other.broken_swing_close_price;
      broken_swing_type = other.broken_swing_type;
      impulse_start_price = other.impulse_start_price;
      breakout_age_in_bars = other.breakout_age_in_bars;
      breakout_bar_idx = other.breakout_bar_idx;
     }

   //--- Reset
   void Reset(void)
     {
      breakout_bar_time = 0;
      breakout_bar_close_price = 0.0;
      direction = DIRECTION_NONE;
      timeframe_occurred = PERIOD_CURRENT;
      broken_swing_original_tf = PERIOD_CURRENT;
      broken_swing_price = 0.0;
      broken_swing_time = 0;
      broken_swing_close_price = 0.0;
      broken_swing_type = SWING_NONE;
      impulse_start_price = 0.0;
      breakout_age_in_bars = 0;
      breakout_bar_idx = 0;
     }

   //--- Validation
   bool IsValid() const { return direction != DIRECTION_NONE && broken_swing_time > 0; }
  };

//+------------------------------------------------------------------+
//| SwingPointInfo Structure                                         |
//| Container for detected swing point data                          |
//+------------------------------------------------------------------+
struct SwingPointInfo
  {
   double            price;              // The high/low price of the swing point
   datetime          time;               // The time of the swing bar
   double            close_price;        // The close price of the swing bar
   bool              has_been_broken;    // Flag: has this swing been broken out from?
   ENUM_SWING_TYPE   type;               // Type of swing (SWING_HIGH, SWING_LOW, SWING_NONE)
   ENUM_TIMEFRAMES   original_tf;        // The timeframe this swing was detected on
   double            swing_imprint_top;  // The highest price of the swing's imprint
   double            swing_imprint_bottom; // The lowest price of the swing's imprint
   
   // Performance optimization fields
   datetime          last_check_time;    // When this swing was last checked for breakouts
   bool              is_cached;          // Flag indicating if this swing is in the cache
   int               cache_index;        // Index in the performance cache (-1 if not cached)
   bool              needs_update;       // Flag for batch processing

   //--- Constructor
   SwingPointInfo(double p=0.0, datetime t=0, double cp=0.0, ENUM_SWING_TYPE st=SWING_NONE, ENUM_TIMEFRAMES otf=PERIOD_CURRENT)
     {
      price = p;
      time = t;
      close_price = cp;
      has_been_broken = false;
      type = st;
      original_tf = otf;
      swing_imprint_top = 0.0;
      swing_imprint_bottom = 0.0;
      last_check_time = 0;
      is_cached = false;
      cache_index = -1;
      needs_update = false;
     }

   //--- Copy Constructor
   SwingPointInfo(const SwingPointInfo &other)
     {
      price = other.price;
      time = other.time;
      close_price = other.close_price;
      has_been_broken = other.has_been_broken;
      type = other.type;
      original_tf = other.original_tf;
      swing_imprint_top = other.swing_imprint_top;
      swing_imprint_bottom = other.swing_imprint_bottom;
      last_check_time = other.last_check_time;
      is_cached = other.is_cached;
      cache_index = other.cache_index;
      needs_update = other.needs_update;
     }

   //--- Validation
   bool IsValid() const { return time > 0; }
  };

//+------------------------------------------------------------------+
//| TimeFrameDataCache Structure                                     |
//| Holds cached MqlRates and metadata for a single timeframe        |
//+------------------------------------------------------------------+
struct TimeFrameDataCache
  {
   MqlRates          rates[];              // The actual MqlRates data, sorted oldest to newest
   datetime          last_loaded_bar_time; // Timestamp of the newest bar in the cache
   int               loaded_bars_count;    // Number of bars currently in rates[]
   ENUM_TIMEFRAMES   timeframe;            // The timeframe this cache is for

   //--- Default Constructor
   TimeFrameDataCache()
     {
      ArrayFree(rates);
      last_loaded_bar_time = 0;
      loaded_bars_count = 0;
      timeframe = PERIOD_CURRENT;
     }
   
   //--- Copy Constructor
   TimeFrameDataCache(const TimeFrameDataCache &other)
     {
      last_loaded_bar_time = other.last_loaded_bar_time;
      loaded_bars_count = other.loaded_bars_count;
      timeframe = other.timeframe;
      
      ArrayFree(rates);
      int size = ArraySize(other.rates);
      ArrayResize(rates, size);
      for(int i = 0; i < size; i++)
        {
         rates[i] = other.rates[i];
        }
     }

   //--- Initialize
   void Initialize(ENUM_TIMEFRAMES tf)
     {
      timeframe = tf;
      ArrayFree(rates);
      last_loaded_bar_time = 0;
      loaded_bars_count = 0;
     }
   
   //--- Validation
   bool IsPopulated() const { return loaded_bars_count > 0 && ArraySize(rates) > 0; }
  };

//+------------------------------------------------------------------+
//| B2BZoneInfo Structure                                            |
//| Break of Two Barriers zone - the core trading signal             |
//| BUY B2B: High → Higher High (HH)                                 |
//| SELL B2B: Lower High (LH) → Lower Low (LL)                       |
//+------------------------------------------------------------------+
struct B2BZoneInfo
  {
   //=== Identification ===
   ulong               zone_id;              // Unique zone identifier (hash for backend matching)
   int                 display_number;       // V5.1.2: Sequential number for UI display (#1, #2, #3...)
   ENUM_TIMEFRAMES     timeframe;            // Zone's timeframe
   ENUM_SIGNAL_DIRECTION direction;          // DIRECTION_BULLISH (BUY) or DIRECTION_BEARISH (SELL)
   
   //=== Zone Boundaries ===
   double              L1_price;             // First touch level (entry side)
   double              L2_price;             // Deep touch level (invalidation side)
   double              fifty_percent;        // Midpoint = (L1 + L2) / 2
   
   //=== Pattern Components ===
   // For BUY B2B:  first_barrier = First High, second_barrier = HH, swing_between = Swing Low
   // For SELL B2B: first_barrier = First Low, second_barrier = LL, swing_between = Swing High
   double              first_barrier_price;  
   datetime            first_barrier_time;
   double              second_barrier_price; 
   datetime            second_barrier_time;
   double              swing_between_price;  
   datetime            swing_between_time;
   
   //=== Touch Tracking (T0/T1/T2/T3 depth-based) ===
   bool                L1_touched;           // T1: Has price wicked through L1?
   bool                fifty_touched;        // T2: Has price wicked through 50%?
   bool                L2_touched;           // T3: Has price wicked through L2?
   
   //=== Trade Signal Tracking (to prevent duplicate signals) ===
   bool                L1_traded;            // Trade signal generated at L1?
   bool                fifty_traded;         // Trade signal generated at 50%?
   bool                L2_traded;            // Trade signal generated at L2?
   
   //=== Status ===
   bool                is_valid;             // Zone still active?
   bool                is_invalidated;       // L1→50%→L2 sequence complete?
   datetime            zone_created_time;    // When B2B pattern completed
   datetime            invalidation_time;    // When zone was invalidated (0 if still valid)
   
   //=== Visualization Object Names ===
   string              rect_name;            // Chart object name for rectangle
   string              L1_line_name;         // Chart object name for L1 line
   string              L2_line_name;         // Chart object name for L2 line
   string              fifty_line_name;      // Chart object name for 50% line
   string              label_name;           // Chart object name for zone label
   
   //=== Confluence / Parent-Child Hierarchy ===
   bool                has_narrative_parent;  // True if overlaps with Narrative zone (MN1, W1, D1)
   bool                has_control_parent;    // True if overlaps with Control zone (H4, H1, M30, M15)
   ulong               parent_zone_id;        // ID of best-matching parent zone (0 if orphan)
   bool                is_inside_parent;      // True if L1 AND L2 both within parent L1-L2 range
   ENUM_TIMEFRAMES     parent_tf;             // TF of the parent zone
   double              parent_L1_price;       // Parent zone L1 price (for TP calculation)
   double              parent_L2_price;       // Parent zone L2 price (for TP calculation)
   
   //=== V5.0.1: Multi-Parent Tracking (Russian Doll) ===
   int                 parent_count;          // How many overlapping parent zones
   ulong               parent_zone_ids[9];    // All parent zone IDs (one per TF rank 0-8)
   bool                any_parent_touched;    // Quick check: at least one parent touched?
   datetime            earliest_parent_touch; // When first parent was touched
   int                 tf_rank;               // 0=MN1, 1=W1, 2=D1, 3=H4, 4=H1, 5=M30, 6=M15, 7=M5, 8=M1
   bool                can_trade;             // Passes Russian Doll rules?
   bool                is_pioneer;            // V5.0.1: Zone at ATH/ATL, can trade without parent
   
   //=== V5.3: Fractal Domino - M15 Opener Tracking (for M5 zones) ===
   ulong               m15_parent_id;         // M15 zone that contains this M5 (0 if none)
   datetime            m15_touch_time;        // When M15 parent was touched (L1 or deeper)
   bool                m15_has_h4_parent;     // M15's H4 permission (copied from M15)
   bool                m15_has_h1_parent;     // M15's H1 permission (copied from M15)
   
   //=== Parent Zone Touch Status (for parent zones only) ===
   bool                is_parent_touched;     // TRUE if this parent zone has been touched
   datetime            parent_touched_time;   // When price first touched this parent zone
   int                 parent_touch_depth;    // 1=L1, 2=50%, 3=L2 (deepest touch level)
   
   //=== V5.6: HTF Touch Tracking (H1/H4 Permission Source) ===
   ulong               h1_parent_id;          // H1 zone that overlaps this zone (0 if none)
   datetime            h1_touch_time;         // When H1 parent was touched
   int                 h1_touch_depth;        // 1=L1, 2=50%, 3=L2 (deepest touch level)
   ulong               h4_parent_id;          // H4 zone that overlaps this zone (0 if none)
   datetime            h4_touch_time;         // When H4 parent was touched
   int                 h4_touch_depth;        // 1=L1, 2=50%, 3=L2 (deepest touch level)
   
   //=== ENHANCED: Zone Lifecycle Tracking ===
   int                 created_bar_index;     // Bar index when zone was created
   int                 zone_age_bars;         // Bars since zone creation (updated each tick)
   datetime            L1_touch_time;         // When L1 was first touched
   datetime            fifty_touch_time;      // When 50% was first touched
   datetime            L2_touch_time;         // When L2 was first touched
   int                 L1_touch_bar;          // Bar index when L1 touched
   int                 fifty_touch_bar;       // Bar index when 50% touched
   int                 L2_touch_bar;          // Bar index when L2 touched
   int                 touch_count;           // How many times zone has been entered (retests)
   
   //=== ENHANCED: Market Context at Creation ===
   ENUM_SIGNAL_DIRECTION narrative_direction; // D1/W1/MN1 overall bias when zone created
   double              atr_at_creation;       // ATR value at zone creation (volatility context)
   string              session_created;       // "ASIAN", "LONDON", "NEWYORK", "OFF"
   int                 conflicting_zones;     // Count of opposite direction zones active
   
   //=== GOD DATA (AI Features) ===
   int                 fractal_depth_score;   // Russian Doll Score (0-10)
   double              tf_dominance_score;    // HTF Tailwind Score (-5.0 to +5.0)
   int                 cluster_density;       // Nearby zones count
   double              elasticity_velocity;   // Return speed (Pips/Bar)
   
   //=== V6: ANCHOR LOGIC TRACKING ===
   ulong               anchor_zone_id;        // ID of the anchor zone (H4/H1/M30/M15) this zone targets
   ENUM_TIMEFRAMES     anchor_tf;             // Timeframe of the anchor zone
   bool                is_at_key_level;       // True if M15 is at anchor L2 level
   ENUM_TIMEFRAMES     execution_tf;          // Which TF was used for entry (M1 or M5)
   double              anchor_tp1_price;      // TP1: Anchor 50% level
   double              anchor_tp2_price;      // TP2: Anchor L2 level
   double              distance_to_anchor;    // Distance in points from entry to anchor L2
   
   //=== ENHANCED: Trade Outcome Tracking ===
   bool                was_traded;            // True if a trade was opened on this zone
   string              entry_level_used;      // "L1", "FIFTY", "L2"
   double              entry_price;           // Actual entry price
   double              sl_price;              // Stop loss price
   double              tp_price;              // Take profit price
   double              exit_price;            // Actual exit price
   string              exit_reason;           // "TP", "SL", "INVALIDATED", "MANUAL"
   datetime            trade_open_time;       // When trade was opened
   datetime            trade_close_time;      // When trade was closed
   int                 trade_duration_bars;   // Bars from open to close
   double              max_adverse_excursion; // Max drawdown during trade (points)
   double              max_favorable_excursion; // Max profit during trade (points)
   double              rr_planned;            // Planned R:R ratio
   double              rr_achieved;           // Actual R:R ratio
   double              pnl_points;            // Profit/loss in points
   double              pnl_money;             // Profit/loss in money
   
   //=== V10.4: Phase 1 Physics (Time-to-Event) ===
   datetime            mfe_time;              // When Max Favorable Excursion occurred
   datetime            mae_time;              // When Max Adverse Excursion occurred

   //=== PHASE DELTA 3: NARRATIVE SENSORS ($H11 & $H9) ===
   bool                is_narrative_conflicted; // Signals if M15 Sell is inside D1/W1 Buy
   bool                is_bulldozer_active;    // Signals if HTF is in vertical expansion (Vacuum)
   double              narrative_vacuum;       // Distance to next HTF anchor
   
   //=== Constructor ===
   B2BZoneInfo()
     {
      Reset();
     }
   
   //=== Copy Constructor ===
   B2BZoneInfo(const B2BZoneInfo &other)
     {
      zone_id = other.zone_id;
      display_number = other.display_number;
      timeframe = other.timeframe;
      direction = other.direction;
      L1_price = other.L1_price;
      L2_price = other.L2_price;
      fifty_percent = other.fifty_percent;
      first_barrier_price = other.first_barrier_price;
      first_barrier_time = other.first_barrier_time;
      second_barrier_price = other.second_barrier_price;
      second_barrier_time = other.second_barrier_time;
      swing_between_price = other.swing_between_price;
      swing_between_time = other.swing_between_time;
      L1_touched = other.L1_touched;
      fifty_touched = other.fifty_touched;
      L2_touched = other.L2_touched;
      L1_traded = other.L1_traded;
      fifty_traded = other.fifty_traded;
      L2_traded = other.L2_traded;
      is_valid = other.is_valid;
      is_invalidated = other.is_invalidated;
      zone_created_time = other.zone_created_time;
      invalidation_time = other.invalidation_time;
      rect_name = other.rect_name;
      L1_line_name = other.L1_line_name;
      L2_line_name = other.L2_line_name;
      fifty_line_name = other.fifty_line_name;
      label_name = other.label_name;
      has_narrative_parent = other.has_narrative_parent;
      has_control_parent = other.has_control_parent;
      parent_zone_id = other.parent_zone_id;
      is_inside_parent = other.is_inside_parent;
      parent_tf = other.parent_tf;
      parent_L1_price = other.parent_L1_price;
      parent_L2_price = other.parent_L2_price;
      is_parent_touched = other.is_parent_touched;
      parent_touched_time = other.parent_touched_time;
      parent_touch_depth = other.parent_touch_depth;
      // V5.6: HTF Touch Tracking
      h1_parent_id = other.h1_parent_id;
      h1_touch_time = other.h1_touch_time;
      h1_touch_depth = other.h1_touch_depth;
      h4_parent_id = other.h4_parent_id;
      h4_touch_time = other.h4_touch_time;
      h4_touch_depth = other.h4_touch_depth;
      // V5.0.1: Multi-Parent Tracking
      parent_count = other.parent_count;
      for(int i = 0; i < 9; i++) parent_zone_ids[i] = other.parent_zone_ids[i];
      any_parent_touched = other.any_parent_touched;
      earliest_parent_touch = other.earliest_parent_touch;
      tf_rank = other.tf_rank;
      can_trade = other.can_trade;
      is_pioneer = other.is_pioneer;
      // V5.3: Fractal Domino M15 Opener
      m15_parent_id = other.m15_parent_id;
      m15_touch_time = other.m15_touch_time;
      m15_has_h4_parent = other.m15_has_h4_parent;
      m15_has_h1_parent = other.m15_has_h1_parent;
      // Enhanced Zone Lifecycle
      created_bar_index = other.created_bar_index;
      zone_age_bars = other.zone_age_bars;
      L1_touch_time = other.L1_touch_time;
      fifty_touch_time = other.fifty_touch_time;
      L2_touch_time = other.L2_touch_time;
      L1_touch_bar = other.L1_touch_bar;
      fifty_touch_bar = other.fifty_touch_bar;
      L2_touch_bar = other.L2_touch_bar;
      touch_count = other.touch_count;
      // Enhanced Market Context
      narrative_direction = other.narrative_direction;
      atr_at_creation = other.atr_at_creation;
      session_created = other.session_created;
      conflicting_zones = other.conflicting_zones;
      // God Data
      fractal_depth_score = other.fractal_depth_score;
      tf_dominance_score = other.tf_dominance_score;
      cluster_density = other.cluster_density;
      elasticity_velocity = other.elasticity_velocity;
      // Enhanced Trade Outcome
      was_traded = other.was_traded;
      entry_level_used = other.entry_level_used;
      entry_price = other.entry_price;
      sl_price = other.sl_price;
      tp_price = other.tp_price;
      exit_price = other.exit_price;
      exit_reason = other.exit_reason;
      trade_open_time = other.trade_open_time;
      trade_close_time = other.trade_close_time;
      trade_duration_bars = other.trade_duration_bars;
      max_adverse_excursion = other.max_adverse_excursion;
      max_favorable_excursion = other.max_favorable_excursion;
      rr_planned = other.rr_planned;
      rr_achieved = other.rr_achieved;
      pnl_points = other.pnl_points;
      pnl_money = other.pnl_money;
      mfe_time = other.mfe_time;
      mae_time = other.mae_time;
      is_narrative_conflicted = other.is_narrative_conflicted;
      is_bulldozer_active = other.is_bulldozer_active;
      narrative_vacuum = other.narrative_vacuum;
     }
   
   //=== Validation ===
   bool IsValid() const { return is_valid && !is_invalidated && zone_id > 0; }
   
   //=== Get Zone Size in Points ===
   double GetZoneSize() const { return MathAbs(L1_price - L2_price) / _Point; }
   
   //=== Reset ===
   void Reset()
     {
      zone_id = 0;
      display_number = 0;
      timeframe = PERIOD_CURRENT;
      direction = DIRECTION_NONE;
      L1_price = 0.0;
      L2_price = 0.0;
      fifty_percent = 0.0;
      first_barrier_price = 0.0;
      first_barrier_time = 0;
      second_barrier_price = 0.0;
      second_barrier_time = 0;
      swing_between_price = 0.0;
      swing_between_time = 0;
      L1_touched = false;
      fifty_touched = false;
      L2_touched = false;
      L1_traded = false;
      fifty_traded = false;
      L2_traded = false;
      is_valid = false;
      is_invalidated = false;
      zone_created_time = 0;
      invalidation_time = 0;
      rect_name = "";
      L1_line_name = "";
      L2_line_name = "";
      fifty_line_name = "";
      label_name = "";
      has_narrative_parent = false;
      has_control_parent = false;
      parent_zone_id = 0;
      is_inside_parent = false;
      parent_tf = PERIOD_CURRENT;
      parent_L1_price = 0.0;
      parent_L2_price = 0.0;
      is_parent_touched = false;
      parent_touched_time = 0;
      parent_touch_depth = 0;
      // V5.6: HTF Touch Tracking
      h1_parent_id = 0;
      h1_touch_time = 0;
      h1_touch_depth = 0;
      h4_parent_id = 0;
      h4_touch_time = 0;
      h4_touch_depth = 0;
      // V5.0.1: Multi-Parent Tracking
      parent_count = 0;
      for(int i = 0; i < 9; i++) parent_zone_ids[i] = 0;
      any_parent_touched = false;
      earliest_parent_touch = 0;
      tf_rank = 0;
      can_trade = false;
      is_pioneer = false;
      // V5.3: Fractal Domino M15 Opener
      m15_parent_id = 0;
      m15_touch_time = 0;
      m15_has_h4_parent = false;
      m15_has_h1_parent = false;
      // Enhanced Zone Lifecycle
      created_bar_index = 0;
      zone_age_bars = 0;
      L1_touch_time = 0;
      fifty_touch_time = 0;
      L2_touch_time = 0;
      L1_touch_bar = 0;
      fifty_touch_bar = 0;
      L2_touch_bar = 0;
      touch_count = 0;
      // Enhanced Market Context
      narrative_direction = DIRECTION_NONE;
      atr_at_creation = 0.0;
      session_created = "";
      conflicting_zones = 0;
      // God Data
      fractal_depth_score = 0;
      tf_dominance_score = 0.0;
      cluster_density = 0;
      elasticity_velocity = 0.0;
      // Enhanced Trade Outcome
      was_traded = false;
      entry_level_used = "";
      entry_price = 0.0;
      sl_price = 0.0;
      tp_price = 0.0;
      exit_price = 0.0;
      exit_reason = "";
      trade_open_time = 0;
      trade_close_time = 0;
      trade_duration_bars = 0;
      max_adverse_excursion = 0.0;
      max_favorable_excursion = 0.0;
      rr_planned = 0.0;
      rr_achieved = 0.0;
      pnl_points = 0.0;
      pnl_money = 0.0;
      mfe_time = 0;
      mae_time = 0;
      is_narrative_conflicted = false;
      is_bulldozer_active = false;
      narrative_vacuum = 0.0;
     }
  };

//+------------------------------------------------------------------+
//| PendingB2BZone Structure                                          |
//| V5.1: 5-Pointer Detection System                                  |
//| Holds L1-L2 swing pairs awaiting P4 confirmation                  |
//| Flow: P1(L2) → P2(L1) → P3 → P5 → wait for P4 breakout            |
//+------------------------------------------------------------------+
struct PendingB2BZone
  {
   //=== L1 Swing (Entry Level) ===
   double              L1_price;             // Price of L1 swing
   datetime            L1_swing_time;        // Time of L1 swing point
   ENUM_SWING_TYPE     L1_swing_type;        // Type of L1 swing (LOW for SELL, HIGH for BUY)
   
   //=== L2 Swing (Adjacent, Stop Level) ===
   double              L2_price;             // Price of L2 swing (adjacent to L1)
   datetime            L2_swing_time;        // Time of L2 swing point
   ENUM_SWING_TYPE     L2_swing_type;        // Type of L2 swing (HIGH for SELL, LOW for BUY)
   
   //=== Breakout Info ===
   datetime            L1_breakout_time;     // When L1 was broken (entry signal)
   double              L1_breakout_price;    // Price of breakout bar when L1 was broken
   
   //=== Zone Metadata ===
   ENUM_SIGNAL_DIRECTION direction;          // BULLISH (BUY) or BEARISH (SELL)
   ENUM_TIMEFRAMES     timeframe;            // Timeframe of detection
   datetime            created_time;         // When this pending zone was created
   
   //--- Constructor
   PendingB2BZone(void)
     {
      Reset();
     }
   
   //--- Copy Constructor
   PendingB2BZone(const PendingB2BZone &other)
     {
      L1_price = other.L1_price;
      L1_swing_time = other.L1_swing_time;
      L1_swing_type = other.L1_swing_type;
      L2_price = other.L2_price;
      L2_swing_time = other.L2_swing_time;
      L2_swing_type = other.L2_swing_type;
      L1_breakout_time = other.L1_breakout_time;
      L1_breakout_price = other.L1_breakout_price;
      direction = other.direction;
      timeframe = other.timeframe;
      created_time = other.created_time;
     }
   
   //--- Reset
   void Reset(void)
     {
      L1_price = 0.0;
      L1_swing_time = 0;
      L1_swing_type = SWING_NONE;
      L2_price = 0.0;
      L2_swing_time = 0;
      L2_swing_type = SWING_NONE;
      L1_breakout_time = 0;
      L1_breakout_price = 0.0;
      direction = DIRECTION_NONE;
      timeframe = PERIOD_CURRENT;
      created_time = 0;
     }
   
   //--- Validation
   bool IsValid() const
     {
      return L1_price > 0.0 && L2_price > 0.0 && 
             L1_swing_time > 0 && L2_swing_time > 0 &&
             direction != DIRECTION_NONE;
     }
   
   //--- Calculate fifty percent level
   double FiftyPercent() const
     {
      return (L1_price + L2_price) / 2.0;
     }
  };

//+------------------------------------------------------------------+
//| B2BZoneList Structure                                            |
//| V5.7.2: Wrapper for dynamic arrays to allow array of arrays      |
//| Necessary because MQL5 forbids Type arr[STATIC][DYNAMIC]         |
//+------------------------------------------------------------------+
struct B2BZoneList
  {
   B2BZoneInfo       items[]; // Dynamic array of zones
   
   // Helper methods
   int Count() const { return ArraySize(items); }
   
   void Clear() { ArrayResize(items, 0); }
   
   void Add(const B2BZoneInfo &item)
     {
      int size = ArraySize(items);
      ArrayResize(items, size + 1);
      items[size] = item;
     }
  };


//+------------------------------------------------------------------+
//| ENUM_TRADE_SIGNAL_TYPE                                           |
//| Moved from TradeSignalGenerator.mqh for visibility               |
//+------------------------------------------------------------------+
enum ENUM_TRADE_SIGNAL_TYPE
  {
   SIGNAL_NONE = 0,     // No signal
   SIGNAL_ENTRY_L1 = 1, // Entry at L1 touch
   SIGNAL_ENTRY_50 = 2, // Entry at 50% touch
   SIGNAL_ENTRY_L2 = 3  // Entry at L2 touch
  };

//+------------------------------------------------------------------+
//| TradeSignalInfo Structure                                        |
//| Moved from TradeSignalGenerator.mqh for visibility               |
//+------------------------------------------------------------------+
struct TradeSignalInfo
  {
   //=== Constructor ===
   TradeSignalInfo()
     {
      Reset();
     }
   
   //=== Reset ===
   void Reset()
     {
      zone_id = 0;
      zone_tf = PERIOD_CURRENT;
      signal_type = SIGNAL_NONE;
      direction = DIRECTION_NONE;
      entry_price = 0.0;
      stop_loss = 0.0;
      take_profit = 0.0;
      position_pct = 0.0;
      sl_distance_points = 0.0;
      signal_time = 0;
      is_valid = false;
      lifecycle_phase = "";
      vector_signature = "";
      vector_sum = 0;
      target_r = 0.0;
      atr_at_entry = 0.0; 
      is_narrative_conflict = false;
      
      // Compatibility Fields
      zone_age_bars = 0;
      zone_size_points = 0.0;
      fractal_depth = 0;
      cascade_score = 0;
      d1_aligned = false;
       layer_1_tide = "";
       layer_2_wind = "";
       layer_3_trap = "";
       layer_4_trigger = "";
       
       anchor_id = 0;
       outpost_id = 0;
       bridge_state = "";
       is_with_trend = true;
       parent_tf = PERIOD_D1;
       
       mom_mode = 0; // 0=Normal
       is_intraday = false;
      }
    
   //=== Fields ===
   ulong               zone_id;           // Source zone ID
   ENUM_TIMEFRAMES     zone_tf;           // Zone timeframe
   ENUM_TRADE_SIGNAL_TYPE signal_type;    // Type of signal
   ENUM_SIGNAL_DIRECTION direction;       // BUY or SELL
   double              entry_price;
   double              stop_loss;
   double              take_profit;
   double              position_pct;      // Risk allocation
   double              sl_distance_points;
   datetime            signal_time;
   ulong               anchor_id;         // V5.9: Primary Origin
   ulong               outpost_id;        // V5.9: Forward Successor
   string              bridge_state;      // V5.9: Recursive Handshake
   bool                is_with_trend;     // V2.0: With-Trend or Counter-Trend
   ENUM_TIMEFRAMES     parent_tf;         // V2.0: Which TF authorized (D1/W1)
   bool                is_valid;
   string              lifecycle_phase;
   string              vector_signature;
   int                 vector_sum;
   double              target_r;
   double              atr_at_entry;
   int                 net_delta;
   int                 buy_votes;
   int                 sell_votes;
   bool                is_narrative_conflict;
   
   string              layer_1_tide;
   string              layer_2_wind;
   string              layer_3_trap;
   string              layer_4_trigger;
   
   // Compatibility Fields (Required by OrderManager logging)
   int                 zone_age_bars;
   double              zone_size_points;
   int                 fractal_depth;
   int                 cascade_score;
   bool                d1_aligned;
   // Gamma REMOVED
   // ulong               roadblock_id;
   // double              roadblock_dist;
   // double              elasticity;
   // double              beta_thresh;
   // double              gamma_thresh;
    int                 mom_mode;
    bool                is_intraday;       // V6.3: True if from IntradayOrchestrator
   };

#endif // V50_STRUCTURES_MQH
