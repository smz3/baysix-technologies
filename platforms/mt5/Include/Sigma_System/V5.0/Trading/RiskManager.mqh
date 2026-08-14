//+------------------------------------------------------------------+
//|                                                  RiskManager.mqh |
//|                             Copyright 2025, Sigma Trading System |
//+------------------------------------------------------------------+
//| V5.0 Risk Manager - Position Sizing & Risk Control               |
//| Based on V3.2 patterns, simplified for B2B zone trading          |
//+------------------------------------------------------------------+
#ifndef V50_RISKMANAGER_MQH
#define V50_RISKMANAGER_MQH

#property strict

#include "../Common/UniversalSymbolManager.mqh"
#include "../Configuration/TradingParameters.mqh"
#include "../Data/Structures.mqh"
// #include "TradeSignalGenerator.mqh" // REMOVED to break circular dependency

// Global symbol manager instance
// MOVED TO MAIN FILE: CUniversalSymbolManager g_SymbolManager;
extern CUniversalSymbolManager g_SymbolManager;

//+------------------------------------------------------------------+
//| CRiskManager Class                                                |
//| Handles position sizing, margin checks, and risk control          |
//+------------------------------------------------------------------+
class CRiskManager
  {
private:
   double              m_start_of_day_balance;
   bool                m_initialized;
   
public:
                       CRiskManager(void);
                      ~CRiskManager(void);
   
   bool                Initialize();
   
   // === CORE POSITION SIZING ===
   double              CalculateRiskBasedLot(const TradeSignalInfo &signal);
   double              NormalizeLotSize(double lot_size);
   
   // === RISK CHECKS ===
   bool                CanOpenNewPosition();
   double              GetCurrentMarginLevel();
   int                 GetCurrentPositionCount();
   
   // === ACCOUNT INFO ===
   void                UpdateDailyBalance();
   double              GetAccountBalance();
   double              GetAccountEquity();
   double              GetFreeMargin();
   double              GetAccountLeverage();
   
   // === DISPLAY ===
   string              GetPositionSummary();
   string              GetMarginLevelDisplay();
   void                PrintAccountInfo();
  };

//+------------------------------------------------------------------+
//| Constructor                                                       |
//+------------------------------------------------------------------+
CRiskManager::CRiskManager(void)
  {
   m_start_of_day_balance = 0.0;
   m_initialized = false;
  }

//+------------------------------------------------------------------+
//| Destructor                                                        |
//+------------------------------------------------------------------+
CRiskManager::~CRiskManager(void)
  {
  }

//+------------------------------------------------------------------+
//| Initialize                                                        |
//+------------------------------------------------------------------+
bool CRiskManager::Initialize()
  {
   if(m_initialized)
      return true;
   
   // Initialize symbol manager
   if(!g_SymbolManager.Initialize())
     {
      Print("[RISK] Failed to initialize SymbolManager");
      return false;
     }
   
   // Analyze current symbol
   if(!g_SymbolManager.AnalyzeSymbol(_Symbol))
     {
      Print("[RISK] Failed to analyze symbol: ", _Symbol);
      return false;
     }
   
   // Store starting balance
   m_start_of_day_balance = AccountInfoDouble(ACCOUNT_BALANCE);
   
   m_initialized = true;
   
   // Print account info on initialization
   PrintAccountInfo();
   
   return true;
  }

//+------------------------------------------------------------------+
//| Print Account Information                                         |
//+------------------------------------------------------------------+
void CRiskManager::PrintAccountInfo()
  {
   SymbolInfo symbol_info = g_SymbolManager.GetSymbolInfo(_Symbol);
   
   Print("=== ACCOUNT INFO ===");
   PrintFormat("  Balance: %.2f %s", GetAccountBalance(), AccountInfoString(ACCOUNT_CURRENCY));
   PrintFormat("  Equity: %.2f", GetAccountEquity());
   PrintFormat("  Free Margin: %.2f", GetFreeMargin());
   PrintFormat("  Leverage: 1:%.0f", GetAccountLeverage());
   PrintFormat("  Margin Level: %s", GetMarginLevelDisplay());
   Print("=== SYMBOL INFO ===");
   PrintFormat("  Symbol: %s", _Symbol);
   PrintFormat("  Type: %s", g_SymbolManager.GetSymbolTypeString(symbol_info.symbol_type));
   PrintFormat("  Pip Size: %.5f", symbol_info.pip_size);
   PrintFormat("  Pip Value/Lot: %.4f", symbol_info.pip_value_per_lot);
   PrintFormat("  Min Lot: %.2f | Max Lot: %.2f | Step: %.2f", 
              symbol_info.min_lot, symbol_info.max_lot, symbol_info.lot_step);
   Print("====================");
  }

//+------------------------------------------------------------------+
//| Calculate Risk-Based Lot Size                                     |
//| Formula: Risk Amount / (SL Distance in Pips * Pip Value Per Lot)  |
//+------------------------------------------------------------------+
double CRiskManager::CalculateRiskBasedLot(const TradeSignalInfo &signal)
  {
   if(!signal.is_valid)
     {
      Print("[RISK] Invalid signal - cannot calculate lot size");
      return 0.0;
     }
   
   // === STEP 1: Calculate Risk Amount ===
   if(signal.position_pct <= 0.001)
     {
      // If allocation is 0%, do not trade (even min lot)
      return 0.0;
     }

   // === STEP 1: Calculate Risk Amount based on Signal Type ===
   double balance = GetAccountBalance();
   double risk_percent = 0.0;
   
   double allocation_pct = 0.0;
   
   if(signal.signal_type == SIGNAL_ENTRY_L1) allocation_pct = InpAllocation_T1;
   else if(signal.signal_type == SIGNAL_ENTRY_50) allocation_pct = InpAllocation_T2;
   else if(signal.signal_type == SIGNAL_ENTRY_L2) allocation_pct = InpAllocation_T3;
   else {
      // Default fallback (should not happen if signal valid)
      Print("[RISK] Unknown signal type, defaulting to T1 allocation");
      allocation_pct = InpAllocation_T1; 
   }

   // V6.3: Use Intraday Risk logic if the signal comes from IntradayOrchestrator
   double base_risk = InpBaseRisk;
   if(signal.is_intraday)
   {
      // Specific intraday percentage (often wider stops, so less risk logic vs swing logic might apply, but default we respect the setting)
      base_risk = InpDayTradeRiskPct;
   }
   else if(signal.parent_tf == PERIOD_H4)
   {
      base_risk = InpDayTradeRiskPct;
   }
   
   risk_percent = base_risk * allocation_pct;
   
   // === PHASE DELTA_1: PRECISION RISK SCALING ===
   // V5.2 Update: Structural scaling is now centralized in TradeSignalGenerator 
   // via signal.position_pct for maximum user configurability.
   
   // Safety Cap: Lifted to 10% to support user's high-risk mining tests
   if(risk_percent > 10.0) risk_percent = 10.0;

   double risk_amount = balance * (risk_percent / 100.0);
   
   // Apply scale-in factor (if scale-in enabled, each entry is partial)
   double position_factor = signal.position_pct / 100.0;
   risk_amount *= position_factor;
   
   // === STEP 2: Get SL Distance in Pips ===
   SymbolInfo symbol_info = g_SymbolManager.GetSymbolInfo(_Symbol);
   if(!symbol_info.is_valid)
     {
      Print("[RISK] Invalid symbol info - cannot calculate lot size");
      return 0.0;
     }
   
   // SL distance in points is already in signal
   double sl_distance_points = signal.sl_distance_points;
   
   // Convert points to pips (for forex, 10 points = 1 pip typically)
   // For Gold (XAUUSD), pip_size is 0.1, point is 0.01, so 10 points = 1 pip
   double pip_size = symbol_info.pip_size;
   if(pip_size == 0.0) pip_size = _Point; // Safety definition for non-forex
   
   double sl_distance_pips = sl_distance_points * (_Point / pip_size);
   
   if(sl_distance_pips <= 0.0)
     {
      PrintFormat("[RISK] Invalid SL distance: %.1f points (%.2f pips) | PipSize: %.5f", 
                 sl_distance_points, sl_distance_pips, pip_size);
      return 0.0;
     }
   
   // === STEP 3: Get Pip Value Per Lot ===
   double pip_value = symbol_info.pip_value_per_lot;
   if(pip_value <= 0.0)
     {
      Print("[RISK] Invalid pip value - cannot calculate lot size");
      return 0.0;
     }
   
   // === STEP 4: Calculate Lot Size ===
   double calculation_sl_pips = sl_distance_pips;
   
   // SAFETY: Clamp SL distance to minimum 5 pips for calculation
   // This prevents massive lot sizes when price is extremely close to SL (e.g. 0.5 pips)
   if(calculation_sl_pips < 5.0)
     {
      PrintFormat("[RISK] ⚠️ SL distance %.1f pips is too tight! Clamping to 5.0 pips for safety.", calculation_sl_pips);
      calculation_sl_pips = 5.0;
     }

   double lot_size = risk_amount / (calculation_sl_pips * pip_value);
   
   // DEBUG: Verbose Print for Quant Audit
   // PrintFormat("[RISK AUDIT] Zone #%I64u | Risk$: %.2f | SL Pips: %.1f | PipVal: %.2f | RawLot: %.2f",
   //             signal.zone_id, risk_amount, calculation_sl_pips, pip_value, lot_size);
   
   // === STEP 5: Apply Max Lots Limit ===
   if(lot_size > InpMaxLotsPerTrade)
     {
      PrintFormat("[RISK] Lot size %.2f exceeds max %.2f - capping", lot_size, InpMaxLotsPerTrade);
      lot_size = InpMaxLotsPerTrade;
     }
   
   // === STEP 6: Normalize to Broker Constraints ===
   if(lot_size > 0)
      lot_size = NormalizeLotSize(lot_size);
   
   // === STEP 7: Final Validation ===
   if(lot_size > 0 && lot_size < symbol_info.min_lot)
     {
      PrintFormat("[RISK] Lot size %.4f below minimum %.2f - rejected", lot_size, symbol_info.min_lot);
      return 0.0;
     }
   
   // === STEP 8: Logging ===
   if(InpLogSystem)
     {
      string dir_str = (signal.direction == DIRECTION_BULLISH) ? "BUY" : "SELL";
      PrintFormat("[RISK] %s | Risk: %.2f%% ($%.2f) | SL: %.1f pips (Calc: %.1f) | PipVal: %.2f | Lot: %.2f",
                 dir_str, risk_percent, risk_amount,
                 sl_distance_pips, calculation_sl_pips, pip_value, lot_size);
     }
   
   return lot_size;
  }

//+------------------------------------------------------------------+
//| Normalize Lot Size to Broker Constraints                          |
//+------------------------------------------------------------------+
double CRiskManager::NormalizeLotSize(double lot_size)
  {
   double min_lot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double max_lot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double lot_step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   
   // Ensure minimum (only if not a block signal)
   double normalized = lot_size;
   if(lot_size > 0)
      normalized = MathMax(lot_size, min_lot);
   
   // Ensure maximum
   normalized = MathMin(normalized, max_lot);
   
   // Round to lot step
   if(lot_step > 0.0)
      normalized = MathRound(normalized / lot_step) * lot_step;
   
   return NormalizeDouble(normalized, 2);
  }

//+------------------------------------------------------------------+
//| Check if New Position Can Be Opened                               |
//+------------------------------------------------------------------+
bool CRiskManager::CanOpenNewPosition()
  {
   // Check 1: Position count limit
   int current_positions = GetCurrentPositionCount();
   
   if(current_positions >= InpMaxOpenPositions)
     {
      PrintFormat("[RISK] Position limit reached: %d/%d", current_positions, InpMaxOpenPositions);
      return false;
     }
   
   // Check 2: Margin level check (skip if no positions)
   if(current_positions > 0)
     {
      double margin_level = GetCurrentMarginLevel();
      
      if(margin_level > 0.0 && margin_level < InpMinMarginLevel)
        {
         PrintFormat("[RISK] Margin level too low: %.1f%% (min: %.1f%%)", margin_level, InpMinMarginLevel);
         return false;
        }
     }
   
   // Check 3: Free margin check
   double free_margin = GetFreeMargin();
   if(free_margin <= 0.0)
     {
      Print("[RISK] No free margin available");
      return false;
     }
   
   return true;
  }

//+------------------------------------------------------------------+
//| Get Current Margin Level                                          |
//+------------------------------------------------------------------+
double CRiskManager::GetCurrentMarginLevel()
  {
   return AccountInfoDouble(ACCOUNT_MARGIN_LEVEL);
  }

//+------------------------------------------------------------------+
//| Get Current Position Count                                        |
//+------------------------------------------------------------------+
int CRiskManager::GetCurrentPositionCount()
  {
   return PositionsTotal();
  }

//+------------------------------------------------------------------+
//| Update Daily Balance (call at start of each day)                  |
//+------------------------------------------------------------------+
void CRiskManager::UpdateDailyBalance()
  {
   datetime current_time = TimeCurrent();
   static datetime last_update = 0;
   
   MqlDateTime dt_current, dt_last;
   TimeToStruct(current_time, dt_current);
   TimeToStruct(last_update, dt_last);
   
   if(dt_current.day != dt_last.day || last_update == 0)
     {
      m_start_of_day_balance = AccountInfoDouble(ACCOUNT_BALANCE);
      last_update = current_time;
      
      if(InpLogSystem)
         PrintFormat("[RISK] New day - Starting balance: %.2f", m_start_of_day_balance);
     }
  }

//+------------------------------------------------------------------+
//| Get Account Balance                                               |
//+------------------------------------------------------------------+
double CRiskManager::GetAccountBalance()
  {
   return AccountInfoDouble(ACCOUNT_BALANCE);
  }

//+------------------------------------------------------------------+
//| Get Account Equity                                                |
//+------------------------------------------------------------------+
double CRiskManager::GetAccountEquity()
  {
   return AccountInfoDouble(ACCOUNT_EQUITY);
  }

//+------------------------------------------------------------------+
//| Get Free Margin                                                   |
//+------------------------------------------------------------------+
double CRiskManager::GetFreeMargin()
  {
   return AccountInfoDouble(ACCOUNT_MARGIN_FREE);
  }

//+------------------------------------------------------------------+
//| Get Account Leverage                                              |
//+------------------------------------------------------------------+
double CRiskManager::GetAccountLeverage()
  {
   return (double)AccountInfoInteger(ACCOUNT_LEVERAGE);
  }

//+------------------------------------------------------------------+
//| Get Position Summary                                              |
//+------------------------------------------------------------------+
string CRiskManager::GetPositionSummary()
  {
   return StringFormat("%d positions", GetCurrentPositionCount());
  }

//+------------------------------------------------------------------+
//| Get Margin Level Display                                          |
//+------------------------------------------------------------------+
string CRiskManager::GetMarginLevelDisplay()
  {
   double margin_level = GetCurrentMarginLevel();
   
   if(margin_level <= 0.0)
      return "N/A";
   
   return StringFormat("%.1f%%", margin_level);
  }

#endif // V50_RISKMANAGER_MQH
