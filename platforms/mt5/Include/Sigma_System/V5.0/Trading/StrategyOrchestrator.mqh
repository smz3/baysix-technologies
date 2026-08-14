//+------------------------------------------------------------------+
//|                                         StrategyOrchestrator.mqh |
//|                             Copyright 2026, Sigma Trading System |
//| V6.2: 3-Gate Execution Engine                                    |
//|   Gate 1: DIRECTION (FlowState)                                  |
//|   Gate 2: LOCATION  (ContextMapper)                              |
//|   Gate 3: STRUCTURE (Tier 2 Nesting)                             |
//+------------------------------------------------------------------+
#ifndef V50_STRATEGYORCHESTRATOR_MQH
#define V50_STRATEGYORCHESTRATOR_MQH

#include "../Data/Structures.mqh" 
#include "../Detection/B2BDetector.mqh"
#include "../Detection/B2BZoneManager.mqh"
#include "../Detection/B2BConfluence.mqh"
#include "../Detection/B2BTradeTracker.mqh"
#include "../Data/QuantLogger.mqh"
#include "../Configuration/TradingParameters.mqh"
#include "ContextMapper.mqh"

//=== FlowState: Per-Timeframe Directional Context ===
struct FlowState
{
   ulong             origin_id;           
   ulong             magnet_id;           
   ulong             outpost_id;          
   ulong             roadblock_id;        
   ENUM_SIGNAL_DIRECTION origin_dir;      
   ENUM_SIGNAL_DIRECTION magnet_dir;      
   int               origin_display_id;   
   int               magnet_display_id;
   double            details_origin_price;
   double            details_magnet_price;
   double            details_origin_L2;
   double            details_magnet_L2;
   bool              magnet_fifty_touched;
   bool              magnet_L2_touched;
   double            details_outpost_price; 
   bool              is_valid;            
   bool              is_siege_active;     
   datetime          last_update_time;    
   datetime          origin_touch_time;   
   datetime          outpost_touch_time;  
   bool              anchor_is_traded;
   bool              is_magnet_extreme;
   
   FlowState() : origin_id(0), magnet_id(0), outpost_id(0), roadblock_id(0),
                 origin_dir(DIRECTION_NONE), magnet_dir(DIRECTION_NONE),
                 origin_display_id(0), magnet_display_id(0),
                 is_valid(false), is_siege_active(false), last_update_time(0),
                 details_origin_price(0), details_magnet_price(0), 
                 details_origin_L2(0), details_magnet_L2(0),
                 magnet_fifty_touched(false), magnet_L2_touched(false),
                 details_outpost_price(0), anchor_is_traded(false), is_magnet_extreme(false),
                 origin_touch_time(0), outpost_touch_time(0) {}
   
   void Reset() 
   {
      origin_id = 0; magnet_id = 0; outpost_id = 0; roadblock_id = 0;
      origin_display_id = 0; magnet_display_id = 0;
      origin_dir = DIRECTION_NONE; magnet_dir = DIRECTION_NONE;
      details_origin_price = 0; details_magnet_price = 0; 
      details_origin_L2 = 0; details_magnet_L2 = 0;
      magnet_fifty_touched = false; magnet_L2_touched = false;
      details_outpost_price = 0; anchor_is_traded = false; is_magnet_extreme = false;
      is_valid = false; is_siege_active = false; last_update_time = 0;
      origin_touch_time = 0; outpost_touch_time = 0;
   }
};

enum ENUM_TRADE_TYPE
{
   TRADE_CONTINUATION,
   TRADE_FADE,
   TRADE_BREAKOUT,
   TRADE_NONE
};

class CStrategyOrchestrator
{
private:
   CContextMapper*   m_context;
   double            m_current_price;
   
   FlowState         m_mn1; 
   FlowState         m_w1;  
   FlowState         m_d1;  
   FlowState         m_h4;
   FlowState         m_h1;
   FlowState         m_m30;
   
public:
                     CStrategyOrchestrator();
                    ~CStrategyOrchestrator();

   void              SetContextMapper(CContextMapper *ctx) { m_context = ctx; }
   void              Orchestrate(B2BZoneInfo &zones[], int zone_count);
   bool              IsTradeAllowed(TradeSignalInfo &signal, double &out_tp, double &out_sl);
   
   void              Initialize(CB2BDetector *detector) {}
   void              UpdateState(double current_price, datetime current_time, B2BZoneInfo &zones[], int total_zones, int change_mask) { Orchestrate(zones, total_zones); }
   void              GetFlowState(string &tide, string &wind, string &trap, string &trigger, string &bridge); 
   void              SetDirty(bool dirty) {}
   
   void              GetFlowDirections(FlowState &out_mn1, FlowState &out_w1, FlowState &out_d1) const { out_mn1 = m_mn1; out_w1 = m_w1; out_d1 = m_d1; }
   string            GetBridgeState() { return CollectBridgeState(); }
   CContextMapper*   GetContextMapper() { return m_context; }
   
   bool              IsTradeAllowed(ENUM_SIGNAL_DIRECTION dir, ENUM_TIMEFRAMES tf,
                                   const B2BZoneInfo &zone, B2BZoneInfo &zones[], int total_zones,
                                   double &sl, double &tp,
                                   ulong &anchor_id, ulong &magnet_id,
                                   bool &is_with_trend, ENUM_TIMEFRAMES &parent_tf) { return false; }

private:
   void              UpdateFlowState(B2BZoneInfo &zones[], int zone_count);
   void              UpdateTimeframeFlow(B2BZoneInfo &zones[], int zone_count, ENUM_TIMEFRAMES tf, FlowState &state);
   void              QuickDefeatCheck();
   void              RefreshTouchStatus(B2BZoneInfo &zones[], int zone_count);
   int               GetZoneIndexByID(ulong id, B2BZoneInfo &zones[], int count);
   ulong             GetLatestOutpost(ENUM_TIMEFRAMES tf, ENUM_SIGNAL_DIRECTION dir, double limit_price, datetime after_time, B2BZoneInfo &zones[], int count);
   bool              ValidateTrap(B2BZoneInfo &trap, FlowState &narrative, ENUM_TIMEFRAMES flow_tf);
   double            GetOfficerTarget();
   string            GetTFString(ENUM_TIMEFRAMES tf);
   string            CollectBridgeState();
   
   // 3-Gate System
   ENUM_TRADE_TYPE   Gate1_Direction(TradeSignalInfo &signal, B2BZoneInfo &zone, double current_price, double &target_price, string &reason);
   bool              Gate2_Location(ENUM_TRADE_TYPE trade_type, ENUM_SIGNAL_DIRECTION dir, double current_price, double target_price, string &reason);
};

CStrategyOrchestrator::CStrategyOrchestrator()
{
   m_context = NULL;
   m_mn1.Reset(); m_w1.Reset(); m_d1.Reset();
   m_h4.Reset();  m_h1.Reset();  m_m30.Reset();
}

CStrategyOrchestrator::~CStrategyOrchestrator() {}

//+------------------------------------------------------------------+
//| Orchestrate: Dual-Layer Update (Performance Optimized)           |
//| - QuickDefeatCheck: O(1) every call                              |
//| - RefreshTouchStatus: O(n) every call (6 lookups)                |
//| - UpdateFlowState: O(n*k) only once per M1 bar                  |
//+------------------------------------------------------------------+
void CStrategyOrchestrator::Orchestrate(B2BZoneInfo &zones[], int zone_count)
{
   m_current_price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   
   QuickDefeatCheck();
   
   static datetime last_flow_bar = 0;
   datetime current_bar = iTime(_Symbol, PERIOD_M1, 0);
   if(current_bar != last_flow_bar)
   {
       RefreshTouchStatus(zones, zone_count);
       UpdateFlowState(zones, zone_count);
       last_flow_bar = current_bar;
   }
}

//+------------------------------------------------------------------+
//| QuickDefeatCheck: O(1) — Reset any FlowState whose Origin is     |
//| defeated (price broke through L2). No zone scanning needed.      |
//+------------------------------------------------------------------+
void CStrategyOrchestrator::QuickDefeatCheck()
{
   double p = m_current_price;
   if(m_mn1.is_valid && ((m_mn1.origin_dir == DIRECTION_BULLISH && p < m_mn1.details_origin_L2) || (m_mn1.origin_dir == DIRECTION_BEARISH && p > m_mn1.details_origin_L2))) m_mn1.Reset();
   if(m_w1.is_valid && ((m_w1.origin_dir == DIRECTION_BULLISH && p < m_w1.details_origin_L2) || (m_w1.origin_dir == DIRECTION_BEARISH && p > m_w1.details_origin_L2))) m_w1.Reset();
   if(m_d1.is_valid && ((m_d1.origin_dir == DIRECTION_BULLISH && p < m_d1.details_origin_L2) || (m_d1.origin_dir == DIRECTION_BEARISH && p > m_d1.details_origin_L2))) m_d1.Reset();
   if(m_h4.is_valid && ((m_h4.origin_dir == DIRECTION_BULLISH && p < m_h4.details_origin_L2) || (m_h4.origin_dir == DIRECTION_BEARISH && p > m_h4.details_origin_L2))) m_h4.Reset();
   if(m_h1.is_valid && ((m_h1.origin_dir == DIRECTION_BULLISH && p < m_h1.details_origin_L2) || (m_h1.origin_dir == DIRECTION_BEARISH && p > m_h1.details_origin_L2))) m_h1.Reset();
   if(m_m30.is_valid && ((m_m30.origin_dir == DIRECTION_BULLISH && p < m_m30.details_origin_L2) || (m_m30.origin_dir == DIRECTION_BEARISH && p > m_m30.details_origin_L2))) m_m30.Reset();
}

//+------------------------------------------------------------------+
//| RefreshTouchStatus: O(n) — Update magnet touch flags from the    |
//| live zone array using cached zone IDs (6 lookups only)           |
//+------------------------------------------------------------------+
void CStrategyOrchestrator::RefreshTouchStatus(B2BZoneInfo &zones[], int zone_count)
{
   int idx;
   if(m_mn1.is_valid && m_mn1.magnet_id != 0) { idx = GetZoneIndexByID(m_mn1.magnet_id, zones, zone_count); if(idx >= 0) { m_mn1.magnet_fifty_touched = zones[idx].fifty_touched; m_mn1.magnet_L2_touched = zones[idx].L2_touched; } }
   if(m_w1.is_valid && m_w1.magnet_id != 0)   { idx = GetZoneIndexByID(m_w1.magnet_id, zones, zone_count);  if(idx >= 0) { m_w1.magnet_fifty_touched = zones[idx].fifty_touched; m_w1.magnet_L2_touched = zones[idx].L2_touched; } }
   if(m_d1.is_valid && m_d1.magnet_id != 0)   { idx = GetZoneIndexByID(m_d1.magnet_id, zones, zone_count);  if(idx >= 0) { m_d1.magnet_fifty_touched = zones[idx].fifty_touched; m_d1.magnet_L2_touched = zones[idx].L2_touched; } }
   if(m_h4.is_valid && m_h4.magnet_id != 0)   { idx = GetZoneIndexByID(m_h4.magnet_id, zones, zone_count);  if(idx >= 0) { m_h4.magnet_fifty_touched = zones[idx].fifty_touched; m_h4.magnet_L2_touched = zones[idx].L2_touched; } }
   if(m_h1.is_valid && m_h1.magnet_id != 0)   { idx = GetZoneIndexByID(m_h1.magnet_id, zones, zone_count);  if(idx >= 0) { m_h1.magnet_fifty_touched = zones[idx].fifty_touched; m_h1.magnet_L2_touched = zones[idx].L2_touched; } }
   if(m_m30.is_valid && m_m30.magnet_id != 0) { idx = GetZoneIndexByID(m_m30.magnet_id, zones, zone_count); if(idx >= 0) { m_m30.magnet_fifty_touched = zones[idx].fifty_touched; m_m30.magnet_L2_touched = zones[idx].L2_touched; } }
}
//+------------------------------------------------------------------+
//| UpdateFlowState: All 6 Timeframe Narratives                      |
//+------------------------------------------------------------------+
void CStrategyOrchestrator::UpdateFlowState(B2BZoneInfo &zones[], int zone_count)
{
   UpdateTimeframeFlow(zones, zone_count, PERIOD_MN1, m_mn1);
   UpdateTimeframeFlow(zones, zone_count, PERIOD_W1, m_w1);
   UpdateTimeframeFlow(zones, zone_count, PERIOD_D1, m_d1);
   UpdateTimeframeFlow(zones, zone_count, PERIOD_H4, m_h4);
   UpdateTimeframeFlow(zones, zone_count, PERIOD_H1, m_h1);
   UpdateTimeframeFlow(zones, zone_count, PERIOD_M30, m_m30);
   
   static int log_timer = 0;
   if(TimeCurrent() % 60 == 0 && log_timer != (int)TimeCurrent()) 
   {
      log_timer = (int)TimeCurrent();
      string mn1_s = m_mn1.is_valid ? EnumToString(m_mn1.origin_dir) : "INVALID";
      string w1_s = m_w1.is_valid ? EnumToString(m_w1.origin_dir) : "INVALID";
      string d1_s = m_d1.is_valid ? EnumToString(m_d1.origin_dir) : "INVALID";
      string h4_s = m_h4.is_valid ? EnumToString(m_h4.origin_dir) : "INVALID";
      string h1_s = m_h1.is_valid ? EnumToString(m_h1.origin_dir) : "INVALID";
      string m30_s = m_m30.is_valid ? EnumToString(m_m30.origin_dir) : "INVALID";
      
      double epoch_pos = m_context.GetEpochPosition(m_mn1.is_valid ? m_mn1.origin_dir : DIRECTION_BULLISH, m_current_price);
      
      PrintFormat("=== V6.2 ORCHESTRATOR HEARTBEAT ===");
      PrintFormat("MN1 Tide: %s | Origin:#%04d -> Magnet:#%04d | Siege:%s", mn1_s, m_mn1.origin_display_id, m_mn1.magnet_display_id, m_mn1.is_siege_active ? "YES" : "NO");
      PrintFormat("W1 Wind:  %s | Origin:#%04d -> Magnet:#%04d | Siege:%s", w1_s, m_w1.origin_display_id, m_w1.magnet_display_id, m_w1.is_siege_active ? "YES" : "NO");
      PrintFormat("D1 Path:  %s | Origin:#%04d -> Magnet:#%04d | Siege:%s", d1_s, m_d1.origin_display_id, m_d1.magnet_display_id, m_d1.is_siege_active ? "YES" : "NO");
      PrintFormat(">>> T2: H4:%s #%04d | H1:%s #%04d | M30:%s #%04d", h4_s, m_h4.origin_display_id, h1_s, m_h1.origin_display_id, m30_s, m_m30.origin_display_id);
      PrintFormat(">>> Epoch Position: %.1f%% | Bridge: %s", epoch_pos * 100, CollectBridgeState());
   }
}

//+------------------------------------------------------------------+
//| UpdateTimeframeFlow: Origin → Outpost → Magnet → Siege           |
//+------------------------------------------------------------------+
void CStrategyOrchestrator::UpdateTimeframeFlow(B2BZoneInfo &zones[], int zone_count, ENUM_TIMEFRAMES tf, FlowState &state)
{
   double current_price = m_current_price;
   if(state.is_valid)
   {
      int origin_idx = (int)GetZoneIndexByID(state.origin_id, zones, zone_count);
      int magnet_idx = (int)GetZoneIndexByID(state.magnet_id, zones, zone_count);
      if(origin_idx == -1) { state.Reset(); return; }
      
      state.origin_touch_time = zones[origin_idx].L1_touch_time;
      state.details_origin_price = zones[origin_idx].L1_price;
      state.details_origin_L2 = zones[origin_idx].L2_price;
      
      bool defeat = false;
      if(state.origin_dir == DIRECTION_BULLISH && current_price < zones[origin_idx].L2_price) defeat = true;
      if(state.origin_dir == DIRECTION_BEARISH && current_price > zones[origin_idx].L2_price) defeat = true;
      if(defeat) { state.Reset(); return; }
      
      if(magnet_idx != -1)
      {
         state.magnet_fifty_touched = zones[magnet_idx].fifty_touched;
         state.magnet_L2_touched = zones[magnet_idx].L2_touched;
         if(zones[magnet_idx].L2_touched) 
         {
            ulong successor_id = GetLatestOutpost(tf, state.origin_dir, current_price, zones[origin_idx].zone_created_time, zones, zone_count);
            if(successor_id > 0) { 
               state.origin_id = successor_id; 
               state.origin_display_id = (int)(successor_id % 10000); 
               state.magnet_id = 0; state.magnet_display_id = 0; 
               state.is_siege_active = false;
               int succ_idx = (int)GetZoneIndexByID(successor_id, zones, zone_count);
               if(succ_idx != -1) state.anchor_is_traded = zones[succ_idx].L1_touched;
               else state.anchor_is_traded = false;
            }
            else { 
               if(m_mn1.magnet_id == 0 && (tf == PERIOD_D1 || tf == PERIOD_W1 || tf == PERIOD_H4 || tf == PERIOD_H1 || tf == PERIOD_M30)) {
                  state.magnet_id = 0; state.magnet_display_id = 0; state.is_siege_active = false;
               }
               else state.Reset(); 
               return; 
            }
         }
      }
      if(magnet_idx == -1 && state.magnet_id != 0) state.magnet_id = 0;
      
      ulong latest_outpost_id = GetLatestOutpost(tf, state.origin_dir, current_price, zones[origin_idx].zone_created_time, zones, zone_count);
      if(latest_outpost_id > 0)
      {
         state.outpost_id = latest_outpost_id;
         int outpost_idx = (int)GetZoneIndexByID(latest_outpost_id, zones, zone_count);
         if(outpost_idx != -1) 
         { 
             state.outpost_touch_time = zones[outpost_idx].L1_touch_time; 
             state.anchor_is_traded = zones[outpost_idx].L1_touched;
             if(state.magnet_id > 0 && magnet_idx != -1 && zones[magnet_idx].L1_touched)
             {
                 state.is_siege_active = (state.outpost_touch_time > zones[magnet_idx].L1_touch_time);
             }
         }
      }
      else { state.outpost_id = 0; state.details_outpost_price = 0; state.outpost_touch_time = 0; state.is_siege_active = false; }
      
      state.roadblock_id = m_context.IsPathBlocked(state.origin_dir, current_price, tf, zones, zone_count, state.is_siege_active ? state.magnet_id : 0);
      
      if(state.magnet_id != 0) 
      {
          state.is_magnet_extreme = true;
          for(int i=0; i<zone_count; i++) {
              if(zones[i].timeframe == tf && zones[i].direction == state.magnet_dir && zones[i].IsValid()) {
                  if(state.magnet_dir == DIRECTION_BEARISH) { if(zones[i].L1_price > state.details_magnet_price) { state.is_magnet_extreme = false; break; } }
                  else { if(zones[i].L1_price < state.details_magnet_price) { state.is_magnet_extreme = false; break; } }
              }
          }
          return;
      }
   }
   
   int best_origin_idx = -1;
   if(state.origin_id != 0) best_origin_idx = (int)GetZoneIndexByID(state.origin_id, zones, zone_count);
   else
   {
      datetime latest_time = 0;
      for(int i=0; i<zone_count; i++)
      {
         if(zones[i].timeframe != tf || !zones[i].IsValid()) continue;
         if(m_mn1.magnet_id == 0 && (tf == PERIOD_D1 || tf == PERIOD_W1) && zones[i].direction != m_mn1.origin_dir) continue;
         bool is_broken = (zones[i].direction == DIRECTION_BULLISH) ? (current_price < zones[i].L2_price) : (current_price > zones[i].L2_price);
         if(is_broken) continue;
         bool is_ahead = (zones[i].direction == DIRECTION_BULLISH) ? (current_price > zones[i].L1_price) : (current_price < zones[i].L1_price);
         if(!zones[i].L1_touched && is_ahead) continue;
         datetime t = MathMax(zones[i].L1_touch_time, zones[i].zone_created_time);
         if(t > latest_time) { latest_time = t; best_origin_idx = i; }
      }
   }
   if(best_origin_idx != -1)
   {
      state.origin_id = zones[best_origin_idx].zone_id;
      state.origin_display_id = (int)(state.origin_id % 10000);
      state.origin_dir = zones[best_origin_idx].direction;
      state.details_origin_price = zones[best_origin_idx].L1_price;
      state.details_origin_L2 = zones[best_origin_idx].L2_price;
      state.origin_touch_time = zones[best_origin_idx].L1_touch_time;
      state.last_update_time = MathMax(zones[best_origin_idx].L1_touch_time, zones[best_origin_idx].zone_created_time);
      state.is_valid = true;
      state.anchor_is_traded = zones[best_origin_idx].L1_touched;
      
      int best_magnet_idx = -1; double min_dist = DBL_MAX;
      ENUM_SIGNAL_DIRECTION target_dir = (state.origin_dir == DIRECTION_BULLISH) ? DIRECTION_BEARISH : DIRECTION_BULLISH;
      for(int i=0; i<zone_count; i++)
      {
         if(zones[i].timeframe != tf || !zones[i].IsValid() || zones[i].direction != target_dir) continue;
         double dist = DBL_MAX;
         if(state.origin_dir == DIRECTION_BULLISH) { if(zones[i].L1_price > current_price) dist = zones[i].L1_price - current_price; }
         else { if(zones[i].L1_price < current_price) dist = current_price - zones[i].L1_price; }
         if(dist < min_dist) { min_dist = dist; best_magnet_idx = i; }
      }
      if(best_magnet_idx != -1) 
      { 
          state.magnet_id = zones[best_magnet_idx].zone_id; 
          state.magnet_display_id = (int)(state.magnet_id % 10000); 
          state.magnet_dir = zones[best_magnet_idx].direction; 
          state.details_magnet_price = zones[best_magnet_idx].L1_price;
          state.details_magnet_L2 = zones[best_magnet_idx].L2_price;
          state.magnet_fifty_touched = zones[best_magnet_idx].fifty_touched;
          state.magnet_L2_touched = zones[best_magnet_idx].L2_touched;
          
          state.is_magnet_extreme = true;
          for(int i=0; i<zone_count; i++) {
              if(zones[i].timeframe == tf && zones[i].direction == state.magnet_dir && zones[i].IsValid()) {
                  if(state.magnet_dir == DIRECTION_BEARISH) { if(zones[i].L1_price > state.details_magnet_price) { state.is_magnet_extreme = false; break; } }
                  else { if(zones[i].L1_price < state.details_magnet_price) { state.is_magnet_extreme = false; break; } }
              }
          }
      }
      else { 
          state.magnet_id = 0; state.magnet_display_id = 0; state.magnet_dir = target_dir; 
          state.details_magnet_price = 0; state.details_magnet_L2 = 0; 
          state.magnet_fifty_touched = false; state.magnet_L2_touched = false;
          state.is_magnet_extreme = false;
      }
      state.roadblock_id = m_context.IsPathBlocked(state.origin_dir, current_price, tf, zones, zone_count, state.is_siege_active ? state.magnet_id : 0);
   }
   else state.Reset();
}

//+------------------------------------------------------------------+
//| ========== 3-GATE TRADE AUTHORIZATION SYSTEM ========== |
//+------------------------------------------------------------------+
bool CStrategyOrchestrator::IsTradeAllowed(TradeSignalInfo &signal, double &out_tp, double &out_sl)
{
   double current_price = m_current_price;
   
   B2BZoneInfo zone; 
   zone.zone_id = signal.zone_id; zone.timeframe = signal.zone_tf; zone.direction = signal.direction;   
   zone.L1_price = signal.entry_price; zone.L2_price = signal.stop_loss; zone.zone_created_time = signal.signal_time;
   
   double target_price = 0;
   string reason = "";
   
   // === GATE 1: DIRECTION (FlowState) ===
   ENUM_TRADE_TYPE trade_type = Gate1_Direction(signal, zone, current_price, target_price, reason);
   if(trade_type == TRADE_NONE)
   {
      static datetime last_fail_log = 0;
      if(TimeCurrent() - last_fail_log > 300) 
      {
          last_fail_log = TimeCurrent();
          PrintFormat(">> [G1 FAIL] %s %s | No Directional Authorization", GetTFString(signal.zone_tf), EnumToString(signal.direction));
      }
      return false;
   }
   
   // === GATE 2: LOCATION (ContextMapper) ===
   string g2_reason = "";
   if(!Gate2_Location(trade_type, signal.direction, current_price, target_price, g2_reason))
   {
      PrintFormat(">> [G2 FAIL] %s %s | %s", GetTFString(signal.zone_tf), EnumToString(signal.direction), g2_reason);
      return false;
   }
   reason += " | " + g2_reason;
   
   // === GATE 3: STRUCTURE (Tier 2 Nesting + Freshness) ===
   // Tier 3 sniper must be:
   //   1. Spatially INSIDE a Tier 2 zone (H4/H1/M30)
   //   2. Born AFTER the Tier 2 zone was activated (touch time or creation time)
   string g3_reason = "";
   bool is_breakout = m_context.IsBreakout(signal.direction, current_price);
   bool has_t2_nesting = false;
   datetime sniper_born = zone.zone_created_time;
   
   if(m_h4.is_valid && m_h4.origin_dir == signal.direction)
   {
       double h4_high = MathMax(m_h4.details_origin_price, m_h4.details_origin_L2);
       double h4_low = MathMin(m_h4.details_origin_price, m_h4.details_origin_L2);
       datetime h4_active = (m_h4.origin_touch_time > 0) ? m_h4.origin_touch_time : m_h4.last_update_time;
       if(current_price <= h4_high && current_price >= h4_low && sniper_born > h4_active) 
       { has_t2_nesting = true; g3_reason = "Nested:H4(Fresh)"; }
   }
   if(!has_t2_nesting && m_h1.is_valid && m_h1.origin_dir == signal.direction)
   {
       double h1_high = MathMax(m_h1.details_origin_price, m_h1.details_origin_L2);
       double h1_low = MathMin(m_h1.details_origin_price, m_h1.details_origin_L2);
       datetime h1_active = (m_h1.origin_touch_time > 0) ? m_h1.origin_touch_time : m_h1.last_update_time;
       if(current_price <= h1_high && current_price >= h1_low && sniper_born > h1_active) 
       { has_t2_nesting = true; g3_reason = "Nested:H1(Fresh)"; }
   }
   if(!has_t2_nesting && m_m30.is_valid && m_m30.origin_dir == signal.direction)
   {
       double m30_high = MathMax(m_m30.details_origin_price, m_m30.details_origin_L2);
       double m30_low = MathMin(m_m30.details_origin_price, m_m30.details_origin_L2);
       datetime m30_active = (m_m30.origin_touch_time > 0) ? m_m30.origin_touch_time : m_m30.last_update_time;
       if(current_price <= m30_high && current_price >= m30_low && sniper_born > m30_active) 
       { has_t2_nesting = true; g3_reason = "Nested:M30(Fresh)"; }
   }
   
   // Breakout bypass: no T2 zones may exist in vacuum
   if(!has_t2_nesting && is_breakout) { has_t2_nesting = true; g3_reason = "Breakout:NoNestReq"; }
   
   // Fade bypass: The HTF Magnet zone itself IS the structural backing
   // When MN1/W1/D1 says "we're at the wall", that wall IS institutional structure
   // Don't require T2 Officers to have flipped — they may still be trending
   if(!has_t2_nesting && trade_type == TRADE_FADE)
   {
       has_t2_nesting = true;
       g3_reason = StringFormat("FadeWall:%s", EnumToString(signal.parent_tf));
   }
   
   if(!has_t2_nesting)
   {
      PrintFormat(">> [G3 FAIL] %s %s | No Tier 2 Nesting (Spatial or Stale)", GetTFString(signal.zone_tf), EnumToString(signal.direction));
      return false;
   }
   reason += " | " + g3_reason;
   
   // === ALL 3 GATES PASSED ===
   signal.lifecycle_phase = reason;
   signal.bridge_state = CollectBridgeState();
   
   out_sl = (signal.direction == DIRECTION_BULLISH) ? (signal.stop_loss - InpSLBufferPoints * _Point) : (signal.stop_loss + InpSLBufferPoints * _Point);
   out_tp = target_price;
   
   PrintFormat(">> [AUTHORIZED] %s %s | G1:%s | G2:%s | G3:%s | TP:%.5f", 
               GetTFString(signal.zone_tf), EnumToString(signal.direction), 
               EnumToString(trade_type), g2_reason, g3_reason, target_price);
   
   return (out_sl != 0);
}

//+------------------------------------------------------------------+
//| Gate 1: DIRECTION — FlowState Authorization                      |
//+------------------------------------------------------------------+
ENUM_TRADE_TYPE CStrategyOrchestrator::Gate1_Direction(TradeSignalInfo &signal, B2BZoneInfo &zone, double current_price, double &target_price, string &reason)
{
   // === Global Siege Guard ===
   if(m_mn1.is_siege_active && signal.direction != m_mn1.origin_dir) return TRADE_NONE;
   if(m_w1.is_siege_active && signal.direction != m_w1.origin_dir) return TRADE_NONE;
   if(m_d1.is_siege_active && signal.direction != m_d1.origin_dir) return TRADE_NONE;
   
   // === Handover Detection ===
   bool d1_fresh = false, w1_fresh = false;
   if(m_d1.is_valid && m_d1.origin_dir == signal.direction)
   {
       if(m_mn1.is_valid && m_d1.origin_dir == m_mn1.origin_dir && m_d1.origin_touch_time > m_mn1.origin_touch_time) d1_fresh = true;
       if(m_w1.is_valid && m_d1.origin_dir == m_w1.origin_dir && m_d1.origin_touch_time > m_w1.origin_touch_time) d1_fresh = true;
   }
   if(m_w1.is_valid && m_w1.origin_dir == signal.direction)
   {
       if(m_mn1.is_valid && m_w1.origin_dir == m_mn1.origin_dir && m_w1.origin_touch_time > m_mn1.origin_touch_time) w1_fresh = true;
   }

   // 1. MN1 CONTINUATION
   if(!d1_fresh && !w1_fresh && m_mn1.is_valid && ValidateTrap(zone, m_mn1, PERIOD_MN1))
   {
      target_price = m_mn1.details_magnet_L2;
      if(target_price == 0)
      {
          double officer_tp = GetOfficerTarget();
          target_price = (officer_tp > 0) ? officer_tp : m_context.GetTargetCoordinate(signal.direction, current_price);
      }
      reason = "MN1 Flow"; signal.parent_tf = PERIOD_MN1;
      signal.anchor_id = m_mn1.origin_id; signal.outpost_id = m_mn1.outpost_id;
      return TRADE_CONTINUATION;
   }
   
   // 2. W1 CONTINUATION
   if(!d1_fresh && m_w1.is_valid && ValidateTrap(zone, m_w1, PERIOD_W1) && m_w1.roadblock_id == 0)
   {
      if(m_mn1.is_valid && m_w1.origin_dir != m_mn1.origin_dir) { /* skip counter-trend W1 continuation */ }
      else
      {
          target_price = m_mn1.details_magnet_L2 > 0 ? m_mn1.details_magnet_L2 : m_w1.details_magnet_L2;
          if(target_price == 0)
          {
              double officer_tp = GetOfficerTarget();
              target_price = (officer_tp > 0) ? officer_tp : m_context.GetTargetCoordinate(signal.direction, current_price);
          }
          reason = w1_fresh ? "W1 Flow (Handover)" : "W1 Flow"; signal.parent_tf = PERIOD_W1;
          signal.anchor_id = m_w1.origin_id; signal.outpost_id = m_w1.outpost_id;
          return TRADE_CONTINUATION;
      }
   }
   
   // 3. D1 CONTINUATION
   if(m_d1.is_valid && ValidateTrap(zone, m_d1, PERIOD_D1) && m_d1.roadblock_id == 0)
   {
      target_price = m_d1.details_magnet_L2;
      if(m_w1.is_valid && m_d1.origin_dir == m_w1.origin_dir && m_w1.details_magnet_L2 > 0) target_price = m_w1.details_magnet_L2;
      if(target_price == 0)
      {
          double officer_tp = GetOfficerTarget();
          target_price = (officer_tp > 0) ? officer_tp : m_context.GetTargetCoordinate(signal.direction, current_price);
      }
      reason = d1_fresh ? "D1 Flow (Handover)" : "D1 Flow"; signal.parent_tf = PERIOD_D1;
      signal.anchor_id = m_d1.origin_id; signal.outpost_id = m_d1.outpost_id;
      return TRADE_CONTINUATION;
   }
   
   // 4. BREAKOUT (no magnets on any Tier 1)
   if(m_mn1.is_valid && m_mn1.magnet_id == 0 && signal.direction == m_mn1.origin_dir)
   {
       if(m_context.IsBreakout(signal.direction, current_price))
       {
           double officer_tp = GetOfficerTarget();
           target_price = (officer_tp > 0) ? officer_tp : m_context.GetTargetCoordinate(signal.direction, current_price);
           reason = "Breakout Discovery"; signal.parent_tf = PERIOD_MN1;
           signal.anchor_id = m_mn1.origin_id; signal.outpost_id = m_mn1.outpost_id;
           return TRADE_BREAKOUT;
       }
   }
   
   // 5. MN1 MAGNET FADE (full zone L1-L2)
   if(m_mn1.is_valid && (m_mn1.magnet_fifty_touched || m_mn1.magnet_L2_touched) && !m_mn1.is_siege_active)
   {
       double zone_high = MathMax(m_mn1.details_magnet_price, m_mn1.details_magnet_L2);
       double zone_low = MathMin(m_mn1.details_magnet_price, m_mn1.details_magnet_L2);
       if(current_price <= zone_high && current_price >= zone_low && signal.direction != m_mn1.origin_dir)
       {
           target_price = m_mn1.details_origin_L2 > 0 ? m_mn1.details_origin_L2 : m_context.GetTargetCoordinate(signal.direction, current_price);
           reason = "MN1 Magnet Fade"; signal.parent_tf = PERIOD_MN1;
           signal.anchor_id = m_mn1.magnet_id; signal.outpost_id = m_mn1.origin_id;
           return TRADE_FADE;
       }
   }
   
   // 6. W1 MAGNET FADE (full zone L1-L2)
   if(m_w1.is_valid && (m_w1.magnet_fifty_touched || m_w1.magnet_L2_touched) && !m_w1.is_siege_active)
   {
       double zone_high = MathMax(m_w1.details_magnet_price, m_w1.details_magnet_L2);
       double zone_low = MathMin(m_w1.details_magnet_price, m_w1.details_magnet_L2);
       if(current_price <= zone_high && current_price >= zone_low && signal.direction != m_w1.origin_dir)
       {
           target_price = m_w1.details_origin_L2 > 0 ? m_w1.details_origin_L2 : m_context.GetTargetCoordinate(signal.direction, current_price);
           reason = "W1 Magnet Fade"; signal.parent_tf = PERIOD_W1;
           signal.anchor_id = m_w1.magnet_id; signal.outpost_id = m_w1.origin_id;
           return TRADE_FADE;
       }
   }
   
   // 7. D1 ATH MAGNET FADE (full zone L1-L2)
   if(m_d1.is_valid && m_mn1.magnet_id == 0 && (m_d1.magnet_fifty_touched || m_d1.magnet_L2_touched) && !m_d1.is_siege_active)
   {
       double zone_high = MathMax(m_d1.details_magnet_price, m_d1.details_magnet_L2);
       double zone_low = MathMin(m_d1.details_magnet_price, m_d1.details_magnet_L2);
       if(m_d1.is_magnet_extreme && current_price <= zone_high && current_price >= zone_low && signal.direction != m_d1.origin_dir)
       {
           target_price = m_d1.details_origin_L2 > 0 ? m_d1.details_origin_L2 : m_context.GetTargetCoordinate(signal.direction, current_price);
           reason = "D1 ATH Fade"; signal.parent_tf = PERIOD_D1;
           signal.anchor_id = m_d1.magnet_id; signal.outpost_id = m_d1.origin_id;
           return TRADE_FADE;
       }
   }
   
   return TRADE_NONE;
}

//+------------------------------------------------------------------+
//| Gate 2: LOCATION — ContextMapper Spatial Check                   |
//+------------------------------------------------------------------+
bool CStrategyOrchestrator::Gate2_Location(ENUM_TRADE_TYPE trade_type, ENUM_SIGNAL_DIRECTION dir, double current_price, double target_price, string &reason)
{
   double epoch_pos = m_context.GetEpochPosition(dir, current_price);
   double intraday_pos = m_context.GetIntradayPosition(current_price);
   
   if(trade_type == TRADE_CONTINUATION)
   {
       // Monthly range exhaustion
       if(dir == DIRECTION_BULLISH && epoch_pos > 0.90)
       {
           reason = StringFormat("MthCeiling:%.0f%%", epoch_pos * 100);
           return false;
       }
       if(dir == DIRECTION_BEARISH && epoch_pos < 0.10)
       {
           reason = StringFormat("MthFloor:%.0f%%", epoch_pos * 100);
           return false;
       }
       // Intraday range exhaustion (softer — only block if ALSO near monthly extreme)
       if(dir == DIRECTION_BULLISH && intraday_pos > 0.90 && epoch_pos > 0.75)
       {
           reason = StringFormat("IntradayCeiling:%.0f%%|Mth:%.0f%%", intraday_pos * 100, epoch_pos * 100);
           return false;
       }
       if(dir == DIRECTION_BEARISH && intraday_pos < 0.10 && epoch_pos < 0.25)
       {
           reason = StringFormat("IntradayFloor:%.0f%%|Mth:%.0f%%", intraday_pos * 100, epoch_pos * 100);
           return false;
       }
       reason = StringFormat("Mth:%.0f%%|Day:%.0f%%", epoch_pos * 100, intraday_pos * 100);
       return true;
   }
   
   if(trade_type == TRADE_FADE)
   {
       reason = StringFormat("Fade|Mth:%.0f%%|Day:%.0f%%", epoch_pos * 100, intraday_pos * 100);
       return true;
   }
   
   if(trade_type == TRADE_BREAKOUT)
   {
       reason = StringFormat("Breakout|Mth:%.0f%%|Day:%.0f%%", epoch_pos * 100, intraday_pos * 100);
       return true;
   }
   
   reason = "Unknown";
   return false;
}

//+------------------------------------------------------------------+
//| ValidateTrap: Freshness + Shield + Free-Flow/Strict              |
//+------------------------------------------------------------------+
bool CStrategyOrchestrator::ValidateTrap(B2BZoneInfo &trap, FlowState &narrative, ENUM_TIMEFRAMES flow_tf)
{
   if(trap.direction != narrative.origin_dir) return false;

   datetime freshness_baseline = narrative.origin_touch_time;
   if(narrative.outpost_id > 0)
   {
       if(narrative.outpost_touch_time > 0) freshness_baseline = narrative.outpost_touch_time;
       else freshness_baseline = TimeCurrent();
   }
   if(trap.zone_created_time <= freshness_baseline) return false;
   
   bool mn1_shield_up = (m_mn1.is_valid && (m_mn1.magnet_fifty_touched || m_mn1.magnet_L2_touched) && !m_mn1.is_siege_active);
   bool w1_shield_up = (m_w1.is_valid && (m_w1.magnet_fifty_touched || m_w1.magnet_L2_touched) && !m_w1.is_siege_active);
   
   if(mn1_shield_up) return false; 
   if(flow_tf == PERIOD_D1 && w1_shield_up) return false;
   
   bool is_free_flow = (narrative.outpost_id > 0 && narrative.anchor_is_traded);
   if(is_free_flow)
   {
       if((narrative.magnet_fifty_touched || narrative.magnet_L2_touched) && !narrative.is_siege_active)
           return false;
   }
   else
   {
       if(trap.direction == DIRECTION_BULLISH) { if(trap.L1_price > narrative.details_origin_price + _Point) return false; }
       else { if(trap.L1_price < narrative.details_origin_price - _Point) return false; }
   }
   
   return true;
}

//+------------------------------------------------------------------+
//| GetLatestOutpost: Successor Chain Logic                          |
//+------------------------------------------------------------------+
ulong CStrategyOrchestrator::GetLatestOutpost(ENUM_TIMEFRAMES tf, ENUM_SIGNAL_DIRECTION dir, double limit_price, datetime after_time, B2BZoneInfo &zones[], int count)
{
   int best_idx = -1; datetime best_time = after_time;
   for(int i=0; i<count; i++)
   {
      if(zones[i].timeframe != tf || zones[i].direction != dir || !zones[i].IsValid()) continue;
      if(zones[i].zone_created_time > best_time) { best_time = zones[i].zone_created_time; best_idx = i; }
   }
   if(best_idx != -1)
   {
       bool is_broken = (dir == DIRECTION_BULLISH) ? (limit_price < zones[best_idx].L2_price) : (limit_price > zones[best_idx].L2_price);
       if(is_broken) return 0; 
       return zones[best_idx].zone_id;
   }
   return 0;
}

//+------------------------------------------------------------------+
//| Utility Functions                                                |
//+------------------------------------------------------------------+
double CStrategyOrchestrator::GetOfficerTarget()
{
   if(m_h4.is_valid && m_h4.details_magnet_L2 > 0) return m_h4.details_magnet_L2;
   if(m_h1.is_valid && m_h1.details_magnet_L2 > 0) return m_h1.details_magnet_L2;
   if(m_m30.is_valid && m_m30.details_magnet_L2 > 0) return m_m30.details_magnet_L2;
   return 0;
}

int CStrategyOrchestrator::GetZoneIndexByID(ulong id, B2BZoneInfo &zones[], int count)
{
   for(int i=0; i<count; i++) { if(zones[i].zone_id == id) return i; }
   return -1;
}

string CStrategyOrchestrator::GetTFString(ENUM_TIMEFRAMES tf)
{
   if(tf == PERIOD_MN1) return "MN1"; if(tf == PERIOD_W1) return "W1"; if(tf == PERIOD_D1) return "D1";
   if(tf == PERIOD_H4) return "H4"; if(tf == PERIOD_H1) return "H1"; if(tf == PERIOD_M30) return "M30";
   if(tf == PERIOD_M15) return "M15"; if(tf == PERIOD_M5) return "M5"; if(tf == PERIOD_M1) return "M1";
   return "CUR";
}

void CStrategyOrchestrator::GetFlowState(string &tide, string &wind, string &trap, string &trigger, string &bridge)
{
   tide = m_mn1.is_valid ? EnumToString(m_mn1.origin_dir) : "NONE";
   wind = m_w1.is_valid ? EnumToString(m_w1.origin_dir) : "NONE";
   trap = m_d1.is_valid ? EnumToString(m_d1.origin_dir) : "NONE";
   trigger = m_h4.is_valid ? EnumToString(m_h4.origin_dir) : "NONE";
   bridge = CollectBridgeState();
}

string CStrategyOrchestrator::CollectBridgeState()
{
    string state = "";
    state += m_h4.is_valid ? (m_h4.origin_dir == DIRECTION_BULLISH ? "U" : (m_h4.origin_dir == DIRECTION_BEARISH ? "D" : "X")) : "X";
    state += m_h1.is_valid ? (m_h1.origin_dir == DIRECTION_BULLISH ? "U" : (m_h1.origin_dir == DIRECTION_BEARISH ? "D" : "X")) : "X";
    state += m_m30.is_valid ? (m_m30.origin_dir == DIRECTION_BULLISH ? "U" : (m_m30.origin_dir == DIRECTION_BEARISH ? "D" : "X")) : "X";
    return state;
}

#endif // V50_STRATEGYORCHESTRATOR_MQH
