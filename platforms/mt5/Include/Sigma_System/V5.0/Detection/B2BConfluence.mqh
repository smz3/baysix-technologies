//+------------------------------------------------------------------+
//|                                               B2BConfluence.mqh |
//|                             Copyright 2025, Sigma Trading System |
//| V5.1: Zone Confluence and Hierarchy                               |
//| - Parent/child zone relationships                                 |
//| - Russian Doll multi-parent tracking                              |
//| - Pioneer zone detection                                          |
//| - Entry zone filtering                                            |
//+------------------------------------------------------------------+
#ifndef V50_B2BCONFLUENCE_MQH
#define V50_B2BCONFLUENCE_MQH

#include "../Data/Structures.mqh"
#include "../Configuration/TradingParameters.mqh"

//+------------------------------------------------------------------+
//| CB2BConfluence Class                                              |
//| Handles zone hierarchy and confluence logic                       |
//+------------------------------------------------------------------+
class CB2BConfluence
  {
public:
   //=== TF Hierarchy ===
   static int    GetTFRank(ENUM_TIMEFRAMES tf);
   static bool   IsNarrativeTF(ENUM_TIMEFRAMES tf);
   static bool   IsControlTF(ENUM_TIMEFRAMES tf);
   static bool   IsEntryTF(ENUM_TIMEFRAMES tf);
   
   //=== Confluence Flags ===
   static void   SetConfluenceFlags(B2BZoneInfo &zones[], int zone_count);
   static void   SetMultiParentFlags(B2BZoneInfo &zones[], int zone_count);
   
   //=== Pioneer Zones ===
   static bool   IsPioneerZone(const B2BZoneInfo &zone, double ath, double atl);
   static void   SetPioneerFlags(B2BZoneInfo &zones[], int zone_count);
   
   //=== Filtering ===
   static int    FilterEntryZonesByNesting(B2BZoneInfo &zones[], int zone_count, 
                                            int nesting_mode, bool m1_requires_m5 = false);
   
   //=== Parent Zone Status ===
   static bool   IsParentZoneTouched(const B2BZoneInfo &zones[], int zone_count, 
                                      ulong parent_zone_id, datetime &touched_time);
   

   

  };

//+------------------------------------------------------------------+
//| GetTFRank - TF hierarchy (0=MN1 highest, 8=M1 lowest)             |
//+------------------------------------------------------------------+
int CB2BConfluence::GetTFRank(ENUM_TIMEFRAMES tf)
  {
   switch(tf)
     {
      case PERIOD_MN1: return 0;
      case PERIOD_W1:  return 1;
      case PERIOD_D1:  return 2;
      case PERIOD_H4:  return 3;
      case PERIOD_H1:  return 4;
      case PERIOD_M30: return 5;
      case PERIOD_M15: return 6;
      case PERIOD_M5:  return 7;
      case PERIOD_M1:  return 8;
      default:         return 9;
     }
  }

//+------------------------------------------------------------------+
//| IsNarrativeTF - MN1, W1, D1                                       |
//+------------------------------------------------------------------+
bool CB2BConfluence::IsNarrativeTF(ENUM_TIMEFRAMES tf)
  {
   return (tf == PERIOD_MN1 || tf == PERIOD_W1 || tf == PERIOD_D1);
  }

//+------------------------------------------------------------------+
//| IsControlTF - H4 Only (Strategy B Strict)                         |
//+------------------------------------------------------------------+
bool CB2BConfluence::IsControlTF(ENUM_TIMEFRAMES tf)
  {
   // V14: Unified with Orchestrator - H4, H1, and M30 are all valid traps/control zones
   return (tf == PERIOD_H4 || tf == PERIOD_H1 || tf == PERIOD_M30); 
  }

//+------------------------------------------------------------------+
//| IsEntryTF - M1, M5                                                |
//+------------------------------------------------------------------+
bool CB2BConfluence::IsEntryTF(ENUM_TIMEFRAMES tf)
  {
   return (tf == PERIOD_M1 || tf == PERIOD_M5);
  }

//+------------------------------------------------------------------+
//| SetConfluenceFlags - Find parent zones for each zone              |
//+------------------------------------------------------------------+
//+------------------------------------------------------------------+
//| SetConfluenceFlags - V11.3 Generalized Parent Detection          |
//| Now supports ALL higher TF parents for Fractal Anchor system     |
//+------------------------------------------------------------------+
void CB2BConfluence::SetConfluenceFlags(B2BZoneInfo &zones[], int zone_count)
  {
   for(int i = 0; i < zone_count; i++)
     {
      zones[i].has_narrative_parent = false;
      zones[i].has_control_parent = false;
      zones[i].parent_zone_id = 0;
      zones[i].is_inside_parent = false;
      zones[i].parent_tf = PERIOD_CURRENT;
      
      // Skip Narrative TFs (D1/W1/MN1) - they don't need parents
      if(IsNarrativeTF(zones[i].timeframe)) continue;
      
      double zone_top = MathMax(zones[i].L1_price, zones[i].L2_price);
      double zone_bottom = MathMin(zones[i].L1_price, zones[i].L2_price);
      double zone_center = (zone_top + zone_bottom) / 2.0;
      
      for(int j = 0; j < zone_count; j++)
        {
         if(i == j) continue;
         if(!zones[j].IsValid()) continue;
         if(zones[j].direction != zones[i].direction) continue;
         
         // V11.3: Parent must be a HIGHER timeframe (lower rank = higher TF)
         int my_rank = GetTFRank(zones[i].timeframe);
         int parent_rank = GetTFRank(zones[j].timeframe);
         if(parent_rank >= my_rank) continue; // Not a higher TF
         
         double parent_top = MathMax(zones[j].L1_price, zones[j].L2_price);
         double parent_bottom = MathMin(zones[j].L1_price, zones[j].L2_price);
         
         // V14: Use ANY overlap for containment check (loosened per user request)
         bool overlaps = (zone_bottom <= parent_top && zone_top >= parent_bottom);
         
         if(overlaps)
           {
            bool is_fully_inside = (zones[i].L1_price >= parent_bottom && zones[i].L1_price <= parent_top &&
                                   zones[i].L2_price >= parent_bottom && zones[i].L2_price <= parent_top);
            
            // Set narrative/control flags based on parent TF
            bool parent_is_narrative = IsNarrativeTF(zones[j].timeframe);
            bool parent_is_control = IsControlTF(zones[j].timeframe);
            
            if(parent_is_narrative)
               zones[i].has_narrative_parent = true;
            
            if(parent_is_control)
               zones[i].has_control_parent = true;
            
            // Record the HIGHEST TF parent (priority: D1+ > H4 > H1 > etc)
            if(zones[i].parent_zone_id == 0 || parent_rank < GetTFRank(zones[i].parent_tf))
              {
               zones[i].parent_zone_id = zones[j].zone_id;
               zones[i].parent_tf = zones[j].timeframe;
               zones[i].is_inside_parent = is_fully_inside;
               zones[i].parent_L1_price = zones[j].L1_price;
               zones[i].parent_L2_price = zones[j].L2_price;
               
               // V11.4: Calculate Anchor TP Levels
               // TP1 = Parent 50%, TP2 = Parent L2 (Invalidation side)
               zones[i].anchor_tp1_price = zones[j].fifty_percent;
               zones[i].anchor_tp2_price = zones[j].L2_price;
               
               zones[i].is_parent_touched = zones[j].is_parent_touched;
               zones[i].parent_touched_time = zones[j].parent_touched_time;
               zones[i].parent_touch_depth = zones[j].parent_touch_depth;
              }
           }
        }
     }
  }

//+------------------------------------------------------------------+
//| SetMultiParentFlags - V11.3 Generalized Ancestry Tracking        |
//| Populates parent_zone_ids for ALL timeframes (Russian Doll)      |
//+------------------------------------------------------------------+
void CB2BConfluence::SetMultiParentFlags(B2BZoneInfo &zones[], int zone_count)
  {
   for(int i = 0; i < zone_count; i++)
     {
      // V11.3: Run for ALL zones (D1 down to M1)
      if(zones[i].timeframe == PERIOD_MN1) continue; // MN1 has no parents
      
      zones[i].tf_rank = GetTFRank(zones[i].timeframe);
      zones[i].parent_count = 0;
      for(int k = 0; k < 9; k++) zones[i].parent_zone_ids[k] = 0;
      zones[i].any_parent_touched = false;
      zones[i].earliest_parent_touch = 0;
      zones[i].can_trade = false;
      
      double zone_top = MathMax(zones[i].L1_price, zones[i].L2_price);
      double zone_bottom = MathMin(zones[i].L1_price, zones[i].L2_price);
      double zone_center = (zone_top + zone_bottom) / 2.0;
      
      for(int j = 0; j < zone_count; j++)
        {
         if(i == j) continue;
         if(!zones[j].IsValid()) continue;
         if(zones[j].direction != zones[i].direction) continue;
         
         int parent_rank = GetTFRank(zones[j].timeframe);
         if(parent_rank >= zones[i].tf_rank) continue; // Not a higher TF
         
         // V11.3: Remove Strategy B restrictions. Record ANY higher TF zone that overlaps.
         double parent_top = MathMax(zones[j].L1_price, zones[j].L2_price);
         double parent_bottom = MathMin(zones[j].L1_price, zones[j].L2_price);
         
         // V14: Use ANY overlap for containment check
         bool overlaps = (zone_bottom <= parent_top && zone_top >= parent_bottom);
         
         if(overlaps)
           {
            // Record the parent in its specific TF slot
            zones[i].parent_zone_ids[parent_rank] = zones[j].zone_id;
            zones[i].parent_count++;
            
            // Track if any parent has been touched
            if(zones[j].is_parent_touched)
              {
               zones[i].any_parent_touched = true;
               if(zones[i].earliest_parent_touch == 0 || zones[j].parent_touched_time < zones[i].earliest_parent_touch)
                  zones[i].earliest_parent_touch = zones[j].parent_touched_time;
              }
           }
        }
      
      // V11.3: can_trade now just indicates if structural permission exists
      zones[i].can_trade = (zones[i].parent_count > 0);
     }
   
   //=================================================================
   // V5.3 FRACTAL DOMINO: M15 Opener Tracking for M5 Zones
   // V5.5: For ML data harvesting, M5 can overlap with ANY M15 (direction-agnostic)
   // M15 needs (H4 OR H1) for cascade validation
   //=================================================================
   for(int i = 0; i < zone_count; i++)
     {
      // Only process M5 zones
      if(zones[i].timeframe != PERIOD_M5)
         continue;
      
      // Reset M15 fields
      zones[i].m15_parent_id = 0;
      zones[i].m15_touch_time = 0;
      zones[i].m15_has_h4_parent = false;
      zones[i].m15_has_h1_parent = false;
      
      double zone_top = MathMax(zones[i].L1_price, zones[i].L2_price);
      double zone_bottom = MathMin(zones[i].L1_price, zones[i].L2_price);
      
      // V5.5 FIX: Find valid overlapping M15 zone in SAME DIRECTION
      // M5 BUY needs M15 BUY, M5 SELL needs M15 SELL
      for(int j = 0; j < zone_count; j++)
        {
         if(zones[j].timeframe != PERIOD_M15) continue;
         if(zones[j].direction != zones[i].direction) continue;  // Must be same direction
         if(!zones[j].IsValid()) continue;
         
         double m15_top = MathMax(zones[j].L1_price, zones[j].L2_price);
         double m15_bottom = MathMin(zones[j].L1_price, zones[j].L2_price);
         bool overlaps = (zone_bottom <= m15_top) && (zone_top >= m15_bottom);
         
         if(overlaps)
           {
            // Found valid overlapping M15 - use it
            zones[i].m15_parent_id = zones[j].zone_id;
            
            // V5.5 DEBUG: Log M15 parent assignment with direction
            string dir_str = (zones[i].direction == DIRECTION_BULLISH) ? "BUY" : "SELL";
            // PrintFormat("[DEBUG M15] %s | M5 Zone %I64u gets M15 Parent %I64u | M5: %.2f-%.2f | M15: %.2f-%.2f",
            //             dir_str,
            //             zones[i].zone_id, zones[j].zone_id,
            //             zones[i].L1_price, zones[i].L2_price,
            //             zones[j].L1_price, zones[j].L2_price);
            
            // Calculate touch time for this M15
            datetime m15_touch = 0;
            if(zones[j].L1_touched)
              {
               if(m15_touch == 0 || zones[j].L1_touch_time < m15_touch)
                  m15_touch = zones[j].L1_touch_time;
              }
            if(zones[j].fifty_touched)
              {
               if(m15_touch == 0 || zones[j].fifty_touch_time < m15_touch)
                  m15_touch = zones[j].fifty_touch_time;
              }
            if(zones[j].L2_touched)
              {
               if(m15_touch == 0 || zones[j].L2_touch_time < m15_touch)
                  m15_touch = zones[j].L2_touch_time;
              }
            zones[i].m15_touch_time = m15_touch;
            
            // M15's H4 permission
            zones[i].m15_has_h4_parent = zones[j].has_control_parent;
            
            // M15's H1 permission: check if M15 overlaps with any H1 zone
            for(int k = 0; k < zone_count; k++)
              {
               if(zones[k].timeframe != PERIOD_H1) continue;
               // H1 check remains direction-aware (M15 direction, not M5)
               if(zones[k].direction != zones[j].direction) continue;
               if(!zones[k].IsValid()) continue;
               
               double h1_top = MathMax(zones[k].L1_price, zones[k].L2_price);
               double h1_bottom = MathMin(zones[k].L1_price, zones[k].L2_price);
               bool h1_overlaps = (m15_bottom <= h1_top) && (m15_top >= h1_bottom);
               
               if(h1_overlaps)
                 {
                  zones[i].m15_has_h1_parent = true;
                  break;
                 }
              }
            
            break; // Found valid M15 overlap, stop searching
           }
        }
     }
  }

//+------------------------------------------------------------------+
//| IsPioneerZone - Check if zone is at ATH/ATL                       |
//+------------------------------------------------------------------+
bool CB2BConfluence::IsPioneerZone(const B2BZoneInfo &zone, double ath, double atl)
  {
   if(!IsEntryTF(zone.timeframe))
      return false;
   
   if(zone.parent_count > 0)
      return false;
   
   double range = ath - atl;
   if(range <= 0)
      return false;
      
   double tolerance = range * 0.01;
   
   if(zone.direction == DIRECTION_BULLISH)
     {
      double zone_low = MathMin(zone.L1_price, zone.L2_price);
      if(zone_low <= atl + tolerance)
         return true;
     }
   
   if(zone.direction == DIRECTION_BEARISH)
     {
      double zone_high = MathMax(zone.L1_price, zone.L2_price);
      if(zone_high >= ath - tolerance)
         return true;
     }
   
   return false;
  }

//+------------------------------------------------------------------+
//| SetPioneerFlags - Mark parentless zones at ATH/ATL                |
//| V5.2: Pioneer flags still set for data export, but not used in    |
//| trading logic (Strategy B uses H4→M5/M1 only)                     |
//+------------------------------------------------------------------+
void CB2BConfluence::SetPioneerFlags(B2BZoneInfo &zones[], int zone_count)
  {
   double ath = 0.0;
   double atl = DBL_MAX;
   
   MqlRates monthly_rates[];
   int bars_copied = CopyRates(_Symbol, PERIOD_MN1, 0, 120, monthly_rates);
   
   if(bars_copied > 0)
     {
      for(int i = 0; i < bars_copied; i++)
        {
         if(monthly_rates[i].high > ath) ath = monthly_rates[i].high;
         if(monthly_rates[i].low < atl) atl = monthly_rates[i].low;
        }
     }
   
   if(ath == 0.0 || atl == DBL_MAX)
      return;
   
   for(int i = 0; i < zone_count; i++)
     {
      zones[i].is_pioneer = IsPioneerZone(zones[i], ath, atl);
      
      if(zones[i].is_pioneer)
         zones[i].can_trade = true;
     }
  }



//+------------------------------------------------------------------+
//| IsParentZoneTouched - Check if parent zone was touched            |
//+------------------------------------------------------------------+
bool CB2BConfluence::IsParentZoneTouched(const B2BZoneInfo &zones[], int zone_count, 
                                          ulong parent_zone_id, datetime &touched_time)
  {
   if(parent_zone_id == 0)
      return false;
   
   for(int i = 0; i < zone_count; i++)
     {
      if(zones[i].zone_id == parent_zone_id)
        {
         if(zones[i].is_parent_touched)
           {
            touched_time = zones[i].parent_touched_time;
            return true;
           }
         return false;
        }
     }
   return false;
  }

//+------------------------------------------------------------------+
//| Get5TFVote - Count votes from MN1, W1, D1, H4, H1                 |
//| Returns majority direction and populates vote counts              |
//+------------------------------------------------------------------+





#endif // V50_B2BCONFLUENCE_MQH

