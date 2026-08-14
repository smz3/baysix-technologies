//+------------------------------------------------------------------+
//|                                                 OrderManager.mqh |
//|                             Copyright 2025, Sigma Trading System |
//+------------------------------------------------------------------+
//| V5.0 SNIPER PROTOCOL (Refactored Phase 3)                        |
//| Simplified Execution Engine for B2B Market Flow                    |
//| "One Shot, One Kill" - Strict 1 Trade Per Flow Policy            |
//+------------------------------------------------------------------+
#ifndef V50_ORDERMANAGER_MQH
#define V50_ORDERMANAGER_MQH

#property strict

#include <Trade\Trade.mqh>
#include "../Configuration/TradingParameters.mqh"
#include "TradeSignalGenerator.mqh"
// #include "RiskManager.mqh"
// Risk logic handled by RiskManager or simplified here. OrderManager just EXECUTES. 

//=== V6.0: Quant Logger for Supabase CSV Export ===
#include <Sigma_System/V5.0/Data/QuantLogger.mqh>
#include <Sigma_System/V5.0/Data/Structures.mqh>
#include <Sigma_System/V5.0/Analysis/MetricCalculator.mqh>  // V11.2: Statistical Anchors

// External reference to QuantLogger
extern CQuantLogger g_QuantLogger;

// V8: Access to global Signal Generator for logic snapshots
// extern CTradeSignalGenerator g_SignalGenerator; // REMOVED to break circular dependency

// ShadowTrade struct removed

//+------------------------------------------------------------------+
//| COrderManager Class (Sniper Protocol)                             |
//+------------------------------------------------------------------+
class COrderManager
  {
private:
   CTrade              m_trade;
   bool                m_initialized;
   
   // Safety: Track active Zone IDs to prevent spam (Cache)
   // Using a simple array of active ticket IDs or Zone IDs
   // For now, we query PositionsTotal() which is robust but slightly slower.
   // Given 15% window, speed is okay.
   
   // Shadow buffers removed
   
   bool                IsWithinChaosWindow(datetime time_val); // Phase Beta 1
   
public:
                       COrderManager(void);
                      ~COrderManager(void);
   
   bool                Initialize();
   
   // === CORE EXECUTION ===
   // Receives a fully validated, risk-calculated signal
   bool                ExecuteSignal(const TradeSignalInfo &signal, double lot_size);

   // --- SURVIVAL PROTOCOL ---
   bool                PassesSurvivalGate(const TradeSignalInfo &signal);
   bool                IsWithinSurvivalSession(datetime time);
   
   // Shadow methods removed
   
   // === SAFETY CHECKS ===
   bool                TradeExistsForZone(ulong zone_id, ENUM_TRADE_SIGNAL_TYPE tier);
   void                SetMagicNumber(int magic) { m_trade.SetExpertMagicNumber(magic); }
   
   // === UTILITIES ===
   void                CloseAllTrades(); // For panic/reset
   bool                CloseAllPositions(); // Compatibility
   int                 GetOpenPositionCount(); // Compatibility
   
   // Compatibility Helpers
   bool                ModifyPosition(ulong ticket, double sl, double tp);
   bool                ClosePosition(ulong ticket);
   int                 ForceCloseByDirection(ENUM_SIGNAL_DIRECTION dir);
   
   // EOD Control
   void                CheckEODExit();
   
   
   string              GetLastError();
  };

//+------------------------------------------------------------------+
//| Constructor                                                       |
//+------------------------------------------------------------------+
COrderManager::COrderManager(void) : m_initialized(false)
  {
  }

//+------------------------------------------------------------------+
//| Destructor                                                        |
//+------------------------------------------------------------------+
COrderManager::~COrderManager(void)
  {
  }

//+------------------------------------------------------------------+
//| Initialize                                                        |
//+------------------------------------------------------------------+
bool COrderManager::Initialize()
  {
   if(m_initialized) return true;
   
   // Configure CTrade
   m_trade.SetExpertMagicNumber(InpMagicNumber);
   m_trade.SetDeviationInPoints(InpSlippage);
   m_trade.SetTypeFilling(ORDER_FILLING_IOC);
   m_trade.SetAsyncMode(false); // Synchronous for safety
   
   m_initialized = true;
   Print("[SNIPER] Order Manager Initialized (Clean Protocol)");
   return true;
  }

//+------------------------------------------------------------------+
//| Check if trade exists for Zone ID                                 |
//| Scans open positions for comment containing "T{zone_id}"          |
//+------------------------------------------------------------------+
//+------------------------------------------------------------------+
//| Check if trade exists for Zone ID                                 |
//| Scans open positions for "#{ID}_" and Tier Code                   |
//+------------------------------------------------------------------+
bool COrderManager::TradeExistsForZone(ulong zone_id, ENUM_TRADE_SIGNAL_TYPE tier)
  {
   int total = PositionsTotal();
   
   // V5.2 FIX: Universal ID Marker "#{ID}_"
   // New Format: "M30#3352_T1..." -> Contains "#3352_"
   // Old Format: "..._#3352_..."  -> Contains "#3352_"
   string marker_universal = StringFormat("#%04I64u_", zone_id % 10000);

   // Tier Marker
   string tier_str = "";
   if(tier == SIGNAL_ENTRY_L1) tier_str = "_T1";
   else if(tier == SIGNAL_ENTRY_50) tier_str = "_T2";
   else if(tier == SIGNAL_ENTRY_L2) tier_str = "_T3";
   
   // DEBUG: Print what we are looking for
   // PrintFormat("[DEBUG] Checking Zone %I64u | Marker: '%s' | Tier: '%s'", zone_id, marker_universal, tier_str);
   
   for(int i = 0; i < total; i++)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      
      if(PositionGetInteger(POSITION_MAGIC) != InpMagicNumber) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      
      string comment = PositionGetString(POSITION_COMMENT);
      
      // Check 1: ID Match
      if(StringFind(comment, marker_universal) >= 0)
        {
         // Check 2: Tier Match (Critical for Stacking)
         if(tier_str != "")
           {
            // Must contain Tier Marker (e.g. "_T1")
            if(StringFind(comment, tier_str) >= 0)
               return true; 
           }
         else
           {
            // No tier specified implies global block for this ID
            return true; 
           }
        }
     }
   return false;
  }

//+------------------------------------------------------------------+
//| Execute Signal (Sniper Entry)                                     |
//+------------------------------------------------------------------+
bool COrderManager::ExecuteSignal(const TradeSignalInfo &signal, double lot_size)
  {

   if(!InpEnableOrderExecution) return false;
   if(lot_size <= 0.0) 
   {
      if(InpLogTrading)
         PrintFormat("[ORDER] ⚠️ Signal REJECTED: Invalid Lot Size (0.00). Check RiskManager settings or account balance.");
      return false; // Rejected by RiskManager
   }
   
   // --- SURVIVAL GATE (Live Trading Only) ---
   // We only take the "Alpha" trades to ensure the backtest survives 3 years.
   // Filters: No Asian Session, Min Vector Sum >= 3.
   if(!PassesSurvivalGate(signal))
     {
      // Signal logged to CSV by ShadowLog above, but rejected for Live execution.
      return false;
     }

   // 1. DUPLICATE CHECK (The Spam Blocker)
   if(TradeExistsForZone(signal.zone_id, signal.signal_type))
     {
      return false; 
     }

   // 2. Prepare execution
   double price = 0.0;
   double sl = signal.stop_loss;
   double tp = signal.take_profit;
   
   // V5.2 FIX: USER REQUESTED FORMAT : "{TF}#{TrapID}_{Tier}_{ParentTF}#{AnchorID}#{OutpostID}"
   
   // 1. Trap TF & ID
   string tf_str = EnumToString(signal.zone_tf);
   StringReplace(tf_str, "PERIOD_", ""); // M30
   string trap_part = StringFormat("%s#%04I64u", tf_str, signal.zone_id % 10000);
   
   // 2. Tier
   string tier_marker = "_T0";
   string trigger_label = "UNKNOWN";
   if(signal.signal_type == SIGNAL_ENTRY_L1) { tier_marker = "_T1"; trigger_label = "T1_PROBE"; }
   else if(signal.signal_type == SIGNAL_ENTRY_50) { tier_marker = "_T2"; trigger_label = "T2_PRIME"; }
   else if(signal.signal_type == SIGNAL_ENTRY_L2) { tier_marker = "_T3"; trigger_label = "T3_SNIPER"; }
   
   // 3. Parent TF
   string parent_str = "XX";
   if(signal.parent_tf == PERIOD_D1) parent_str = "D1";
   else if(signal.parent_tf == PERIOD_W1) parent_str = "W1";
   else if(signal.parent_tf == PERIOD_MN1) parent_str = "MN"; // Shorten MN1 to MN
   
   string parent_part = StringFormat("_%s", parent_str);
   
   // 4. Anchor & Outpost IDs
   string flow_ids = "";
   if(signal.is_with_trend)
   {
      if(signal.outpost_id > 0) // Forward Outpost Active
         flow_ids = StringFormat("#%04I64u#%04I64u", signal.anchor_id % 10000, signal.outpost_id % 10000);
      else
         flow_ids = StringFormat("#%04I64u", signal.anchor_id % 10000);
   }
   else
   {
      // CT flow usually against Magnet
      flow_ids = StringFormat("#%04I64u", signal.outpost_id % 10000);
   }
   
   // Combine: M30#3352_T1_D1#2862#6595
   string comment = trap_part + tier_marker + parent_part + flow_ids;
   
   // Safety Truncate
   if(StringLen(comment) > 31) comment = StringSubstr(comment, 0, 31);
   
   bool result = false;
   
   // 3. Fire
   string dir_str = (signal.direction == DIRECTION_BULLISH) ? "BUY" : "SELL";
   
   if(signal.direction == DIRECTION_BULLISH)
     {
      price = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      result = m_trade.Buy(lot_size, _Symbol, price, sl, tp, comment);
     }
   else
     {
      price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      result = m_trade.Sell(lot_size, _Symbol, price, sl, tp, comment);
     }
     
   // 4. Log Outcome
   if(result)
     {
      ulong ticket = m_trade.ResultOrder();
      
      // Calculate Execution Count (Simulated for log - Logic would involve scanning history, simplified here)
      // For now, we just log the tier execution.
      string exec_id = "1/1"; // Default single shot per tier
      
      if(InpLogTrading)
         PrintFormat("[SNIPER] ⚡ EXECUTION VERIFIED | Ticket: %I64u | %s %.2f lots | Zone %d | Trigger: %s | Count: %s", 
                     ticket, dir_str, lot_size, signal.zone_id, trigger_label, exec_id);
                  
      // Export to Quant (Crucial for Analysis)
      QuantTradeExport q_trade;
      q_trade.mae_points = 0.0;
      q_trade.mfe_points = 0.0;
      q_trade.edge_ratio = 0.0;
      q_trade.ticket = (long)ticket;
      q_trade.symbol = _Symbol;
      q_trade.direction = dir_str;
      q_trade.entry_time = TimeCurrent();
      q_trade.entry_price = m_trade.ResultPrice(); // Actual fill price
      string trigger_type = "UNKNOWN";
      if(signal.signal_type == SIGNAL_ENTRY_L1) trigger_type = "T1_PROBE";
      else if(signal.signal_type == SIGNAL_ENTRY_50) trigger_type = "T2_PRIME";
      else if(signal.signal_type == SIGNAL_ENTRY_L2) trigger_type = "T3_SNIPER";
      
      q_trade.entry_trigger = trigger_type;
      q_trade.sl_price = sl;
      q_trade.tp_price = tp;
      q_trade.lot_size = lot_size;
      q_trade.zone_id = (string)signal.zone_id;
      q_trade.zone_tf = EnumToString(signal.zone_tf);
      q_trade.zone_age_bars = signal.zone_age_bars; // DEBUG FIX
      q_trade.vector_signature = signal.vector_signature; // V8: 5-TF Vector
      q_trade.vector_sum = signal.vector_sum;             // V5.0: Explicit Sum
      
      q_trade.sl_distance_points = MathAbs(q_trade.entry_price - q_trade.sl_price) / _Point;
      q_trade.atr_at_entry = signal.atr_at_entry;
      q_trade.fractal_depth = signal.fractal_depth;
      q_trade.cascade_score = signal.cascade_score;
      q_trade.d1_aligned = signal.d1_aligned; // Phase Delta 3
      
      // Values removed in purge
      q_trade.buy_votes = signal.buy_votes;
      q_trade.sell_votes = signal.sell_votes;
      
      // Russian Doll Protocol (V12)
      q_trade.layer_1_tide = signal.layer_1_tide;
      q_trade.layer_2_wind = signal.layer_2_wind;
      q_trade.layer_3_trap = signal.layer_3_trap;
      q_trade.layer_4_trigger = signal.layer_4_trigger;
      
      q_trade.anchor_id = signal.anchor_id;
      q_trade.outpost_id = signal.outpost_id;
      q_trade.bridge_state = signal.bridge_state;
    
      // Gamma REMOVED
      // q_trade.roadblock_id = (string)signal.roadblock_id;
      // q_trade.roadblock_dist = signal.roadblock_dist;
      // q_trade.elasticity = signal.elasticity;
      // q_trade.beta_elasticity = signal.beta_thresh;
      // q_trade.gamma_elasticity = signal.gamma_thresh;

      q_trade.narrative_conflict_blocked = signal.is_narrative_conflict;
      
      // Context - REMOVED
      q_trade.zone_rel_pos = 0.0;
        
      // Time Context
      MqlDateTime dt;
      TimeToStruct(q_trade.entry_time, dt);
      q_trade.day_of_week = dt.day_of_week;
      q_trade.hour_of_day = dt.hour;
      q_trade.session = CQuantLogger::GetTradingSession(q_trade.entry_time);
      
    
    // Quantum Audit V2: Execution Type
      
      // Quantum Audit V2: Risk & Capital Foundation
      q_trade.base_risk_pct = InpBaseRisk;
      // Touch risk based on tier
      if(signal.signal_type == SIGNAL_ENTRY_L1) 
         q_trade.touch_risk_pct = InpBaseRisk * (InpAllocation_T1 / 100.0);
      else if(signal.signal_type == SIGNAL_ENTRY_50)
         q_trade.touch_risk_pct = InpBaseRisk * (InpAllocation_T2 / 100.0);
      else if(signal.signal_type == SIGNAL_ENTRY_L2)
         q_trade.touch_risk_pct = InpBaseRisk * (InpAllocation_T3 / 100.0);
      else
         q_trade.touch_risk_pct = InpBaseRisk;
      q_trade.leverage = (int)AccountInfoInteger(ACCOUNT_LEVERAGE);
      q_trade.capital_at_entry = AccountInfoDouble(ACCOUNT_BALANCE);
      
      // Quantum Audit V2: Trade Management (initialized, updated on exit)
      q_trade.trailing_sl_locked_pts = 0.0;
      q_trade.be_activated = false;
      
         
      g_QuantLogger.LogTrade(q_trade);
     }
   else
     {
      PrintFormat("[SNIPER] ❌ EXECUTION FAILED | Error: %d - %s", m_trade.ResultRetcode(), m_trade.ResultRetcodeDescription());
     }
     
   return result;
  }

//+------------------------------------------------------------------+
//| Shadow Log - Capture signal metadata without live execution      |
//+------------------------------------------------------------------+
// ShadowLog implementation removed

//+------------------------------------------------------------------+
//| Utilities                                                         |
//+------------------------------------------------------------------+
void COrderManager::CloseAllTrades()
  {
   // Use new compatibility wrapper
   CloseAllPositions();
  }

//+------------------------------------------------------------------+
//| Compatibility: Close All Positions                                |
//+------------------------------------------------------------------+
bool COrderManager::CloseAllPositions()
  {
   int total = PositionsTotal();
   int closed = 0;
   
   for(int i = total - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      
      // Only close positions with our magic number
      if(PositionGetInteger(POSITION_MAGIC) != InpMagicNumber) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      
      if(m_trade.PositionClose(ticket))
         closed++;
     }
   
   PrintFormat("[ORDER] Closed %d positions", closed);
   return (closed > 0);
  }

//+------------------------------------------------------------------+
//| Get Open Position Count                                           |
//+------------------------------------------------------------------+
int COrderManager::GetOpenPositionCount()
  {
   int count = 0;
   int total = PositionsTotal();
   
   for(int i = 0; i < total; i++)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      
      if(PositionGetInteger(POSITION_MAGIC) == InpMagicNumber &&
         PositionGetString(POSITION_SYMBOL) == _Symbol)
        {
         count++;
        }
     }
   
   return count;
  }

//+------------------------------------------------------------------+
//| Modify Position Wrapper                                          |
//+------------------------------------------------------------------+
bool COrderManager::ModifyPosition(ulong ticket, double sl, double tp)
  {
   if(!m_initialized) return false;
   return m_trade.PositionModify(ticket, sl, tp);
  }

//+------------------------------------------------------------------+
//| Close Position Wrapper                                           |
//+------------------------------------------------------------------+
bool COrderManager::ClosePosition(ulong ticket)
  {
   if(!m_initialized) return false;
   return m_trade.PositionClose(ticket);
  }

//+------------------------------------------------------------------+
//| Force Close By Direction                                         |
//+------------------------------------------------------------------+
int COrderManager::ForceCloseByDirection(ENUM_SIGNAL_DIRECTION dir)
  {
   int total = PositionsTotal();
   int closed = 0;
   ENUM_POSITION_TYPE target_type = (dir == DIRECTION_BULLISH) ? POSITION_TYPE_BUY : POSITION_TYPE_SELL;
   
   for(int i = total - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      
      if(PositionGetInteger(POSITION_MAGIC) != InpMagicNumber) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      
      if((ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE) == target_type)
        {
         if(m_trade.PositionClose(ticket))
            closed++;
        }
     }
   
   if(closed > 0)
     PrintFormat("[ORDER] Force Closed %d %s positions", closed, EnumToString(dir));
     
   return closed;
  }


string COrderManager::GetLastError()
  {
   return m_trade.ResultRetcodeDescription();
  }

//+------------------------------------------------------------------+
//| UpdateShadowExits - Simulates Trade Management for Shadow Trades  |
//+------------------------------------------------------------------+
// UpdateShadowExits implementation removed

//+------------------------------------------------------------------+
//| Passes Survival Gate (Live Execution Only)                        |
//+------------------------------------------------------------------+
bool COrderManager::PassesSurvivalGate(const TradeSignalInfo &signal)
  {
   if(!InpEnableSurvivalGate) return true; // Gate is open

   // 1. TIER REJECTION (L1 Probe is Toxic - Block from Live unless overridden)
   if(signal.signal_type == SIGNAL_ENTRY_L1 && !InpSurvivalAllowT1) return false;

   // 2. SESSION REJECTION (Exclude Asian Session Noise from Live Trades)
   if(!IsWithinSurvivalSession(TimeCurrent())) return false;


   return true;
  }


//+------------------------------------------------------------------+
//| IsWithinSurvivalSession (Configurable Window)                    |
//+------------------------------------------------------------------+
bool COrderManager::IsWithinSurvivalSession(datetime time_val)
  {
   MqlDateTime dt;
   TimeToStruct(time_val, dt);
   
   string current_time = StringFormat("%02d:%02d", dt.hour, dt.min);
   
   if (InpSurvivalSessionStart < InpSurvivalSessionEnd)
     {
      return (current_time >= InpSurvivalSessionStart && current_time <= InpSurvivalSessionEnd);
     }
   else // Overnight window
     {
      return (current_time >= InpSurvivalSessionStart || current_time <= InpSurvivalSessionEnd);
     }
  }

//+------------------------------------------------------------------+
//| CheckEODExit - Hard session reset                                |
//+------------------------------------------------------------------+
void COrderManager::CheckEODExit()
{
   if(!InpEnableEODExit) return;
   
   MqlDateTime dt;
   TimeCurrent(dt);
   string current_time = StringFormat("%02d:%02d", dt.hour, dt.min);
   
   if(current_time >= InpEODExitTime)
   {
      if(PositionsTotal() > 0)
      {
         if(InpLogTrading)
            PrintFormat("[SNIPER] ⏰ EOD EXIT TRIGGERED (%s) | Closing all live positions", current_time);
         CloseAllPositions();
      }
   }
}

//+------------------------------------------------------------------+
//| CloseAllShadowTrades - Force close all virtual trackers            |
//+------------------------------------------------------------------+
// CloseAllShadowTrades removed


#endif // V50_ORDERMANAGER_MQH
