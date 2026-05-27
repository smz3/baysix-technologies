//+------------------------------------------------------------------+
//|                                                  B2BDetector.mqh |
//|                             Copyright 2025, Sigma Trading System |
//| V5.1 MODULAR - 5-Pointer Detection + Compatibility Wrappers      |
//| Core detection + wrapper methods for EA backwards compatibility   |
//| Heavy lifting moved to modular files (called via static methods)  |
//+------------------------------------------------------------------+
#ifndef V50_B2BDETECTOR_MQH
#define V50_B2BDETECTOR_MQH

#property strict

#include "../Data/Structures.mqh"
#include "../Common/Defines.mqh"
#include "../Common/CircularBuffer.mqh"
#include "../Configuration/TradingParameters.mqh"

// V5.1: Include modular utilities (static method classes)
#include "B2BZoneStatus.mqh"
#include "B2BZoneManager.mqh"
#include "B2BConfluence.mqh"
#include "B2BTradeTracker.mqh"
#include "../Analysis/MetricCalculator.mqh"
// V5.1: Using CZonePersistence directly (B2BPersistence removed)

// V5.0: Logging input
input bool InpLog_B2B = false;  // Enable B2B detection logging

// V5.1.2: Extern reference to display number counter (defined in Sigma_V5.0.mq5)
extern int g_next_display_number;

//+------------------------------------------------------------------+
//| CB2BDetector Class                                                |
//| Core 5-Pointer Detection + EA Compatibility Wrappers              |
//+------------------------------------------------------------------+
class CB2BDetector
  {
private:
   bool              m_initialized;
   CZonePersistence  m_persistence;  // V5.1: Direct usage, no wrapper
   
   // Internal zone storage (for EA compatibility)
   B2BZoneInfo       m_zones[];
   int               m_zone_count;
   
public:
                     CB2BDetector(void);
                    ~CB2BDetector(void);
   
   //=== Initialization ===
   void              Initialize();
   void              Reset();
   bool              IsInitialized() const { return m_initialized; }
   
   //=== CORE: 5-Pointer Detection ===
   // start_index: Index to start scanning from (0 = full scan, higher = skip older swings)
   int               DetectB2B_5Pointer(ENUM_TIMEFRAMES tf,
                                         CCircularBuffer<SwingPointInfo> &swings,
                                         B2BZoneInfo &out_zones[],
                                         int start_index = 0);
   
   //=== EA Compatibility Wrappers (delegate to static classes) ===
   // Zone Status
   int               ValidateZonesInBuffer(B2BZoneInfo &zones[], int &zone_count);
   int               UpdateZoneStatusInBuffer(B2BZoneInfo &zones[], int zone_count,
                                               double current_close, double current_high, double current_low,
                                               bool is_new_bar = false);
   
   // Zone Access (uses internal m_zones for legacy support)
   void              ClearAllZones();
   int               GetZoneCount() const { return m_zone_count; }
   bool              GetZone(int index, B2BZoneInfo &zone) const;
   void              GetAllZones(B2BZoneInfo &zones[], int &count) const;
   bool              GetZoneById(ulong zone_id, B2BZoneInfo &zone);
   int               GetZoneIndexById(ulong zone_id) const;
   
   // Trade Tracking (operates on internal m_zones)
   bool              RecordTradeOpen(ulong zone_id, string entry_level, 
                                      double entry_price, double sl, double tp, double rr_planned);
   bool              RecordTradeClose(ulong zone_id, double exit_price, 
                                       string exit_reason, double pnl_points, double pnl_money);
   void              UpdateTradeExcursions(ulong zone_id, double current_price);
   bool              SetZoneTraded(ulong zone_id, string level);
   
   // Confluence  
   void              SetConfluenceFlags();
   void              SetMultiParentFlags();
   void              SetPioneerFlags();

   
   // Persistence
   CZonePersistence* GetPersistence() { return &m_persistence; }
   datetime          GetEAAttachTime() const { return m_persistence.GetEAAttachTime(); }
   bool              SaveZonesToFile();
   int               LoadZonesFromFile();
   
   // V5.1: Buffer persistence wrappers (avoid pointer issues in EA)
   bool              SaveZonesFromBuffers(B2BZoneList &buffers[], int &counts[])
                       { return m_persistence.SaveZonesFromBuffers(buffers, counts); }
   int               LoadZonesToBuffers(B2BZoneList &buffers[], int &counts[])
                       { return m_persistence.LoadZonesToBuffers(buffers, counts); }
                       
   // V5.2: Sync buffers to internal storage for OnTester scanning
   void              LoadZonesFromBuffers(B2BZoneList &buffers[], int &counts[]);
   

                       
   // RE-IMPLEMENTATION: Pruning operates on buffers via ZoneManager static methods
   int               PruneBuffers(B2BZoneList &buffers[], int &counts[], int age_seconds)
     {
      int pruned = 0;
      int total_buffers = ArraySize(buffers);
      for(int i=0; i<total_buffers; i++)
        {
         pruned += CB2BZoneManager::PruneInvalidatedZones(buffers[i].items, counts[i], age_seconds);
        }
      return pruned;
     }
   
private:
   //=== 5-Pointer Detection Helpers ===
   int               FindP5_OlderBarrier(CCircularBuffer<SwingPointInfo> &swings,
                                          int p1_index, double p2_price,
                                          ENUM_SIGNAL_DIRECTION direction);
   
   bool              IsP4_BreakoutConfirmed(const SwingPointInfo &P5, 
                                             double bar_close,
                                             ENUM_SIGNAL_DIRECTION direction);
   
   B2BZoneInfo       CreateZoneFrom5Pointer(const SwingPointInfo &P1,
                                             const SwingPointInfo &P2,
                                             const SwingPointInfo &P3,
                                             const SwingPointInfo &P5,
                                             datetime P4_time,
                                             ENUM_TIMEFRAMES tf,
                                             ENUM_SIGNAL_DIRECTION direction,
                                             double atr = 0);
   
   // V5.1.2: Buffer-aware swing usage check (replaces local used[] array)
   // V8: Direction parameter - only blocks same-direction zones
   bool              IsSwingUsedInZones(B2BZoneInfo &zones[],
                                         double swing_price, datetime swing_time,
                                         ENUM_SIGNAL_DIRECTION direction = DIRECTION_NONE);
  };

//+------------------------------------------------------------------+
//| Constructor                                                       |
//+------------------------------------------------------------------+
CB2BDetector::CB2BDetector(void)
  {
   m_initialized = false;
   m_zone_count = 0;
   ArrayResize(m_zones, 0);
  }

//+------------------------------------------------------------------+
//| Destructor                                                        |
//+------------------------------------------------------------------+
CB2BDetector::~CB2BDetector(void)
  {
   ArrayFree(m_zones);
  }

//+------------------------------------------------------------------+
//| Initialize                                                        |
//+------------------------------------------------------------------+
void CB2BDetector::Initialize()
  {
   Reset();
   m_persistence.Initialize(_Symbol);
   m_initialized = true;
   
   if(InpLog_B2B)
     {
      Print("[B2B] Detector initialized (V5.1 Modular)");
      PrintFormat("[B2B] EA attach time: %s", TimeToString(m_persistence.GetEAAttachTime()));
     }
  }

//+------------------------------------------------------------------+
//| Reset                                                             |
//+------------------------------------------------------------------+
void CB2BDetector::Reset()
  {
   ArrayResize(m_zones, 0);
   m_zone_count = 0;
  }

//+------------------------------------------------------------------+
//| ClearAllZones                                                     |
//+------------------------------------------------------------------+
void CB2BDetector::ClearAllZones()
  {
   ArrayResize(m_zones, 0);
   m_zone_count = 0;
  }

//+------------------------------------------------------------------+
//| ValidateZonesInBuffer - Wrapper                                   |
//+------------------------------------------------------------------+
int CB2BDetector::ValidateZonesInBuffer(B2BZoneInfo &zones[], int &zone_count)
  {
   return CB2BZoneStatus::ValidateZonesInBuffer(zones, zone_count);
  }

//+------------------------------------------------------------------+
//| UpdateZoneStatusInBuffer - Wrapper                                |
//| V6.2 FIX: Added is_new_bar parameter for bar-close-only invalidation |
//+------------------------------------------------------------------+
int CB2BDetector::UpdateZoneStatusInBuffer(B2BZoneInfo &zones[], int zone_count,
                                            double current_close, double current_high, double current_low,
                                            bool is_new_bar)
  {
   return CB2BZoneStatus::UpdateZoneStatusInBuffer(zones, zone_count, current_close, current_high, current_low, is_new_bar);
  }

//+------------------------------------------------------------------+
//| GetZone                                                           |
//+------------------------------------------------------------------+
bool CB2BDetector::GetZone(int index, B2BZoneInfo &zone) const
  {
   return CB2BZoneManager::GetZone(m_zones, m_zone_count, index, zone);
  }

//+------------------------------------------------------------------+
//| GetAllZones                                                       |
//+------------------------------------------------------------------+
void CB2BDetector::GetAllZones(B2BZoneInfo &zones[], int &count) const
  {
   CB2BZoneManager::GetAllZones(m_zones, m_zone_count, zones, count);
  }

//+------------------------------------------------------------------+
//| GetZoneById                                                       |
//+------------------------------------------------------------------+
bool CB2BDetector::GetZoneById(ulong zone_id, B2BZoneInfo &zone)
  {
   return CB2BZoneManager::FindZoneById(m_zones, m_zone_count, zone_id, zone);
  }

//+------------------------------------------------------------------+
//| GetZoneIndexById                                                  |
//+------------------------------------------------------------------+
int CB2BDetector::GetZoneIndexById(ulong zone_id) const
  {
   return CB2BZoneManager::FindZoneIndexById(m_zones, m_zone_count, zone_id);
  }

//+------------------------------------------------------------------+
//| RecordTradeOpen - Wrapper                                         |
//+------------------------------------------------------------------+
bool CB2BDetector::RecordTradeOpen(ulong zone_id, string entry_level, 
                                    double entry_price, double sl, double tp, double rr_planned)
  {
   return CB2BTradeTracker::RecordTradeOpen(m_zones, m_zone_count, zone_id, 
                                             entry_level, entry_price, sl, tp, rr_planned);
  }

//+------------------------------------------------------------------+
//| RecordTradeClose - Wrapper                                        |
//+------------------------------------------------------------------+
bool CB2BDetector::RecordTradeClose(ulong zone_id, double exit_price, 
                                     string exit_reason, double pnl_points, double pnl_money)
  {
   return CB2BTradeTracker::RecordTradeClose(m_zones, m_zone_count, zone_id,
                                              exit_price, exit_reason, pnl_points, pnl_money);
  }

//+------------------------------------------------------------------+
//| UpdateTradeExcursions - Wrapper                                   |
//+------------------------------------------------------------------+
void CB2BDetector::UpdateTradeExcursions(ulong zone_id, double current_price)
  {
   CB2BTradeTracker::UpdateTradeExcursions(m_zones, m_zone_count, zone_id, current_price);
  }

//+------------------------------------------------------------------+
//| SetZoneTraded - Wrapper                                           |
//+------------------------------------------------------------------+
bool CB2BDetector::SetZoneTraded(ulong zone_id, string level)
  {
   return CB2BTradeTracker::SetZoneTraded(m_zones, m_zone_count, zone_id, level);
  }

//+------------------------------------------------------------------+
//| SetConfluenceFlags - Wrapper                                      |
//+------------------------------------------------------------------+
void CB2BDetector::SetConfluenceFlags()
  {
   CB2BConfluence::SetConfluenceFlags(m_zones, m_zone_count);
  }

//+------------------------------------------------------------------+
//| SetMultiParentFlags - Wrapper                                     |
//+------------------------------------------------------------------+
void CB2BDetector::SetMultiParentFlags()
  {
   CB2BConfluence::SetMultiParentFlags(m_zones, m_zone_count);
  }

//+------------------------------------------------------------------+
//| SetPioneerFlags - Wrapper                                         |
//+------------------------------------------------------------------+
void CB2BDetector::SetPioneerFlags()
  {
   CB2BConfluence::SetPioneerFlags(m_zones, m_zone_count);
  }



//+------------------------------------------------------------------+
//| SaveZonesToFile - Wrapper                                         |
//+------------------------------------------------------------------+
bool CB2BDetector::SaveZonesToFile()
  {
   return m_persistence.SaveZones(m_zones, m_zone_count);
  }

//+------------------------------------------------------------------+
//| LoadZonesFromFile - Wrapper                                       |
//+------------------------------------------------------------------+
int CB2BDetector::LoadZonesFromFile()
  {
   return m_persistence.MergeLoadedZones(m_zones, m_zone_count);
  }

//+------------------------------------------------------------------+
//| FindP5_OlderBarrier                                               |
//+------------------------------------------------------------------+
int CB2BDetector::FindP5_OlderBarrier(CCircularBuffer<SwingPointInfo> &swings,
                                       int p1_index, double p2_price,
                                       ENUM_SIGNAL_DIRECTION direction)
  {
   if(p1_index < 0)
      return -1;
   
   SwingPointInfo P1 = swings.Get(p1_index);
   ENUM_SWING_TYPE target_type = (direction == DIRECTION_BEARISH) ? SWING_LOW : SWING_HIGH;
   
   for(int i = p1_index - 1; i >= 0; i--)
     {
      SwingPointInfo swing = swings.Get(i);
      
      if(swing.time >= P1.time)
         continue;
      
      if(swing.type != target_type)
         continue;
      
      if(direction == DIRECTION_BEARISH)
        {
         if(swing.price < p2_price)
            return i;
        }
      else
        {
         if(swing.price > p2_price)
            return i;
        }
     }
   
   return -1;
  }

//+------------------------------------------------------------------+
//| IsP4_BreakoutConfirmed                                            |
//+------------------------------------------------------------------+
bool CB2BDetector::IsP4_BreakoutConfirmed(const SwingPointInfo &P5, 
                                           double bar_close,
                                           ENUM_SIGNAL_DIRECTION direction)
  {
   if(direction == DIRECTION_BEARISH)
      return (bar_close < P5.price);
   else
      return (bar_close > P5.price);
  }

//+------------------------------------------------------------------+
//| CreateZoneFrom5Pointer                                            |
//+------------------------------------------------------------------+
B2BZoneInfo CB2BDetector::CreateZoneFrom5Pointer(const SwingPointInfo &P1,
                                                  const SwingPointInfo &P2,
                                                  const SwingPointInfo &P3,
                                                  const SwingPointInfo &P5,
                                                  datetime P4_time,
                                                  ENUM_TIMEFRAMES tf,
                                                  ENUM_SIGNAL_DIRECTION direction,
                                                  double atr)
  {
   B2BZoneInfo zone;
   
   double L2_price;
   datetime L2_time;
   
   if(direction == DIRECTION_BEARISH)
     {
      if(P1.price >= P3.price)
        { L2_price = P1.price; L2_time = P1.time; }
      else
        { L2_price = P3.price; L2_time = P3.time; }
     }
   else
     {
      if(P1.price <= P3.price)
        { L2_price = P1.price; L2_time = P1.time; }
      else
        { L2_price = P3.price; L2_time = P3.time; }
     }
   
   zone.L2_price = L2_price;
   zone.L1_price = P2.price;
   zone.fifty_percent = (zone.L1_price + zone.L2_price) / 2.0;
   
   zone.timeframe = tf;
   zone.direction = direction;
   zone.zone_id = CB2BZoneManager::GenerateZoneId(zone.L1_price, zone.L2_price, tf, direction, L2_time);
   
   // V5.1.2: Assign sequential display number for UI
   zone.display_number = g_next_display_number++;
   
   zone.first_barrier_price = P2.price;
   zone.first_barrier_time = P2.time;
   zone.second_barrier_price = P5.price;
   zone.second_barrier_time = P5.time;
   zone.swing_between_price = L2_price;
   zone.swing_between_time = L2_time;
   
   zone.L1_touched = false;
   zone.fifty_touched = false;
   zone.L2_touched = false;
   zone.is_valid = true;
   zone.is_invalidated = false;
   zone.zone_created_time = P4_time;
   zone.invalidation_time = 0;
   
   zone.rect_name = "";
   zone.L1_line_name = "";
   zone.L2_line_name = "";
   zone.fifty_line_name = "";
   zone.label_name = "";
   
   zone.has_narrative_parent = false;
   zone.has_control_parent = false;
   zone.parent_zone_id = 0;
   zone.is_inside_parent = false;
   zone.parent_tf = PERIOD_CURRENT;
   
   zone.created_bar_index = iBarShift(_Symbol, tf, P4_time);
   zone.zone_age_bars = 0;
   zone.L1_touch_time = 0;
   zone.fifty_touch_time = 0;
   zone.L2_touch_time = 0;
   zone.L1_touch_bar = 0;
   zone.fifty_touch_bar = 0;
   zone.L2_touch_bar = 0;
   zone.touch_count = 0;
   
   MqlDateTime dt;
   TimeToStruct(P4_time, dt);
   int hour = dt.hour;
   if(hour >= 0 && hour < 8)
      zone.session_created = "ASIAN";
   else if(hour >= 8 && hour < 16)
      zone.session_created = "LONDON";
   else
      zone.session_created = "NEWYORK";
   
   zone.atr_at_creation = atr;
   zone.narrative_direction = DIRECTION_NONE;
   zone.conflicting_zones = 0;
   
   zone.was_traded = false;
   zone.entry_level_used = "";
   zone.entry_price = 0;
   zone.sl_price = 0;
   zone.tp_price = 0;
   zone.exit_price = 0;
   zone.exit_reason = "";
   zone.trade_open_time = 0;
   zone.trade_close_time = 0;
   zone.trade_duration_bars = 0;
   zone.max_adverse_excursion = 0;
   zone.max_favorable_excursion = 0;
   zone.rr_planned = 0;
   zone.rr_achieved = 0;
   zone.pnl_points = 0;
   zone.pnl_money = 0;
   
   return zone;
  }

//+------------------------------------------------------------------+
//| IsSwingUsedInZones - V5.1.2 Buffer-aware swing check              |
//| V8: Only check within same direction - BUY/SELL can share swings  |
//| Checks if a swing point (by price+time) is already used in any    |
//| existing zone OF THE SAME DIRECTION in the buffer.                |
//+------------------------------------------------------------------+
bool CB2BDetector::IsSwingUsedInZones(B2BZoneInfo &zones[],
                                       double swing_price, datetime swing_time,
                                       ENUM_SIGNAL_DIRECTION direction = DIRECTION_NONE)
  {
   double tolerance = _Point / 2;
   
   int count = ArraySize(zones);
   for(int i = 0; i < count; i++)
     {
      // Skip invalidated zones - they don't block swing reuse
      if(zones[i].is_invalidated || !zones[i].is_valid)
         continue;
      
      // V8: Only block if SAME direction (or direction not specified)
      if(direction != DIRECTION_NONE && zones[i].direction != direction)
         continue;
      
      // Check L1 (first barrier / P2 in 5-pointer)
      if(MathAbs(zones[i].first_barrier_price - swing_price) < tolerance &&
         zones[i].first_barrier_time == swing_time)
         return true;
      
      // Check L2 / swing_between (P1 or P3 in 5-pointer)
      if(MathAbs(zones[i].swing_between_price - swing_price) < tolerance &&
         zones[i].swing_between_time == swing_time)
         return true;
      
      // Check second barrier (P5 in 5-pointer)
      if(MathAbs(zones[i].second_barrier_price - swing_price) < tolerance &&
         zones[i].second_barrier_time == swing_time)
         return true;
     }
   
   return false;
  }

//+------------------------------------------------------------------+
//| DetectB2B_5Pointer                                                |
//| IMPORTANT: CCircularBuffer index 0 = NEWEST, high index = OLDEST  |
//| So we iterate from high to low (oldest to newest chronologically) |
//+------------------------------------------------------------------+
int CB2BDetector::DetectB2B_5Pointer(ENUM_TIMEFRAMES tf,
                                      CCircularBuffer<SwingPointInfo> &swings,
                                      B2BZoneInfo &out_zones[],
                                      int start_index)
  {
   if(!m_initialized)
      return 0;
   
   int zones_detected = 0;
   int swing_count = swings.Count();
   
   if(swing_count < 4)
      return 0;
   
   if(InpLog_B2B)
      PrintFormat("[B2B] 5-Pointer Detection: TF=%s, Swings=%d, StartIndex=%d", EnumToString(tf), swing_count, start_index);
   
   // Clamp start_index to valid range
   if(start_index < 0) start_index = 0;
   if(start_index >= swing_count - 2) return 0; // Not enough swings after start_index
   
   MqlRates rates[];
   int bars_copied = CopyRates(_Symbol, tf, 0, InpHistoricalBars, rates);
   if(bars_copied <= 0)
      return 0;
   ArraySetAsSeries(rates, true);  // rates[0] = most recent bar
   
   // V5.1.2: Removed local used[] array - now using buffer-aware IsSwingUsedInZones()
   // This ensures swing usage persists across detection calls
   
// STRUCT for candidate logic
   struct B2BCandidate {
      int p1_idx;
      int p2_idx;
      int p3_idx;
      int p5_idx;
      datetime p4_time;
      ENUM_SIGNAL_DIRECTION dir;
   };

   B2BCandidate candidates[];

   //==========================================================================
   // PASS 1: SCAN FOR ALL CANDIDATES (SELL & BUY)
   // Iterate from OLDEST swing to NEWEST
   // Store every valid pattern found
   //==========================================================================
   
   // 1A. SCAN FOR SELL CANDIDATES
   for(int i = start_index; i < swing_count - 2; i++)
     {
      SwingPointInfo P1 = swings.Get(i);
      if(P1.type != SWING_HIGH) continue;
      
      // Find P2
      int p2_idx = -1;
      for(int j = i + 1; j < swing_count; j++)
        {
         SwingPointInfo s = swings.Get(j);
         if(s.time > P1.time && s.type == SWING_LOW) { p2_idx = j; break; }
        }
      if(p2_idx < 0) continue;
      SwingPointInfo P2 = swings.Get(p2_idx);
      
      // Find P3
      int p3_idx = -1;
      for(int j = p2_idx + 1; j < swing_count; j++)
        {
         SwingPointInfo s = swings.Get(j);
         if(s.time > P2.time && s.type == SWING_HIGH) { p3_idx = j; break; }
        }
      if(p3_idx < 0) continue;
      SwingPointInfo P3 = swings.Get(p3_idx);
      
      // Find P5
      int p5_idx = -1;
      for(int j = i - 1; j >= 0; j--)
        {
         SwingPointInfo s = swings.Get(j);
         if(s.time < P1.time && s.type == SWING_LOW && s.price < P2.price) { p5_idx = j; break; }
        }
      if(p5_idx < 0) continue;
      SwingPointInfo P5 = swings.Get(p5_idx);
      
      // Find P4
      datetime p4_time = 0;
      for(int b = bars_copied - 1; b >= 0; b--)
        {
         if(rates[b].time <= P3.time) continue;
         if(rates[b].close < P5.price) { p4_time = rates[b].time; break; }
        }
      if(p4_time == 0) continue;

      // STRICT FRESHNESS VALIDATION (USER REQUEST):
      // Ensure "Cannot be interrupted" - No new swings between P3 and P4.
      // We iterate ALL swings to find if any falls in (P3.time, p4_time).
      bool interrupted = false;
      for(int k = 0; k < swing_count; k++)
        {
         SwingPointInfo s_check = swings.Get(k);
         if(s_check.time > P3.time && s_check.time < p4_time)
           {
            interrupted = true;
            break;
           }
        }
      if(interrupted) continue;
      
      // GAP VALIDATION: Ensure L2 was not broken between P3 and P4
      bool invalidated_in_gap = false;
      double L2_check = MathMax(P1.price, P3.price);
      
      for(int b = bars_copied - 1; b >= 0; b--)
        {
         if(rates[b].time <= P3.time) continue; // Start after P3
         if(rates[b].time > p4_time) break;     // End at P4 (inclusive? P4 closes below P5, so likely safe)
         
         // If any bar closed above L2 before P4 confirmed, it's invalid
         if(rates[b].close > L2_check)
           { invalidated_in_gap = true; break; }
        }
      
      if(!invalidated_in_gap)
        {
         int size = ArraySize(candidates);
         ArrayResize(candidates, size + 1);
         candidates[size].p1_idx = i;
         candidates[size].p2_idx = p2_idx;
         candidates[size].p3_idx = p3_idx;
         candidates[size].p5_idx = p5_idx;
         candidates[size].p4_time = p4_time;
         candidates[size].dir = DIRECTION_BEARISH;
        }
     }

   // 1B. SCAN FOR BUY CANDIDATES
   for(int i = start_index; i < swing_count - 2; i++)
     {
      SwingPointInfo P1 = swings.Get(i);
      if(P1.type != SWING_LOW) continue;
      
      // Find P2
      int p2_idx = -1;
      for(int j = i + 1; j < swing_count; j++)
        {
         SwingPointInfo s = swings.Get(j);
         if(s.time > P1.time && s.type == SWING_HIGH) { p2_idx = j; break; }
        }
      if(p2_idx < 0) continue;
      SwingPointInfo P2 = swings.Get(p2_idx);
      
      // Find P3
      int p3_idx = -1;
      for(int j = p2_idx + 1; j < swing_count; j++)
        {
         SwingPointInfo s = swings.Get(j);
         if(s.time > P2.time && s.type == SWING_LOW) { p3_idx = j; break; }
        }
      if(p3_idx < 0) continue;
      SwingPointInfo P3 = swings.Get(p3_idx);
      
      // Find P5
      int p5_idx = -1;
      for(int j = i - 1; j >= 0; j--)
        {
         SwingPointInfo s = swings.Get(j);
         if(s.time < P1.time && s.type == SWING_HIGH && s.price > P2.price) { p5_idx = j; break; }
        }
      if(p5_idx < 0) continue;
      SwingPointInfo P5 = swings.Get(p5_idx);
      
      // Find P4
      datetime p4_time = 0;
      for(int b = bars_copied - 1; b >= 0; b--)
        {
         if(rates[b].time <= P3.time) continue;
         if(rates[b].close > P5.price) { p4_time = rates[b].time; break; }
        }
      if(p4_time == 0) continue;
      
      // STRICT FRESHNESS VALIDATION (USER REQUEST):
      // Ensure "Cannot be interrupted" - No new swings between P3 and P4.
      bool interrupted = false;
      for(int k = 0; k < swing_count; k++)
        {
         SwingPointInfo s_check = swings.Get(k);
         if(s_check.time > P3.time && s_check.time < p4_time)
           {
            interrupted = true;
            break;
           }
        }
      if(interrupted) continue;
      
      // GAP VALIDATION: Ensure L2 was not broken between P3 and P4
      bool invalidated_in_gap = false;
      double L2_check = MathMin(P1.price, P3.price); // For BUY: MIN(P1, P3)
      
      for(int b = bars_copied - 1; b >= 0; b--)
        {
         if(rates[b].time <= P3.time) continue;
         if(rates[b].time > p4_time) break;
         
         if(rates[b].close < L2_check)
           { invalidated_in_gap = true; break; }
        }

      if(!invalidated_in_gap)
        {
         int size = ArraySize(candidates);
         ArrayResize(candidates, size + 1);
         candidates[size].p1_idx = i;
         candidates[size].p2_idx = p2_idx;
         candidates[size].p3_idx = p3_idx;
         candidates[size].p5_idx = p5_idx;
         candidates[size].p4_time = p4_time;
         candidates[size].dir = DIRECTION_BULLISH;
        }
     }

   //==========================================================================
   // PASS 2: SELECT WINNERS (Freshest Pattern per P5)
   // Group by P5 index -> Keep Candidate with HIGHEST P1 index (Newest)
   //==========================================================================
   
   int final_count = 0;
   B2BCandidate final_list[];
   
   int total_candidates = ArraySize(candidates);
   bool processed[]; // Track which candidates are processed
   ArrayResize(processed, total_candidates);
   ArrayInitialize(processed, false);
   
   for(int i = 0; i < total_candidates; i++)
     {
      if(processed[i]) continue;
      
      // Start with this candidate as the best for this P5
      int best_candidate_idx = i;
      int current_p5 = candidates[i].p5_idx;
      
      // Check all other candidates for SAME P5
      for(int j = i + 1; j < total_candidates; j++)
        {
         if(processed[j]) continue;
         
         if(candidates[j].p5_idx == current_p5)
           {
            // Found duplicate P5 usage! Compare P1 logic
            // We want NEWEST pattern => HIGHEST P1 index
            if(candidates[j].p1_idx > candidates[best_candidate_idx].p1_idx)
              {
               best_candidate_idx = j;
              }
            
            // Mark as processed so we don't check it again as a primary
            processed[j] = true; 
           }
        }
      
      // Add the winner to final list
      int f_size = ArraySize(final_list);
      ArrayResize(final_list, f_size + 1);
      final_list[f_size] = candidates[best_candidate_idx];
      processed[best_candidate_idx] = true;
     }

   //==========================================================================
   // PASS 3: CREATE ZONES & MARK USED (All Points + P5)
   // Only create zones from the FINAL list of winners
   //==========================================================================
   
   int finals = ArraySize(final_list);
   if(InpLog_B2B)
      PrintFormat("[B2B] Logic V5.1.1: Candidates=%d -> Finals=%d (Unique P5s)", total_candidates, finals);

   // Sort finals by time (OPTIONAL but good for display consistency) 
   // - Simple bubble sort by P1 index
   for(int i=0; i<finals-1; i++) {
      for(int j=0; j<finals-i-1; j++) {
         if(final_list[j].p1_idx > final_list[j+1].p1_idx) {
            B2BCandidate temp = final_list[j];
            final_list[j] = final_list[j+1];
            final_list[j+1] = temp;
         }
      }
   }

   for(int i = 0; i < finals; i++)
     {
      B2BCandidate cand = final_list[i];
      
      SwingPointInfo P1 = swings.Get(cand.p1_idx);
      SwingPointInfo P2 = swings.Get(cand.p2_idx);
      SwingPointInfo P3 = swings.Get(cand.p3_idx);
      SwingPointInfo P5 = swings.Get(cand.p5_idx);
      
      // V5.1.2: Buffer-aware swing usage check (persists across calls)
      // V8: Only check same direction - BUY zones don't block SELL zones and vice versa
      if(IsSwingUsedInZones(out_zones, P1.price, P1.time, cand.dir) ||
         IsSwingUsedInZones(out_zones, P2.price, P2.time, cand.dir) ||
         IsSwingUsedInZones(out_zones, P3.price, P3.time, cand.dir) ||
         IsSwingUsedInZones(out_zones, P5.price, P5.time, cand.dir))
        {
         if(InpLog_B2B)
            PrintFormat("[B2B] Skipping pattern - swing already used in existing zone");
         continue;
        }
      
      // Check strictly for duplicates in OUTPUT buffer (redundancy check)
      bool exists = false;
      int current_out_count = ArraySize(out_zones);
       for(int k = 0; k < current_out_count; k++)
         {
          B2BZoneInfo e = out_zones[k];
         double check_L2 = (cand.dir == DIRECTION_BEARISH) ? MathMax(P1.price, P3.price) : MathMin(P1.price, P3.price);
         if(e.direction == cand.dir &&
            MathAbs(e.L1_price - P2.price) < _Point/2 &&
            MathAbs(e.L2_price - check_L2) < _Point/2)
           { exists = true; break; }
        }
      
       if(!exists)
        {
          // V15: Calculate ATR(14) at P4_time (Breakout Confirm) for Stride Physics
          double zone_atr = 0;
          int p4_idx = -1;
          for(int b = 0; b < bars_copied; b++) {
             if(rates[b].time == cand.p4_time) { p4_idx = b; break; }
          }
          
          if(p4_idx >= 0) {
             double tr_sum = 0;
             int count = 0;
             for(int k = p4_idx; k < p4_idx + 14 && k < bars_copied - 1; k++) {
                double tr = MathMax(rates[k].high - rates[k].low, 
                            MathMax(MathAbs(rates[k].high - rates[k+1].close), 
                                    MathAbs(rates[k].low - rates[k+1].close)));
                tr_sum += tr;
                count++;
             }
             zone_atr = (count > 0) ? (tr_sum / count) : 0;
          }
          
          B2BZoneInfo zone = CreateZoneFrom5Pointer(P1, P2, P3, P5, cand.p4_time, tf, cand.dir, zone_atr);
          
          int new_size = ArraySize(out_zones);
          ArrayResize(out_zones, new_size + 1);
          out_zones[new_size] = zone;
          zones_detected++;
         
         // V5.1.2: No longer need to mark used[] - IsSwingUsedInZones checks buffer directly
         
         // Phase 0: Log zone creation
         // V10.3 FIX: Logging delayed to Sigma_V5.0.mq5 after Confluence Update
         // if(g_zone_logger != NULL)
         //    g_zone_logger.LogZoneCreated(zone);
         
         if(InpLog_B2B)
            PrintFormat("[B2B] %s: P1=%.2f P2=%.2f P3=%.2f P5=%.2f (Latest Pattern)", 
                       (cand.dir==DIRECTION_BEARISH ? "SELL":"BUY"),
                       P1.price, P2.price, P3.price, P5.price);
        }
     }
    
    if(InpLog_B2B)
       PrintFormat("[B2B] Detection complete: %d zones for %s", zones_detected, EnumToString(tf));
    
    return zones_detected;
  }

//+------------------------------------------------------------------+
//| LoadZonesFromBuffers                                              |
//| V5.2: Sync buffers to internal storage for OnTester scanning      |
//+------------------------------------------------------------------+
//+------------------------------------------------------------------+
//| LoadZonesFromBuffers                                              |
//| V5.2: Sync buffers to internal storage for OnTester scanning      |
//+------------------------------------------------------------------+
void CB2BDetector::LoadZonesFromBuffers(B2BZoneList &buffers[], int &counts[])
  {
   // 1. Count total zones
   int total = 0;
   int buffers_count = ArraySize(buffers);
   
   for(int i = 0; i < buffers_count; i++)
     {
      total += counts[i];
     }
   
   // 2. Resize internal array
   ArrayResize(m_zones, total);
   m_zone_count = total;
   
   // 3. Copy zones
   int idx = 0;
   for(int i = 0; i < buffers_count; i++)
     {
      int count = counts[i];
      for(int j = 0; j < count; j++)
        {
         m_zones[idx++] = buffers[i].items[j];
        }
     }
     
   if(InpLog_B2B)
      PrintFormat("[B2B] Synced %d zones from buffers for OnTester analysis", total);
  }

#endif // V50_B2BDETECTOR_MQH
