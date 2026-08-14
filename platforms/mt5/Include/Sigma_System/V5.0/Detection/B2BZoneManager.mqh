//+------------------------------------------------------------------+
//|                                              B2BZoneManager.mqh |
//|                             Copyright 2025, Sigma Trading System |
//| V5.1: Zone Storage and Management                                 |
//| - Zone CRUD operations                                            |
//| - Zone ID generation                                              |
//| - Overlap consolidation                                           |
//+------------------------------------------------------------------+
#ifndef V50_B2BZONEMANAGER_MQH
#define V50_B2BZONEMANAGER_MQH

#include "../Data/Structures.mqh"
#include "../Common/CircularBuffer.mqh"

//+------------------------------------------------------------------+
//| CB2BZoneManager Class                                             |
//| Manages zone storage, retrieval, and cleanup                      |
//+------------------------------------------------------------------+
class CB2BZoneManager
  {
public:
   //=== Zone ID Generation ===
   static ulong  GenerateZoneId(double L1_price, double L2_price, 
                                 ENUM_TIMEFRAMES tf, ENUM_SIGNAL_DIRECTION direction, 
                                 datetime creation_time);
   
   //=== Zone Lookup ===
   static int    FindZoneIndexById(const B2BZoneInfo &zones[], int zone_count, ulong zone_id);
   static bool   FindZoneById(const B2BZoneInfo &zones[], int zone_count, 
                               ulong zone_id, B2BZoneInfo &out_zone);
   
   //=== Zone Cleanup ===
   static int    RemoveInvalidatedZones(B2BZoneInfo &zones[], int &zone_count);

   static int    RemoveDeadZones(B2BZoneInfo &zones[], int &zone_count);  // V5.7.3: Conservative cleanup
   
   //=== V5.8: Entropy Pruning ===
   static int    PruneInvalidatedZones(B2BZoneInfo &zones[], int &zone_count, int age_seconds);
   
   //=== Overlap Consolidation ===
   static int    ConsolidateOverlappingZones(CCircularBuffer<B2BZoneInfo> &zones, 
                                              double overlap_threshold_pct = 50.0);
   
   //=== Zone Access ===
   static bool   GetZone(const B2BZoneInfo &zones[], int zone_count, int index, B2BZoneInfo &zone);
   static void   GetAllZones(const B2BZoneInfo &zones[], int zone_count, B2BZoneInfo &out_zones[], int &out_count);
  };

//+------------------------------------------------------------------+
//| GenerateZoneId - Deterministic Hash                               |
//| Same zone always gets same ID regardless of session               |
//+------------------------------------------------------------------+
ulong CB2BZoneManager::GenerateZoneId(double L1_price, double L2_price, 
                                       ENUM_TIMEFRAMES tf, ENUM_SIGNAL_DIRECTION direction, 
                                       datetime creation_time)
  {
   ulong L1_pips = (ulong)MathRound(L1_price * 100000);
   ulong L2_pips = (ulong)MathRound(L2_price * 100000);
   ulong tf_val = (ulong)tf;
   ulong dir_val = (direction == DIRECTION_BULLISH) ? 1 : 2;
   ulong time_val = (ulong)creation_time;
   
   // FNV-1a hash
   ulong hash = 14695981039346656037;
   ulong prime = 1099511628211;
   
   hash = hash ^ L1_pips;
   hash = hash * prime;
   hash = hash ^ L2_pips;
   hash = hash * prime;
   hash = hash ^ tf_val;
   hash = hash * prime;
   hash = hash ^ dir_val;
   hash = hash * prime;
   hash = hash ^ time_val;
   hash = hash * prime;
   
   // V5.4.1: Mask to 53-bits for JS Number safety & MQL5 parsing
   // Fixes "OPEN" trades bug (parsing overflow) and WebApp precision issues
   return hash & 0x1FFFFFFFFFFFFF;
  }

//+------------------------------------------------------------------+
//| FindZoneIndexById - Find zone index by ID                         |
//+------------------------------------------------------------------+
int CB2BZoneManager::FindZoneIndexById(const B2BZoneInfo &zones[], int zone_count, ulong zone_id)
  {
   for(int i = 0; i < zone_count; i++)
     {
      if(zones[i].zone_id == zone_id)
         return i;
     }
   return -1;
  }

//+------------------------------------------------------------------+
//| FindZoneById - Get zone by ID                                     |
//+------------------------------------------------------------------+
bool CB2BZoneManager::FindZoneById(const B2BZoneInfo &zones[], int zone_count, 
                                    ulong zone_id, B2BZoneInfo &out_zone)
  {
   int idx = FindZoneIndexById(zones, zone_count, zone_id);
   if(idx >= 0)
     {
      out_zone = zones[idx];
      return true;
     }
   return false;
  }

//+------------------------------------------------------------------+
//| RemoveInvalidatedZones - Compact array removing invalid zones     |
//+------------------------------------------------------------------+
int CB2BZoneManager::RemoveInvalidatedZones(B2BZoneInfo &zones[], int &zone_count)
  {
   int new_count = 0;
   int removed = 0;
   
   for(int i = 0; i < zone_count; i++)
     {
      if(zones[i].IsValid())
        {
         if(new_count != i)
            zones[new_count] = zones[i];
         new_count++;
        }
      else
         removed++;
     }
   
   if(removed > 0)
     {
      ArrayResize(zones, new_count);
      zone_count = new_count;
     }
   
   return removed;
  }

//+------------------------------------------------------------------+
//| RemoveDeadZones - V5.7.3 Conservative Cleanup                     |
//| Only removes zones that are INVALIDATED and NEVER TRADED          |
//| Preserves traded zones for ML data export                         |
//+------------------------------------------------------------------+
int CB2BZoneManager::RemoveDeadZones(B2BZoneInfo &zones[], int &zone_count)
  {
   int new_count = 0;
   int removed = 0;
   
   for(int i = 0; i < zone_count; i++)
     {
      // Keep zone if:
      // 1. Still valid (active zone)
      // 2. OR was traded (needed for ML export)
      bool keep = zones[i].IsValid() || zones[i].was_traded;
      
      if(keep)
        {
         if(new_count != i)
            zones[new_count] = zones[i];
         new_count++;
        }
      else
         removed++;
     }
   
   if(removed > 0)
     {
      ArrayResize(zones, new_count);
      zone_count = new_count;
     }
   
   return removed;
  }

//+------------------------------------------------------------------+
//| PruneInvalidatedZones - V5.8 Entropy Pruning (Garbage Collector)  |
//| Removes zones that are INVALIDATED and older than age_seconds.      |
//| This keeps memory usage constant (O(1)) instead of O(N).          |
//+------------------------------------------------------------------+
int CB2BZoneManager::PruneInvalidatedZones(B2BZoneInfo &zones[], int &zone_count, int age_seconds)
  {
   if (age_seconds <= 0) return 0; // Pruning disabled
   
   int new_count = 0;
   int removed = 0;
   datetime cutoff_time = TimeCurrent() - age_seconds;
   
   for(int i = 0; i < zone_count; i++)
     {
      bool remove = false;
      
      // CRITERIA:
      // 1. Must be INVALIDATED (Dead)
      // 2. Invalidation time must be older than cutoff (Event Horizon)
      // 3. SAFETY: Do NOT remove zones that were TRADED (unless we archive them)
      //For backtesting speed, we remove even traded zones if they are ancient dead history
      // BUT for now, let's keep traded zones to be safe for stats
      
      if(zones[i].is_invalidated && !zones[i].was_traded)
        {
         if(zones[i].invalidation_time > 0 && zones[i].invalidation_time < cutoff_time)
           {
            remove = true;
           }
        }
        
      if(!remove)
        {
         if(new_count != i)
            zones[new_count] = zones[i];
         new_count++;
        }
      else
         removed++;
     }
   
   if(removed > 0)
     {
      ArrayResize(zones, new_count);
      zone_count = new_count;
     }
   
   return removed;
  }

//+------------------------------------------------------------------+
//| ConsolidateOverlappingZones - Remove redundant overlapping zones  |
//+------------------------------------------------------------------+
int CB2BZoneManager::ConsolidateOverlappingZones(CCircularBuffer<B2BZoneInfo> &zones, 
                                                  double overlap_threshold_pct)
  {
   int count = zones.Count();
   if(count < 2)
      return 0;
   
   int removed = 0;
   
   bool to_remove[];
   ArrayResize(to_remove, count);
   ArrayInitialize(to_remove, false);
   
   for(int i = 0; i < count; i++)
     {
      if(to_remove[i])
         continue;
      
      B2BZoneInfo zone_i = zones.Get(i);
      
      double top_i = MathMax(zone_i.L1_price, zone_i.L2_price);
      double bot_i = MathMin(zone_i.L1_price, zone_i.L2_price);
      double range_i = top_i - bot_i;
      
      if(range_i <= 0)
         continue;
      
      for(int j = i + 1; j < count; j++)
        {
         if(to_remove[j])
            continue;
         
         B2BZoneInfo zone_j = zones.Get(j);
         
         if(zone_i.timeframe != zone_j.timeframe)
            continue;
         if(zone_i.direction != zone_j.direction)
            continue;
         
         double top_j = MathMax(zone_j.L1_price, zone_j.L2_price);
         double bot_j = MathMin(zone_j.L1_price, zone_j.L2_price);
         double range_j = top_j - bot_j;
         
         if(range_j <= 0)
            continue;
         
         double intersect_top = MathMin(top_i, top_j);
         double intersect_bot = MathMax(bot_i, bot_j);
         double intersection = (intersect_top > intersect_bot) ? (intersect_top - intersect_bot) : 0;
         
         if(intersection <= 0)
            continue;
         
         double smaller_range = MathMin(range_i, range_j);
         double overlap_pct = (intersection / smaller_range) * 100.0;
         
         if(overlap_pct >= overlap_threshold_pct)
           {
            // Keep the BIGGEST zone
            bool keep_zone_i = (range_i >= range_j);
            
            if(keep_zone_i)
               to_remove[j] = true;
            else
              {
               to_remove[i] = true;
               break;
              }
           }
        }
     }
   
   // Rebuild buffer without removed zones
   B2BZoneInfo survivors[];
   int survivor_count = 0;
   
   for(int i = 0; i < count; i++)
     {
      if(!to_remove[i])
        {
         ArrayResize(survivors, survivor_count + 1);
         survivors[survivor_count] = zones.Get(i);
         survivor_count++;
        }
      else
         removed++;
     }
   
   if(removed > 0)
     {
      zones.Clear();
      for(int i = 0; i < survivor_count; i++)
         zones.Add(survivors[i]);
     }
   
   return removed;
  }

//+------------------------------------------------------------------+
//| GetZone - Get zone at index                                       |
//+------------------------------------------------------------------+
bool CB2BZoneManager::GetZone(const B2BZoneInfo &zones[], int zone_count, int index, B2BZoneInfo &zone)
  {
   if(index < 0 || index >= zone_count)
      return false;
   
   zone = zones[index];
   return true;
  }

//+------------------------------------------------------------------+
//| GetAllZones - Copy all zones to output array                      |
//+------------------------------------------------------------------+
void CB2BZoneManager::GetAllZones(const B2BZoneInfo &zones[], int zone_count, B2BZoneInfo &out_zones[], int &out_count)
  {
   out_count = zone_count;
   ArrayResize(out_zones, zone_count);
   
   for(int i = 0; i < zone_count; i++)
      out_zones[i] = zones[i];
  }

#endif // V50_B2BZONEMANAGER_MQH
