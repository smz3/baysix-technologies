//+------------------------------------------------------------------+
//|                                          TrailingStopManager.mqh |
//|                             Copyright 2025, Sigma Trading System |
//+------------------------------------------------------------------+
//| V7.0 - Full Break-Even and Trailing Stop Implementation          |
//| Configurable parameters for backtesting optimization             |
//+------------------------------------------------------------------+
#ifndef V70_TRAILINGSTOPMANAGER_MQH
#define V70_TRAILINGSTOPMANAGER_MQH

#property strict

#include <Trade\Trade.mqh>
#include "../Configuration/TradingParameters.mqh"

//+------------------------------------------------------------------+
//| CTrailingStopManager Class                                        |
//| Manages Break-Even and Trailing Stop for open positions          |
//+------------------------------------------------------------------+
class CTrailingStopManager
  {
private:
   CTrade            m_trade;
   bool              m_initialized;
   
   // Track which positions have already been moved to BE
   ulong             m_be_applied_tickets[];
   int               m_be_applied_count;
   
   // V17: Milestone Tracking
   struct TrailingMilestone {
      ulong ticket;
      double next_update_price;
   };
   TrailingMilestone m_milestones[];
   int               m_milestone_count;
   
public:
                     CTrailingStopManager(void);
                    ~CTrailingStopManager(void);

   bool              Initialize();
   void              UpdateAllPositions();  // Main function - call from OnTick
   
private:
   bool              ProcessPosition(ulong ticket);
   bool              ApplyBreakEven(ulong ticket, double entry_price, double current_price, ENUM_POSITION_TYPE pos_type);
   bool              ApplyTrailingStop(ulong ticket, double entry_price, double current_price, double current_sl, ENUM_POSITION_TYPE pos_type);
   bool              ModifySL(ulong ticket, double new_sl);
   bool              IsBEApplied(ulong ticket);
   void              MarkBEApplied(ulong ticket);
   double            GetProfitInPoints(double entry_price, double current_price, ENUM_POSITION_TYPE pos_type);
   
   // V17 Milestone Helpers
   double            GetNextMilestone(ulong ticket);
   void              UpdateMilestone(ulong ticket, double next_price);
   void              InitMilestone(ulong ticket, double entry_price, ENUM_POSITION_TYPE type);
  };

//+------------------------------------------------------------------+
//| Constructor                                                       |
//+------------------------------------------------------------------+
CTrailingStopManager::CTrailingStopManager(void)
  {
   m_initialized = false;
   m_be_applied_count = 0;
   m_milestone_count = 0;
   ArrayResize(m_be_applied_tickets, 0);
   ArrayResize(m_milestones, 0);
  }

//+------------------------------------------------------------------+
//| Destructor                                                        |
//+------------------------------------------------------------------+
CTrailingStopManager::~CTrailingStopManager(void)
  {
   ArrayFree(m_be_applied_tickets);
   ArrayFree(m_milestones);
  }

//+------------------------------------------------------------------+
//| Initialize                                                        |
//+------------------------------------------------------------------+
bool CTrailingStopManager::Initialize()
  {
   m_trade.SetExpertMagicNumber(InpMagicNumber);
   m_trade.SetDeviationInPoints(InpSlippage);
   m_trade.SetTypeFilling(ORDER_FILLING_IOC);
   
   m_initialized = true;
   
   if(InpLogSystem)
     {
      PrintFormat("[TRAIL] Manager Initialized");
      PrintFormat("[TRAIL] BE Enabled: %s | Activation: %.0f pts | Lock-in: %.0f pts",
                  InpEnableBreakEven ? "YES" : "NO",
                  InpBEActivationPoints,
                  InpBELockInPoints);
      PrintFormat("[TRAIL] Trail Enabled: %s | Start: %.0f pts | Step: %.0f pts",
                  InpEnableTrailing ? "YES" : "NO",
                  InpTrailStartPoints,
                  InpTrailStepPoints);
     }
   
   return true;
  }

//+------------------------------------------------------------------+
//| UpdateAllPositions - Call this from OnTick                        |
//+------------------------------------------------------------------+
void CTrailingStopManager::UpdateAllPositions()
  {
   if(!m_initialized)
      return;
   
   // V6.3: Intraday EOD Exit Check
   if(InpEnableIntraday && InpEnableEODExit)
   {
      MqlDateTime dt;
      TimeCurrent(dt);
      string current_time = StringFormat("%02d:%02d", dt.hour, dt.min);
      
      if(current_time >= InpEODExitTime)
      {
         for(int i = PositionsTotal() - 1; i >= 0; i--)
         {
            ulong ticket = PositionGetTicket(i);
            if(ticket == 0) continue;
            if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
            if(PositionGetInteger(POSITION_MAGIC) == InpMagicNumber + 1)
            {
               if(InpLogSystem)
                  PrintFormat("[TRAIL] INTRA EOD EXIT | Ticket #%I64u | Time: %s", ticket, current_time);
               m_trade.PositionClose(ticket);
            }
         }
      }
   }
   
   // Skip if both features are disabled
   if(!InpEnableBreakEven && !InpEnableTrailing)
      return;
   
   // Process all positions with our magic numbers (swing + intraday)
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0)
         continue;
      
      // Check magic number: accept both swing and intraday
      long magic = PositionGetInteger(POSITION_MAGIC);
      if(magic != InpMagicNumber && magic != InpMagicNumber + 1)
         continue;
      
      // Check symbol
      if(PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;
      
      ProcessPosition(ticket);
     }
  }

//+------------------------------------------------------------------+
//| ProcessPosition - Handle BE and Trailing for single position      |
//+------------------------------------------------------------------+
bool CTrailingStopManager::ProcessPosition(ulong ticket)
  {
   if(!PositionSelectByTicket(ticket))
      return false;
   
   double entry_price = PositionGetDouble(POSITION_PRICE_OPEN);
   double current_price = PositionGetDouble(POSITION_PRICE_CURRENT);
   double current_sl = PositionGetDouble(POSITION_SL);
   ENUM_POSITION_TYPE pos_type = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);

   // V17 MILESTONE GATE
   double next_milestone = GetNextMilestone(ticket);
   if(next_milestone == 0) // First time seeing this position
   {
      InitMilestone(ticket, entry_price, pos_type);
      next_milestone = GetNextMilestone(ticket);
   }

   bool breached = (pos_type == POSITION_TYPE_BUY) ? (current_price >= next_milestone) : (current_price <= next_milestone);
   if(!breached) return false; // PHYSICS GATE: Price hasn't crossed the milestone. Do nothing.

   double profit_points = GetProfitInPoints(entry_price, current_price, pos_type);
   
   // STEP 1: Check Break-Even first
   if(InpEnableBreakEven && !IsBEApplied(ticket))
     {
      if(profit_points >= InpBEActivationPoints)
        {
         if(ApplyBreakEven(ticket, entry_price, current_price, pos_type))
           {
            MarkBEApplied(ticket);
            // After BE, set next milestone to Trail Start
            double trail_start_price = (pos_type == POSITION_TYPE_BUY) ? (entry_price + InpTrailStartPoints * _Point) : (entry_price - InpTrailStartPoints * _Point);
            UpdateMilestone(ticket, trail_start_price);
            return true;
           }
        }
     }
   
   // STEP 2: Trailing Stop
   if(InpEnableTrailing)
     {
      if(profit_points >= InpTrailStartPoints)
        {
         if(ApplyTrailingStop(ticket, entry_price, current_price, current_sl, pos_type))
         {
            // Update milestone to next step
            double next_price = (pos_type == POSITION_TYPE_BUY) ? (current_price + InpTrailStepPoints * _Point) : (current_price - InpTrailStepPoints * _Point);
            UpdateMilestone(ticket, next_price);
         }
        }
     }
   
   return true;
  }

//+------------------------------------------------------------------+
//| Milestone Helpers                                                 |
//+------------------------------------------------------------------+
double CTrailingStopManager::GetNextMilestone(ulong ticket)
{
   for(int i=0; i<m_milestone_count; i++)
      if(m_milestones[i].ticket == ticket) return m_milestones[i].next_update_price;
   return 0;
}

void CTrailingStopManager::UpdateMilestone(ulong ticket, double next_price)
{
   for(int i=0; i<m_milestone_count; i++)
   {
      if(m_milestones[i].ticket == ticket)
      {
         m_milestones[i].next_update_price = next_price;
         return;
      }
   }
   // If not found, add it
   m_milestone_count++;
   ArrayResize(m_milestones, m_milestone_count);
   m_milestones[m_milestone_count-1].ticket = ticket;
   m_milestones[m_milestone_count-1].next_update_price = next_price;
}

void CTrailingStopManager::InitMilestone(ulong ticket, double entry_price, ENUM_POSITION_TYPE type)
{
   double first_milestone = 0;
   if(InpEnableBreakEven)
      first_milestone = (type == POSITION_TYPE_BUY) ? (entry_price + InpBEActivationPoints * _Point) : (entry_price - InpBEActivationPoints * _Point);
   else
      first_milestone = (type == POSITION_TYPE_BUY) ? (entry_price + InpTrailStartPoints * _Point) : (entry_price - InpTrailStartPoints * _Point);
   
   UpdateMilestone(ticket, first_milestone);
}

//+------------------------------------------------------------------+
//| GetProfitInPoints - Calculate current profit in points            |
//+------------------------------------------------------------------+
double CTrailingStopManager::GetProfitInPoints(double entry_price, double current_price, ENUM_POSITION_TYPE pos_type)
  {
   double profit = 0.0;
   
   if(pos_type == POSITION_TYPE_BUY)
      profit = (current_price - entry_price) / _Point;
   else
      profit = (entry_price - current_price) / _Point;
   
   return profit;
  }

//+------------------------------------------------------------------+
//| ApplyBreakEven - Move SL to entry + lock-in buffer                |
//+------------------------------------------------------------------+
bool CTrailingStopManager::ApplyBreakEven(ulong ticket, double entry_price, double current_price, ENUM_POSITION_TYPE pos_type)
  {
   double new_sl = 0.0;
   double lock_in_price = InpBELockInPoints * _Point;
   
   if(pos_type == POSITION_TYPE_BUY)
     {
      new_sl = entry_price + lock_in_price;
      // Ensure new SL is below current price
      if(new_sl >= current_price)
         return false;
     }
   else  // SELL
     {
      new_sl = entry_price - lock_in_price;
      // Ensure new SL is above current price
      if(new_sl <= current_price)
         return false;
     }
   
   // Normalize price
   new_sl = NormalizeDouble(new_sl, _Digits);
   
   if(ModifySL(ticket, new_sl))
     {
      if(InpLogSystem)
         PrintFormat("[TRAIL] BE Applied: Ticket #%I64u | Entry: %.5f | New SL: %.5f (+%.0f pts lock-in)",
                     ticket, entry_price, new_sl, InpBELockInPoints);
      return true;
     }
   
   return false;
  }

//+------------------------------------------------------------------+
//| ApplyTrailingStop - Trail SL behind price by step distance        |
//+------------------------------------------------------------------+
bool CTrailingStopManager::ApplyTrailingStop(ulong ticket, double entry_price, double current_price, double current_sl, ENUM_POSITION_TYPE pos_type)
  {
   double trail_distance = InpTrailStepPoints * _Point;
   double new_sl = 0.0;
   
   // OPTIMIZATION: Minimum Modification Step (10 Points) to prevent tick-spamming
   double optimization_step = 10.0 * _Point; 

   if(pos_type == POSITION_TYPE_BUY)
     {
      // For BUY: SL trails below price
      new_sl = current_price - trail_distance;
      
      // Only move if new SL is higher than current SL (lock in more profit)
      if(new_sl <= current_sl)
         return false;
      
      // OPTIMIZATION: Don't modify if change is tiny
      if((new_sl - current_sl) < optimization_step)
         return false;
      
      // Ensure SL is still below current price
      if(new_sl >= current_price)
         return false;
     }
   else  // SELL
     {
      // For SELL: SL trails above price
      new_sl = current_price + trail_distance;
      
      // Only move if new SL is lower than current SL (lock in more profit)
      if(new_sl >= current_sl && current_sl > 0)
         return false;

      // OPTIMIZATION: Don't modify if change is tiny (abs diff)
      if((current_sl > 0) && (current_sl - new_sl) < optimization_step)
         return false;
      
      // Ensure SL is still above current price
      if(new_sl <= current_price)
         return false;
     }
   
   // Normalize price
   new_sl = NormalizeDouble(new_sl, _Digits);
   
   if(ModifySL(ticket, new_sl))
     {
      double locked_profit = GetProfitInPoints(entry_price, new_sl, pos_type);
      if(InpLogSystem)
         PrintFormat("[TRAIL] Trailing Updated: Ticket #%I64u | New SL: %.5f | Locked: %.0f pts",
                     ticket, new_sl, locked_profit);
      return true;
     }
   
   return false;
  }

//+------------------------------------------------------------------+
//| ModifySL - Execute the SL modification                            |
//+------------------------------------------------------------------+
bool CTrailingStopManager::ModifySL(ulong ticket, double new_sl)
  {
   if(!PositionSelectByTicket(ticket))
      return false;
   
   double current_tp = PositionGetDouble(POSITION_TP);
   
   // Use trade object to modify
   if(!m_trade.PositionModify(ticket, new_sl, current_tp))
     {
      if(InpLogSystem)
         PrintFormat("[TRAIL] ERROR: Failed to modify SL. Ticket: %I64u, Error: %d",
                     ticket, GetLastError());
      return false;
     }
   
   return true;
  }

//+------------------------------------------------------------------+
//| IsBEApplied - Check if BE was already applied to this ticket      |
//+------------------------------------------------------------------+
bool CTrailingStopManager::IsBEApplied(ulong ticket)
  {
   for(int i = 0; i < m_be_applied_count; i++)
     {
      if(m_be_applied_tickets[i] == ticket)
         return true;
     }
   return false;
  }

//+------------------------------------------------------------------+
//| MarkBEApplied - Record that BE was applied to this ticket         |
//+------------------------------------------------------------------+
void CTrailingStopManager::MarkBEApplied(ulong ticket)
  {
   m_be_applied_count++;
   ArrayResize(m_be_applied_tickets, m_be_applied_count);
   m_be_applied_tickets[m_be_applied_count - 1] = ticket;
  }

#endif // V70_TRAILINGSTOPMANAGER_MQH
