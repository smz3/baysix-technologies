//+------------------------------------------------------------------+
#ifndef QUANT_LOGGER_MQH
#define QUANT_LOGGER_MQH

#property strict

#include <Sigma_System/V5.0/Data/QuantTypes.mqh>
#include <Sigma_System/V5.0/Configuration/TradingParameters.mqh>
// #include <Sigma_System/V5.0/Trading/TradeSignalGenerator.mqh> // REMOVED

// extern CTradeSignalGenerator g_SignalGenerator; // REMOVED

//+------------------------------------------------------------------+
//| CQuantLogger                                                     |
//| Handles logging of trades to CSV for Supabase Python Loader      |
//+------------------------------------------------------------------+
class CQuantLogger
{
private:
   QuantTradeExport  m_trades[];         // Internal trade array
   int               m_trade_count;      // Number of trades logged
   bool              m_zones_enabled;    // Feature flag for zone logging
   string            m_folder_path;
   string            m_filename_trades;
   string            m_filename_zones;
   
   int               m_zone_file_handle; // Handle for real-time zone logging
   bool              m_zone_header_written;
   
public:
                     CQuantLogger();
                    ~CQuantLogger() {}
   
   //--- Init
   bool              Initialize();
   
   //--- Core Logging
   void              LogTrade(QuantTradeExport &trade);
   
   //--- History Reconciliation (Backtest Exit Data)
   void              ReconcileHistory();
   
   //--- Export
   bool              ExportCSV(const string filename);
   void              LogParameters(void);
   
   //--- Helpers
   static string     GetTradingSession(datetime time);
   static string     GetTradingSessionZone(datetime time); // From ZoneLogger
   static string     GetTouchQuarterZone(datetime time);  // From ZoneLogger
   static string     ToCSV(QuantTradeExport &trade);
   // static string     SerializeGPS(const MarketFlowGPSData &gps); // REMOVED
   // static string     FormatJSONForCSV(string json); // REMOVED
   
   //--- Zone Logging (Consolidated from ZoneLogger)
   void              SetZoneLogging(bool enabled) { m_zones_enabled = enabled; }
   void              LogZoneCreated(const B2BZoneInfo &zone);
   void              LogZoneTouched(const B2BZoneInfo &zone, string touch_level);
   void              LogZoneSurvived(const B2BZoneInfo &zone);
   void              LogZoneBulldozed(const B2BZoneInfo &zone);
   
   //--- State Updates
   void              UpdateBEStatus(long ticket, bool activated);
   
private:
   bool              OpenZoneFile();
   void              CloseZoneFile();
   void              WriteZoneEntry(const ZoneLogEntry &entry);
   string            BuildZoneCSVLine(const ZoneLogEntry &entry);
   string            GetTouchDepth(const B2BZoneInfo &zone);
   string            ZoneIdToString(ulong id);
   
   //--- Stats
   int               TradeCount() const { return m_trade_count; }
};

//+------------------------------------------------------------------+
//| Constructor                                                      |
//+------------------------------------------------------------------+
CQuantLogger::CQuantLogger() : m_trade_count(0), m_zones_enabled(false), m_zone_file_handle(INVALID_HANDLE), m_zone_header_written(false)
{
   m_folder_path = "SIGMA_Quant";
}

//+------------------------------------------------------------------+
//| Initialize                                                       |
//+------------------------------------------------------------------+
bool CQuantLogger::Initialize()
{
   string date_str = TimeToString(TimeCurrent(), TIME_DATE);
   StringReplace(date_str, ".", "_");
   
   // Create directories
   string trades_path = m_folder_path + "\\Trades";
   string zones_path = m_folder_path + "\\Zones";
   
   if(!FolderCreate(m_folder_path, FILE_COMMON)) 
      Print("[QuantLogger] Note: Quant folder might already exist");
   if(!FolderCreate(trades_path, FILE_COMMON))
      Print("[QuantLogger] Note: Trades folder might already exist");
   if(!FolderCreate(zones_path, FILE_COMMON))
      Print("[QuantLogger] Note: Zones folder might already exist");
      
   m_filename_trades = trades_path + "\\QUANT_TRADES_" + date_str + ".csv";
   m_filename_zones = zones_path + "\\QUANT_ZONES_" + date_str + ".csv";
   
   ArrayResize(m_trades, 0);
   m_trade_count = 0;
   
   Print("[QuantLogger] Initialized. Trades Output: ", m_filename_trades);
   Print("[QuantLogger] Zones Output: ", m_filename_zones);
   return true;
}

//+------------------------------------------------------------------+
//| LogParameters - Export "DNA Card" (Protocol Audit)                |
//+------------------------------------------------------------------+
void CQuantLogger::LogParameters(void)
  {

   



   // Define Param Filename: QUANT_PARAMS_YYYY_MM_DD.json
   string date_str = TimeToString(TimeCurrent(), TIME_DATE);
   StringReplace(date_str, ".", "_");
   string filename = m_folder_path + "\\Trades\\QUANT_PARAMS_" + date_str + ".json";
   
   int handle = FileOpen(filename, FILE_WRITE|FILE_TXT|FILE_ANSI);
   
   if(handle != INVALID_HANDLE)
     {
      // Construct JSON manually (MQL5 has no native JSON lib)
      string json = "{";
      
      // 1. Protocol Version
      json += "\"Protocol_Version\": \"Quant 2.0 (Phase 3)\",";
      
      // 2. Execution Settings
      string exec_tfs = "";
      if(InpExecuteM1) exec_tfs += "M1,";
      if(InpExecuteM5) exec_tfs += "M5,";
      if(InpExecuteM15) exec_tfs += "M15,";
      if(InpExecuteM30) exec_tfs += "M30,";
      if(InpExecuteH1) exec_tfs += "H1,";
      if(InpExecuteH4) exec_tfs += "H4,";
      if(InpExecuteD1) exec_tfs += "D1,";
      if(InpExecuteW1) exec_tfs += "W1,";
      if(InpExecuteMN1) exec_tfs += "MN1,";
      if(StringLen(exec_tfs) > 0) exec_tfs = StringSubstr(exec_tfs, 0, StringLen(exec_tfs)-1);
      
      json += "\"Execution_Timeframes\": \"" + exec_tfs + "\",";
      
      // 3. Strategy Mode (Phase Gamma)
      // string strategy_mode_str = EnumToString(InpStrategyMode); // REMOVED
      json += "\"Strategy_Mode\": \"RUSSIAN_DOLL_UNIFIED\",";
      
      // 4. Elasticity & Physics (Phase Delta)
      // 4. Elasticity & Physics (Phase Delta) - PURGED
      json += "\"Target_Min_Age\": " + IntegerToString(InpQuantMinAgeBars) + ",";
      json += "\"Min_Signal_Age\": " + IntegerToString(InpQuantMinAgeBars) + ",";
      
      // 5. Exit Settings (Dynamic TP & Trailing)
      json += "\"Exit_Mode\": \"Trailing (∞)\",";
      
      // 6. Risk Settings (Nested Object)
      json += "\"Risk_Settings\": {";
      json += StringFormat("\"risk_t1\": %.2f,", InpBaseRisk * (InpAllocation_T1 / 100.0));
      json += StringFormat("\"risk_t2\": %.2f,", InpBaseRisk * (InpAllocation_T2 / 100.0));
      json += StringFormat("\"risk_t3\": %.2f,", InpBaseRisk * (InpAllocation_T3 / 100.0));
      
      // Extended fields for granularity
      json += StringFormat("\"base_risk\": %.2f,", InpBaseRisk);
      json += StringFormat("\"alloc_t1\": %.2f,", InpAllocation_T1);
      json += StringFormat("\"alloc_t2\": %.2f,", InpAllocation_T2);
      json += StringFormat("\"alloc_t3\": %.2f", InpAllocation_T3);
      json += "},";
      
      // 6. Tester Settings (Nested Object)
      json += "\"Tester_Settings\": {";
      json += "\"Initial_Balance\": " + DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE), 2) + ",";
      json += "\"Leverage\": " + IntegerToString(AccountInfoInteger(ACCOUNT_LEVERAGE)) + ",";
      json += "\"Currency\": \"" + AccountInfoString(ACCOUNT_CURRENCY) + "\"";
      json += "}";
      
      json += "}"; // End JSON
      
      FileWrite(handle, json);
      FileClose(handle);
      
      Print("[QuantLogger] DNA Card Exported: ", filename);
     }

  }

//+------------------------------------------------------------------+
//| LogTrade - Stores trade in memory for later export               |
//+------------------------------------------------------------------+
void CQuantLogger::LogTrade(QuantTradeExport &trade)
{
   ArrayResize(m_trades, m_trade_count + 1);
   m_trades[m_trade_count] = trade;
   m_trade_count++;
   
   if(InpLogTrading)
      PrintFormat("[QuantLogger] Trade logged: Ticket %d | %s | Entry: %.5f", 
                  trade.ticket, trade.direction, trade.entry_price);
}

//+------------------------------------------------------------------+
//| GetTradingSession - Detect trading session from time (UTC)       |
//+------------------------------------------------------------------+
string CQuantLogger::GetTradingSession(datetime time)
{
   MqlDateTime dt;
   TimeToStruct(time, dt);
   int hour = dt.hour;
   
   if(hour >= 0 && hour < 8)   return "ASIAN";
   if(hour >= 8 && hour < 13)  return "LONDON";
   if(hour >= 13 && hour < 17) return "OVERLAP";
   if(hour >= 17 && hour < 22) return "NEWYORK";
   return "ASIAN";
}

//+------------------------------------------------------------------+
//| ReconcileHistory - Fill exit data from MT5 deal history          |
//+------------------------------------------------------------------+
void CQuantLogger::ReconcileHistory()
{
   Print("[QuantLogger] Reconciling History...");
   int matched_count = 0;
   
   for(int i = 0; i < m_trade_count; i++)
   {
      long ticket = m_trades[i].ticket;
      if(ticket == 0) continue;
      
      // Select complete history for this position
      if(HistorySelectByPosition((ulong)ticket))
      {
         int deals = HistoryDealsTotal();
         double realized_pnl = 0;
         double total_swap = 0;
         double total_comm = 0;
         datetime close_time = 0;
         double close_price = 0;
         string close_reason = "";
         double volume = 0;
         
         for(int d = 0; d < deals; d++)
         {
            ulong deal_ticket = HistoryDealGetTicket(d);
            if(deal_ticket > 0)
            {
               realized_pnl += HistoryDealGetDouble(deal_ticket, DEAL_PROFIT);
               total_swap += HistoryDealGetDouble(deal_ticket, DEAL_SWAP);
               total_comm += HistoryDealGetDouble(deal_ticket, DEAL_COMMISSION);
               
               ENUM_DEAL_ENTRY entry_type = (ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal_ticket, DEAL_ENTRY);
               
               if(entry_type == DEAL_ENTRY_IN)
                  volume = HistoryDealGetDouble(deal_ticket, DEAL_VOLUME);
               
               if(entry_type == DEAL_ENTRY_OUT || entry_type == DEAL_ENTRY_OUT_BY)
               {
                  close_time = (datetime)HistoryDealGetInteger(deal_ticket, DEAL_TIME);
                  close_price = HistoryDealGetDouble(deal_ticket, DEAL_PRICE);
                  
                  long reason = HistoryDealGetInteger(deal_ticket, DEAL_REASON);
                  if(reason == DEAL_REASON_SL) close_reason = "SL";
                  else if(reason == DEAL_REASON_TP) close_reason = "TP";
                  else if(reason == DEAL_REASON_CLIENT) close_reason = "MANUAL";
                  else if(reason == DEAL_REASON_EXPERT) close_reason = "EA";
               }
            }
         }
         
         // Update Trade Record if we found an exit
         if(close_time > 0)
         {
            m_trades[i].result = (realized_pnl >= 0) ? "WIN" : "LOSS";
            m_trades[i].pnl_money = realized_pnl + total_swap + total_comm;
            m_trades[i].exit_time = close_time;
            m_trades[i].exit_price = close_price;
            m_trades[i].exit_reason = close_reason;
            m_trades[i].commission = total_comm;
            m_trades[i].swap = total_swap;
            m_trades[i].lot_size = volume;
            
            // Duration
            if(m_trades[i].entry_time > 0)
               m_trades[i].duration_seconds = (long)(close_time - m_trades[i].entry_time);
            
            // PnL Points
            double point = SymbolInfoDouble(m_trades[i].symbol, SYMBOL_POINT);
            if(point > 0)
            {
               if(m_trades[i].direction == "BUY")
                  m_trades[i].pnl_points = (close_price - m_trades[i].entry_price) / point;
               else
                  m_trades[i].pnl_points = (m_trades[i].entry_price - close_price) / point;
            }
            
            // Risk and R-Multiple
            double sl_dist = MathAbs(m_trades[i].entry_price - m_trades[i].sl_price);
            if(point > 0 && sl_dist > 0)
            {
               m_trades[i].sl_distance_points = sl_dist / point;
               double tick_val = SymbolInfoDouble(m_trades[i].symbol, SYMBOL_TRADE_TICK_VALUE);
               m_trades[i].risk_money = m_trades[i].sl_distance_points * tick_val * volume;
               if(m_trades[i].risk_money > 0)
                  m_trades[i].r_multiple = m_trades[i].pnl_money / m_trades[i].risk_money;
            }
            
            //=== MAE/MFE Calculation ===
            if(m_trades[i].entry_time > 0 && close_time > m_trades[i].entry_time)
            {
               MqlRates rates[];
               int count = CopyRates(m_trades[i].symbol, PERIOD_M1, m_trades[i].entry_time, close_time, rates);
               if(count > 0)
               {
                  double highest = 0;
                  double lowest = 999999;
                  
                  for(int r = 0; r < count; r++)
                  {
                     if(rates[r].high > highest) highest = rates[r].high;
                     if(rates[r].low < lowest) lowest = rates[r].low;
                  }
                  
                  double entry = m_trades[i].entry_price;
                  
                  if(m_trades[i].direction == "BUY")
                  {
                     m_trades[i].mfe_points = (highest - entry) / point;
                     m_trades[i].mae_points = (entry - lowest) / point;
                  }
                  else
                  {
                     m_trades[i].mfe_points = (entry - lowest) / point;
                     m_trades[i].mae_points = (highest - entry) / point;
                  }
                  
                  if(m_trades[i].mfe_points < 0) m_trades[i].mfe_points = 0;
                  if(m_trades[i].mae_points < 0) m_trades[i].mae_points = 0;
                  
                  // Edge Ratio = MFE / MAE
                  if(m_trades[i].mae_points > 0)
                     m_trades[i].edge_ratio = m_trades[i].mfe_points / m_trades[i].mae_points;
               }
            }
            
            matched_count++;
         }
         else
         {
            m_trades[i].result = "OPEN";
         }
      }
   }
   PrintFormat("[QuantLogger] Reconciliation Complete. Matched %d/%d trades.", matched_count, m_trade_count);
}


//+------------------------------------------------------------------+
//| UpdateBEStatus - Update BE status for an active trade             |
//+------------------------------------------------------------------+
void CQuantLogger::UpdateBEStatus(long ticket, bool activated)
{
   for(int i = 0; i < m_trade_count; i++)
   {
      if(m_trades[i].ticket == ticket)
      {
         m_trades[i].be_activated = activated;
         return;
      }
   }
}


//+------------------------------------------------------------------+
//| ExportCSV - Write all trades to CSV file                         |
//+------------------------------------------------------------------+
bool CQuantLogger::ExportCSV(const string filename)
{
   if(m_trade_count == 0)
   {
      Print("[QuantLogger] No trades to export.");
      return false;
   }
   
   string final_filename = (filename != "") ? filename : m_filename_trades;
   int handle = FileOpen(final_filename, FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON, ",");
   if(handle == INVALID_HANDLE)
   {
      PrintFormat("[QuantLogger] ERROR: Cannot open file %s. Error: %d", final_filename, GetLastError());
      return false;
   }
   
   // Write Header - Quantum Audit V2
   string header = "ticket,symbol,direction,entry_time,entry_price,entry_trigger," +
                   "exit_time,exit_price,exit_reason,result," +
                   "sl_price,tp_price,sl_distance_points,risk_money,lot_size," +
                   "pnl_points,pnl_money,r_multiple,commission,swap," +
                   "mae_points,mfe_points,edge_ratio,duration_seconds," +
                   "zone_id,zone_tf,zone_age_bars,zone_rel_pos,zone_size_points,zone_touch_num,p_class,cascade_score,fractal_depth,d1_aligned,buy_votes,sell_votes," +
                   "session,day_of_week,hour_of_day,atr_at_entry," +
                    "sequence_index,bars_held,lifecycle_phase,landing_type,vector_signature,vector_sum,target_r," +
                    // V5.9 Fractal Resolution
                    "layer_1_tide,layer_2_wind,layer_3_trap,layer_4_trigger," +
                    "anchor_id,outpost_id,bridge_state," +
                    "narrative_conflict_blocked," + 
                    // Quantum Audit V2 Fields
                    "base_risk_pct,touch_risk_pct,leverage,capital_at_entry," +
                    "trailing_sl_locked_pts,be_activated";
   FileWrite(handle, header);
   
   // Write Rows
   for(int i = 0; i < m_trade_count; i++)
   {
      string line = ToCSV(m_trades[i]);
      FileWrite(handle, line);
   }
   
   FileClose(handle);
   PrintFormat("[QuantLogger] Exported %d trades to %s", m_trade_count, final_filename);
   return true;
}

//+------------------------------------------------------------------+
//| ToCSV - Serialize struct to CSV Line                             |
//+------------------------------------------------------------------+
string CQuantLogger::ToCSV(QuantTradeExport &t)
{
   string sep = ",";
   string line = 
      (string)t.ticket + sep +
      t.symbol + sep +
      t.direction + sep +
      TimeToString(t.entry_time, TIME_DATE|TIME_MINUTES|TIME_SECONDS) + sep +
      DoubleToString(t.entry_price, 5) + sep +
      t.entry_trigger + sep +
      TimeToString(t.exit_time, TIME_DATE|TIME_MINUTES|TIME_SECONDS) + sep +
      DoubleToString(t.exit_price, 5) + sep +
      t.exit_reason + sep +
      t.result + sep +
      
      DoubleToString(t.sl_price, 5) + sep +
      DoubleToString(t.tp_price, 5) + sep +
      DoubleToString(t.sl_distance_points, 1) + sep +
      DoubleToString(t.risk_money, 2) + sep +
      DoubleToString(t.lot_size, 2) + sep +
      
      DoubleToString(t.pnl_points, 1) + sep +
      DoubleToString(t.pnl_money, 2) + sep +
      DoubleToString(t.r_multiple, 2) + sep +
      DoubleToString(t.commission, 2) + sep +
      DoubleToString(t.swap, 2) + sep +
      
      DoubleToString(t.mae_points, 1) + sep +
      DoubleToString(t.mfe_points, 1) + sep +
      DoubleToString(t.edge_ratio, 2) + sep +
      (string)t.duration_seconds + sep +
      
      t.zone_id + sep +
      t.zone_tf + sep +
      (string)t.zone_age_bars + sep +
      DoubleToString(t.zone_rel_pos, 2) + sep +
      DoubleToString(t.zone_size_points, 1) + sep +
      (string)t.zone_touch_num + sep +
      t.p_class + sep +
      (string)t.cascade_score + sep +
      (string)t.fractal_depth + sep +
      (t.d1_aligned ? "true" : "false") + sep +
      (string)t.buy_votes + sep +
      (string)t.sell_votes + sep +
      
      t.session + sep +
      (string)t.day_of_week + sep +
      (string)t.hour_of_day + sep +
      DoubleToString(t.atr_at_entry, 2) + sep +
      
      // Quant 2.0
      (string)t.sequence_index + sep +
      (string)t.bars_held + sep +
      t.lifecycle_phase + sep +
      t.landing_type + sep +
      t.vector_signature + sep +
      (string)t.vector_sum + sep +
      DoubleToString(t.target_r, 2) + sep +
      
      // V5.9 Fractal Resolution
      t.layer_1_tide + sep +
      t.layer_2_wind + sep +
      t.layer_3_trap + sep +
      t.layer_4_trigger + sep +
      (string)t.anchor_id + sep +
      (string)t.outpost_id + sep +
      t.bridge_state + sep +
      (t.narrative_conflict_blocked ? "true" : "false") + sep +
       
       DoubleToString(t.base_risk_pct, 2) + sep +
       DoubleToString(t.touch_risk_pct, 2) + sep +
       (string)t.leverage + sep +
       DoubleToString(t.capital_at_entry, 2) + sep +
       DoubleToString(t.trailing_sl_locked_pts, 1) + sep +
       (t.be_activated ? "true" : "false");
      
   return line;
}



//+------------------------------------------------------------------+
//| OpenZoneFile (Private)                                           |
//+------------------------------------------------------------------+
bool CQuantLogger::OpenZoneFile()
{
   if(!m_zones_enabled) return false;
   if(m_zone_file_handle != INVALID_HANDLE) return true;
   
   bool file_exists = FileIsExist(m_filename_zones, FILE_COMMON);
   
   m_zone_file_handle = FileOpen(m_filename_zones, FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_SHARE_READ, ',');
   
   if(m_zone_file_handle == INVALID_HANDLE)
   {
      PrintFormat("[QuantLogger] Failed to open zone file: %s, Error: %d", m_filename_zones, GetLastError());
      return false;
   }
   
   FileSeek(m_zone_file_handle, 0, SEEK_END);
   
   if(!file_exists || FileSize(m_zone_file_handle) == 0)
   {
       string header = "event_type,zone_id,tf,direction,"
                    "l1_price,l2_price,fifty_percent,"
                    "first_barrier_price,first_barrier_time,second_barrier_price,second_barrier_time,"
                    "created_time,event_time,l1_touch_time,fifty_touch_time,l2_touch_time,invalidation_time,"
                    "l1_touched,fifty_touched,l2_touched,"
                    "outcome,age_at_first_touch,age_at_invalidation,touch_depth_at_outcome,"
                    "sequence_index,htf_parent_id,has_htf_alignment,has_narrative_parent,has_control_parent,"
                    "session_at_touch,touch_quarter,bars_after_t1,bars_after_t2,bars_after_t3,"
                    "mfe_pips,mae_pips,zone_size_pips,"
                    "mfe_time,mae_time,"  
                    "dataset_type";
       FileWriteString(m_zone_file_handle, header + "\n");
       m_zone_header_written = true;
   }
   
   return true;
}

//+------------------------------------------------------------------+
//| CloseZoneFile                                                     |
//+------------------------------------------------------------------+
void CQuantLogger::CloseZoneFile()
{
   if(m_zone_file_handle != INVALID_HANDLE)
   {
      FileClose(m_zone_file_handle);
      m_zone_file_handle = INVALID_HANDLE;
   }
}

//+------------------------------------------------------------------+
//| LogZoneCreated                                                    |
//+------------------------------------------------------------------+
void CQuantLogger::LogZoneCreated(const B2BZoneInfo &zone)
{
   if(!m_zones_enabled || !OpenZoneFile()) return;
   
   ZoneLogEntry entry;
   entry.event_type = "CREATED";
   entry.zone_id = ZoneIdToString(zone.zone_id);
   entry.tf = EnumToString(zone.timeframe);
   entry.direction = (zone.direction == DIRECTION_BULLISH) ? "BUY" : "SELL";
   
   entry.l1_price = zone.L1_price;
   entry.l2_price = zone.L2_price;
   entry.fifty_percent = zone.fifty_percent;
   
   entry.first_barrier_price = zone.first_barrier_price;
   entry.first_barrier_time = zone.first_barrier_time;
   entry.second_barrier_price = zone.second_barrier_price;
   entry.second_barrier_time = zone.second_barrier_time;
   
   entry.created_time = zone.zone_created_time;
   entry.event_time = TimeCurrent();
   entry.l1_touch_time = 0;
   entry.fifty_touch_time = 0;
   entry.l2_touch_time = 0;
   entry.invalidation_time = 0;
   
   entry.l1_touched = false;
   entry.fifty_touched = false;
   entry.l2_touched = false;
   
   entry.outcome = "UNTOUCHED";
   entry.age_at_first_touch = 0;
   entry.age_at_invalidation = 0;
   entry.touch_depth_at_outcome = "T0";
   
   entry.sequence_index = 0; // Will be updated
   entry.htf_parent_id = ZoneIdToString(zone.parent_zone_id);
   entry.has_htf_alignment = zone.has_narrative_parent || zone.has_control_parent;
   entry.has_narrative_parent = zone.has_narrative_parent;
   entry.has_control_parent = zone.has_control_parent;
   
   entry.dataset_type = "EXPLORATION"; // Default
   
   WriteZoneEntry(entry);
}

//+------------------------------------------------------------------+
//| LogZoneTouched                                                    |
//+------------------------------------------------------------------+
void CQuantLogger::LogZoneTouched(const B2BZoneInfo &zone, string touch_level)
{
   if(!m_zones_enabled || !OpenZoneFile()) return;
   
   ZoneLogEntry entry;
   entry.event_type = "TOUCHED";
   entry.zone_id = ZoneIdToString(zone.zone_id);
   entry.tf = EnumToString(zone.timeframe);
   entry.direction = (zone.direction == DIRECTION_BULLISH) ? "BUY" : "SELL";
   
   entry.l1_price = zone.L1_price;
   entry.l2_price = zone.L2_price;
   entry.fifty_percent = zone.fifty_percent;
   
   entry.first_barrier_price = zone.first_barrier_price;
   entry.first_barrier_time = zone.first_barrier_time;
   entry.second_barrier_price = zone.second_barrier_price;
   entry.second_barrier_time = zone.second_barrier_time;
   
   entry.created_time = zone.zone_created_time;
   entry.event_time = TimeCurrent();
   entry.l1_touch_time = zone.L1_touch_time;
   entry.fifty_touch_time = zone.fifty_touch_time;
   entry.l2_touch_time = zone.L2_touch_time;
   entry.invalidation_time = 0;
   
   entry.l1_touched = zone.L1_touched;
   entry.fifty_touched = zone.fifty_touched;
   entry.l2_touched = zone.L2_touched;
   
   entry.outcome = "";
   entry.age_at_first_touch = zone.zone_age_bars;
   entry.age_at_invalidation = 0;
   entry.touch_depth_at_outcome = touch_level;
   
   entry.sequence_index = 0;
   entry.htf_parent_id = ZoneIdToString(zone.parent_zone_id);
   entry.has_htf_alignment = zone.has_narrative_parent || zone.has_control_parent;
   entry.has_narrative_parent = zone.has_narrative_parent;
   entry.has_control_parent = zone.has_control_parent;
   
   entry.dataset_type = "EXPLORATION";
   
   WriteZoneEntry(entry);
}

//+------------------------------------------------------------------+
//| LogZoneSurvived                                                   |
//+------------------------------------------------------------------+
void CQuantLogger::LogZoneSurvived(const B2BZoneInfo &zone)
{
   if(!m_zones_enabled || !OpenZoneFile()) return;
   
   ZoneLogEntry entry;
   entry.event_type = "SURVIVED";
   entry.zone_id = ZoneIdToString(zone.zone_id);
   entry.tf = EnumToString(zone.timeframe);
   entry.direction = (zone.direction == DIRECTION_BULLISH) ? "BUY" : "SELL";
   
   entry.l1_price = zone.L1_price;
   entry.l2_price = zone.L2_price;
   entry.fifty_percent = zone.fifty_percent;
   
   entry.first_barrier_price = zone.first_barrier_price;
   entry.first_barrier_time = zone.first_barrier_time;
   entry.second_barrier_price = zone.second_barrier_price;
   entry.second_barrier_time = zone.second_barrier_time;
   
   entry.created_time = zone.zone_created_time;
   entry.event_time = TimeCurrent();
   entry.l1_touch_time = zone.L1_touch_time;
   entry.fifty_touch_time = zone.fifty_touch_time;
   entry.l2_touch_time = zone.L2_touch_time;
   entry.invalidation_time = 0;
   
   entry.l1_touched = zone.L1_touched;
   entry.fifty_touched = zone.fifty_touched;
   entry.l2_touched = zone.L2_touched;
   
   entry.outcome = "SURVIVED";
   entry.age_at_first_touch = zone.zone_age_bars;
   entry.age_at_invalidation = 0;
   entry.touch_depth_at_outcome = GetTouchDepth(zone);
   
   entry.sequence_index = 0;
   entry.htf_parent_id = ZoneIdToString(zone.parent_zone_id);
   entry.has_htf_alignment = zone.has_narrative_parent || zone.has_control_parent;
   entry.has_narrative_parent = zone.has_narrative_parent;
   entry.has_control_parent = zone.has_control_parent;
   
   // Phase 0.5B Fields
   entry.session_at_touch = GetTradingSessionZone(zone.L1_touch_time);
   entry.touch_quarter = GetTouchQuarterZone(zone.L1_touch_time);
   
   // Bar survival tracking
   if(zone.L1_touch_time > 0)
      entry.bars_after_t1 = iBarShift(_Symbol, zone.timeframe, zone.L1_touch_time); // For survivors, it's bars since touch to NOW
   else
      entry.bars_after_t1 = 0;
      
   if(zone.fifty_touch_time > 0)
      entry.bars_after_t2 = iBarShift(_Symbol, zone.timeframe, zone.fifty_touch_time);
   else
      entry.bars_after_t2 = 0;
      
   if(zone.L2_touch_time > 0)
      entry.bars_after_t3 = iBarShift(_Symbol, zone.timeframe, zone.L2_touch_time);
   else
      entry.bars_after_t3 = 0;
   
   // MFE/MAE (already in points from B2BZoneStatus)
   entry.mfe_pips = zone.max_favorable_excursion / 10.0;
   entry.mae_pips = zone.max_adverse_excursion / 10.0;
   entry.zone_size_pips = MathAbs(zone.L1_price - zone.L2_price) / _Point / 10.0;
   
   entry.mfe_time = zone.mfe_time;
   entry.mae_time = zone.mae_time;
   
   entry.dataset_type = "EXPLORATION";
   
   WriteZoneEntry(entry);
}

//+------------------------------------------------------------------+
//| LogZoneBulldozed                                                  |
//+------------------------------------------------------------------+
void CQuantLogger::LogZoneBulldozed(const B2BZoneInfo &zone)
{
   if(!m_zones_enabled || !OpenZoneFile()) return;
   
   ZoneLogEntry entry;
   entry.event_type = "BULLDOZED";
   entry.zone_id = ZoneIdToString(zone.zone_id);
   entry.tf = EnumToString(zone.timeframe);
   entry.direction = (zone.direction == DIRECTION_BULLISH) ? "BUY" : "SELL";
   
   entry.l1_price = zone.L1_price;
   entry.l2_price = zone.L2_price;
   entry.fifty_percent = zone.fifty_percent;
   
   entry.first_barrier_price = zone.first_barrier_price;
   entry.first_barrier_time = zone.first_barrier_time;
   entry.second_barrier_price = zone.second_barrier_price;
   entry.second_barrier_time = zone.second_barrier_time;
   
   entry.created_time = zone.zone_created_time;
   entry.event_time = TimeCurrent();
   entry.l1_touch_time = zone.L1_touch_time;
   entry.fifty_touch_time = zone.fifty_touch_time;
   entry.l2_touch_time = zone.L2_touch_time;
   entry.invalidation_time = zone.invalidation_time;
   
   entry.l1_touched = zone.L1_touched;
   entry.fifty_touched = zone.fifty_touched;
   entry.l2_touched = zone.L2_touched;
   
   entry.outcome = "BULLDOZED";
   entry.age_at_first_touch = 0;
   if(zone.L1_touch_time > 0)
      entry.age_at_first_touch = iBarShift(_Symbol, zone.timeframe, zone.L1_touch_time);
   entry.age_at_invalidation = zone.zone_age_bars;
   entry.touch_depth_at_outcome = GetTouchDepth(zone);
   
   entry.sequence_index = 0;
   entry.htf_parent_id = ZoneIdToString(zone.parent_zone_id);
   entry.has_htf_alignment = zone.has_narrative_parent || zone.has_control_parent;
   entry.has_narrative_parent = zone.has_narrative_parent;
   entry.has_control_parent = zone.has_control_parent;
   
   // Derive session/quarter from L1 touch time (first touch)
   datetime touch_time = (zone.L1_touch_time > 0) ? zone.L1_touch_time : zone.zone_created_time;
   entry.session_at_touch = GetTradingSessionZone(touch_time);
   entry.touch_quarter = GetTouchQuarterZone(touch_time);
   
   // Calculate bars from each touch level to death
   int period_seconds = PeriodSeconds(zone.timeframe);
   
   // Bars after T1 (L1 touch to death)
   if(zone.L1_touch_time > 0 && zone.invalidation_time > zone.L1_touch_time && period_seconds > 0)
      entry.bars_after_t1 = (int)((zone.invalidation_time - zone.L1_touch_time) / period_seconds);
   else
      entry.bars_after_t1 = 0;
   
   // Bars after T2 (50% touch to death)
   if(zone.fifty_touch_time > 0 && zone.invalidation_time > zone.fifty_touch_time && period_seconds > 0)
      entry.bars_after_t2 = (int)((zone.invalidation_time - zone.fifty_touch_time) / period_seconds);
   else
      entry.bars_after_t2 = 0;
   
   // Bars after T3 (L2 touch to death)
   if(zone.L2_touch_time > 0 && zone.invalidation_time > zone.L2_touch_time && period_seconds > 0)
      entry.bars_after_t3 = (int)((zone.invalidation_time - zone.L2_touch_time) / period_seconds);
   else
      entry.bars_after_t3 = 0;
   
   entry.mfe_pips = zone.max_favorable_excursion / 10.0;
   entry.mae_pips = zone.max_adverse_excursion / 10.0;
   entry.zone_size_pips = MathAbs(zone.L1_price - zone.L2_price) / _Point / 10.0;
   
   entry.mfe_time = zone.mfe_time;
   entry.mae_time = zone.mae_time;
   
   entry.dataset_type = "EXPLORATION";
   
   WriteZoneEntry(entry);
}

//+------------------------------------------------------------------+
//| WriteZoneEntry                                                    |
//+------------------------------------------------------------------+
void CQuantLogger::WriteZoneEntry(const ZoneLogEntry &entry)
{
   if(m_zone_file_handle == INVALID_HANDLE) return;
   
   string line = BuildZoneCSVLine(entry);
   FileWriteString(m_zone_file_handle, line + "\n");
   FileFlush(m_zone_file_handle);
}

//+------------------------------------------------------------------+
//| BuildZoneCSVLine                                                  |
//+------------------------------------------------------------------+
string CQuantLogger::BuildZoneCSVLine(const ZoneLogEntry &entry)
{
   string line = "";
   string sep = ",";
   
   line += entry.event_type + sep;
   line += entry.zone_id + sep;
   line += entry.tf + sep;
   line += entry.direction + sep;
   
   line += DoubleToString(entry.l1_price, _Digits) + sep;
   line += DoubleToString(entry.l2_price, _Digits) + sep;
   line += DoubleToString(entry.fifty_percent, _Digits) + sep;
   
   line += DoubleToString(entry.first_barrier_price, _Digits) + sep;
   line += (entry.first_barrier_time > 0 ? TimeToString(entry.first_barrier_time, TIME_DATE|TIME_SECONDS) : "") + sep;
   line += DoubleToString(entry.second_barrier_price, _Digits) + sep;
   line += (entry.second_barrier_time > 0 ? TimeToString(entry.second_barrier_time, TIME_DATE|TIME_SECONDS) : "") + sep;
   
   line += (entry.created_time > 0 ? TimeToString(entry.created_time, TIME_DATE|TIME_SECONDS) : "") + sep;
   line += (entry.event_time > 0 ? TimeToString(entry.event_time, TIME_DATE|TIME_SECONDS) : "") + sep;
   line += (entry.l1_touch_time > 0 ? TimeToString(entry.l1_touch_time, TIME_DATE|TIME_SECONDS) : "") + sep;
   line += (entry.fifty_touch_time > 0 ? TimeToString(entry.fifty_touch_time, TIME_DATE|TIME_SECONDS) : "") + sep;
   line += (entry.l2_touch_time > 0 ? TimeToString(entry.l2_touch_time, TIME_DATE|TIME_SECONDS) : "") + sep;
   line += (entry.invalidation_time > 0 ? TimeToString(entry.invalidation_time, TIME_DATE|TIME_SECONDS) : "") + sep;
   
   line += (entry.l1_touched ? "true" : "false") + sep;
   line += (entry.fifty_touched ? "true" : "false") + sep;
   line += (entry.l2_touched ? "true" : "false") + sep;
   
   line += entry.outcome + sep;
   line += IntegerToString(entry.age_at_first_touch) + sep;
   line += IntegerToString(entry.age_at_invalidation) + sep;
   line += entry.touch_depth_at_outcome + sep;
   
   line += IntegerToString(entry.sequence_index) + sep;
   line += entry.htf_parent_id + sep;
   line += (entry.has_htf_alignment ? "true" : "false") + sep;
   line += (entry.has_narrative_parent ? "true" : "false") + sep;
   line += (entry.has_control_parent ? "true" : "false") + sep;
   
   line += entry.session_at_touch + sep;
   line += entry.touch_quarter + sep;
   line += IntegerToString(entry.bars_after_t1) + sep;
   line += IntegerToString(entry.bars_after_t2) + sep;
   line += IntegerToString(entry.bars_after_t3) + sep;
   line += DoubleToString(entry.mfe_pips, 1) + sep;
   line += DoubleToString(entry.mae_pips, 1) + sep;
   line += DoubleToString(entry.zone_size_pips, 1) + sep;
   
   line += (entry.mfe_time > 0 ? TimeToString(entry.mfe_time, TIME_DATE|TIME_SECONDS) : "") + sep;
   line += (entry.mae_time > 0 ? TimeToString(entry.mae_time, TIME_DATE|TIME_SECONDS) : "") + sep;
   
   line += entry.dataset_type;
   
   return line;
}

//+------------------------------------------------------------------+
//| Helpers (Zone)                                                   |
//+------------------------------------------------------------------+
string CQuantLogger::GetTouchDepth(const B2BZoneInfo &zone)
{
   if(zone.L2_touched) return "T3";
   if(zone.fifty_touched) return "T2";
   if(zone.L1_touched) return "T1";
   return "T0";
}

string CQuantLogger::ZoneIdToString(ulong id)
{
   if(id == 0) return "";
   return IntegerToString(id);
}

string CQuantLogger::GetTradingSessionZone(datetime time)
{
   if(time == 0) return "";
   
   MqlDateTime dt;
   TimeToStruct(time, dt);
   int hour = dt.hour;
   
   if(hour >= 0 && hour < 7)
      return "ASIAN";
   else if(hour >= 7 && hour < 12)
      return "LONDON";
   else if(hour >= 12 && hour < 16)
      return "OVERLAP";
   else if(hour >= 16 && hour < 21)
      return "NY";
   else
      return "OFF_HOURS";
}

string CQuantLogger::GetTouchQuarterZone(datetime time)
{
   if(time == 0) return "";
   
   MqlDateTime dt;
   TimeToStruct(time, dt);
   int month = dt.mon;
   
   if(month >= 1 && month <= 3)
      return "Q1";
   else if(month >= 4 && month <= 6)
      return "Q2";
   else if(month >= 7 && month <= 9)
      return "Q3";
   else
      return "Q4";
}


#endif // QUANT_LOGGER_MQH
