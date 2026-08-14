//+------------------------------------------------------------------+
//|                                         TradeSignalGenerator.mqh |
//|                             Copyright 2025, Sigma Trading System |
//+------------------------------------------------------------------+
#property strict

#include "../Common/Defines.mqh"
// #include "../Common/Logger.mqh" // REMOVED
#include "../Data/Structures.mqh"
#include "../Detection/B2BDetector.mqh"
#include "../Detection/SwingPointDetector.mqh"
#include "../Detection/RawBreakoutDetector.mqh"
#include "../Configuration/TradingParameters.mqh"
#include "../Trading/OrderManager.mqh" // [NEW] Link to Execution
#include "StrategyOrchestrator.mqh" // [NEW] Russian Doll Engine
#include "ContextMapper.mqh"        // [V6.3] Shared Map
#include "IntradayOrchestrator.mqh" // [V6.3] Intraday Engine
#include "RiskManager.mqh"          // [NEW] For sizing

class CRiskManager; // Forward declaration

class CTradeSignalGenerator
{
private:
   //--- Dependencies
   CB2BDetector*     m_b2b_detector;
   CSwingPointDetector* m_swing_detector;
   CRawBreakoutDetector* m_breakout_detector;
   COrderManager*    m_order_manager;
   CStrategyOrchestrator* m_orchestrator;
   CRiskManager*     m_risk_manager;
   
   //--- V6.3: Owned instances
   CContextMapper*          m_context_mapper;
   CIntradayOrchestrator*   m_intraday;
   
   //--- State
   datetime          m_last_check_time;
   ulong             m_last_logged_zone_id; // V18.2: Logging Muzzle
   
public:
                     CTradeSignalGenerator();
                    ~CTradeSignalGenerator();

   void              Initialize(CB2BDetector* b2b, CSwingPointDetector* swing, CRawBreakoutDetector* bo, COrderManager* om, CRiskManager* rm);
   
   // V13: Performance Gating
   void              SetDirty(bool dirty) { if(m_orchestrator) m_orchestrator.SetDirty(dirty); }
   
   // Main Tick Entry
   void              OnTick(double current_price, datetime current_time, double ask, double bid, B2BZoneInfo &zones[], int total_zones, int change_mask = 0);

private:
   void              ProcessRussianDollStrategy(double current_price, double ask, double bid, B2BZoneInfo &zones[], int total_zones);
   void              ProcessIntradayStrategy(double current_price, double ask, double bid, B2BZoneInfo &zones[], int total_zones);
   bool              SendTradeSignal(ENUM_TRADE_SIGNAL_TYPE sig_type, ENUM_SIGNAL_DIRECTION dir, double price, double sl, double tp, string comment, const B2BZoneInfo &zone, ulong anchor_id, ulong outpost_id, bool is_with_trend, ENUM_TIMEFRAMES parent_tf, bool is_intraday = false);
};

//+------------------------------------------------------------------+
//| Constructor                                                      |
//+------------------------------------------------------------------+
CTradeSignalGenerator::CTradeSignalGenerator()
   : m_b2b_detector(NULL), 
     m_swing_detector(NULL),
     m_breakout_detector(NULL),
     m_order_manager(NULL),
     m_risk_manager(NULL),
     m_orchestrator(new CStrategyOrchestrator()),
     m_context_mapper(new CContextMapper()),
     m_intraday(new CIntradayOrchestrator()),
     m_last_check_time(0),
     m_last_logged_zone_id(0)
{
}

//+------------------------------------------------------------------+
//| Destructor                                                       |
//+------------------------------------------------------------------+
CTradeSignalGenerator::~CTradeSignalGenerator()
{
   if(m_orchestrator != NULL) delete m_orchestrator;
   if(m_context_mapper != NULL) delete m_context_mapper;
   if(m_intraday != NULL) delete m_intraday;
}

//+------------------------------------------------------------------+
//| Initialize                                                       |
//+------------------------------------------------------------------+
void CTradeSignalGenerator::Initialize(CB2BDetector* b2b, CSwingPointDetector* swing, CRawBreakoutDetector* bo, COrderManager* om, CRiskManager* rm)
{
   m_b2b_detector = b2b;
   m_swing_detector = swing;
   m_breakout_detector = bo;
   m_order_manager = om;
   m_risk_manager = rm;
   
   // Wire shared ContextMapper to StrategyOrchestrator
   if(m_orchestrator != NULL && m_context_mapper != NULL)
   {
      m_orchestrator.SetContextMapper(m_context_mapper);
      m_orchestrator.Initialize(b2b);
   }
   
   // Wire IntradayOrchestrator
   if(m_intraday != NULL && m_context_mapper != NULL && m_orchestrator != NULL)
      m_intraday.Initialize(m_context_mapper, m_orchestrator);
   
   Print("TradeSignalGenerator: Initialized with Russian Doll + Intraday Protocol (V6.3).");
}

//+------------------------------------------------------------------+
//| OnTick: Main Processing Loop                                     |
//+------------------------------------------------------------------+
void CTradeSignalGenerator::OnTick(double current_price, datetime current_time, double ask, double bid, B2BZoneInfo &zones[], int total_zones, int change_mask)
{
   if(!InpEnableTradeSignals) return;
   
   if(m_orchestrator == NULL) return;
   
   // 1. Evaluate shared ContextMapper (dual-cadence: daily + per-M1-bar)
   if(m_context_mapper != NULL)
      m_context_mapper.EvaluateContext(zones, total_zones);
   
   // 2. Update the Brain (Orchestrator)
   m_orchestrator.UpdateState(current_price, current_time, zones, total_zones, change_mask);
   
   // 3. Update Intraday state
   if(m_intraday != NULL)
      m_intraday.UpdateState(current_price, current_time);
   
   // 4. Execute Swing Strategy
   ProcessRussianDollStrategy(current_price, ask, bid, zones, total_zones);
   
   // 5. Execute Intraday Strategy
   if(InpEnableIntraday && m_intraday != NULL)
      ProcessIntradayStrategy(current_price, ask, bid, zones, total_zones);
}

//+------------------------------------------------------------------+
//| ProcessRussianDollStrategy: The 4-Layer Hierarchy                |
//+------------------------------------------------------------------+
void CTradeSignalGenerator::ProcessRussianDollStrategy(double current_price, double ask, double bid, B2BZoneInfo &zones[], int total_zones)
{
   // V13 OPTIMIZATION: SINGLE-PASS TRIGGER SCANNER
   // We find the best "Spark" for each TF/Direction in one go
   // V18.12: UNLEASH THE GENERALS (H4, H1, M30 Execution)
   // We now find the best "Spark" for ALL execution timeframes in one go
   int trig_buy[6] = {-1, -1, -1, -1, -1, -1}; // H4, H1, M30, M15, M5, M1
   int trig_sell[6] = {-1, -1, -1, -1, -1, -1};
   
   for(int i=total_zones-1; i>=0; i--)
   {
      if(!zones[i].is_valid || zones[i].is_invalidated || zones[i].was_traded) continue;
      
      // Map TF to Index: 0=H4, 1=H1, 2=M30, 3=M15, 4=M5, 5=M1
      int t_idx = -1;
      if(zones[i].timeframe == PERIOD_H4) t_idx = 0;
      else if(zones[i].timeframe == PERIOD_H1) t_idx = 1;
      else if(zones[i].timeframe == PERIOD_M30) t_idx = 2;
      else if(zones[i].timeframe == PERIOD_M15) t_idx = 3;
      else if(zones[i].timeframe == PERIOD_M5) t_idx = 4;
      else if(zones[i].timeframe == PERIOD_M1) t_idx = 5;
      
      if(t_idx == -1) continue;
      
      // Check for Buy Trigger (Price inside Bullish Zone)
      if(trig_buy[t_idx] == -1 && zones[i].direction == DIRECTION_BULLISH)
      {
         if(ask <= zones[i].L1_price && ask >= zones[i].L2_price) trig_buy[t_idx] = i;
      }
      
      // Check for Sell Trigger (Price inside Bearish Zone)
      if(trig_sell[t_idx] == -1 && zones[i].direction == DIRECTION_BEARISH)
      {
         if(bid >= zones[i].L1_price && bid <= zones[i].L2_price) trig_sell[t_idx] = i;
      }
   }

   // DEBUG: Print trigger status if any found
   for(int t=0; t<3; t++) {
      if(trig_buy[t] != -1 || trig_sell[t] != -1) {
         ENUM_TIMEFRAMES d_tf = (t==0)?PERIOD_M15:(t==1)?PERIOD_M5:PERIOD_M1;
         // PrintFormat("[Signal] Found Trigger on %s: BuyIdx: %d, SellIdx: %d", EnumToString(d_tf), trig_buy[t], trig_sell[t]);
      }
   }

   // Narrative 4: EXECUTION EVALUATION (TIER 3 SNIPERS ONLY)
   // V6.0: We check if the identified triggers match the Orchestrator's Active Sniper
   // The Orchestrator handles H4/H1/M30 Trap Zones. SignalGenerator ONLY hunts M15/M5/M1
   ENUM_TIMEFRAMES eval_tfs[] = {PERIOD_M15, PERIOD_M5, PERIOD_M1};
   bool enabled_tfs[] = {InpExecuteM15, InpExecuteM5, InpExecuteM1};
   
   // V5.3 SMART STACKING: Collect valid signals first, then filter
   struct PotentialSignal {
      int zone_idx;
      double sl_dist;
      double anchor_dist;
      ENUM_TIMEFRAMES tf;
      ENUM_SIGNAL_DIRECTION dir;
   };
   
   PotentialSignal best_buy; best_buy.zone_idx = -1; best_buy.sl_dist = 0; best_buy.anchor_dist = 0;
   PotentialSignal best_sell; best_sell.zone_idx = -1; best_sell.sl_dist = 0; best_sell.anchor_dist = 0;
   
   for(int t=0; t<3; t++)
   {
       if(!enabled_tfs[t]) continue;
       ENUM_TIMEFRAMES tf = eval_tfs[t];
       
       // Map to trig_buy/sell arrays correctly (indices 3, 4, 5 correspond to M15, M5, M1 in the original scan)
       int arr_idx = t + 3; 
       
       // --- EVALUATE DISCOVERED BUY ---
       if(trig_buy[arr_idx] != -1)
       {
          int z_idx = trig_buy[arr_idx];
          B2BZoneInfo zone = zones[z_idx];
          double tp=0, sl=0;
          
          TradeSignalInfo check_sig;
          check_sig.zone_id = zone.zone_id;
          check_sig.zone_tf = tf;
          check_sig.direction = DIRECTION_BULLISH;
          check_sig.entry_price = zone.L1_price;
          check_sig.stop_loss = zone.L2_price;
          check_sig.signal_time = zone.zone_created_time;
          check_sig.anchor_id = zone.anchor_zone_id;
          
          if(m_orchestrator.IsTradeAllowed(check_sig, tp, sl))
          {
              if(best_buy.zone_idx == -1) 
              {
                  best_buy.zone_idx = z_idx;
                  best_buy.tf = tf;
                  best_buy.dir = DIRECTION_BULLISH;
              }
          }
       }
       
       // --- EVALUATE DISCOVERED SELL ---
       if(trig_sell[arr_idx] != -1)
       {
          int z_idx = trig_sell[arr_idx];
          B2BZoneInfo zone = zones[z_idx];
          double tp=0, sl=0;
          
          TradeSignalInfo check_sig;
          check_sig.zone_id = zone.zone_id;
          check_sig.zone_tf = tf;
          check_sig.direction = DIRECTION_BEARISH;
          check_sig.entry_price = zone.L1_price;
          check_sig.stop_loss = zone.L2_price;
          check_sig.signal_time = zone.zone_created_time;
          check_sig.anchor_id = zone.anchor_zone_id;
          
          if(m_orchestrator.IsTradeAllowed(check_sig, tp, sl))
          {
              if(best_sell.zone_idx == -1) 
              {
                  best_sell.zone_idx = z_idx;
                  best_sell.tf = tf;
                  best_sell.dir = DIRECTION_BEARISH;
              }
          }
       }
   }
   
   // EXECUTE THE WINNER (BUY)
   if(best_buy.zone_idx != -1)
   {
       int z_idx = best_buy.zone_idx;
       B2BZoneInfo zone = zones[z_idx];
       ENUM_TIMEFRAMES tf = best_buy.tf;
       double tp=0, sl=0;
       
       // Re-verify allow (cheap) to get TP/SL
       TradeSignalInfo exec_sig;
       exec_sig.zone_id = zone.zone_id;
       exec_sig.zone_tf = tf;
       exec_sig.direction = DIRECTION_BULLISH;
       exec_sig.entry_price = zone.L1_price;
       exec_sig.stop_loss = zone.L2_price;
       exec_sig.signal_time = zone.zone_created_time;
       exec_sig.anchor_id = zone.anchor_zone_id;
       
       if(m_orchestrator.IsTradeAllowed(exec_sig, tp, sl))
       {
           double range = MathAbs(zone.L1_price - zone.L2_price);
           double tol = range * 0.25;
           double mid = (zone.L1_price + zone.L2_price) / 2.0;

           if(MathAbs(ask - zone.L1_price) < tol)
           {
              if(InpEnableEntry_T1)
                 if(SendTradeSignal(SIGNAL_ENTRY_L1, DIRECTION_BULLISH, ask, sl, tp, "V5.3 SmartStack T1: " + EnumToString(tf) + " [" + exec_sig.lifecycle_phase + "]", zone, exec_sig.anchor_id, exec_sig.outpost_id, true, exec_sig.parent_tf))
                     zones[z_idx].was_traded = true;
           }
           else if(MathAbs(ask - mid) < tol)
           {
              if(InpEnableEntry_T2)
                 if(SendTradeSignal(SIGNAL_ENTRY_50, DIRECTION_BULLISH, ask, sl, tp, "V5.3 SmartStack T2: " + EnumToString(tf) + " [" + exec_sig.lifecycle_phase + "]", zone, exec_sig.anchor_id, exec_sig.outpost_id, true, exec_sig.parent_tf))
                     zones[z_idx].was_traded = true;
           }
           else if(MathAbs(ask - zone.L2_price) < tol)
           {
              if(InpEnableEntry_T3)
                 if(SendTradeSignal(SIGNAL_ENTRY_L2, DIRECTION_BULLISH, ask, sl, tp, "V5.3 SmartStack T3: " + EnumToString(tf) + " [" + exec_sig.lifecycle_phase + "]", zone, exec_sig.anchor_id, exec_sig.outpost_id, true, exec_sig.parent_tf))
                     zones[z_idx].was_traded = true;
           }
       }
   }
   
   // EXECUTE THE WINNER (SELL)
   if(best_sell.zone_idx != -1)
   {
       int z_idx = best_sell.zone_idx;
       B2BZoneInfo zone = zones[z_idx];
       ENUM_TIMEFRAMES tf = best_sell.tf;
       double tp=0, sl=0;
       
       // Re-verify allow (cheap) to get TP/SL
       TradeSignalInfo exec_sig;
       exec_sig.zone_id = zone.zone_id;
       exec_sig.zone_tf = tf;
       exec_sig.direction = DIRECTION_BEARISH;
       exec_sig.entry_price = zone.L1_price;
       exec_sig.stop_loss = zone.L2_price;
       exec_sig.signal_time = zone.zone_created_time;
       exec_sig.anchor_id = zone.anchor_zone_id;
       
       if(m_orchestrator.IsTradeAllowed(exec_sig, tp, sl))
       {
           double range = MathAbs(zone.L1_price - zone.L2_price);
           double tol = range * 0.25;
           double mid = (zone.L1_price + zone.L2_price) / 2.0;
           
           if(MathAbs(bid - zone.L1_price) < tol)
           {
              if(InpEnableEntry_T1)
                 if(SendTradeSignal(SIGNAL_ENTRY_L1, DIRECTION_BEARISH, bid, sl, tp, "V5.3 SmartStack T1: " + EnumToString(tf) + " [" + exec_sig.lifecycle_phase + "]", zone, exec_sig.anchor_id, exec_sig.outpost_id, true, exec_sig.parent_tf))
                     zones[z_idx].was_traded = true;
           }
           else if(MathAbs(bid - mid) < tol)
           {
              if(InpEnableEntry_T2)
                 if(SendTradeSignal(SIGNAL_ENTRY_50, DIRECTION_BEARISH, bid, sl, tp, "V5.3 SmartStack T2: " + EnumToString(tf) + " [" + exec_sig.lifecycle_phase + "]", zone, exec_sig.anchor_id, exec_sig.outpost_id, true, exec_sig.parent_tf))
                     zones[z_idx].was_traded = true;
           }
           else if(MathAbs(bid - zone.L2_price) < tol)
           {
              if(InpEnableEntry_T3)
                 if(SendTradeSignal(SIGNAL_ENTRY_L2, DIRECTION_BEARISH, bid, sl, tp, "V5.3 SmartStack T3: " + EnumToString(tf) + " [" + exec_sig.lifecycle_phase + "]", zone, exec_sig.anchor_id, exec_sig.outpost_id, true, exec_sig.parent_tf))
                     zones[z_idx].was_traded = true;
           }
       }
   }
}

//+------------------------------------------------------------------+
//| ProcessIntradayStrategy: Scan zones for intraday mean-reversion   |
//+------------------------------------------------------------------+
void CTradeSignalGenerator::ProcessIntradayStrategy(double current_price, double ask, double bid, B2BZoneInfo &zones[], int total_zones)
{
   if(m_intraday == NULL) return;
   
   // Get FlowState freshness baseline (mirrors ValidateTrap in StrategyOrchestrator)
   FlowState mn1, w1, d1;
   m_orchestrator.GetFlowDirections(mn1, w1, d1);
   
   int best_buy_idx = -1, best_sell_idx = -1;
   
   for(int i = total_zones - 1; i >= 0; i--)
   {
      if(!zones[i].is_valid || zones[i].is_invalidated || zones[i].was_traded) continue;
      if(zones[i].timeframe != PERIOD_H1 && zones[i].timeframe != PERIOD_M30) continue;
      
      // FRESHNESS GUARD: Zone must be born AFTER the latest HTF structural event
      // This mirrors ValidateTrap logic — prevents stale zones from catching falling knives
      datetime freshness_baseline = 0;
      ENUM_SIGNAL_DIRECTION zone_dir = zones[i].direction;
      
      if(d1.is_valid && d1.origin_dir == zone_dir)
      {
         datetime d1_base = d1.origin_touch_time;
         if(d1.outpost_id > 0 && d1.outpost_touch_time > 0) d1_base = d1.outpost_touch_time;
         if(d1_base > freshness_baseline) freshness_baseline = d1_base;
      }
      if(w1.is_valid && w1.origin_dir == zone_dir)
      {
         datetime w1_base = w1.origin_touch_time;
         if(w1.outpost_id > 0 && w1.outpost_touch_time > 0) w1_base = w1.outpost_touch_time;
         if(w1_base > freshness_baseline) freshness_baseline = w1_base;
      }
      if(mn1.is_valid && mn1.origin_dir == zone_dir)
      {
         datetime mn1_base = mn1.origin_touch_time;
         if(mn1.outpost_id > 0 && mn1.outpost_touch_time > 0) mn1_base = mn1.outpost_touch_time;
         if(mn1_base > freshness_baseline) freshness_baseline = mn1_base;
      }
      
      if(freshness_baseline > 0 && zones[i].zone_created_time <= freshness_baseline)
         continue;
      
      if(zones[i].direction == DIRECTION_BULLISH && best_buy_idx == -1)
      {
         if(ask <= zones[i].L1_price && ask >= zones[i].L2_price)
            best_buy_idx = i;
      }
      if(zones[i].direction == DIRECTION_BEARISH && best_sell_idx == -1)
      {
         if(bid >= zones[i].L1_price && bid <= zones[i].L2_price)
            best_sell_idx = i;
      }
   }
   
   // Evaluate Buy
   if(best_buy_idx != -1)
   {
      B2BZoneInfo zone = zones[best_buy_idx];
      TradeSignalInfo sig;
      sig.Reset();
      sig.zone_id = zone.zone_id;
      sig.zone_tf = zone.timeframe;
      sig.direction = DIRECTION_BULLISH;
      sig.entry_price = zone.L1_price;
      sig.stop_loss = zone.L2_price;
      sig.signal_time = zone.zone_created_time;
      
      double tp = 0, sl = 0;
      if(m_intraday.IsTradeAllowed(sig, tp, sl))
      {
         if(SendTradeSignal(SIGNAL_ENTRY_L1, DIRECTION_BULLISH, ask, sl, tp,
                            "INTRA " + EnumToString(zone.timeframe) + " [" + sig.lifecycle_phase + "]",
                            zone, sig.anchor_id, sig.outpost_id, true, sig.parent_tf, true))
            zones[best_buy_idx].was_traded = true;
      }
   }
   
   // Evaluate Sell
   if(best_sell_idx != -1)
   {
      B2BZoneInfo zone = zones[best_sell_idx];
      TradeSignalInfo sig;
      sig.Reset();
      sig.zone_id = zone.zone_id;
      sig.zone_tf = zone.timeframe;
      sig.direction = DIRECTION_BEARISH;
      sig.entry_price = zone.L1_price;
      sig.stop_loss = zone.L2_price;
      sig.signal_time = zone.zone_created_time;
      
      double tp = 0, sl = 0;
      if(m_intraday.IsTradeAllowed(sig, tp, sl))
      {
         if(SendTradeSignal(SIGNAL_ENTRY_L1, DIRECTION_BEARISH, bid, sl, tp,
                            "INTRA " + EnumToString(zone.timeframe) + " [" + sig.lifecycle_phase + "]",
                            zone, sig.anchor_id, sig.outpost_id, true, sig.parent_tf, true))
            zones[best_sell_idx].was_traded = true;
      }
   }
}

//+------------------------------------------------------------------+
//| SendTradeSignal: Dispatch to Order Manager                       |
//+------------------------------------------------------------------+
bool CTradeSignalGenerator::SendTradeSignal(ENUM_TRADE_SIGNAL_TYPE sig_type, ENUM_SIGNAL_DIRECTION dir, double price, double sl, double tp, string comment, const B2BZoneInfo &zone, ulong anchor_id, ulong outpost_id, bool is_with_trend, ENUM_TIMEFRAMES parent_tf, bool is_intraday)
{
   string dir_str = EnumToString(dir);
   string price_str = DoubleToString(price, _Digits);
   string sl_str = DoubleToString(sl, _Digits);
   string tp_str = (tp > 0) ? DoubleToString(tp, _Digits) : "TRAILING";
   
   string logbox = StringFormat("SIGNAL: %s | %s | P: %s SL: %s TP: %s | Anchor:#%04I64u > Magnet:#%04I64u", 
                                dir_str, comment, price_str, sl_str, tp_str, anchor_id % 10000, outpost_id % 10000);
   
   if(InpLogTrading && m_last_logged_zone_id != zone.zone_id) 
   {
      // Spam Reduction: Signal is logged by OrderManager execution or ShadowLog
      // Print(logbox);
      m_last_logged_zone_id = zone.zone_id;
   }
   
   if(m_order_manager == NULL) return false;
   
   // Construct Signal Struct
   TradeSignalInfo signal;
   signal.Reset();
   signal.signal_type = sig_type;
   signal.direction = dir;
   signal.entry_price = price;
   signal.stop_loss = sl;
   signal.take_profit = tp;
   signal.is_valid = true;
   signal.is_narrative_conflict = false;
   signal.vector_signature = comment;
   signal.vector_sum = 3;
   
   // Calculate R-multiple
   double risk_pts = MathAbs(price - sl);
   if(tp > 0 && risk_pts > 0)
      signal.target_r = MathAbs(tp - price) / risk_pts;
   else
      signal.target_r = InpTarget_R;
   
   signal.is_intraday = is_intraday;
   signal.zone_id = zone.zone_id;
   signal.zone_tf = zone.timeframe;
   signal.anchor_id = anchor_id;
   signal.outpost_id = outpost_id;
   signal.is_with_trend = is_with_trend;
   signal.parent_tf = parent_tf;
   
   signal.position_pct = 100.0;
   signal.sl_distance_points = MathAbs(price - sl) / _Point;
   
   if(m_orchestrator != NULL)
   {
      m_orchestrator.GetFlowState(signal.layer_1_tide, signal.layer_2_wind, signal.layer_3_trap, signal.layer_4_trigger, signal.bridge_state);
   }
   
   double lot_size = 0.0;
   if(m_risk_manager != NULL)
   {
      lot_size = m_risk_manager.CalculateRiskBasedLot(signal);
   }
   
   if(InpEnableOrderExecution)
   {
      if(m_risk_manager != NULL && !m_risk_manager.CanOpenNewPosition()) return false;
      
      // V6.3: Set magic number for intraday trades
      if(is_intraday)
         m_order_manager.SetMagicNumber(InpMagicNumber + 1);
      else
         m_order_manager.SetMagicNumber(InpMagicNumber);
      
      return m_order_manager.ExecuteSignal(signal, lot_size);
   }
   
   return true;
}
