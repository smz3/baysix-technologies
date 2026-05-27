//+------------------------------------------------------------------+
//|                                               DataExporter.mqh    |
//|                             Copyright 2025, Sigma Trading System  |
//+------------------------------------------------------------------+
//| Exports zone data to JSON for dashboard visualization             |
//| SAFETY: Writes to local file only, no network access              |
//+------------------------------------------------------------------+
#ifndef V50_DATA_EXPORTER_MQH
#define V50_DATA_EXPORTER_MQH

#property strict

#include "../Common/Defines.mqh"
#include "../Data/Structures.mqh"
#include "../Analysis/MetricCalculator.mqh"

// Windows API import for file operations outside MQL5 sandbox
#import "shell32.dll"
   int ShellExecuteW(long hwnd, string lpOperation, string lpFile, string lpParameters, string lpDirectory, int nShowCmd);
#import

//+------------------------------------------------------------------+
//| CDataExporter Class                                               |
//+------------------------------------------------------------------+
class CDataExporter
  {
private:
   string            m_export_path;       // Path to export file
   bool              m_is_initialized;
   
   // Helper functions
   string            EscapeJSON(const string text);
   string            DirectionToString(ENUM_SIGNAL_DIRECTION dir);
   string            TFToShortString(ENUM_TIMEFRAMES tf);
   string            OutcomeToString(int outcome);
   string            GetNextVersion(const string base_pattern, const string folder_path);
   
public:
                     CDataExporter(void);
   
   // Initialization
   bool              Initialize(const string custom_path = "");
   
   // Export functions - Backtest
   bool              ExportZoneData(const B2BZoneInfo &zones[], int zone_count);
   bool              ExportZoneDataWithStats(const B2BZoneInfo &zones[], int zone_count);
   
   // Export functions - Live Data (Phase 2)
   bool              ExportAccountInfo(void);
   bool              ExportActiveZones(const B2BZoneInfo &zones[], int zone_count);
   
   // Mode detection
   bool              IsBacktest(void) const { return (MQLInfoInteger(MQL_TESTER) != 0); }
   bool              IsOptimization(void) const { return (MQLInfoInteger(MQL_OPTIMIZATION) != 0); }
   bool              IsLive(void) const { return !IsBacktest() && !IsOptimization(); }
   string            GetModeString(void) const;
  };

//+------------------------------------------------------------------+
//| Constructor                                                       |
//+------------------------------------------------------------------+
CDataExporter::CDataExporter(void)
  {
   m_is_initialized = false;
   m_export_path = "";
  }

//+------------------------------------------------------------------+
//| GetNextVersion - Get next version from persistent counter         |
//| Returns: "1a", "1b", "1c", ... "1z", "2a", "2b", etc.              |
//| Uses a counter file in MQL5 sandbox to track versions             |
//+------------------------------------------------------------------+
string CDataExporter::GetNextVersion(const string base_pattern, const string folder_path)
  {
   // Version letters: a-z
   string letters = "abcdefghijklmnopqrstuvwxyz";
   
   // Counter file path in MQL5 sandbox (Files folder)
   string counter_file = "sigma_backtest_counter.txt";
   
   int current_number = 1;
   int current_letter = 0;  // 0 = 'a'
   
   // Try to read existing counter
   int file_handle = FileOpen(counter_file, FILE_READ | FILE_TXT);
   if(file_handle != INVALID_HANDLE)
     {
      string last_version = FileReadString(file_handle);
      FileClose(file_handle);
      
      // Parse last version (e.g., "1b" -> number=1, letter=1)
      int ver_len = StringLen(last_version);
      if(ver_len >= 2)
        {
         string num_str = StringSubstr(last_version, 0, ver_len - 1);
         string let_str = StringSubstr(last_version, ver_len - 1, 1);
         
         current_number = (int)StringToInteger(num_str);
         current_letter = StringFind(letters, let_str);
         
         // Increment to next version
         current_letter++;
         if(current_letter >= 26)  // Wrap around after 'z'
           {
            current_letter = 0;
            current_number++;
           }
        }
     }
   
   // Create the new version string
   string new_version = StringFormat("%d%s", current_number, StringSubstr(letters, current_letter, 1));
   
   // Save updated counter
   file_handle = FileOpen(counter_file, FILE_WRITE | FILE_TXT);
   if(file_handle != INVALID_HANDLE)
     {
      FileWriteString(file_handle, new_version);
      FileClose(file_handle);
     }
   
   return new_version;
  }

//+------------------------------------------------------------------+
//| Initialize - Set export path                                      |
//+------------------------------------------------------------------+
bool CDataExporter::Initialize(const string custom_path = "")
  {
   // Direct export to SIGMA Analyst dashboard folder
   // This path is accessible from both live and backtest modes
   if(custom_path == "")
     {
      // Generate base filename with timestamp
      datetime now = TimeCurrent();
      MqlDateTime dt;
      TimeToStruct(now, dt);
      
      string base_pattern = StringFormat("%s_%s_%04d%02d%02d_%02d%02d%02d",
                                     _Symbol,
                                     TFToShortString(PERIOD_CURRENT),
                                     dt.year, dt.mon, dt.day,
                                     dt.hour, dt.min, dt.sec);
      
      string folder_path = "C:\\Users\\User\\Desktop\\SIGMA Analyst\\public\\data\\backtests\\";
      
      // Get next version (1a, 1b, 1c, etc.)
      string version = GetNextVersion(base_pattern, folder_path);
      
      string filename = StringFormat("%s_%s.json", base_pattern, version);
      
      // Absolute path to SIGMA Analyst backtests folder
      m_export_path = folder_path + filename;
      
      Print("[DataExporter] Version: ", version);
     }
   else
     {
      m_export_path = custom_path;
     }
   
   m_is_initialized = true;
   
   Print("[DataExporter] Initialized. Mode: ", GetModeString());
   Print("[DataExporter] Export path: ", m_export_path);
   
   return true;
  }

//+------------------------------------------------------------------+
//| GetModeString - Returns current mode as string                    |
//+------------------------------------------------------------------+
string CDataExporter::GetModeString(void) const
  {
   if(IsOptimization()) return "OPTIMIZATION";
   if(IsBacktest()) return "BACKTEST";
   return "LIVE";
  }

//+------------------------------------------------------------------+
//| EscapeJSON - Escape special characters for JSON                   |
//+------------------------------------------------------------------+
string CDataExporter::EscapeJSON(const string text)
  {
   string result = text;
   StringReplace(result, "\\", "\\\\");
   StringReplace(result, "\"", "\\\"");
   StringReplace(result, "\n", "\\n");
   StringReplace(result, "\r", "\\r");
   StringReplace(result, "\t", "\\t");
   return result;
  }

//+------------------------------------------------------------------+
//| DirectionToString                                                 |
//+------------------------------------------------------------------+
string CDataExporter::DirectionToString(ENUM_SIGNAL_DIRECTION dir)
  {
   return (dir == DIRECTION_BULLISH) ? "BUY" : "SELL";
  }

//+------------------------------------------------------------------+
//| TFToShortString                                                   |
//+------------------------------------------------------------------+
string CDataExporter::TFToShortString(ENUM_TIMEFRAMES tf)
  {
   switch(tf)
     {
      case PERIOD_M1:  return "M1";
      case PERIOD_M5:  return "M5";
      case PERIOD_M15: return "M15";
      case PERIOD_M30: return "M30";
      case PERIOD_H1:  return "H1";
      case PERIOD_H4:  return "H4";
      case PERIOD_D1:  return "D1";
      case PERIOD_W1:  return "W1";
      case PERIOD_MN1: return "MN1";
      default: return "UNKNOWN";
     }
  }

//+------------------------------------------------------------------+
//| OutcomeToString                                                   |
//+------------------------------------------------------------------+
string CDataExporter::OutcomeToString(int outcome)
  {
   // 0 = open, 1 = TP hit, 2 = SL hit, 3 = invalidated
   switch(outcome)
     {
      case 0: return "OPEN";
      case 1: return "TP";
      case 2: return "SL";
      case 3: return "INVALIDATED";
      default: return "UNKNOWN";
     }
  }

//+------------------------------------------------------------------+
//| ExportZoneDataWithStats - Main export function                    |
//+------------------------------------------------------------------+
bool CDataExporter::ExportZoneDataWithStats(const B2BZoneInfo &zones[], int zone_count)
  {
   if(!m_is_initialized)
     {
      Print("[DataExporter] ERROR: Not initialized");
      return false;
     }
   
   // Skip export during optimization (too many runs)
   if(IsOptimization())
     {
      return true;
     }
   
   // Extract just the filename from m_export_path (which already has version)
   string filename = "";
   int last_slash = StringFind(m_export_path, "\\", 0);
   int pos = 0;
   while(last_slash >= 0)
     {
      pos = last_slash + 1;
      last_slash = StringFind(m_export_path, "\\", pos);
     }
   filename = StringSubstr(m_export_path, pos);
   
   if(filename == "")
     {
      // Fallback: generate filename with version from today's date
      datetime now = TimeLocal(); // Use LOCAL time to avoid backtest date confusion
      MqlDateTime dt;
      TimeToStruct(now, dt);
      filename = StringFormat("%s_%s_%04d%02d%02d_%02d%02d%02d.json",
                                     _Symbol,
                                     TFToShortString((ENUM_TIMEFRAMES)Period()),
                                     dt.year, dt.mon, dt.day,
                                     dt.hour, dt.min, dt.sec);
     }
   
   Print("[DataExporter] Using filename: ", filename);
   
   // Write to MQL5 Common Files folder first
   string temp_path = filename;
   int handle = FileOpen(temp_path, FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON);
   if(handle == INVALID_HANDLE)
     {
      Print("[DataExporter] ERROR: Cannot open file for writing. Error: ", GetLastError());
      return false;
     }
   
   // Create a mutable copy of zones to calculate God Data stats
   B2BZoneInfo mutable_zones[];
   ArrayResize(mutable_zones, zone_count);
   for(int i=0; i<zone_count; i++) mutable_zones[i] = zones[i];
   
   // CALCULATE GOD DATA METRICS
   // This is the "Brain" step where we enrich the raw pattern data
   for(int i = 0; i < zone_count; i++)
     {
      if(!mutable_zones[i].IsValid()) continue;
      
      mutable_zones[i].fractal_depth_score = CMetricCalculator::CalculateFractalDepth(mutable_zones[i], mutable_zones, zone_count);
      mutable_zones[i].tf_dominance_score = CMetricCalculator::CalculateTFDominance(mutable_zones[i], mutable_zones, zone_count);
      // mutable_zones[i].elasticity_velocity = CMetricCalculator::CalculateElasticity(mutable_zones[i]); // Phase 2
     }
   
   // Calculate statistics
   int wins = 0, losses = 0, open_zones = 0, invalidated = 0;
   
   for(int i = 0; i < zone_count; i++)
     {
      if(mutable_zones[i].is_invalidated) 
        {
         invalidated++;
        }
      else if(mutable_zones[i].was_traded)
        {
         // Check actual trade outcome
         if(mutable_zones[i].exit_reason == "TP")
            wins++;
         else if(mutable_zones[i].exit_reason == "SL")
            losses++;
         else
            open_zones++; // Trade still open
        }
      else if(mutable_zones[i].is_valid)
        {
         open_zones++; // Valid but not traded yet
        }
     }
   
   // Build JSON string
   string json = "{\n";
   
   // Meta section
   json += "  \"meta\": {\n";
   json += "    \"mode\": \"" + GetModeString() + "\",\n";
   json += "    \"symbol\": \"" + _Symbol + "\",\n";
   json += "    \"export_time\": \"" + TimeToString(TimeLocal(), TIME_DATE|TIME_MINUTES|TIME_SECONDS) + "\",\n";
   json += "    \"ea_version\": \"5.0\",\n";
   
   // Backtest period (if applicable)
   if(IsBacktest())
     {
      // Note: MQL5 doesn't expose tester start/end time directly
      // Use current time as reference
      json += "    \"backtest_period\": {\n";
      json += "      \"start\": \"BACKTEST\",\n";
      json += "      \"end\": \"" + TimeToString(TimeCurrent(), TIME_DATE) + "\"\n";
      json += "    }\n";
     }
   else
     {
      json += "    \"backtest_period\": null\n";
     }
   json += "  },\n";
   
   // Stats section
   json += "  \"stats\": {\n";
   json += "    \"total_zones\": " + IntegerToString(zone_count) + ",\n";
   json += "    \"wins\": " + IntegerToString(wins) + ",\n";
   json += "    \"losses\": " + IntegerToString(losses) + ",\n";
   json += "    \"open\": " + IntegerToString(open_zones) + ",\n";
   json += "    \"invalidated\": " + IntegerToString(invalidated) + "\n";
   json += "  },\n";
   
   // Zones array
   json += "  \"zones\": [\n";
   
   int valid_zone_count = 0;
   for(int i = 0; i < zone_count; i++)
     {
      if(!mutable_zones[i].IsValid() && !mutable_zones[i].is_invalidated)
         continue;
      
      if(valid_zone_count > 0)
         json += ",\n";
      
      json += "    {\n";
      // Identity
      json += "      \"id\": " + IntegerToString(mutable_zones[i].zone_id) + ",\n";
      json += "      \"tf\": \"" + TFToShortString(mutable_zones[i].timeframe) + "\",\n";
      json += "      \"direction\": \"" + DirectionToString(mutable_zones[i].direction) + "\",\n";
      
      // Zone levels
      json += "      \"L1\": " + DoubleToString(mutable_zones[i].L1_price, 2) + ",\n";
      json += "      \"L2\": " + DoubleToString(mutable_zones[i].L2_price, 2) + ",\n";
      json += "      \"fifty\": " + DoubleToString(mutable_zones[i].fifty_percent, 2) + ",\n";
      json += "      \"zone_size_points\": " + DoubleToString(mutable_zones[i].GetZoneSize(), 1) + ",\n";
      
      // Timing
      json += "      \"created_time\": \"" + TimeToString(mutable_zones[i].zone_created_time, TIME_DATE|TIME_MINUTES) + "\",\n";
      json += "      \"created_bar_index\": " + IntegerToString(mutable_zones[i].created_bar_index) + ",\n";
      json += "      \"zone_age_bars\": " + IntegerToString(mutable_zones[i].zone_age_bars) + ",\n";
      
      // Touch status
      json += "      \"touch_count\": " + IntegerToString(mutable_zones[i].touch_count) + ",\n";
      json += "      \"L1_touched\": " + (mutable_zones[i].L1_touched ? "true" : "false") + ",\n";
      json += "      \"L1_touch_time\": \"" + (mutable_zones[i].L1_touch_time > 0 ? TimeToString(mutable_zones[i].L1_touch_time, TIME_DATE|TIME_MINUTES) : "") + "\",\n";
      json += "      \"L1_touch_bar\": " + IntegerToString(mutable_zones[i].L1_touch_bar) + ",\n";
      json += "      \"fifty_touched\": " + (mutable_zones[i].fifty_touched ? "true" : "false") + ",\n";
      json += "      \"fifty_touch_time\": \"" + (mutable_zones[i].fifty_touch_time > 0 ? TimeToString(mutable_zones[i].fifty_touch_time, TIME_DATE|TIME_MINUTES) : "") + "\",\n";
      json += "      \"fifty_touch_bar\": " + IntegerToString(mutable_zones[i].fifty_touch_bar) + ",\n";
      json += "      \"L2_touched\": " + (mutable_zones[i].L2_touched ? "true" : "false") + ",\n";
      json += "      \"L2_touch_time\": \"" + (mutable_zones[i].L2_touch_time > 0 ? TimeToString(mutable_zones[i].L2_touch_time, TIME_DATE|TIME_MINUTES) : "") + "\",\n";
      json += "      \"L2_touch_bar\": " + IntegerToString(mutable_zones[i].L2_touch_bar) + ",\n";
      
      // Analysis
      json += "      \"narrative_direction\": \"" + DirectionToString(mutable_zones[i].direction) + "\",\n";
      json += "      \"atr_at_creation\": " + DoubleToString(mutable_zones[i].atr_at_creation, 2) + ",\n";
      json += "      \"session_created\": \"" + mutable_zones[i].session_created + "\",\n";
      json += "      \"conflicting_zones\": " + IntegerToString(mutable_zones[i].conflicting_zones) + ",\n";
      json += "      \"has_narrative_parent\": " + (mutable_zones[i].has_narrative_parent ? "true" : "false") + ",\n";
      json += "      \"parent_tf\": \"" + TFToShortString(mutable_zones[i].parent_tf) + "\",\n";
      json += "      \"is_inside_parent\": " + (mutable_zones[i].is_inside_parent ? "true" : "false") + ",\n";
      
      // GOD DATA (AI Metrics) - V5.1.2 Complete Export
      json += "      \"fractal_depth_score\": " + IntegerToString(mutable_zones[i].fractal_depth_score) + ",\n";
      json += "      \"tf_dominance_score\": " + DoubleToString(mutable_zones[i].tf_dominance_score, 1) + ",\n";
      json += "      \"cluster_density\": " + IntegerToString(mutable_zones[i].cluster_density) + ",\n";
      json += "      \"elasticity_velocity\": " + DoubleToString(mutable_zones[i].elasticity_velocity, 2) + ",\n";
      json += "      \"parent_count\": " + IntegerToString(mutable_zones[i].parent_count) + ",\n";
      json += "      \"can_trade\": " + (mutable_zones[i].can_trade ? "true" : "false") + ",\n";
      json += "      \"is_pioneer\": " + (mutable_zones[i].is_pioneer ? "true" : "false") + ",\n";
      json += "      \"display_number\": " + IntegerToString(mutable_zones[i].display_number) + ",\n";
      
      // Trade info
      json += "      \"was_traded\": " + (mutable_zones[i].was_traded ? "true" : "false") + ",\n";
      json += "      \"entry_level_used\": \"" + mutable_zones[i].entry_level_used + "\",\n";
      json += "      \"entry_price\": " + DoubleToString(mutable_zones[i].entry_price, 2) + ",\n";
      json += "      \"sl_price\": " + DoubleToString(mutable_zones[i].sl_price, 2) + ",\n";
      json += "      \"tp_price\": " + DoubleToString(mutable_zones[i].tp_price, 2) + ",\n";
      json += "      \"exit_price\": " + DoubleToString(mutable_zones[i].exit_price, 2) + ",\n";
      json += "      \"exit_reason\": \"" + mutable_zones[i].exit_reason + "\",\n";
      json += "      \"trade_duration_bars\": " + IntegerToString(mutable_zones[i].trade_duration_bars) + ",\n";
      json += "      \"max_adverse_excursion\": " + DoubleToString(mutable_zones[i].max_adverse_excursion, 1) + ",\n";
      json += "      \"max_favorable_excursion\": " + DoubleToString(mutable_zones[i].max_favorable_excursion, 1) + ",\n";
      json += "      \"rr_planned\": " + DoubleToString(mutable_zones[i].rr_planned, 2) + ",\n";
      json += "      \"rr_achieved\": " + DoubleToString(mutable_zones[i].rr_achieved, 2) + ",\n";
      json += "      \"pnl_points\": " + DoubleToString(mutable_zones[i].pnl_points, 1) + ",\n";
      json += "      \"pnl_money\": " + DoubleToString(mutable_zones[i].pnl_money, 2) + ",\n";
      
      // Status
      string outcome = "OPEN";
      if(mutable_zones[i].is_invalidated) outcome = "INVALIDATED";
      else if(mutable_zones[i].was_traded && mutable_zones[i].exit_reason != "") outcome = mutable_zones[i].exit_reason;
      
      json += "      \"outcome\": \"" + outcome + "\",\n";
      json += "      \"is_valid\": " + (mutable_zones[i].is_valid ? "true" : "false") + ",\n";
      json += "      \"is_invalidated\": " + (mutable_zones[i].is_invalidated ? "true" : "false") + "\n";
      json += "    }";
      
      valid_zone_count++;
     }
   
   json += "\n  ]\n";
   json += "}\n";
   
   // Write to file
   FileWriteString(handle, json);
   FileClose(handle);
   
   Print("[DataExporter] Exported ", valid_zone_count, " zones to Common Files: ", temp_path);
   Print("[DataExporter] Stats: ", wins, " wins, ", losses, " losses, ", open_zones, " open, ", invalidated, " invalidated");
   
   // Copy to SIGMA Analyst backtests folder
   // Using ShellExecuteW to run cmd.exe for copy outside MQL5 sandbox
   string source_path = TerminalInfoString(TERMINAL_COMMONDATA_PATH) + "\\Files\\" + temp_path;
   string dest_folder = "C:\\Users\\User\\Desktop\\SIGMA Analyst\\public\\data\\backtests\\";
   string dest_path = dest_folder + temp_path;
   
   // Use xcopy for more reliable copying (waits for completion)
   string copy_params = "/C xcopy /Y \"" + source_path + "\" \"" + dest_folder + "\"";
   shell32::ShellExecuteW(0, "open", "cmd.exe", copy_params, "", 0);
   
   Print("[DataExporter] Copying to dashboard: ", dest_path);
   
   // Also copy as "latest.json" for quick access
   string latest_params = "/C copy /Y \"" + source_path + "\" \"" + dest_folder + "latest.json\"";
   shell32::ShellExecuteW(0, "open", "cmd.exe", latest_params, "", 0);
   
   return true;
  }

//+------------------------------------------------------------------+
//| ExportZoneData - Simple version                                   |
//+------------------------------------------------------------------+
bool CDataExporter::ExportZoneData(const B2BZoneInfo &zones[], int zone_count)
  {
   return ExportZoneDataWithStats(zones, zone_count);
  }

//+------------------------------------------------------------------+
//| ExportAccountInfo - Export live account data for Command Center  |
//| Phase 2: Live Data Connection                                     |
//+------------------------------------------------------------------+
bool CDataExporter::ExportAccountInfo(void)
  {
   // Only export in live mode (not during backtest)
   if(IsBacktest() || IsOptimization())
      return false;
   
   // Destination folder for live data
   string dest_folder = "C:\\Users\\User\\Desktop\\SIGMA Analyst\\public\\data\\live\\";
   string filename = "account_info.json";
   
   // Write to MQL5 Common Files first
   int handle = FileOpen(filename, FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON);
   if(handle == INVALID_HANDLE)
     {
      Print("[DataExporter] ERROR: Cannot open account_info.json for writing. Error: ", GetLastError());
      return false;
     }
   
   // Get account information
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double margin = AccountInfoDouble(ACCOUNT_MARGIN);
   double free_margin = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
   double margin_level = AccountInfoDouble(ACCOUNT_MARGIN_LEVEL);
   double profit = AccountInfoDouble(ACCOUNT_PROFIT);
   long leverage = AccountInfoInteger(ACCOUNT_LEVERAGE);
   string currency = AccountInfoString(ACCOUNT_CURRENCY);
   long account_number = AccountInfoInteger(ACCOUNT_LOGIN);
   string broker = AccountInfoString(ACCOUNT_COMPANY);
   string server = AccountInfoString(ACCOUNT_SERVER);
   
   // Build JSON
   string json = "{\n";
   json += "  \"account\": {\n";
   json += "    \"number\": \"" + IntegerToString(account_number) + "\",\n";
   json += "    \"broker\": \"" + EscapeJSON(broker) + "\",\n";
   json += "    \"server\": \"" + EscapeJSON(server) + "\",\n";
   json += "    \"currency\": \"" + currency + "\",\n";
   json += "    \"leverage\": " + IntegerToString(leverage) + ",\n";
   json += "    \"balance\": " + DoubleToString(balance, 2) + ",\n";
   json += "    \"equity\": " + DoubleToString(equity, 2) + ",\n";
   json += "    \"margin\": " + DoubleToString(margin, 2) + ",\n";
   json += "    \"free_margin\": " + DoubleToString(free_margin, 2) + ",\n";
   json += "    \"margin_level\": " + DoubleToString(margin_level, 2) + ",\n";
   json += "    \"profit\": " + DoubleToString(profit, 2) + "\n";
   json += "  },\n";
   
   // Get current symbol info
   json += "  \"symbol\": {\n";
   json += "    \"name\": \"" + _Symbol + "\",\n";
   json += "    \"bid\": " + DoubleToString(SymbolInfoDouble(_Symbol, SYMBOL_BID), (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS)) + ",\n";
   json += "    \"ask\": " + DoubleToString(SymbolInfoDouble(_Symbol, SYMBOL_ASK), (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS)) + ",\n";
   json += "    \"spread\": " + IntegerToString(SymbolInfoInteger(_Symbol, SYMBOL_SPREAD)) + "\n";
   json += "  },\n";
   
   // Timestamp
   json += "  \"timestamp\": \"" + TimeToString(TimeLocal(), TIME_DATE|TIME_MINUTES|TIME_SECONDS) + "\",\n";
   json += "  \"server_time\": \"" + TimeToString(TimeCurrent(), TIME_DATE|TIME_MINUTES|TIME_SECONDS) + "\",\n";
   json += "  \"is_connected\": true\n";
   json += "}\n";
   
   // Write to file
   FileWriteString(handle, json);
   FileClose(handle);
   
   // Copy to SIGMA Analyst live data folder
   string source_path = TerminalInfoString(TERMINAL_COMMONDATA_PATH) + "\\Files\\" + filename;
   string copy_params = "/C xcopy /Y \"" + source_path + "\" \"" + dest_folder + "\"";
   shell32::ShellExecuteW(0, "open", "cmd.exe", copy_params, "", 0);
   
   return true;
  }

//+------------------------------------------------------------------+
//| ExportActiveZones - Export active B2B zones for live monitoring   |
//| Phase 2: Live Data Connection                                      |
//+------------------------------------------------------------------+
bool CDataExporter::ExportActiveZones(const B2BZoneInfo &zones[], int zone_count)
  {
   // Only export in live mode
   if(IsBacktest() || IsOptimization())
      return false;
   
   // Destination folder for live data
   string dest_folder = "C:\\Users\\User\\Desktop\\SIGMA Analyst\\public\\data\\live\\";
   string filename = "active_zones.json";
   
   // Write to MQL5 Common Files first
   int handle = FileOpen(filename, FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON);
   if(handle == INVALID_HANDLE)
     {
      Print("[DataExporter] ERROR: Cannot open active_zones.json for writing. Error: ", GetLastError());
      return false;
     }
   
   // Create a mutable copy of zones to calculate God Data stats
   B2BZoneInfo mutable_zones[];
   ArrayResize(mutable_zones, zone_count);
   for(int i=0; i<zone_count; i++) mutable_zones[i] = zones[i];
   
   // CALCULATE GOD DATA METRICS
   for(int i = 0; i < zone_count; i++)
     {
      if(!mutable_zones[i].IsValid()) continue;
      
      mutable_zones[i].fractal_depth_score = CMetricCalculator::CalculateFractalDepth(mutable_zones[i], mutable_zones, zone_count);
      mutable_zones[i].tf_dominance_score = CMetricCalculator::CalculateTFDominance(mutable_zones[i], mutable_zones, zone_count);
     }
   
   // Build JSON
   string json = "{\n";
   json += "  \"symbol\": \"" + _Symbol + "\",\n";
   json += "  \"timestamp\": \"" + TimeToString(TimeLocal(), TIME_DATE|TIME_MINUTES|TIME_SECONDS) + "\",\n";
   json += "  \"zones\": [\n";
   
   int valid_count = 0;
   for(int i = 0; i < zone_count; i++)
     {
      // Only export valid, non-invalidated zones
      if(!mutable_zones[i].is_valid || mutable_zones[i].is_invalidated)
         continue;
      
      if(valid_count > 0)
         json += ",\n";
      
      json += "    {\n";
      json += "      \"id\": " + IntegerToString(mutable_zones[i].zone_id) + ",\n";
      json += "      \"tf\": \"" + TFToShortString(mutable_zones[i].timeframe) + "\",\n";
      json += "      \"direction\": \"" + DirectionToString(mutable_zones[i].direction) + "\",\n";
      json += "      \"L1\": " + DoubleToString(mutable_zones[i].L1_price, 2) + ",\n";
      json += "      \"L2\": " + DoubleToString(mutable_zones[i].L2_price, 2) + ",\n";
      json += "      \"fifty\": " + DoubleToString(mutable_zones[i].fifty_percent, 2) + ",\n";
      json += "      \"zone_size_points\": " + DoubleToString(mutable_zones[i].GetZoneSize(), 1) + ",\n";
      json += "      \"created_time\": \"" + TimeToString(mutable_zones[i].zone_created_time, TIME_DATE|TIME_MINUTES) + "\",\n";
      json += "      \"zone_age_bars\": " + IntegerToString(mutable_zones[i].zone_age_bars) + ",\n";
      json += "      \"touch_count\": " + IntegerToString(mutable_zones[i].touch_count) + ",\n";
      json += "      \"L1_touched\": " + (mutable_zones[i].L1_touched ? "true" : "false") + ",\n";
      json += "      \"fifty_touched\": " + (mutable_zones[i].fifty_touched ? "true" : "false") + ",\n";
      json += "      \"L2_touched\": " + (mutable_zones[i].L2_touched ? "true" : "false") + ",\n";
      json += "      \"has_narrative_parent\": " + (mutable_zones[i].has_narrative_parent ? "true" : "false") + ",\n";
      json += "      \"parent_tf\": \"" + TFToShortString(mutable_zones[i].parent_tf) + "\",\n";
      
      // GOD DATA - V5.1.2 Complete Export
      json += "      \"fractal_depth_score\": " + IntegerToString(mutable_zones[i].fractal_depth_score) + ",\n";
      json += "      \"tf_dominance_score\": " + DoubleToString(mutable_zones[i].tf_dominance_score, 1) + ",\n";
      json += "      \"cluster_density\": " + IntegerToString(mutable_zones[i].cluster_density) + ",\n";
      json += "      \"elasticity_velocity\": " + DoubleToString(mutable_zones[i].elasticity_velocity, 2) + ",\n";
      json += "      \"parent_count\": " + IntegerToString(mutable_zones[i].parent_count) + ",\n";
      json += "      \"can_trade\": " + (mutable_zones[i].can_trade ? "true" : "false") + ",\n";
      json += "      \"is_pioneer\": " + (mutable_zones[i].is_pioneer ? "true" : "false") + ",\n";
      json += "      \"display_number\": " + IntegerToString(mutable_zones[i].display_number) + ",\n";
      
      json += "      \"session_created\": \"" + mutable_zones[i].session_created + "\",\n";
      json += "      \"atr_at_creation\": " + DoubleToString(mutable_zones[i].atr_at_creation, 2) + "\n";
      json += "    }";
      
      valid_count++;
     }
   
   json += "\n  ],\n";
   json += "  \"total_active\": " + IntegerToString(valid_count) + "\n";
   json += "}\n";
   
   // Write to file
   FileWriteString(handle, json);
   FileClose(handle);
   
   // Copy to SIGMA Analyst live data folder
   string source_path = TerminalInfoString(TERMINAL_COMMONDATA_PATH) + "\\Files\\" + filename;
   string copy_params = "/C xcopy /Y \"" + source_path + "\" \"" + dest_folder + "\"";
   shell32::ShellExecuteW(0, "open", "cmd.exe", copy_params, "", 0);
   
   return true;
  }

#endif // V50_DATA_EXPORTER_MQH

