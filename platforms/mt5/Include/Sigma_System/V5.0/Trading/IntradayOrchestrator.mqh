//+------------------------------------------------------------------+
//|                                        IntradayOrchestrator.mqh  |
//|                             Copyright 2026, Sigma Trading System |
//| V6.3: Intraday Execution Engine (Option B)                       |
//|   Gate 1: NARRATIVE POSTURE (T1 Lifecycle × T2 Bridge)           |
//|   Gate 2: RANGE POSITION   (ContextMapper Intraday)              |
//|   Gate 3: REWARD CHECK     (Wall Distance vs SL)                 |
//+------------------------------------------------------------------+
#ifndef V50_INTRADAYORCHESTRATOR_MQH
#define V50_INTRADAYORCHESTRATOR_MQH

#include "../Data/Structures.mqh"
#include "../Configuration/TradingParameters.mqh"
#include "ContextMapper.mqh"
#include "StrategyOrchestrator.mqh"

enum ENUM_T1_PHASE
{
   T1_CONQUEST,
   T1_SIEGE,
   T1_EXHAUSTION,
   T1_VACUUM,
   T1_INVALID
};

enum ENUM_BRIDGE_CLASS
{
   BRIDGE_FULL_ALIGN,
   BRIDGE_PARTIAL,
   BRIDGE_COUNTER,
   BRIDGE_NONE
};

class CIntradayOrchestrator
{
private:
   CContextMapper*         m_context;
   CStrategyOrchestrator*  m_swing;
   double                  m_current_price;

public:
                           CIntradayOrchestrator();
                          ~CIntradayOrchestrator();

   void  Initialize(CContextMapper *ctx, CStrategyOrchestrator *swing);
   void  UpdateState(double price, datetime time);
   bool  IsTradeAllowed(TradeSignalInfo &signal, double &out_tp, double &out_sl);

private:
   ENUM_T1_PHASE     DetermineT1Phase(const FlowState &mn1, const FlowState &w1, const FlowState &d1, ENUM_SIGNAL_DIRECTION dir);
   ENUM_BRIDGE_CLASS ClassifyBridge(const string &bridge, ENUM_SIGNAL_DIRECTION dir);
   double            GetEntryThreshold(ENUM_T1_PHASE phase, ENUM_BRIDGE_CLASS bridge_class);
   bool              IsWithinSession(datetime time);

   bool  Gate1_NarrativePosture(ENUM_SIGNAL_DIRECTION dir, double &entry_threshold, string &reason);
   bool  Gate2_RangePosition(ENUM_SIGNAL_DIRECTION dir, double price, double threshold, string &reason);
   bool  Gate3_RewardCheck(ENUM_SIGNAL_DIRECTION dir, double price, double sl_price,
                           double &target_price, string &reason);
};

//+------------------------------------------------------------------+
CIntradayOrchestrator::CIntradayOrchestrator() : m_context(NULL), m_swing(NULL), m_current_price(0) {}
CIntradayOrchestrator::~CIntradayOrchestrator() {}

void CIntradayOrchestrator::Initialize(CContextMapper *ctx, CStrategyOrchestrator *swing)
{
   m_context = ctx;
   m_swing = swing;
   Print("IntradayOrchestrator: Initialized (V6.3 Intraday Engine)");
}

void CIntradayOrchestrator::UpdateState(double price, datetime time)
{
   m_current_price = price;
}

//+------------------------------------------------------------------+
//| IsTradeAllowed: 3-Gate Intraday Authorization                    |
//+------------------------------------------------------------------+
bool CIntradayOrchestrator::IsTradeAllowed(TradeSignalInfo &signal, double &out_tp, double &out_sl)
{
   if(m_context == NULL || m_swing == NULL) return false;
   if(!InpEnableIntraday) return false;
   if(!IsWithinSession(TimeCurrent())) return false;

   double current_price = m_current_price;
   string reason = "";

   // === GATE 1: NARRATIVE POSTURE ===
   double entry_threshold = 0.40;
   string g1_reason = "";
   if(!Gate1_NarrativePosture(signal.direction, entry_threshold, g1_reason))
   {
      static datetime last_g1_log = 0;
      if(TimeCurrent() - last_g1_log > 300)
      {
         last_g1_log = TimeCurrent();
         PrintFormat(">> [INTRA G1 FAIL] %s | %s", EnumToString(signal.direction), g1_reason);
      }
      return false;
   }

   // === GATE 2: RANGE POSITION ===
   string g2_reason = "";
   if(!Gate2_RangePosition(signal.direction, current_price, entry_threshold, g2_reason))
   {
      return false;
   }

   // === GATE 3: REWARD CHECK ===
   double target_price = 0;
   string g3_reason = "";
   if(!Gate3_RewardCheck(signal.direction, current_price, signal.stop_loss, target_price, g3_reason))
   {
      PrintFormat(">> [INTRA G3 FAIL] %s | %s", EnumToString(signal.direction), g3_reason);
      return false;
   }

   // === ALL 3 GATES PASSED ===
   out_sl = (signal.direction == DIRECTION_BULLISH) 
            ? (signal.stop_loss - InpSLBufferPoints * _Point) 
            : (signal.stop_loss + InpSLBufferPoints * _Point);
   out_tp = target_price;

   signal.lifecycle_phase = StringFormat("INTRA|%s|%s|%s", g1_reason, g2_reason, g3_reason);
   signal.parent_tf = PERIOD_H1;

   PrintFormat(">> [INTRA AUTHORIZED] %s | G1:%s | G2:%s | G3:%s | TP:%.5f",
               EnumToString(signal.direction), g1_reason, g2_reason, g3_reason, target_price);

   return (out_sl != 0);
}

//+------------------------------------------------------------------+
//| Gate 1: Narrative Posture — T1 Lifecycle × T2 Bridge             |
//+------------------------------------------------------------------+
bool CIntradayOrchestrator::Gate1_NarrativePosture(ENUM_SIGNAL_DIRECTION dir, double &entry_threshold, string &reason)
{
   FlowState mn1, w1, d1;
   m_swing.GetFlowDirections(mn1, w1, d1);
   string bridge = m_swing.GetBridgeState();

   ENUM_T1_PHASE phase = DetermineT1Phase(mn1, w1, d1, dir);
   ENUM_BRIDGE_CLASS bridge_class = ClassifyBridge(bridge, dir);

   if(phase == T1_INVALID)
   {
      reason = "NoHTFContext";
      return false;
   }

   if(phase == T1_EXHAUSTION)
   {
      reason = "T1Exhaustion";
      return false;
   }

   if(phase == T1_SIEGE && bridge_class != BRIDGE_FULL_ALIGN)
   {
      reason = "Siege+NoAlign";
      return false;
   }

   if(bridge_class == BRIDGE_NONE)
   {
      reason = "NoBridge(XXX)";
      return false;
   }

   entry_threshold = GetEntryThreshold(phase, bridge_class);

   string phase_str = (phase == T1_CONQUEST) ? "Conquest" : (phase == T1_SIEGE) ? "Siege" : "Vacuum";
   string bridge_str = (bridge_class == BRIDGE_FULL_ALIGN) ? "Full" : 
                        (bridge_class == BRIDGE_PARTIAL) ? "Partial" : "Counter";
   reason = StringFormat("%s|%s|Thr:%.0f%%", phase_str, bridge_str, entry_threshold * 100);
   return true;
}

//+------------------------------------------------------------------+
//| Gate 2: Range Position — ContextMapper intraday position         |
//+------------------------------------------------------------------+
bool CIntradayOrchestrator::Gate2_RangePosition(ENUM_SIGNAL_DIRECTION dir, double price, double threshold, string &reason)
{
   double intraday_pos = m_context.GetIntradayPosition(price);

   if(dir == DIRECTION_BULLISH)
   {
      if(intraday_pos >= threshold)
      {
         reason = StringFormat("BuyHigh:%.0f%%>%.0f%%", intraday_pos * 100, threshold * 100);
         return false;
      }
   }
   else
   {
      double sell_threshold = 1.0 - threshold;
      if(intraday_pos <= sell_threshold)
      {
         reason = StringFormat("SellLow:%.0f%%<%.0f%%", intraday_pos * 100, sell_threshold * 100);
         return false;
      }
   }

   reason = StringFormat("Pos:%.0f%%", intraday_pos * 100);
   return true;
}

//+------------------------------------------------------------------+
//| Gate 3: Reward Check — wall distance vs stop loss                |
//+------------------------------------------------------------------+
bool CIntradayOrchestrator::Gate3_RewardCheck(ENUM_SIGNAL_DIRECTION dir, double price, double sl_price,
                                               double &target_price, string &reason)
{
   target_price = m_context.GetTargetCoordinate(dir, price);

   if(target_price == 0.0)
   {
      reason = "NoTarget";
      return false;
   }

   double wall_distance = MathAbs(target_price - price);
   double sl_distance = MathAbs(price - sl_price);

   if(sl_distance <= 0)
   {
      reason = "ZeroSL";
      return false;
   }

   double rr = wall_distance / sl_distance;

   if(rr < InpIntradayMinRR)
   {
      reason = StringFormat("RR:%.1f<%.1f", rr, InpIntradayMinRR);
      return false;
   }

   reason = StringFormat("RR:%.1f|TP:%.5f", rr, target_price);
   return true;
}

//+------------------------------------------------------------------+
//| DetermineT1Phase: Read macro lifecycle from FlowState            |
//+------------------------------------------------------------------+
ENUM_T1_PHASE CIntradayOrchestrator::DetermineT1Phase(const FlowState &mn1, const FlowState &w1, const FlowState &d1, ENUM_SIGNAL_DIRECTION dir)
{
   int aligned_count = 0;
   if(mn1.is_valid && mn1.origin_dir == dir) aligned_count++;
   if(w1.is_valid && w1.origin_dir == dir) aligned_count++;
   if(d1.is_valid && d1.origin_dir == dir) aligned_count++;

   if(aligned_count < 2) return T1_INVALID;

   bool shield_up = false;
   if(mn1.is_valid && (mn1.magnet_fifty_touched || mn1.magnet_L2_touched) && !mn1.is_siege_active) shield_up = true;
   if(w1.is_valid && (w1.magnet_fifty_touched || w1.magnet_L2_touched) && !w1.is_siege_active) shield_up = true;

   if(shield_up) return T1_EXHAUSTION;

   if(mn1.is_siege_active || w1.is_siege_active || d1.is_siege_active) return T1_SIEGE;

   if(mn1.is_valid && mn1.magnet_id == 0) return T1_VACUUM;

   return T1_CONQUEST;
}

//+------------------------------------------------------------------+
//| ClassifyBridge: Interpret the 3-char bridge state                |
//+------------------------------------------------------------------+
ENUM_BRIDGE_CLASS CIntradayOrchestrator::ClassifyBridge(const string &bridge, ENUM_SIGNAL_DIRECTION dir)
{
   if(StringLen(bridge) < 3) return BRIDGE_NONE;

   char target = (dir == DIRECTION_BULLISH) ? 'U' : 'D';
   char counter = (dir == DIRECTION_BULLISH) ? 'D' : 'U';

   int match = 0, oppose = 0, invalid = 0;
   for(int i = 0; i < 3; i++)
   {
      ushort c = StringGetCharacter(bridge, i);
      if(c == (ushort)target)  match++;
      else if(c == (ushort)counter) oppose++;
      else invalid++;
   }

   if(invalid == 3) return BRIDGE_NONE;
   if(match >= 2 && oppose == 0) return BRIDGE_FULL_ALIGN;
   if(oppose >= 2) return BRIDGE_COUNTER;
   return BRIDGE_PARTIAL;
}

//+------------------------------------------------------------------+
//| GetEntryThreshold: Dynamic zone from narrative posture           |
//+------------------------------------------------------------------+
double CIntradayOrchestrator::GetEntryThreshold(ENUM_T1_PHASE phase, ENUM_BRIDGE_CLASS bridge_class)
{
   if(phase == T1_CONQUEST)
   {
      if(bridge_class == BRIDGE_FULL_ALIGN) return 0.50;
      if(bridge_class == BRIDGE_COUNTER)    return 0.25;
      return 0.40;
   }
   if(phase == T1_SIEGE)
   {
      return 0.30;
   }
   if(phase == T1_VACUUM)
   {
      return 0.40;
   }
   return 0.40;
}

//+------------------------------------------------------------------+
//| IsWithinSession: Time filter for intraday entries                |
//+------------------------------------------------------------------+
bool CIntradayOrchestrator::IsWithinSession(datetime time)
{
   MqlDateTime dt;
   TimeToStruct(time, dt);

   int current_minutes = dt.hour * 60 + dt.min;

   string start_str = InpIntradaySessionStart;
   string end_str = InpIntradaySessionEnd;

   int start_h = (int)StringToInteger(StringSubstr(start_str, 0, 2));
   int start_m = (int)StringToInteger(StringSubstr(start_str, 3, 2));
   int end_h = (int)StringToInteger(StringSubstr(end_str, 0, 2));
   int end_m = (int)StringToInteger(StringSubstr(end_str, 3, 2));

   int start_minutes = start_h * 60 + start_m;
   int end_minutes = end_h * 60 + end_m;

   return (current_minutes >= start_minutes && current_minutes <= end_minutes);
}

#endif // V50_INTRADAYORCHESTRATOR_MQH
