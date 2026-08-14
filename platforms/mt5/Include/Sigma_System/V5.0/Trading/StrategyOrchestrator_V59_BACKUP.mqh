//+------------------------------------------------------------------+
//|                                         StrategyOrchestrator.mqh |
//|                             Copyright 2026, Sigma Trading System |
//| V5.2: Multi-Trap "Pure Gate" Logic                                |
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

//=== V5.0 FOUNDATION: FLOW STATE ===
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
   double            details_origin_L2;    // V5.3: Back of Wall
   double            details_magnet_L2;    // V5.3: Back of Wall
   bool              magnet_fifty_touched; // V5.4: T2 Touch
   bool              magnet_L2_touched;    // V5.4: T3 Touch
   double            details_outpost_price; 
   bool              is_valid;            
   bool              is_siege_active;     
   datetime          last_update_time;    
   datetime          origin_touch_time;   
   datetime          outpost_touch_time;  
   bool              anchor_is_traded;     // V5.7: Safety Trigger Flag
   bool              is_magnet_extreme;    // V5.8: Highest Magnet Filter
   
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

//=== V5.0 FOUNDATION: TRAP STATE (DEPRECATED for Multi-Trap) ===
struct TrapState
{
   ulong             trap_zone_id;        
   ENUM_TIMEFRAMES   timeframe;           
   ENUM_SIGNAL_DIRECTION direction;       
   datetime          freshness_time;      
   double            entry_price;         
   double            sl_price;            
   double            tp_price;            
   bool              is_authorized;       
   string            auth_reason;         
   
   TrapState() : trap_zone_id(0), timeframe(PERIOD_CURRENT), direction(DIRECTION_NONE),
                 freshness_time(0), is_authorized(false) {}
   
   void Reset()
   {
      trap_zone_id = 0; timeframe = PERIOD_CURRENT; direction = DIRECTION_NONE;
      freshness_time = 0; 
      entry_price = 0; sl_price = 0; tp_price = 0;
      is_authorized = false; auth_reason = "";
   }
};

class CStrategyOrchestrator
{
private:
   FlowState         m_mn1; 
   FlowState         m_w1;  
   FlowState         m_d1;  
   
   // V5.9: Recursive Bridge States (Officers)
   FlowState         m_h4;
   FlowState         m_h1;
   FlowState         m_m30;
   
public:
                     CStrategyOrchestrator();
                    ~CStrategyOrchestrator();

   void              Orchestrate(B2BZoneInfo &zones[], int zone_count);
   bool              IsTradeAllowed(TradeSignalInfo &signal, double &out_tp, double &out_sl);
   
   void              Initialize(CB2BDetector *detector);
   void              UpdateState(double current_price, datetime current_time, B2BZoneInfo &zones[], int total_zones, int change_mask);
   void              GetFlowState(string &tide, string &wind, string &trap, string &trigger, string &bridge); 
   void              SetDirty(bool dirty) {}
   
   bool              IsTradeAllowed(ENUM_SIGNAL_DIRECTION dir, ENUM_TIMEFRAMES tf,
                                   const B2BZoneInfo &zone, B2BZoneInfo &zones[], int total_zones,
                                   double &sl, double &tp,
                                   ulong &anchor_id, ulong &magnet_id,
                                   bool &is_with_trend, ENUM_TIMEFRAMES &parent_tf);

private:
   void              UpdateFlowState(B2BZoneInfo &zones[], int zone_count);
   void              UpdateTimeframeFlow(B2BZoneInfo &zones[], int zone_count, ENUM_TIMEFRAMES tf, FlowState &state);
   ulong             GetZoneIndexByID(ulong id, B2BZoneInfo &zones[], int count);
   ulong             GetLatestOutpost(ENUM_TIMEFRAMES tf, ENUM_SIGNAL_DIRECTION dir, double limit_price, datetime after_time, B2BZoneInfo &zones[], int count);
   // V5.4: Location Filter Scan
   ulong             IsInsideOpposingZone(ENUM_TIMEFRAMES scan_tf, ENUM_SIGNAL_DIRECTION dir, double current_price, B2BZoneInfo &zones[], int count, ulong siege_magnet_id = 0);
   bool              ValidateTrap(B2BZoneInfo &trap, FlowState &narrative, ENUM_TIMEFRAMES flow_tf);
   double            GetOfficerTarget();
   string            GetTFString(ENUM_TIMEFRAMES tf);
   string            CollectBridgeState();
};

CStrategyOrchestrator::CStrategyOrchestrator()
{
   m_mn1.Reset(); m_w1.Reset(); m_d1.Reset();
   m_h4.Reset();  m_h1.Reset();  m_m30.Reset();
}

CStrategyOrchestrator::~CStrategyOrchestrator() {}

void CStrategyOrchestrator::Orchestrate(B2BZoneInfo &zones[], int zone_count)
{
   UpdateFlowState(zones, zone_count);
}

void CStrategyOrchestrator::UpdateFlowState(B2BZoneInfo &zones[], int zone_count)
{
   // Tier 1: Narrative Generals
   UpdateTimeframeFlow(zones, zone_count, PERIOD_MN1, m_mn1);
   UpdateTimeframeFlow(zones, zone_count, PERIOD_W1, m_w1);
   UpdateTimeframeFlow(zones, zone_count, PERIOD_D1, m_d1);
   
   // Tier 2: Structural Officers (V5.9 Phase 1)
   UpdateTimeframeFlow(zones, zone_count, PERIOD_H4, m_h4);
   UpdateTimeframeFlow(zones, zone_count, PERIOD_H1, m_h1);
   UpdateTimeframeFlow(zones, zone_count, PERIOD_M30, m_m30);
   
   // Refresh Debug Timer
   static int log_timer = 0;
   if(TimeCurrent() % 60 == 0 && log_timer != (int)TimeCurrent()) 
   {
      log_timer = (int)TimeCurrent();
      string mn1_s = m_mn1.is_valid ? EnumToString(m_mn1.origin_dir) : "INVALID";
      string w1_s = m_w1.is_valid ? EnumToString(m_w1.origin_dir) : "INVALID";
      string d1_s = m_d1.is_valid ? EnumToString(m_d1.origin_dir) : "INVALID";
      
      // Officers (V5.9)
      string h4_s = m_h4.is_valid ? EnumToString(m_h4.origin_dir) : "INVALID";
      string h1_s = m_h1.is_valid ? EnumToString(m_h1.origin_dir) : "INVALID";
      string m30_s = m_m30.is_valid ? EnumToString(m_m30.origin_dir) : "INVALID";
      
      PrintFormat("=== V5.9 ORCHESTRATOR HEARTBEAT ===");
      PrintFormat("MN1 Tide: %s | Origin: #%04d -> Magnet: #%04d", mn1_s, m_mn1.origin_display_id, m_mn1.magnet_display_id);
      PrintFormat("W1 Wind:  %s | Origin: #%04d -> Magnet: #%04d", w1_s, m_w1.origin_display_id, m_w1.magnet_display_id);
      PrintFormat("D1 Path:  %s | Origin: #%04d -> Magnet: #%04d", d1_s, m_d1.origin_display_id, m_d1.magnet_display_id);
      PrintFormat(">>> OFFICERS: H4:#%04d -> #%04d | H1:#%04d -> #%04d | M30:#%04d -> #%04d", 
                  m_h4.origin_display_id, m_h4.magnet_display_id,
                  m_h1.origin_display_id, m_h1.magnet_display_id,
                  m_m30.origin_display_id, m_m30.magnet_display_id);
   }
}

void CStrategyOrchestrator::UpdateTimeframeFlow(B2BZoneInfo &zones[], int zone_count, ENUM_TIMEFRAMES tf, FlowState &state)
{
   double current_price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if(state.is_valid)
   {
      int origin_idx = (int)GetZoneIndexByID(state.origin_id, zones, zone_count);
      int magnet_idx = (int)GetZoneIndexByID(state.magnet_id, zones, zone_count);
      if(origin_idx == -1) { state.Reset(); return; }
      
      // Update data for the persisting Origin (V5.2 Fix: Keep touch times synced)
      state.origin_touch_time = zones[origin_idx].L1_touch_time;
      state.details_origin_price = zones[origin_idx].L1_price;
      state.details_origin_L2 = zones[origin_idx].L2_price; // V5.3
      
      bool defeat = false;
      if(state.origin_dir == DIRECTION_BULLISH && current_price < zones[origin_idx].L2_price) defeat = true;
      if(state.origin_dir == DIRECTION_BEARISH && current_price > zones[origin_idx].L2_price) defeat = true;
      if(defeat) { state.Reset(); return; }
      
      // Check Successor (Magnet Touch)
      if(magnet_idx != -1)
      {
         state.magnet_fifty_touched = zones[magnet_idx].fifty_touched; // V5.4
         state.magnet_L2_touched = zones[magnet_idx].L2_touched;       // V5.4
         if(zones[magnet_idx].L2_touched) 
         {
            ulong successor_id = GetLatestOutpost(tf, state.origin_dir, current_price, zones[origin_idx].zone_created_time, zones, zone_count);
            if(successor_id > 0) { 
               state.origin_id = successor_id; 
               state.origin_display_id = (int)(successor_id % 10000); 
               state.magnet_id = 0; 
               state.magnet_display_id = 0; 
               state.is_siege_active = false;
               
               // V5.7: Successor inherits status based on current touch state
               int succ_idx = (int)GetZoneIndexByID(successor_id, zones, zone_count);
               if(succ_idx != -1) state.anchor_is_traded = zones[succ_idx].L1_touched;
               else state.anchor_is_traded = false;
            }
            else { 
               // V5.8: ATH Discovery Protection
               // If we are at ATH/ATL and no successor exists, do NOT reset the origin.
               if(m_mn1.magnet_id == 0 && (tf == PERIOD_D1 || tf == PERIOD_W1 || tf == PERIOD_H4 || tf == PERIOD_H1 || tf == PERIOD_M30)) {
                  state.magnet_id = 0; 
                  state.magnet_display_id = 0; 
                  state.is_siege_active = false;
               }
               else state.Reset(); 
               return; 
            }
         }
      }
      // Remove old incomplete siege trigger - now handled in Outpost section
      // else if(zones[magnet_idx].L1_touched) state.is_siege_active = true; 
      if(magnet_idx == -1 && state.magnet_id != 0) state.magnet_id = 0;
      
      // Always Update Outpost if we have a valid Origin
      ulong latest_outpost_id = GetLatestOutpost(tf, state.origin_dir, current_price, zones[origin_idx].zone_created_time, zones, zone_count);
      if(latest_outpost_id > 0)
      {
         state.outpost_id = latest_outpost_id;
         int outpost_idx = (int)GetZoneIndexByID(latest_outpost_id, zones, zone_count);
          if(outpost_idx != -1) 
          { 
              state.outpost_touch_time = zones[outpost_idx].L1_touch_time; 
              
              // V5.7: SAFETY TRIGGER (Anchor Must Be Traded)
              // Check if Outpost (Current Anchor) has been touched to authorize Flow
              // FIX: FORCE RESET if new outpost is untraded.
              bool outpost_hit = (zones[outpost_idx].L1_touched);
              
              // If we switched to a NEW Outpost, we must adopt its status (usually false)
              // If we are on the SAME Outpost, we only update if it becomes true (monotonic)
              // Actually, simply assigning the current status is correct and self-correcting.
              state.anchor_is_traded = outpost_hit;
             
             // V5.5 SIEGE TRIGGER:
             // Logic: We hit the wall (Magnet), bounced back, and CONFIRMED support at Outpost.
             // If Outpost touch is FRESHER than Magnet touch => SIEGE MODE ACTIVE.
             if(state.magnet_id > 0 && magnet_idx != -1 && zones[magnet_idx].L1_touched)
             {
                 // Check timestamps
                 if(state.outpost_touch_time > zones[magnet_idx].L1_touch_time)
                 {
                     state.is_siege_active = true;
                 }
                 else
                 {
                     state.is_siege_active = false;
                 }
             }
         }
      }
      else { state.outpost_id = 0; state.details_outpost_price = 0; state.outpost_touch_time = 0; state.is_siege_active = false; }
      
      // V5.4: Replaced Roadblock Scan with Location Filter
      // Pass the siege state to allow "Bulldozer Mode"
      state.roadblock_id = IsInsideOpposingZone(tf, state.origin_dir, current_price, zones, zone_count, state.is_siege_active ? state.magnet_id : 0);
      
      if(state.magnet_id != 0) 
      {
          // V5.8: Refresh Structural Supremacy for existing magnet
          state.is_magnet_extreme = true;
          for(int i=0; i<zone_count; i++) {
              if(zones[i].timeframe == tf && zones[i].direction == state.magnet_dir && zones[i].IsValid()) {
                  if(state.magnet_dir == DIRECTION_BEARISH) { if(zones[i].L1_price > state.details_magnet_price) { state.is_magnet_extreme = false; break; } }
                  else { if(zones[i].L1_price < state.details_magnet_price) { state.is_magnet_extreme = false; break; } }
              }
          }
          return; // Full flow active
      }
   }
   
   // Handle Vacuum or New Origin search
   int best_origin_idx = -1;
   if(state.origin_id != 0) best_origin_idx = (int)GetZoneIndexByID(state.origin_id, zones, zone_count);
   else
   {
      datetime latest_time = 0;
      for(int i=0; i<zone_count; i++)
      {
         if(zones[i].timeframe != tf || !zones[i].IsValid()) continue;
         
         // V5.8: Macro Direction Preference in Discovery Mode (ATH/ATL)
         // At price extremes, we forbid the search loop from picking a zone that opposes the MN1 Tide.
         // This forces the "Hijacker" zone into the Magnet category where it belongs for a Fade.
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
      state.origin_dir = (zones[best_origin_idx].direction == DIRECTION_BEARISH) ? DIRECTION_BEARISH : DIRECTION_BULLISH;
      state.details_origin_price = zones[best_origin_idx].L1_price;
      state.details_origin_L2 = zones[best_origin_idx].L2_price; // V5.3
      state.origin_touch_time = zones[best_origin_idx].L1_touch_time;
      state.last_update_time = MathMax(zones[best_origin_idx].L1_touch_time, zones[best_origin_idx].zone_created_time);
      state.is_valid = true;
      state.anchor_is_traded = (zones[best_origin_idx].L1_touched); // V5.7: strict check at start
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
          state.details_magnet_L2 = zones[best_magnet_idx].L2_price; // V5.3
          state.magnet_fifty_touched = zones[best_magnet_idx].fifty_touched; // V5.4
          state.magnet_L2_touched = zones[best_magnet_idx].L2_touched;       // V5.4
          
          // V5.8: Structural Supremacy Check (Highest Magnet)
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
      // V5.4: Replaced Roadblock Scan with Location Filter
      // Pass the siege state to allow "Bulldozer Mode"
      state.roadblock_id = IsInsideOpposingZone(tf, state.origin_dir, current_price, zones, zone_count, state.is_siege_active ? state.magnet_id : 0);
   }
   else state.Reset();
}

ulong CStrategyOrchestrator::GetLatestOutpost(ENUM_TIMEFRAMES tf, ENUM_SIGNAL_DIRECTION dir, double limit_price, datetime after_time, B2BZoneInfo &zones[], int count)
{
   int best_idx = -1; 
   datetime best_time = after_time; // Must be newer than Origin
   
   // V5.6.4: STRICT LINEAR LOGIC (Zombie Fix)
   // Instead of finding the "newest valid" zone (which falls back to old ones),
   // We find the ABSOLUTE NEWEST candidate zone.
   // If the newest candidate is broken, the TREND IS BROKEN. We return 0.
   
   for(int i=0; i<count; i++)
   {
      if(zones[i].timeframe != tf || zones[i].direction != dir) continue;
      if(!zones[i].IsValid()) continue; // Ignore deleted/invalid slots
      
      // Candidate Check: Is it newer than our baseline (Origin)?
      if(zones[i].zone_created_time > best_time)
      {
          best_time = zones[i].zone_created_time;
          best_idx = i;
      }
   }
   
   // Now validating the champion
   if(best_idx != -1)
   {
       // Is the champion broken by price?
       bool is_broken = (dir == DIRECTION_BULLISH) 
                        ? (limit_price < zones[best_idx].L2_price) 
                        : (limit_price > zones[best_idx].L2_price);
                        
       if(is_broken) 
       {
           // The latest outpost failed. The trend leg is broken.
           // We do NOT return an older outpost. We return 0 to force a reset.
           return 0; 
       }
       
       // Champion is alive. Long live the trend.
       return zones[best_idx].zone_id;
   }
   
   return 0; // No outpost found
}

// V5.4: Location Filter (Are we INSIDE an enemy zone?)
// V5.5: SIEGE MODE - If siege_magnet_id > 0, we IGNORE that specific zone if it's the block.
ulong CStrategyOrchestrator::IsInsideOpposingZone(ENUM_TIMEFRAMES scan_tf, ENUM_SIGNAL_DIRECTION dir, double current_price, B2BZoneInfo &zones[], int count, ulong siege_magnet_id)
{
   ulong blocked_by = 0;
   // Rule: 
   // MN1 Trade: Ignores everything (Returns 0).
   // W1 Trade: Checks MN1 Opposing Zone.
   // D1 Trade: Checks W1 & MN1 Opposing Zones.
   
   if(scan_tf == PERIOD_MN1) return 0; // Tide ignores location
   
   bool check_mn1 = true;
   bool check_w1 = (scan_tf == PERIOD_D1); // Only D1 checks W1
   
   for(int i=0; i<count; i++)
   {
      if(!zones[i].IsValid()) continue;
      if(zones[i].direction == dir) continue; // Ignore same-direction zones
      
      bool tf_match = false;
      if(check_mn1 && zones[i].timeframe == PERIOD_MN1) tf_match = true;
      if(check_w1 && zones[i].timeframe == PERIOD_W1) tf_match = true;
      if(!tf_match) continue;
      
      // V5.7: BULLDOZER MODE - If zone is pierced, it's not a wall.
      if(zones[i].L2_touched) continue;
      
      // Location Check: Is current_price INSIDE L1-L2?
      // Note: L1/L2 might be flipped depending on direction, so use Min/Max
      double high = MathMax(zones[i].L1_price, zones[i].L2_price);
      double low = MathMin(zones[i].L1_price, zones[i].L2_price);
      
      if(current_price <= high && current_price >= low)
      {
          if(siege_magnet_id > 0 && zones[i].zone_id == siege_magnet_id)
          {
              // 3.2 BULLDOZER MODE: We are inside the enemy base, BUT Siege is active.
              // We IGNORE this specific blocker to allow the break.
              continue; 
          }
          
          blocked_by = zones[i].zone_id;
          break; // Found a blocker, stop.
      }
   }
   return blocked_by;
}

ulong CStrategyOrchestrator::GetZoneIndexByID(ulong id, B2BZoneInfo &zones[], int count)
{
   for(int i=0; i<count; i++) { if(zones[i].zone_id == id) return i; }
   return -1;
}

bool CStrategyOrchestrator::ValidateTrap(B2BZoneInfo &trap, FlowState &narrative, ENUM_TIMEFRAMES flow_tf)
{
   if(trap.direction != narrative.origin_dir) return false;
   bool freshness_ok = false;
   
   // Guard 1: Freshness (Timing)
   // V5.6.5: RELATIVE FRESHNESS (Stale Trap Fix)
   // Old Logic: Check against Grand Origin (Allowed stale traps in long trends).
   // New Logic: 
   // - If Free Flow (Outpost > 0): Trap must be newer than OUTPOST. (Current Leg)
   // - If Strict Mode (Outpost == 0): Trap must be newer than ORIGIN. (Initial reaction)
   
   // FIX V5.6.5: Falling Knife Protection.
   // We use OUTPOST TOUCH TIME, not CREATION TIME.
   // This forces traps to be Reactionary Bounces, not Stale Stairs from the ascent.
   datetime freshness_baseline = narrative.origin_touch_time;
   if(narrative.outpost_id > 0)
   {
       if(narrative.outpost_touch_time > 0) freshness_baseline = narrative.outpost_touch_time;
       else freshness_baseline = TimeCurrent(); // Untouched Outpost -> Block All Traps
   }
   
   if(trap.zone_created_time <= freshness_baseline) return false;
   
   // V5.6.3: GLOBAL FADE AWARENESS (The Shield Check)
   // Before we authorize ANY Free Flow, we must ensure higher timeframe magnets are not Fading.
   // Shield Up = Magnet T2/T3 Touched AND Siege OFF.
   
   bool mn1_shield_up = (m_mn1.is_valid && (m_mn1.magnet_fifty_touched || m_mn1.magnet_L2_touched) && !m_mn1.is_siege_active);
   bool w1_shield_up = (m_w1.is_valid && (m_w1.magnet_fifty_touched || m_w1.magnet_L2_touched) && !m_w1.is_siege_active);
   
   // 1. MN1 SHIELD (The Tide Wall)
   // Only MN1 itself can trade against its own shield (if Siege Active context, but here Siege is OFF).
   // So effectively, MN1 Shield blocks EVERYTHING unless Siege is ON.
   if(mn1_shield_up)
   {
       // If local flow IS MN1, we might allow it if we are inside the zone (Pullback Logic handles this separately).
       // But for Standard Flow (Trap Validation), we are blocked.
       return false; 
   }
   
   // 2. W1 SHIELD (The Wave Wall)
   // Blocks D1. (W1 can trade its own fade via Pullback logic, but here we validate Standard Flow).
   if(flow_tf == PERIOD_D1 && w1_shield_up) return false;
   
   
   // V5.7: TRAP LIBERATION (Safety First)
   // If Outpost exists AND has been traded (Safety Trigger), we allow Continuation.
   // If No Outpost OR Outpost untraded, we require Strict Nesting.
   
   bool is_free_flow = (narrative.outpost_id > 0 && narrative.anchor_is_traded);
   
   if(is_free_flow)
   {
       // FREE FLOW MODE (Continuation)
       // Constraint: Local Magnet Fade Check (Moving "Anti-Fade" here)
       // If Local Magnet is Fading, we block Free Flow.
       if((narrative.magnet_fifty_touched || narrative.magnet_L2_touched) && !narrative.is_siege_active)
       {
           return false; // BLOCKED: Local Magnet is Fading.
       }
       
       // If coast is clear (Global & Local), trade is allowed.
       // No spatial check needed.
   }
   else
   {
       // STRICT MODE (Refusing to lose)
       // No Outpost = No Trend. We force strict spatial nesting inside Origin.
       if(trap.direction == DIRECTION_BULLISH) { 
           if(trap.L1_price > narrative.details_origin_price + _Point) return false; 
       } else { 
           if(trap.L1_price < narrative.details_origin_price - _Point) return false; 
       }
   }
   
   return true;
}

bool CStrategyOrchestrator::IsTradeAllowed(TradeSignalInfo &signal, double &out_tp, double &out_sl)
{
   double current_price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   bool authorized = false; double target_price = 0; string reason = "";
   B2BZoneInfo zone; 
   zone.zone_id = signal.zone_id; 
   zone.timeframe = signal.zone_tf; 
   zone.direction = signal.direction;   
   zone.L1_price = signal.entry_price; 
   zone.L2_price = signal.stop_loss; 
   zone.zone_created_time = signal.signal_time;
   
   // === V5.5 GLOBAL SIEGE GUARD ===
   if(m_mn1.is_siege_active && signal.direction != m_mn1.origin_dir) return false;
   if(m_w1.is_siege_active && signal.direction != m_w1.origin_dir) return false;
   if(m_d1.is_siege_active && signal.direction != m_d1.origin_dir) return false;
   
   // === V5.7 HANDOVER LOGIC (Freshness Protocol) ===
   bool d1_fresh_override = false;
   bool w1_fresh_override = false;
   
   if(m_d1.is_valid && m_d1.origin_dir == signal.direction)
   {
       if(m_mn1.is_valid && m_d1.origin_dir == m_mn1.origin_dir && m_d1.origin_touch_time > m_mn1.origin_touch_time) d1_fresh_override = true;
       if(m_w1.is_valid && m_d1.origin_dir == m_w1.origin_dir && m_d1.origin_touch_time > m_w1.origin_touch_time) d1_fresh_override = true;
   }
   if(m_w1.is_valid && m_w1.origin_dir == signal.direction)
   {
       if(m_mn1.is_valid && m_w1.origin_dir == m_mn1.origin_dir && m_w1.origin_touch_time > m_mn1.origin_touch_time) w1_fresh_override = true;
   }

   // 1. MN1 AUTHORITY (The Tide)
   if(!d1_fresh_override && !w1_fresh_override && m_mn1.is_valid && ValidateTrap(zone, m_mn1, PERIOD_MN1))
   {
      authorized = true; 
      target_price = m_mn1.details_magnet_L2; 
      reason = "MN1 Flow (Tide)"; 
      
      // V5.9 DISCOVERY HANDOVER (Greedy Vacuum Protocol)
      if(target_price == 0 && m_mn1.magnet_id == 0 && m_w1.magnet_id == 0 && m_d1.magnet_id == 0)
      {
          double officer_tp = GetOfficerTarget();
          if(officer_tp > 0)
          {
              target_price = officer_tp;
              reason += " (Officer Handover)";
          }
          else reason += " (Discovery)";
      }
      else if(target_price == 0) reason += " (Discovery)";

      PrintFormat(">> [V5.9] AUTH: MN1 Layer | Target:%.5f | Reason:%s", target_price, reason);
      signal.parent_tf = PERIOD_MN1;
      signal.anchor_id = m_mn1.origin_id; 
      signal.outpost_id = (m_mn1.outpost_id > 0) ? m_mn1.outpost_id : 0;   }
   
   // 2. W1 AUTHORITY (The Wave) 
   if(!authorized && !d1_fresh_override && m_w1.is_valid) 
   {
      if(ValidateTrap(zone, m_w1, PERIOD_W1))
      {
         if(m_mn1.is_valid && m_w1.origin_dir != m_mn1.origin_dir)
         {
             if((m_mn1.magnet_fifty_touched || m_mn1.magnet_L2_touched) && !m_mn1.is_siege_active)
             {
                 double mag_fifty = m_mn1.details_magnet_price + (m_mn1.details_magnet_L2 - m_mn1.details_magnet_price) * 0.5;
                 double core_high = MathMax(m_mn1.details_magnet_L2, mag_fifty);
                 double core_low = MathMin(m_mn1.details_magnet_L2, mag_fifty);
                 if(current_price <= core_high && current_price >= core_low)
                 {
                     authorized = true;
                     reason = "W1 Pullback (Magnet Reaction)";
                     target_price = m_mn1.details_origin_L2 > 0 ? m_mn1.details_origin_L2 : m_w1.details_magnet_L2;
                     PrintFormat(">> [V5.9] AUTH: W1 Pullback | Target:%.5f", target_price);
                     signal.parent_tf = PERIOD_W1;
                     signal.anchor_id = m_w1.origin_id;
                     signal.outpost_id = (m_w1.outpost_id > 0) ? m_w1.outpost_id : 0;                 }
             }
         }
         else 
         {
             if(m_w1.roadblock_id == 0)
             {
                 authorized = true;
                 reason = w1_fresh_override ? "W1 Flow (Handover)" : "W1 Flow";
                 target_price = m_mn1.details_magnet_L2 > 0 ? m_mn1.details_magnet_L2 : m_w1.details_magnet_L2;
                 if(target_price == 0) target_price = m_w1.details_magnet_L2;

                 // V5.9 DISCOVERY HANDOVER (Greedy Vacuum Protocol)
                 if(target_price == 0 && m_mn1.magnet_id == 0 && m_w1.magnet_id == 0 && m_d1.magnet_id == 0)
                 {
                     double officer_tp = GetOfficerTarget();
                     if(officer_tp > 0)
                     {
                         target_price = officer_tp;
                         reason += " (Officer Handover)";
                     }
                     else reason += " (Discovery)";
                 }
                 else if(target_price == 0) reason += " (Discovery)";
                 
                 PrintFormat(">> [V5.9] AUTH: W1 Layer | Target:%.5f | Reason:%s", target_price, reason);
                 signal.parent_tf = PERIOD_W1;
                 signal.anchor_id = m_w1.origin_id;
                 signal.outpost_id = (m_w1.outpost_id > 0) ? m_w1.outpost_id : 0;
                 signal.bridge_state = CollectBridgeState();
             }
         }
      }
   }
   
   // 2.5 SPECIAL: AGGRESSIVE PULLBACK 
   if(!authorized && m_mn1.is_valid && (m_mn1.magnet_fifty_touched || m_mn1.magnet_L2_touched))
   {
       double mag_fifty = m_mn1.details_magnet_price + (m_mn1.details_magnet_L2 - m_mn1.details_magnet_price) * 0.5;
       double core_high = MathMax(m_mn1.details_magnet_L2, mag_fifty);
       double core_low = MathMin(m_mn1.details_magnet_L2, mag_fifty);
       if(current_price <= core_high && current_price >= core_low && signal.direction != m_mn1.origin_dir && !m_mn1.is_siege_active)
       {
            authorized = true;
            reason = "Aggressive Magnet Fade (Core T2/T3 Only)";
            target_price = m_mn1.details_origin_L2 > 0 ? m_mn1.details_origin_L2 : signal.entry_price; 
            PrintFormat(">> [V5.9] AUTH: Aggressive Fade | Target:%.5f", target_price);
            signal.parent_tf = PERIOD_MN1; 
            signal.anchor_id = m_mn1.magnet_id; 
            signal.outpost_id = m_mn1.origin_id; 
            signal.bridge_state = CollectBridgeState();
       }
   }

   // 2.7 W1 MAGNET FADE (New V5.8)
   if(!authorized && m_w1.is_valid && (m_w1.magnet_fifty_touched || m_w1.magnet_L2_touched))
   {
       double mag_fifty = m_w1.details_magnet_price + (m_w1.details_magnet_L2 - m_w1.details_magnet_price) * 0.5;
       double core_high = MathMax(m_w1.details_magnet_L2, mag_fifty);
       double core_low = MathMin(m_w1.details_magnet_L2, mag_fifty);
       if(current_price <= core_high && current_price >= core_low && signal.direction != m_w1.origin_dir && !m_w1.is_siege_active)
       {
           authorized = true;
           reason = "W1 Magnet Fade (V5.8)";
           target_price = m_w1.details_origin_L2;
           PrintFormat(">> [V5.9] AUTH: W1 Fade | Target:%.5f", target_price);
           signal.parent_tf = PERIOD_W1;
           signal.anchor_id = m_w1.magnet_id;
           signal.outpost_id = m_w1.origin_id;
       }
   }

   // 2.8 D1 ATH MAGNET FADE (New V5.8)
   if(!authorized && m_d1.is_valid && m_mn1.magnet_id == 0 && (m_d1.magnet_fifty_touched || m_d1.magnet_L2_touched))
   {
       double mag_fifty = m_d1.details_magnet_price + (m_d1.details_magnet_L2 - m_d1.details_magnet_price) * 0.5;
       double core_high = MathMax(m_d1.details_magnet_L2, mag_fifty);
       double core_low = MathMin(m_d1.details_magnet_L2, mag_fifty);
       if(m_d1.is_magnet_extreme && (current_price <= core_high && current_price >= core_low) && signal.direction != m_d1.origin_dir && !m_d1.is_siege_active)
       {
           authorized = true;
           reason = "D1 ATH Magnet Fade (V5.8)";
           target_price = m_d1.details_origin_L2;
           PrintFormat(">> [V5.9] AUTH: D1 ATH Fade | Target:%.5f", target_price);
           signal.parent_tf = PERIOD_D1;
           signal.anchor_id = m_d1.magnet_id;
           signal.outpost_id = m_d1.origin_id;
       }
   }

   // 3. D1 AUTHORITY (The Path)
   if(!authorized && m_d1.is_valid) 
   {
      if(ValidateTrap(zone, m_d1, PERIOD_D1))
      {
         if(m_d1.roadblock_id == 0) 
         {
             authorized = true; 
             target_price = (m_w1.is_valid && m_d1.origin_dir == m_w1.origin_dir && m_w1.details_magnet_L2 > 0) ? m_w1.details_magnet_L2 : m_d1.details_magnet_L2;
             if(target_price == 0) target_price = m_d1.details_magnet_L2;
             reason = d1_fresh_override ? "D1 Flow (Handover)" : "D1 Flow"; 

              // V5.9 DISCOVERY HANDOVER (Greedy Vacuum Protocol)
              if(target_price == 0 && m_mn1.magnet_id == 0 && m_w1.magnet_id == 0 && m_d1.magnet_id == 0)
              {
                  double officer_tp = GetOfficerTarget();
                  if(officer_tp > 0)
                  {
                      target_price = officer_tp;
                      reason += " (Officer Handover)";
                  }
                  else reason += " (Discovery)";
              }
              else if(target_price == 0) reason += " (Discovery)";
              
              PrintFormat(">> [V5.9] AUTH: D1 Layer | Target:%.5f | Reason:%s", target_price, reason);
              signal.parent_tf = PERIOD_D1;
              signal.anchor_id = m_d1.origin_id;
              signal.outpost_id = (m_d1.outpost_id > 0) ? m_d1.outpost_id : 0;         }
      }
   }
   
   signal.lifecycle_phase = reason;
   
   if(!authorized) 
   {
      static datetime last_log = 0;
      if(TimeCurrent() - last_log > 300) 
      {
          last_log = TimeCurrent();
          ulong blocker = 0;
          if(m_w1.is_valid && m_w1.roadblock_id != 0) blocker = m_w1.roadblock_id;
          if(m_d1.is_valid && m_d1.roadblock_id != 0) blocker = m_d1.roadblock_id;
          
          if(blocker > 0)
             PrintFormat(">> [BLOCK] Trap:%s Born:%s @P:%.5f | Location Unsafe (Inside Zone:#%04d)", 
                         GetTFString(signal.zone_tf), TimeToString(zone.zone_created_time, TIME_DATE|TIME_MINUTES),
                         zone.L1_price, blocker % 10000);
          else
             PrintFormat(">> [FAIL] Trap:%s Born:%s @P:%.5f | No Structural Authorization (Tide/Wind/Path Mismatch)", 
                         GetTFString(signal.zone_tf), TimeToString(zone.zone_created_time, TIME_DATE|TIME_MINUTES),
                         zone.L1_price);
      }
      return false;
   }
   
   out_sl = (signal.direction == DIRECTION_BULLISH) ? (signal.stop_loss - InpSLBufferPoints * _Point) : (signal.stop_loss + InpSLBufferPoints * _Point);
   out_tp = target_price;
   return (out_sl != 0);
}

double CStrategyOrchestrator::GetOfficerTarget()
{
   if(m_h4.is_valid && m_h4.details_magnet_L2 > 0) return m_h4.details_magnet_L2;
   if(m_h1.is_valid && m_h1.details_magnet_L2 > 0) return m_h1.details_magnet_L2;
   if(m_m30.is_valid && m_m30.details_magnet_L2 > 0) return m_m30.details_magnet_L2;
   return 0;
}

string CStrategyOrchestrator::GetTFString(ENUM_TIMEFRAMES tf)
{
   if(tf == PERIOD_H4) return "H4";
   if(tf == PERIOD_H1) return "H1";
   if(tf == PERIOD_M30) return "M30";
   if(tf == PERIOD_M15) return "M15";
   if(tf == PERIOD_M5) return "M5";
   if(tf == PERIOD_M1) return "M1";
   if(tf == PERIOD_D1) return "D1";
   if(tf == PERIOD_W1) return "W1";
   if(tf == PERIOD_MN1) return "MN1";
   return "CUR";
}

void CStrategyOrchestrator::Initialize(CB2BDetector *detector) { }
void CStrategyOrchestrator::UpdateState(double current_price, datetime current_time, B2BZoneInfo &zones[], int total_zones, int change_mask) { Orchestrate(zones, total_zones); }

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

bool CStrategyOrchestrator::IsTradeAllowed(ENUM_SIGNAL_DIRECTION dir, ENUM_TIMEFRAMES tf, const B2BZoneInfo &zone, B2BZoneInfo &zones[], int total_zones, double &sl, double &tp, ulong &anchor_id, ulong &magnet_id, bool &is_with_trend, ENUM_TIMEFRAMES &parent_tf)
{ return false; }

#endif // V50_STRATEGYORCHESTRATOR_MQH
