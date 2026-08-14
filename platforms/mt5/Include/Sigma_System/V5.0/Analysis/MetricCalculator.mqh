//+------------------------------------------------------------------+
//|                                             MetricCalculator.mqh |
//|                             Copyright 2025, Sigma Trading System |
//|                                        sigmatrading.ai@gmail.com |
//+------------------------------------------------------------------+
//| V5.0.1 DATA ENGINEERING                                          |
//| Computes "God Data" metrics for AI Pattern Recognition           |
//| 1. Fractal Depth (Russian Doll Density)                          |
//| 2. Timeframe Dominance (HTF Gravity)                             |
//| 3. Elasticity/Velocity (Reaction Speed)                          |
//+------------------------------------------------------------------+
#property strict

#ifndef V50_METRIC_CALCULATOR_MQH
#define V50_METRIC_CALCULATOR_MQH

#include "../Data/Structures.mqh"
#include "../Common/Defines.mqh"

class CMetricCalculator
  {
public:
   //+------------------------------------------------------------------+
   //| CalculateFractalDepth (HTF Parent Count)                         |
   //| V11.3 REPURPOSED: Counts how many HTF parent zones contain this  |
   //| zone. Higher Score = More HTF confluence support.                |
   //| Returns 0-4 based on H1/H4/D1/W1 parent presence.                |
   //+------------------------------------------------------------------+
   static int CalculateFractalDepth(const B2BZoneInfo &zone, const B2BZoneInfo &all_zones[], int total_zones)
     {
      int score = 0;
      
      // Skip if this is HTF itself (D1+ don't need parent count)
      if(zone.timeframe == PERIOD_D1 || zone.timeframe == PERIOD_W1 || zone.timeframe == PERIOD_MN1) 
         return 0;

      double zone_top = MathMax(zone.L1_price, zone.L2_price);
      double zone_bottom = MathMin(zone.L1_price, zone.L2_price);
      double zone_center = (zone_top + zone_bottom) / 2.0;
      
      // Track which parent TFs we've found
      bool has_h1_parent = false;
      bool has_h4_parent = false;
      bool has_d1_parent = false;
      bool has_w1_parent = false;
      
      for(int i = 0; i < total_zones; i++)
        {
         // Skip self
         if(all_zones[i].zone_id == zone.zone_id) continue;
         
         // Parent must be same direction
         if(all_zones[i].direction != zone.direction) continue;
         
         // Parent must be Higher Timeframe
         if(GetTFRank(all_zones[i].timeframe) >= GetTFRank(zone.timeframe)) continue;
         
         // Check if zone center is INSIDE parent
         double parent_top = MathMax(all_zones[i].L1_price, all_zones[i].L2_price);
         double parent_bottom = MathMin(all_zones[i].L1_price, all_zones[i].L2_price);
         
         bool is_inside = (zone_center <= parent_top && zone_center >= parent_bottom);
         
         if(is_inside)
           {
            // Mark which parent TF we found
            ENUM_TIMEFRAMES parent_tf = all_zones[i].timeframe;
            if(parent_tf == PERIOD_H1)  has_h1_parent = true;
            else if(parent_tf == PERIOD_H4)  has_h4_parent = true;
            else if(parent_tf == PERIOD_D1)  has_d1_parent = true;
            else if(parent_tf == PERIOD_W1)  has_w1_parent = true;
           }
        }
      
      // Count parent TFs
      if(has_h1_parent) score++;
      if(has_h4_parent) score++;
      if(has_d1_parent) score++;
      if(has_w1_parent) score++;
        
      return score;
     }

   //+------------------------------------------------------------------+
   //| CalculateTFDominance (The "Overrule" Factor)                     |
   //| Measures the net influence of HTF zones (Tailwind vs Headwind)   |
   //| Positive = Tailwind (Aligned), Negative = Headwind (Conflict)    |
   //+------------------------------------------------------------------+
   static double CalculateTFDominance(const B2BZoneInfo &zone, const B2BZoneInfo &all_zones[], int total_zones)
     {
      double dominance_score = 0.0;
      
      // Only calculate for LTF zones (D1/W1/MN1 don't have many parents)
      if(zone.timeframe == PERIOD_MN1) return 0.0;

      double zone_center = (zone.L1_price + zone.L2_price) / 2.0;
      
      for(int i = 0; i < total_zones; i++)
        {
         // Skip self and invalid zones
         if(all_zones[i].zone_id == zone.zone_id) continue;
         // Skip self only - V5.2 FIX: Include all zones for accurate metrics
         
         // Parent must be Higher Timeframe
         if(GetTFRank(all_zones[i].timeframe) >= GetTFRank(zone.timeframe)) continue;
         
         // Check Proximity (Touching or Overlapping)
         double parent_top = MathMax(all_zones[i].L1_price, all_zones[i].L2_price);
         double parent_bottom = MathMin(all_zones[i].L1_price, all_zones[i].L2_price);
         
         bool overlaps = (zone_center <= parent_top && zone_center >= parent_bottom);
         
         if(overlaps)
           {
            // Weight based on TF Rank (MN1 is heavy, H4 is light)
            double weight = (8.0 - GetTFRank(all_zones[i].timeframe)); // MN1(0)=8.0, H4(3)=5.0
            
            if(all_zones[i].direction == zone.direction)
              {
               // Tailwind (Aligned)
               dominance_score += weight;
              }
            else
              {
               // Headwind (Conflict) - Stronger penalty for headwind!
               dominance_score -= (weight * 1.5); 
              }
           }
        }
        
      return dominance_score;
     }

   //+------------------------------------------------------------------+
   //| CalculateClusterDensity (Nearby Zone Count)                      |
   //| V5.2: NEW - Counts zones within radius_points of current zone    |
   //| Higher Density = More supporting structures nearby               |
   //+------------------------------------------------------------------+
   static int CalculateClusterDensity(const B2BZoneInfo &zone, const B2BZoneInfo &all_zones[], 
                                       int total_zones, double radius_points = 500)
     {
      int count = 0;
      double zone_center = (zone.L1_price + zone.L2_price) / 2.0;
      double radius_price = radius_points * SymbolInfoDouble(_Symbol, SYMBOL_POINT);
      
      for(int i = 0; i < total_zones; i++)
        {
         if(all_zones[i].zone_id == zone.zone_id) continue;
         
         double other_center = (all_zones[i].L1_price + all_zones[i].L2_price) / 2.0;
         if(MathAbs(other_center - zone_center) <= radius_price)
            count++;
        }
      return count;
     }

   //+------------------------------------------------------------------+
   //| CalculateElasticity (Reaction Velocity)                          |
   //| Pips traveled back into zone / Bars taken                        |
   //+------------------------------------------------------------------+
   static double CalculateElasticity(const B2BZoneInfo &zone)
     {
        // Require at least one touch
        if(!zone.L1_touched) return 0.0;
        
        // Time from L1 touch to deepest point (so far)
        // This is tricky for live zones, better calculated on history close
        // For now, return 0 as placeholder for Phase 2
        return 0.0;
     }

   //+------------------------------------------------------------------+
   //| Helper: Get Timeframe Rank                                       |
   //| 0=MN1 ... 8=M1                                                   |
   //+------------------------------------------------------------------+
   static int GetTFRank(ENUM_TIMEFRAMES tf)
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
     
  };

#endif // V50_METRIC_CALCULATOR_MQH
