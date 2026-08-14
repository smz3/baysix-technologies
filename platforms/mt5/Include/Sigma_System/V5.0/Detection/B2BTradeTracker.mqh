//+------------------------------------------------------------------+
//|                                             B2BTradeTracker.mqh |
//|                             Copyright 2025, Sigma Trading System |
//| V5.1: Trade Lifecycle Tracking                                    |
//| - Trade recording (open/close)                                    |
//| - MAE/MFE excursion tracking                                      |
//| - Zone traded flags                                               |
//+------------------------------------------------------------------+
#ifndef V50_B2BTRADETRACKER_MQH
#define V50_B2BTRADETRACKER_MQH

#include "../Data/Structures.mqh"

//+------------------------------------------------------------------+
//| CB2BTradeTracker Class                                            |
//| Handles trade lifecycle on zones                                  |
//+------------------------------------------------------------------+
class CB2BTradeTracker
  {
public:
   //=== Trade Recording ===
   static bool   RecordTradeOpen(B2BZoneInfo &zones[], int zone_count,
                                  ulong zone_id, string entry_level, 
                                  double entry_price, double sl, double tp, 
                                  double rr_planned);
   
   static bool   RecordTradeClose(B2BZoneInfo &zones[], int zone_count,
                                   ulong zone_id, double exit_price, 
                                   string exit_reason, double pnl_points, 
                                   double pnl_money);
   
   //=== Excursion Tracking ===
   static void   UpdateTradeExcursions(B2BZoneInfo &zones[], int zone_count,
                                        ulong zone_id, double current_price);
   
   //=== Zone Traded Flags ===
   static bool   SetZoneTraded(B2BZoneInfo &zones[], int zone_count,
                                ulong zone_id, string level);
   
   //=== Helpers ===
   static double CalculateRR(double entry_price, double sl_price, double exit_price, 
                              ENUM_SIGNAL_DIRECTION direction);
  };

//+------------------------------------------------------------------+
//| RecordTradeOpen - Record trade opening                            |
//+------------------------------------------------------------------+
bool CB2BTradeTracker::RecordTradeOpen(B2BZoneInfo &zones[], int zone_count,
                                        ulong zone_id, string entry_level, 
                                        double entry_price, double sl, double tp, 
                                        double rr_planned)
  {
   int idx = -1;
   for(int i = 0; i < zone_count; i++)
     {
      if(zones[i].zone_id == zone_id)
        {
         idx = i;
         break;
        }
     }
   
   if(idx < 0)
     {
      // V5.0 Architecture: m_zones is often out of sync during OnTick (using buffers instead).
      // This failure is expected and handled by updating the buffers directly in main EA.
      // PrintFormat("[TradeTracker] RecordTradeOpen: Zone %d not found", zone_id);
      return false;
     }
   
   zones[idx].was_traded = true;
   zones[idx].entry_level_used = entry_level;
   zones[idx].entry_price = entry_price;
   zones[idx].sl_price = sl;
   zones[idx].tp_price = tp;
   zones[idx].trade_open_time = TimeCurrent();
   zones[idx].rr_planned = rr_planned;
   zones[idx].max_adverse_excursion = 0;
   zones[idx].max_favorable_excursion = 0;
   
   PrintFormat("[TradeTracker] Trade opened on zone %d @ %.5f (%s) | SL:%.5f TP:%.5f RR:%.2f",
              zone_id, entry_price, entry_level, sl, tp, rr_planned);
   
   return true;
  }

//+------------------------------------------------------------------+
//| RecordTradeClose - Record trade closing                           |
//+------------------------------------------------------------------+
bool CB2BTradeTracker::RecordTradeClose(B2BZoneInfo &zones[], int zone_count,
                                         ulong zone_id, double exit_price, 
                                         string exit_reason, double pnl_points, 
                                         double pnl_money)
  {
   int idx = -1;
   for(int i = 0; i < zone_count; i++)
     {
      if(zones[i].zone_id == zone_id)
        {
         idx = i;
         break;
        }
     }
   
   if(idx < 0)
     {
      PrintFormat("[TradeTracker] RecordTradeClose: Zone %d not found", zone_id);
      return false;
     }
   
   zones[idx].exit_price = exit_price;
   zones[idx].exit_reason = exit_reason;
   zones[idx].trade_close_time = TimeCurrent();
   zones[idx].pnl_points = pnl_points;
   zones[idx].pnl_money = pnl_money;
   
   if(zones[idx].trade_open_time > 0)
      zones[idx].trade_duration_bars = iBarShift(_Symbol, zones[idx].timeframe, zones[idx].trade_open_time);
   
   zones[idx].rr_achieved = CalculateRR(zones[idx].entry_price, zones[idx].sl_price, 
                                         exit_price, zones[idx].direction);
   
   PrintFormat("[TradeTracker] Trade closed on zone %d | %s | PnL: %.1f pts (%.2f $) | RR: %.2f",
              zone_id, exit_reason, pnl_points, pnl_money, zones[idx].rr_achieved);
   
   return true;
  }

//+------------------------------------------------------------------+
//| UpdateTradeExcursions - Track MAE/MFE                             |
//+------------------------------------------------------------------+
void CB2BTradeTracker::UpdateTradeExcursions(B2BZoneInfo &zones[], int zone_count,
                                              ulong zone_id, double current_price)
  {
   int idx = -1;
   for(int i = 0; i < zone_count; i++)
     {
      if(zones[i].zone_id == zone_id)
        {
         idx = i;
         break;
        }
     }
   
   if(idx < 0 || !zones[idx].was_traded)
      return;
   
   double entry = zones[idx].entry_price;
   if(entry == 0)
      return;
   
   double excursion_points = 0;
   
   if(zones[idx].direction == DIRECTION_BULLISH)
      excursion_points = (current_price - entry) / _Point;
   else
      excursion_points = (entry - current_price) / _Point;
   
   if(excursion_points < 0)
     {
      double adverse = MathAbs(excursion_points);
      if(adverse > zones[idx].max_adverse_excursion)
         zones[idx].max_adverse_excursion = adverse;
     }
   
   if(excursion_points > 0)
     {
      if(excursion_points > zones[idx].max_favorable_excursion)
         zones[idx].max_favorable_excursion = excursion_points;
     }
  }

//+------------------------------------------------------------------+
//| SetZoneTraded - Mark zone level as traded                         |
//+------------------------------------------------------------------+
bool CB2BTradeTracker::SetZoneTraded(B2BZoneInfo &zones[], int zone_count,
                                      ulong zone_id, string level)
  {
   int idx = -1;
   for(int i = 0; i < zone_count; i++)
     {
      if(zones[i].zone_id == zone_id)
        {
         idx = i;
         break;
        }
     }
   
   if(idx < 0)
      return false;
   
   if(level == "L1" || level == "T1")
      zones[idx].L1_traded = true;
   else if(level == "FIFTY" || level == "50" || level == "T2")
      zones[idx].fifty_traded = true;
   else if(level == "L2" || level == "T3")
      zones[idx].L2_traded = true;
   else
      return false;
   
   zones[idx].was_traded = true;
   return true;
  }

//+------------------------------------------------------------------+
//| CalculateRR - Calculate risk:reward ratio                         |
//+------------------------------------------------------------------+
double CB2BTradeTracker::CalculateRR(double entry_price, double sl_price, 
                                      double exit_price, ENUM_SIGNAL_DIRECTION direction)
  {
   double risk = MathAbs(entry_price - sl_price);
   if(risk <= 0)
      return 0;
   
   double reward = 0;
   if(direction == DIRECTION_BULLISH)
      reward = exit_price - entry_price;
   else
      reward = entry_price - exit_price;
   
   return reward / risk;
  }

#endif // V50_B2BTRADETRACKER_MQH
