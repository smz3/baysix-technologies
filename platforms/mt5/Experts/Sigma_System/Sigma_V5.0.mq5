//+------------------------------------------------------------------+
//|                                                  Sigma_V5.0.mq5 |
//|                          Copyright 2025, SIGMA Trading Systems |
//|                                        sigmatrading.ai@gmail.com |
//+------------------------------------------------------------------+
//| V5.0 CLEAN SLATE - B2B ONLY                                      |
//| A simplified EA focused exclusively on B2B zone detection        |
//| All sequence logic has been removed                              |
//| All input parameters are centralized in TradingParameters.mqh    |
//+------------------------------------------------------------------+
#property copyright "Copyright 2025, SIGMA Trading Systems"
#property link      "sigmatrading.ai@gmail.com"
#property version   "5.00"
#property strict
#property description "SIGMA V5.0 - B2B Zone Detection System"
#property description "Clean slate implementation focused on Break-to-Break trading"

//+------------------------------------------------------------------+
//| INCLUDES                                                         |
//+------------------------------------------------------------------+

// Configuration FIRST (all input parameters are here)7
#include <Sigma_System/V5.0/Configuration/TradingParameters.mqh>

// Common Modules
#include <Sigma_System/V5.0/Common/Defines.mqh>
#include <Sigma_System/V5.0/Common/Utils.mqh>
#include <Sigma_System/V5.0/Common/CircularBuffer.mqh>
#include <Sigma_System/V5.0/Common/UniversalSymbolManager.mqh>
#include <Sigma_System/V5.0/Common/PerformanceUtils.mqh>

// Data Modules
#include <Sigma_System/V5.0/Data/Structures.mqh>
#include <Sigma_System/V5.0/Data/ZonePersistence.mqh>  // V5.0.1: TF-based persistence

// System Modules
#include <Sigma_System/V5.0/System/TimeFrameManager.mqh>

// Detection Modules
#include <Sigma_System/V5.0/Detection/SwingPointDetector.mqh>
#include <Sigma_System/V5.0/Detection/RawBreakoutDetector.mqh>
#include <Sigma_System/V5.0/Detection/B2BDetector.mqh>
#include <Sigma_System/V5.0/Detection/B2BConfluence.mqh>
#include <Sigma_System/V5.0/Detection/B2BZoneManager.mqh>  // V5.7.3: Zone cleanup

// Visualization Modules
#include <Sigma_System/V5.0/Visualization/Visualizer.mqh>

// Stub Modules (for future implementation)
#include <Sigma_System/V5.0/Communication/TelegramBot.mqh>
#include <Sigma_System/V5.0/UI/FeedbackPanel.mqh>
#include <Sigma_System/V5.0/Trading/RiskManager.mqh> // Restored V5.8
#include <Sigma_System/V5.0/Trading/TrailingStopManager.mqh>
#include <Sigma_System/V5.0/Trading/TradeSignalGenerator.mqh>
#include <Sigma_System/V5.0/Trading/OrderManager.mqh>
// #include <Sigma_System/V5.0/Trading/GPSEngine.mqh> // REMOVED

// Data Export Module
// V5.0: Data Export (Supabase)
#include <Sigma_System/V5.0/Data/DataExporter.mqh>
#include <Sigma_System/V5.0/Data/QuantLogger.mqh>       // V6.0: Quant Supabase CSV logger
// #include <Sigma_System/V5.0/Data/ZoneLogger.mqh>     // REMOVED: Merged into QuantLogger
#include <Sigma_System/V5.0/UI/FeedbackPanel.mqh>

// Analysis Module (God Data Metrics)
#include <Sigma_System/V5.0/Analysis/MetricCalculator.mqh>

//+------------------------------------------------------------------+
//| GLOBAL VARIABLES                                                 |
//+------------------------------------------------------------------+

// Manager Instances
CTimeFrameManager g_TimeFrameManager;
CSwingPointDetector g_SwingDetector;
CRawBreakoutDetector g_BreakoutDetector;
CB2BDetector g_B2BDetector;
CVisualizer g_Visualizer;
CUniversalSymbolManager g_SymbolManager; // MOVED FROM RiskManager.mqh

// Stub Instances (for future)
CTelegramBot g_TelegramBot;
CFeedbackPanel g_FeedbackPanel;
CRiskManager g_RiskManager; // Restored V5.8
CTrailingStopManager g_TrailingManager;
CTradeSignalGenerator g_SignalGenerator;
COrderManager g_OrderManager;
// CGPSEngine g_GPSEngine_H1; // REMOVED
// CGPSEngine g_GPSEngine_H4; // REMOVED
// CGPSEngine g_GPSEngine_D1; // REMOVED
CDataExporter g_DataExporter;
CQuantLogger g_QuantLogger;       // V6.0: Quant Supabase CSV logger
// CZoneLogger* g_zone_logger = NULL; // REMOVED

// Data Storage - Circular Buffers for each timeframe
// V5.0.4: Unified swing array for chronological L2 selection
CCircularBuffer<SwingPointInfo> g_swings[TOTAL_TIMEFRAMES];  // ALL swings (HIGH + LOW), chronological
CCircularBuffer<RawBreakoutInfo> g_breakouts[TOTAL_TIMEFRAMES];

// V5.0.1: B2B Zones - Dynamic array per timeframe (grows as needed, no eviction)
// V5.7.2 FIX: Replaced CircularBuffer with B2BZoneList wrapper to allow array of dynamic arrays
B2BZoneList g_b2b_zones[TOTAL_TIMEFRAMES];
int g_b2b_zone_count[TOTAL_TIMEFRAMES] = {0, 0, 0, 0, 0, 0, 0, 0, 0};

// V5.1: Use g_B2BDetector.GetPersistence() instead of separate global

// Rate Data Cache
TimeFrameDataCache g_rate_cache[TOTAL_TIMEFRAMES];

// Enabled timeframes array
bool g_tf_enabled[TOTAL_TIMEFRAMES];

// V5.1.2: Sequential display number counter for zones
int g_next_display_number = 1;

// V5.2 OPTIMIZATION: Cache of parent zone IDs with active trades
// Rebuilt only when positions change, not every tick
ulong g_active_parent_ids[];
int   g_active_parent_count = 0;
void  RebuildActiveParentCache();  // Forward declaration

// V5.3: Switch Logic State (Fractal Domino)
ENUM_SIGNAL_DIRECTION g_switch_blocked_direction = DIRECTION_NONE;  // Direction blocked from trading
ENUM_SIGNAL_DIRECTION g_last_h1_direction = DIRECTION_NONE;         // Last H1 zone direction seen

// Forward Declaration for optimization function
void UpdateGlobalConfluence(B2BZoneInfo &all_zones[], int total_zones, bool any_major_bar, int change_mask);

// V5.3: Forward declaration for switch logic
void CheckSwitchEvent();

// V7: Warmup period tracking
datetime g_warmup_start_time = 0;  // Set in OnInit

//+------------------------------------------------------------------+
//| OnInit                                                           |
//+------------------------------------------------------------------+
int OnInit()
  {
   Print("DEBUG: Global Init Start");
   Print("DEBUG: Global Init Start");
   Print("===================================================");
   Print("SIGMA V5.0 - B2B Zone Detection System");
   Print("===================================================");
   
   // Initialize timeframe enable flags
   // Initialize timeframe enable flags with PROFILE LOGIC
   // V7.7: Mask Detection based on Profile to save CPU (Manifold 3.0 Optimization)
   // Defaults: Map (H4+) always ON. Lower TFs depend on Profile.
   
   // 1. Base Map (Always ON for Anchors/Roadblocks)
   g_tf_enabled[5] = true; // H4
   g_tf_enabled[6] = true; // D1
   g_tf_enabled[7] = true; // W1
   g_tf_enabled[8] = true; // MN1

   // 2. Profile Specifics
   if (InpExecutionProfile == PROFILE_INTRADAY_M15)
     {
      g_tf_enabled[0] = false; // M1 (Noise)
      g_tf_enabled[1] = true;  // M5 (Fractal Child)
      g_tf_enabled[2] = true;  // M15 (Exec)
      g_tf_enabled[3] = true;  // M30 (Context)
      g_tf_enabled[4] = true;  // H1 (Anchor)
     }
   else // PROFILE_FULL_MANUAL
     {
      g_tf_enabled[0] = InpEnableM1;
      g_tf_enabled[1] = InpEnableM5;
      g_tf_enabled[2] = InpEnableM15;
      g_tf_enabled[3] = InpEnableM30;
      g_tf_enabled[4] = InpEnableH1;
      g_tf_enabled[5] = InpEnableH4;
      g_tf_enabled[6] = InpEnableD1;
      g_tf_enabled[7] = InpEnableW1;
      g_tf_enabled[8] = InpEnableMN1;
     }
   
   // Initialize circular buffers (swings/breakouts) and dynamic arrays (zones)
   for(int i = 0; i < TOTAL_TIMEFRAMES; i++)
     {
      // V5.0.4: Single unified swing buffer (highs + lows, chronological)
      g_swings[i].Initialize(MAX_HISTORICAL_SWINGS * 2);  // Double capacity for both types
      g_breakouts[i].Initialize(MAX_HISTORICAL_BREAKOUTS);
      // V5.7.2: B2B zones now use dynamic arrays (no capacity limit)
      g_b2b_zones[i].Clear();
      g_b2b_zone_count[i] = 0;
      g_rate_cache[i].Initialize(g_timeframes[i]);
     }
   
   
   
   // V5.0: HYBRID INITIALIZATION STRATEGY
   // Live/Demo: Initialize IMMEDIATELY to prevent visual lag (blank chart)
   // Tester: Defer to OnTick to fix "Lazy Loading" Race Condition
   
   if(!MQLInfoInteger(MQL_TESTER))
   {
      Print("DEBUG: [OnInit] Live Environment Detected. Initializing Immediately...");
      
      // 1. Initialize Components
      g_B2BDetector.Initialize();
      g_SignalGenerator.Initialize(&g_B2BDetector, &g_SwingDetector, &g_BreakoutDetector, &g_OrderManager, &g_RiskManager);
      
      if(InpEnableTradeSignals)
      {
         if(!g_RiskManager.Initialize()) Print("[V5.0] WARNING: Risk Manager initialization failed");
         if(!g_OrderManager.Initialize()) Print("[V5.0] WARNING: Order Manager initialization failed");
         if(!g_TrailingManager.Initialize()) Print("[V7] WARNING: Trailing Manager initialization failed");
      }
      
      if(!g_QuantLogger.Initialize()) Print("[V6.0] WARNING: Quant Logger initialization failed.");
      if(InpLogDetection) g_QuantLogger.SetZoneLogging(true);
      
      if(InpShowFeedbackPanel) g_FeedbackPanel.Create(ChartID());
      
      if(InpLogSystem) Print("[V5.0] System initialized successfully (Live Mode)");
      
      // 2. Run Detection Immediately
      DetectHistoricalSignals();
      
      // 3. Flag as initialized so OnTick doesn't run it again
      g_is_initialized = true; 
   }
   else
   {
      // TESTER ONLY: Defer everything to OnTick
      Print("DEBUG: [OnInit] Tester Environment Detected. Deferring Init to OnTick...");
      g_is_initialized = false; 
   }
   
   return INIT_SUCCEEDED;
  }

//+------------------------------------------------------------------+
//| OnDeinit                                                         |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   // Print("[V5.0] OnDeinit - scanning for exit data...");
   
   // Phase 2: Kill the live data export timer
   if(!MQLInfoInteger(MQL_TESTER))
      EventKillTimer();
   
   // V5.0.1: Save zone states to file before shutdown
   // This preserves touch states across TF changes and EA restarts
   // V5.1: Use detector's persistence (single instance)
   if(!MQLInfoInteger(MQL_TESTER))
     {
      g_B2BDetector.SaveZonesFromBuffers(g_b2b_zones, g_b2b_zone_count);
      Print("[V5.0.1] Zone states saved to persistence file");
     }
   
   // Backtest-only: Scan deal history for exit data (fallback if OnTester didn't run)
   if(MQLInfoInteger(MQL_TESTER))
     {
      // V5.0.1: Collect zones from all TF arrays (needed for MAE/MFE lookup)
      B2BZoneInfo export_zones[];
      int export_count = 0;
      for(int tf_idx = 0; tf_idx < TOTAL_TIMEFRAMES; tf_idx++)
        {
         int tf_zone_count = g_b2b_zone_count[tf_idx];
         int old_size = export_count;
         ArrayResize(export_zones, export_count + tf_zone_count);
         for(int i = 0; i < tf_zone_count; i++)
            export_zones[old_size + i] = g_b2b_zones[tf_idx].items[i];
         export_count += tf_zone_count;
        }
      
      // V6.0: Use QuantLogger for Reconciliation and CSV Export
      g_QuantLogger.ReconcileHistory();
      
      Print("[V6.0] Backtest complete. Exporting Quant trade data...");
      
      MqlDateTime dt;
      TimeToStruct(TimeLocal(), dt);
      // Format: QUANT_TRADES_SYMBOL_YYYYMMDD_HHMMSS_BT.csv
      string csv_filename = StringFormat("SIGMA_Quant\\Trades\\QUANT_%s_%04d%02d%02d_%02d%02d%02d_BT.csv",
                                        _Symbol, dt.year, dt.mon, dt.day, dt.hour, dt.min, dt.sec);
      g_QuantLogger.ExportCSV(csv_filename);
      
      // Export DNA Card (Fallback)
      g_QuantLogger.LogParameters();
      
     }  // End backtest-only block
   
   // V9: Export GPS Flow Data (Backtest & Live) - DISABLED
   // V10.2 FIX: Call Reset() first to log active flows as DETOUR before export
   //            This ensures flows still ON_ROUTE at backtest end are captured
   // g_SignalGenerator.GetGPS_H1().Reset();
   // g_SignalGenerator.GetGPS().Reset();
   // g_SignalGenerator.GetGPS_D1().Reset();
   // g_SignalGenerator.GetGPS_W1().Reset();
   // g_SignalGenerator.GetGPS_MN1().Reset();
   
   // g_SignalGenerator.GetGPS_H1().ExportData();
   // g_SignalGenerator.GetGPS().ExportData(); // H4 is default
   // g_SignalGenerator.GetGPS_D1().ExportData();
   // g_SignalGenerator.GetGPS_W1().ExportData();
   // g_SignalGenerator.GetGPS_MN1().ExportData();
   
   // V6.1: Log FINAL zone states for Phase 0 analysis
   // This captures the outcome of ALL zones at backtest end
   // V6.1: Log FINAL zone states for Phase 0 analysis
   // This captures the outcome of ALL zones at backtest end
   if(InpLogDetection)
   {
      int total_logged = 0;
      for(int tf_idx = 0; tf_idx < TOTAL_TIMEFRAMES; tf_idx++)
      {
         int zone_count = g_b2b_zone_count[tf_idx];
         for(int i = 0; i < zone_count; i++)
         {
            B2BZoneInfo zone = g_b2b_zones[tf_idx].items[i];
            
            if(zone.is_invalidated)
            {
               g_QuantLogger.LogZoneBulldozed(zone);
            }
            else if(zone.L1_touched)
            {
               g_QuantLogger.LogZoneSurvived(zone);
            }
            // Note: UNTOUCHED zones are already logged at CREATED
            total_logged++;
         }
      }
      PrintFormat("[V6.1] Logged final state for %d zones via QuantLogger", total_logged);
   }
   
   // V6.1: Cleanup (QuantLogger cleans itself up in destructor)
   
   g_Visualizer.ClearAllVisuals("EA Deinit");
   
   // Destroy Feedback Panel
   if(InpShowFeedbackPanel)
      g_FeedbackPanel.Destroy();
   
   if(InpLogSystem)
      PrintFormat("[V5.0] System shutdown, reason: %d", reason);
  }

//+------------------------------------------------------------------+
//| OnTimer - Phase 2: Export live data for Command Center           |
//+------------------------------------------------------------------+
void OnTimer()
  {
   // Only export in live mode
   if(MQLInfoInteger(MQL_TESTER))
      return;
   
   // V5.3: DISABLED - Legacy live export
   // g_DataExporter.ExportAccountInfo();
   
   // Collect active zones from all timeframes for export
   B2BZoneInfo all_zones[];
   int zone_count = 0;
   
   for(int tf_idx = 0; tf_idx < TOTAL_TIMEFRAMES; tf_idx++)
     {
      int tf_zone_count = g_b2b_zone_count[tf_idx];
      if(tf_zone_count > 0)
        {
         int old_size = zone_count;
         ArrayResize(all_zones, zone_count + tf_zone_count);
         for(int j = 0; j < tf_zone_count; j++)
            all_zones[old_size + j] = g_b2b_zones[tf_idx].items[j];
         zone_count += tf_zone_count;
        }
     }
   
   // V5.3: DISABLED - Legacy active zones export
   // g_DataExporter.ExportActiveZones(all_zones, zone_count);
  }

//+------------------------------------------------------------------+
//| ScanHistoricalDealsForExits - Backtest fallback for exit data    |
//| DEPRECATED V5.4.3: Replaced by Ticket-Based Reconciliation       |
//+------------------------------------------------------------------+
void ScanHistoricalDealsForExits()
  {
   // Function deprecated. Logic moved to CFractalDominoLogger::ReconcileHistory().
   // This function is kept as a stub to avoid compilation errors if called elsewhere (legacy).
  }

// Forward declaration
void UploadToAPI();

//+------------------------------------------------------------------+
//| OnTester - Called after backtest completes                       |
//+------------------------------------------------------------------+
double OnTester()
  {
   Print("[V5.0] OnTester called - scanning for exit data...");
   
   // V5.2: Sync buffers to detector first so RecordTradeClose can find zones
   g_B2BDetector.LoadZonesFromBuffers(g_b2b_zones, g_b2b_zone_count);
   
   // IMPORTANT: Scan deal history first to get exit data
   // (OnTradeTransaction doesn't reliably fire in backtest)
   ScanHistoricalDealsForExits();
   
   Print("[V5.0] OnTester: Exporting Data for AI Training...");
   
   // 1. Calculate total zones across all timeframes
   int total_zones = 0;
   for(int tf_idx = 0; tf_idx < TOTAL_TIMEFRAMES; tf_idx++)
     {
      total_zones += g_b2b_zone_count[tf_idx];
     }
     
   // 2. Aggregate into single array
   B2BZoneInfo export_zones[];
   ArrayResize(export_zones, total_zones);
   
   int idx = 0;
   for(int tf_idx = 0; tf_idx < TOTAL_TIMEFRAMES; tf_idx++)
     {
      int count = g_b2b_zone_count[tf_idx];
      for(int i = 0; i < count; i++)
         export_zones[idx++] = g_b2b_zones[tf_idx].items[i];
     }
   
   // 3. Reconcile History 
   // V6.0: Use QuantLogger for reconciliation
   g_QuantLogger.ReconcileHistory();
   
   // 4. Export CSV
   MqlDateTime dt2;
   TimeToStruct(TimeCurrent(), dt2);
   string csv_filename = StringFormat("SIGMA_Quant\\Trades\\QUANT_%s_%04d%02d%02d_TESTER.csv",
                                     _Symbol, dt2.year, dt2.mon, dt2.day);
   bool exported = g_QuantLogger.ExportCSV(csv_filename);
   
   // 5. Export Protocol DNA Card (Protocol Audit)
   g_QuantLogger.LogParameters();
   
   if(exported)
     {
      Print("[V6.0] CSV export successful.");
      
      // Auto-upload to Python Brain
      // DISABLED: Error 4014 in Tester. Using Python File Watcher instead.
      /*
      if(InpLogSystem)
        {
         Print("[OnTester] Initiating auto-upload to Python Brain...");
         UploadToAPI();
        }
      */
     }
   else
      Print("[V5.0] Data export failed!");
      
   return 0.0;
  }

//+------------------------------------------------------------------+
//+------------------------------------------------------------------+
//| CORE DATA TYPES                                                  |
//+------------------------------------------------------------------+
struct PositionSnapshot
{
   ulong                ticket;
   ENUM_POSITION_TYPE   type;
   double               sl;
   double               tp;
   double               entry_price;
   ulong                zone_id;
   bool                 is_naked;      // TP == 0
};

void ManageDynamicTP(const B2BZoneInfo &all_zones[], int zone_count, const PositionSnapshot &snapshots[], int snapshot_count)
{
   // [REMOVED IN QUANT 3.1 PURGE] - Dynamic TP is now handled exclusively by TrailingManager/BE
}

//+------------------------------------------------------------------+
//| OnTick                                                           |
//+------------------------------------------------------------------+
bool g_is_initialized = false; // V5.0: Track initialization state

void OnTick()
  {
   //=== V5.0: FIRST TICK INITIALIZATION (Lazy Loading Fix) ===
   if(!g_is_initialized)
   {
      Print("DEBUG: [OnTick] First Tick Detected. Starting Late Initialization...");
      
      // 1. Force Data Synchronization (Now safe to block)
      if(MQLInfoInteger(MQL_TESTER))
      {
         Print("DEBUG: Forcing Tester to Synchronize HTF Data (Deep Sync)...");
         EnsureHistoryLoaded(_Symbol, PERIOD_MN1, 1000); 
         EnsureHistoryLoaded(_Symbol, PERIOD_W1, 1000);
         EnsureHistoryLoaded(_Symbol, PERIOD_D1, 1000);
      }
      
      // 2. Initialize Components (Moved from OnInit)
      Print("DEBUG: Initializing B2B Detector...");
      g_B2BDetector.Initialize();
      
      Print("DEBUG: Initializing Signal Generator...");
      g_SignalGenerator.Initialize(&g_B2BDetector, &g_SwingDetector, &g_BreakoutDetector, &g_OrderManager, &g_RiskManager);
      
      if(InpEnableTradeSignals)
      {
         if(!g_RiskManager.Initialize()) Print("[V5.0] WARNING: Risk Manager initialization failed");
         if(!g_OrderManager.Initialize()) Print("[V5.0] WARNING: Order Manager initialization failed");
         if(!g_TrailingManager.Initialize()) Print("[V7] WARNING: Trailing Manager initialization failed");
      }
      
      // 3. Logger Initialization
      if(!g_QuantLogger.Initialize()) Print("[V6.0] WARNING: Quant Logger initialization failed.");
      if(InpLogDetection) g_QuantLogger.SetZoneLogging(true);
      
      // 4. UI Initialization
      if(InpShowFeedbackPanel) g_FeedbackPanel.Create(ChartID());
      
      // 5. Run Historical Detection (Now that data is forcefully loaded)
      DetectHistoricalSignals();
      
      // 6. Load Presisted Zones (Late Merge)
      if(!MQLInfoInteger(MQL_TESTER))
      {
         int loaded = g_B2BDetector.LoadZonesToBuffers(g_b2b_zones, g_b2b_zone_count);
         if(loaded > 0)
         {
            PrintFormat("[V5.1.2] Merged %d zone states from persistence file", loaded);
            for(int tf_idx = 0; tf_idx < TOTAL_TIMEFRAMES; tf_idx++)
               g_B2BDetector.ValidateZonesInBuffer(g_b2b_zones[tf_idx].items, g_b2b_zone_count[tf_idx]);
         }
      }
      
      // 7. Build Cache
      RebuildActiveParentCache();
      
      g_is_initialized = true;
      Print("DEBUG: [OnTick] Late Initialization Complete. System Active.");
      return; // Skip first tick processing
   }

   //=== SESSION MANAGEMENT: Check for Hard EOD Exit ===
   g_OrderManager.CheckEODExit();
   
   //=== RECONNAISSANCE PASS: Single Loop Trade Snapshot ===
   double current_bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double current_ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double current_mid = (current_bid + current_ask) / 2.0;

   PositionSnapshot snapshots[50]; // Reasonable limit for active trades
   int snapshot_count = 0;
   bool has_naked_pos = false;
   int total_at_start = PositionsTotal();

   for(int i = 0; i < total_at_start && snapshot_count < 50; i++)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || !PositionSelectByTicket(ticket)) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol || PositionGetInteger(POSITION_MAGIC) != InpMagicNumber) continue;

      snapshots[snapshot_count].ticket = ticket;
      snapshots[snapshot_count].type = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
      snapshots[snapshot_count].sl = PositionGetDouble(POSITION_SL);
      snapshots[snapshot_count].tp = PositionGetDouble(POSITION_TP);
      snapshots[snapshot_count].entry_price = PositionGetDouble(POSITION_PRICE_OPEN);
      snapshots[snapshot_count].is_naked = (snapshots[snapshot_count].tp == 0.0);
      
      if(snapshots[snapshot_count].is_naked) has_naked_pos = true;

      // Extract zone_id from comment
      string comment = PositionGetString(POSITION_COMMENT);
      int pos_z = StringFind(comment, "_Z");
      if(pos_z >= 0) snapshots[snapshot_count].zone_id = (ulong)StringToInteger(StringSubstr(comment, pos_z + 2));
      else snapshots[snapshot_count].zone_id = 0;

      snapshot_count++;
     }

   // PRICING STRIDE GATE: Removed - we now use Per-Position Milestone Gating in TrailingManager
   
   // Track if any new data came in (to trigger expensive recalculations)
   bool any_new_bar_processed = false;
   bool any_major_bar = false; 
   bool tf_had_new_bar[TOTAL_TIMEFRAMES];
   ArrayInitialize(tf_had_new_bar, false);

   // V10.3 FIX: Track zone counts before detection for safe logging
   int old_counts[TOTAL_TIMEFRAMES];
   for(int i=0; i<TOTAL_TIMEFRAMES; i++) old_counts[i] = g_b2b_zone_count[i];

   // V10.4 OPTIMIZATION: Consolidated collection for Signaling & UI
   static B2BZoneInfo s_all_zones[];
   static int s_all_zones_count = 0;
   static int s_all_zones_capacity = 0;

   // Process each enabled timeframe for new bar events
   for(int tf_idx = 0; tf_idx < TOTAL_TIMEFRAMES; tf_idx++)
     {
      if(!g_tf_enabled[tf_idx])
         continue;
      
      ENUM_TIMEFRAMES tf = g_timeframes[tf_idx];
      
      if(g_TimeFrameManager.IsNewBar(tf))
        {
         ProcessNewBar(tf, tf_idx);
         any_new_bar_processed = true;
         tf_had_new_bar[tf_idx] = true;
         
         // V11.0: Track major bar closes for quadratic wall gating
         if(tf >= PERIOD_H1) any_major_bar = true;
        }
     }
   
   // MAE/MFE Tracking removed (V17 Optimization: Pure Physics Only)
    
   // V5.8: ENTROPY PRUNING (Garbage collection)
   static datetime last_prune_time = 0;
   if(TimeCurrent() - last_prune_time >= 300) // Every 5 minutes
     {
      int pruning_age = InpZonePruningAgeSeconds;
      if(MQLInfoInteger(MQL_TESTER) && !MQLInfoInteger(MQL_VISUAL_MODE)) pruning_age = 1;

      if(pruning_age > 0)
        {
         int pruned = g_B2BDetector.PruneBuffers(g_b2b_zones, g_b2b_zone_count, pruning_age);
         if(pruned > 0)
         {
            if(InpLogSystem) PrintFormat("[OPTIMIZATION] Pruned %d dead zones from memory.", pruned);
            
            // V18: Sync visual state (Targeted Pruning) to remove "ghost" objects from chart
            g_Visualizer.PruneMissingZones(s_all_zones, s_all_zones_count);
         }
        }
      last_prune_time = TimeCurrent();
     }
    
    //=== V7: BREAK-EVEN & TRAILING STOP MANAGEMENT ===
    g_TrailingManager.UpdateAllPositions();
    
    // V5.0.1 FIX: Use price already captured in Recon Pass
    
    // Shadow mining removed
    
    // For touch detection: bid for sells entering, ask for buys entering
    double tick_high = MathMax(current_bid, current_ask);
    double tick_low = MathMin(current_bid, current_ask);

    // V5.0.1: Update touch status for each TF's zones separately
    // V11.0: BITMASK GATING - Only trigger dirty flag on STRUCTURAL changes
    int change_mask = ZONE_CHANGE_NONE;
    for(int tfi = 0; tfi < TOTAL_TIMEFRAMES; tfi++)
      {
       if(g_b2b_zone_count[tfi] > 0)
            change_mask |= g_B2BDetector.UpdateZoneStatusInBuffer(g_b2b_zones[tfi].items, g_b2b_zone_count[tfi], current_bid, tick_high, tick_low, tf_had_new_bar[tfi]);
      }
    
    // V13: If zones changed (touches/invalidations), rethink the narrative
    // PHASE 2 OPTIMIZATION: Only rethink if STRUCTURAL bit is set
    if((change_mask & ZONE_CHANGE_STRUCTURAL) != 0)
       g_SignalGenerator.SetDirty(true);
    
    // V10.4 OPTIMIZATION: Consolidated collection for Signaling & UI moved to top of tick
    // Only re-populate if data changed or first tick or new bar
    // PHASE 2 OPTIMIZATION: Only rebuild flat array on structural changes or new bars
    if(((change_mask & ZONE_CHANGE_STRUCTURAL) != 0) || any_new_bar_processed || s_all_zones_count == 0)
      {
       s_all_zones_count = 0;
       int total_zones_needed = 0;
       for(int tf_idx = 0; tf_idx < TOTAL_TIMEFRAMES; tf_idx++)
          total_zones_needed += g_b2b_zone_count[tf_idx];
       
       if(total_zones_needed > s_all_zones_capacity)
         {
          ArrayResize(s_all_zones, total_zones_needed + 50);
          s_all_zones_capacity = total_zones_needed + 50;
         }
       
       for(int tf_idx = 0; tf_idx < TOTAL_TIMEFRAMES; tf_idx++)
         {
          int tf_zone_count = g_b2b_zone_count[tf_idx];
          for(int j = 0; j < tf_zone_count; j++)
             s_all_zones[s_all_zones_count++] = g_b2b_zones[tf_idx].items[j];
         }
      }

    //=================================================================
    // V11 OPTIMIZATION: CONFLUENCE & COLLECTION RE-ORDERING
    //=================================================================
    if(any_new_bar_processed)
      {
       // V13: New bar triggers Narrative recalculation
       g_SignalGenerator.SetDirty(true);
       
       // 1. Update flags for all zones (Heavy O(N^2) - only on bar close)
       UpdateGlobalConfluence(s_all_zones, s_all_zones_count, any_major_bar, change_mask);
       
       // 2. Check for H1 switch event (D1-aligned force close)
       CheckSwitchEvent();
       
       // V16 OPTIMIZATION: Removed redundant re-sync loop. s_all_zones is updated in-place by UpdateGlobalConfluence.
       
       // Note: New zone logging is handled here to ensure Parent IDs are populated
       if(InpLogDetection)
         {
          for(int tf_idx = 0; tf_idx < TOTAL_TIMEFRAMES; tf_idx++)
            {
             int current_count = g_b2b_zone_count[tf_idx];
             int start_idx = old_counts[tf_idx];
             for(int i = start_idx; i < current_count; i++)
                g_QuantLogger.LogZoneCreated(g_b2b_zones[tf_idx].items[i]);
            }
         }
      }

    if(has_naked_pos)
    {
       ManageDynamicTP(s_all_zones, s_all_zones_count, snapshots, snapshot_count);
    }

    // UI Feedback Panel - Skip in Tester for maximum speed
    if(!MQLInfoInteger(MQL_TESTER) && InpShowFeedbackPanel)
       g_FeedbackPanel.Update(s_all_zones, s_all_zones_count);
    
    // V5.0.1: Moved label update to here - only redraw on changes
    // V11.3: Enable visual sync in TESTER for structural changes (PRUNING)
    // This ensures invalidated zones are removed from the chart even when no new zones are found.
    bool should_sync_visuals = (change_mask != ZONE_CHANGE_NONE);
    if(should_sync_visuals)
      {
       // In Tester, we only sync if structural changes occur (Zero-Twitch)
       if(MQLInfoInteger(MQL_TESTER))
         {
          if((change_mask & ZONE_CHANGE_STRUCTURAL) != 0)
            {
             // Full sync/prune for Multi-TF or single TF
             for(int tf_idx = 0; tf_idx < TOTAL_TIMEFRAMES; tf_idx++)
               {
                if(g_b2b_zone_count[tf_idx] > 0)
                   g_Visualizer.UpdateAllZoneLabels(g_b2b_zones[tf_idx].items, g_b2b_zone_count[tf_idx]);
               }
             g_Visualizer.PruneMissingZones(s_all_zones, s_all_zones_count);
            }
         }
       else
         {
          // Live trading: standard label update
          if(InpShowMultiTFZones)
            {
             for(int tf_idx = 0; tf_idx < TOTAL_TIMEFRAMES; tf_idx++)
               {
                if(g_b2b_zone_count[tf_idx] > 0)
                   g_Visualizer.UpdateAllZoneLabels(g_b2b_zones[tf_idx].items, g_b2b_zone_count[tf_idx]);
               }
            }
          else
            {
             int current_tf_idx = TFEnumToIndex(ChartPeriod());
             if(current_tf_idx >= 0 && current_tf_idx < TOTAL_TIMEFRAMES)
                g_Visualizer.UpdateAllZoneLabels(g_b2b_zones[current_tf_idx].items, g_b2b_zone_count[current_tf_idx]);
            }
         }
      }

    //=================================================================
    // TRADE SIGNAL EVALUATION (if enabled)
    // V5.2 OPTIMIZATION: Only run when touches changed or new bar
    //=================================================================
    
    //=================================================================
    // MARKET CONTEXT & GPS UPDATE (Always Run)
    // V9: Decoupled from InpEnableTradeSignals so we can log flows without trading
    //=================================================================
    
    if(change_mask != ZONE_CHANGE_NONE || any_new_bar_processed)
      {
       // V10.3 OPTIMIZATION: Use cached s_all_zones instead of collecting again
       double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
       double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
       
       //=== V8: Update Market Flow GPS ===
       // g_SignalGenerator.UpdateGPS(s_all_zones, s_all_zones_count, bid); // REMOVED
       
       //=================================================================
       // TRADE SIGNAL EVALUATION (if enabled)
       //=================================================================
       //=================================================================
       // TRADE SIGNAL EVALUATION (if enabled)
       //=================================================================
       if(InpEnableTradeSignals)
         {
           //=== RUSSIAN DOLL PROTOCOL ===
           // The Signal Generator now handles the Orchestrator and Execution Logic internally
           // We pass the fresh s_all_zones array which contains all active zones for the Orchestrator to analyze
           // V1.3: Pass change_mask for event-driven flip detection (performance optimization)
           g_SignalGenerator.OnTick(SymbolInfoDouble(_Symbol, SYMBOL_BID), TimeCurrent(), ask, bid, s_all_zones, s_all_zones_count, change_mask);
         }

       //=== SAFETY: BLOWOUT STOPPER ===
       if(MQLInfoInteger(MQL_TESTER))
         {
          if(AccountInfoDouble(ACCOUNT_EQUITY) <= 0)
            {
             Print("CRITICAL: Account Blown. Stopping Tester.");
             TesterStop();
            }
         }
      }
   
   // V5.2 OPTIMIZATION: Only redraw if something changed
   // V5.2 OPTIMIZATION: Only redraw if something changed
   // V10.3 OPTIMIZATION: Skip visualization entirely in backtest (invisible + expensive)
   if((change_mask != ZONE_CHANGE_NONE || any_new_bar_processed) && !MQLInfoInteger(MQL_TESTER))
     {
       // V8: Update GPS visualization on chart
       // V8.1: MTF GPS Visualization - show all enabled TFs in stacked view
       // if(InpShowMarketFlow) { ... } // REMOVED
      ChartRedraw();
     }

    //=================================================================
    // PHASE 3: GPS ENGINE EXECUTION (Sniper Module)
    // Run after GPS updates and Vis Redraw
    // Only if Order Execution is Enabled (Safety)
    //=================================================================
    // if(InpEnableOrderExecution) { ... GPS Engine ... } // REMOVED
  }

//+------------------------------------------------------------------+
//| OnTradeTransaction - Detect SL/TP hits and manual closes         |
//+------------------------------------------------------------------+
void OnTradeTransaction(const MqlTradeTransaction &trans,
                        const MqlTradeRequest &request,
                        const MqlTradeResult &result)
  {
   // DEBUG: Log all trade transactions
   // static int tx_count = 0;
   // tx_count++;
   
   // We only care about deal transactions (actual fills)
   if(trans.type != TRADE_TRANSACTION_DEAL_ADD)
      return;
   
   // V5.2 OPTIMIZATION: Rebuild parent cache on position changes
   RebuildActiveParentCache();
   
   // Get the deal info
   ulong deal_ticket = trans.deal;
   if(deal_ticket == 0)
      return;
   
   // Select the deal
   if(!HistoryDealSelect(deal_ticket))
      return;
   
   // DEBUG: Log deal details
   ENUM_DEAL_ENTRY entry_type = (ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal_ticket, DEAL_ENTRY);
   long deal_magic = HistoryDealGetInteger(deal_ticket, DEAL_MAGIC);
   string deal_symbol = HistoryDealGetString(deal_ticket, DEAL_SYMBOL);
   string deal_comment = HistoryDealGetString(deal_ticket, DEAL_COMMENT);
   
   // Check if this is our EA's deal
   if(HistoryDealGetInteger(deal_ticket, DEAL_MAGIC) != InpMagicNumber)
      return;
   
   if(HistoryDealGetString(deal_ticket, DEAL_SYMBOL) != _Symbol)
      return;
   
   // Check if this is an OUT deal (closing a position)
   ENUM_DEAL_ENTRY entry = (ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal_ticket, DEAL_ENTRY);
   if(entry != DEAL_ENTRY_OUT && entry != DEAL_ENTRY_INOUT)
      return;
   
   // This is a position close! Get the details
   double exit_price = HistoryDealGetDouble(deal_ticket, DEAL_PRICE);
   double profit = HistoryDealGetDouble(deal_ticket, DEAL_PROFIT);
   double volume = HistoryDealGetDouble(deal_ticket, DEAL_VOLUME);
   string comment = HistoryDealGetString(deal_ticket, DEAL_COMMENT);
   ENUM_DEAL_REASON reason = (ENUM_DEAL_REASON)HistoryDealGetInteger(deal_ticket, DEAL_REASON);
   long deal_type = HistoryDealGetInteger(deal_ticket, DEAL_TYPE);
   
   // Extract zone_id from comment (supported: B2B_Z123, B2B_M5_Z123...)
   // Comment format example: B2B_M5_Z8529128193198785_D402_F
   ulong zone_id = 0;
   int pos_z = StringFind(comment, "_Z");
   if(pos_z >= 0)
     {
      // Find end of Zone ID (next underscore)
      int start_idx = pos_z + 2;
      int end_idx = StringFind(comment, "_", start_idx);
      
      string id_str;
      if(end_idx > start_idx)
         id_str = StringSubstr(comment, start_idx, end_idx - start_idx);
      else
         id_str = StringSubstr(comment, start_idx); // No suffix, take rest
         
      zone_id = (ulong)StringToInteger(id_str);
     }
   
   if(zone_id == 0)
      return;  // Not our zone trade
   
   // Determine exit reason
   string exit_reason = "MANUAL";
   if(reason == DEAL_REASON_SL)
      exit_reason = "SL";
   else if(reason == DEAL_REASON_TP)
      exit_reason = "TP";
   else if(reason == DEAL_REASON_EXPERT)
      exit_reason = "EA";
   
   // Calculate PnL in points (we need to get the entry price from the zone)
   B2BZoneInfo zone_info;
   double pnl_points = 0;
   if(g_B2BDetector.GetZoneById(zone_id, zone_info))
     {
      if(zone_info.direction == DIRECTION_BULLISH)
         pnl_points = (exit_price - zone_info.entry_price) / _Point;
      else
         pnl_points = (zone_info.entry_price - exit_price) / _Point;
     }
   else
     {
      // V5.0.2: Silent fail if zone not found in buffer (likely from previous run or optimized out)
      // PrintFormat("[WARNING] Zone %I64u not found for closed trade ticket %I64u", zone_id, deal_ticket);
     }
   
   // Record the trade close
   g_B2BDetector.RecordTradeClose(zone_id, exit_price, exit_reason, pnl_points, profit);
   
   PrintFormat("[TRADE] Zone %I64u closed by %s | Exit: %.2f | P&L: %.2f (%.1f pts)",
               zone_id, exit_reason, exit_price, profit, pnl_points);
  }

//+------------------------------------------------------------------+
//| OnChartEvent                                                     |
//+------------------------------------------------------------------+
void OnChartEvent(const int id, const long &lparam, const double &dparam, const string &sparam)
  {
   // Handle mouse clicks for FeedbackPanel minimize button
   if(id == CHARTEVENT_CLICK && InpShowFeedbackPanel)
     {
      g_FeedbackPanel.HandleMinimizeClick((int)lparam, (int)dparam);
     }
   
   // Handle keyboard shortcuts
   if(id == CHARTEVENT_KEYDOWN)
     {
      // 'R' key - Refresh/Rescan
      if(lparam == 82)
        {
         Print("[V5.0] Manual rescan triggered");
         
         // CRITICAL: Clear all circular buffers to reset has_been_broken flags
         // Without this, swings accumulate and stale broken flags persist
         for(int i = 0; i < TOTAL_TIMEFRAMES; i++)
           {
            g_swings[i].Clear();  // V5.0.4: Single unified swing buffer
            g_breakouts[i].Clear();
           }
         
         g_B2BDetector.ClearAllZones();
         g_Visualizer.ClearAllVisuals("Manual Rescan");
         DetectHistoricalSignals();
        }
      
      // 'C' key - Clear visuals
      if(lparam == 67)
        {
         g_Visualizer.ClearAllVisuals("Manual Clear");
        }
     }
   
   // V5.1.2: Handle TF/Chart change - redraw zones immediately
   // Without this, zones disappear when user changes TF and don't reappear
   // until the next zones_detected > 0 event
   if(id == CHARTEVENT_CHART_CHANGE)
     {
      // Collect all zones from global buffers and redraw
      B2BZoneInfo all_zones[];
      int total_zone_count = 0;
      
      if(InpShowMultiTFZones)
        {
         // Collect from ALL TFs
         for(int tf_idx = 0; tf_idx < TOTAL_TIMEFRAMES; tf_idx++)
           {
            int tf_zone_count = g_b2b_zone_count[tf_idx];
            if(tf_zone_count > 0)
              {
               int old_size = total_zone_count;
               ArrayResize(all_zones, total_zone_count + tf_zone_count);
               for(int j = 0; j < tf_zone_count; j++)
                  all_zones[old_size + j] = g_b2b_zones[tf_idx].items[j];
               total_zone_count += tf_zone_count;
              }
           }
        }
      else
        {
         // Only current chart TF
         int current_tf_idx = TFEnumToIndex(ChartPeriod());
         if(current_tf_idx >= 0 && current_tf_idx < TOTAL_TIMEFRAMES)
           {
            total_zone_count = g_b2b_zone_count[current_tf_idx];
            ArrayResize(all_zones, total_zone_count);
            for(int j = 0; j < total_zone_count; j++)
               all_zones[j] = g_b2b_zones[current_tf_idx].items[j];
           }
        }
      
      // Force redraw with current zone data
      if(total_zone_count > 0)
        {
         // V7: Show all zones directly (TF visibility controlled by individual toggles)
         // V8: Prepare GPS IDs
         // Pass 0,0 as legacy arguments (Visualizer will ignore)
         g_Visualizer.DrawAllB2BZones(all_zones, total_zone_count, 0, 0);
        }
     }
  }

//+------------------------------------------------------------------+
//| IsSwingAlreadyInHistory (V3.2 Pattern)                           |
//| Checks if a swing point already exists in the buffer             |
//+------------------------------------------------------------------+
bool IsSwingAlreadyInHistory(int tf_idx, const SwingPointInfo &swing_to_check)
  {
   // V5.0.4: Search single unified buffer
   for(int i = 0; i < g_swings[tf_idx].Count(); i++)
     {
      SwingPointInfo existing = g_swings[tf_idx].Get(i);
      if(existing.time == swing_to_check.time && 
         existing.price == swing_to_check.price &&
         existing.type == swing_to_check.type)
        {
         return true;
        }
     }
   return false;
  }

//+------------------------------------------------------------------+
//| ProcessNewBar                                                    |
//| Main processing logic for a new bar on a given timeframe         |
//| V3.2 PATTERN: Uses closed bars only, checks for duplicates       |
//+------------------------------------------------------------------+
void ProcessNewBar(ENUM_TIMEFRAMES tf, int tf_idx)
  {
   // Load fresh rate data
   MqlRates rates[];
   int bars_copied = CopyRates(_Symbol, tf, 0, InpSwingLookback, rates);
   
   // Use available bars if less than requested (for HTF like MN1)
   int min_bars_required = InpSwingWindow + 4;  // Need extra bars for V3.2 pattern
   if(bars_copied < min_bars_required)
      return;
   
   ArraySetAsSeries(rates, true);
   
   // Store in cache
   ArrayFree(g_rate_cache[tf_idx].rates);
   ArrayResize(g_rate_cache[tf_idx].rates, bars_copied);
   for(int i = 0; i < bars_copied; i++)
      g_rate_cache[tf_idx].rates[i] = rates[i];
   g_rate_cache[tf_idx].loaded_bars_count = bars_copied;
   g_rate_cache[tf_idx].last_loaded_bar_time = rates[0].time;
   
   //=================================================================
   // SWING DETECTION - Using same method as historical detection
   // V5.1.2: Aligned with V3.2 "Accurate but Patient" doctrine
   // Start at index 2 to ensure 2-bar delay for full confirmation
   //=================================================================
   int window_radius = InpSwingWindow / 2;
   
   // V5.1.2: "Accurate but Patient" - Start at bar index 2 for 2-bar delay
   // This ensures the 3-bar swing pattern uses only fully closed bars
   // Matches V3.2 behavior for signal integrity (no plateau handling)
   for(int bar_idx = 2; bar_idx < 5 && bar_idx < bars_copied - window_radius; bar_idx++)
     {
      // Check for Swing HIGH using same detector as historical
      SwingPointInfo high_result = g_SwingDetector.CheckForSwingHigh(tf, InpSwingWindow, InpSwingLookback,
                                                                      rates[bar_idx].time, rates, bars_copied);
      if(high_result.type == SWING_HIGH)
        {
         if(!IsSwingAlreadyInHistory(tf_idx, high_result))
           {
            g_swings[tf_idx].Add(high_result);  // V5.0.4: Unified buffer
            g_Visualizer.DrawSwingPoint(high_result.time, high_result.price, high_result.close_price, DIRECTION_BEARISH, tf);
           }
        }
      
      // Check for Swing LOW using same detector as historical
      SwingPointInfo low_result = g_SwingDetector.CheckForSwingLow(tf, InpSwingWindow, InpSwingLookback,
                                                                    rates[bar_idx].time, rates, bars_copied);
      if(low_result.type == SWING_LOW)
        {
         if(!IsSwingAlreadyInHistory(tf_idx, low_result))
           {
            g_swings[tf_idx].Add(low_result);  // V5.0.4: Unified buffer
            g_Visualizer.DrawSwingPoint(low_result.time, low_result.price, low_result.close_price, DIRECTION_BULLISH, tf);
           }
        }
     }
   
   //=================================================================
   // BREAKOUT DETECTION on the most recently closed bar (index 1)
   // Using same approach as historical: pass ALL swings to detector
   // The detector handles has_been_broken flag internally
   //=================================================================
   MqlRates bar_to_check = rates[1];
   
   // V5.0.4: Build single unified swing array (already chronological)
   SwingPointInfo swings_arr[];
   int swings_count = g_swings[tf_idx].Count();
   ArrayResize(swings_arr, swings_count);
   
   for(int i = 0; i < swings_count; i++)
      swings_arr[i] = g_swings[tf_idx].Get(i);
   
   // V5.0.4: Detect breakouts using unified swing array
   RawBreakoutInfo found_breakouts[];
   int bo_count = g_BreakoutDetector.Detect(found_breakouts, bar_to_check, rates, InpMaxBreakoutAge,
                                            swings_arr, swings_count,
                                            tf, InpLogDetection, true);
   
   // Write back has_been_broken flags to circular buffer
   for(int i = 0; i < swings_count; i++)
      g_swings[tf_idx].Update(i, swings_arr[i]);
   
   // Store breakouts and draw
   for(int i = 0; i < bo_count; i++)
     {
      g_breakouts[tf_idx].Add(found_breakouts[i]);
      g_Visualizer.DrawRawBreakout(found_breakouts[i]);
     }
   
   // Detect B2B zones
   // V5.1: Use 5-Pointer detection - P1(L2) → P2(L1) → P3(structure) → P4(breakout) → P5(older barrier)
   // V5.2 OPTIMIZATION: Incremental scan - only check last 10 swings (new zones only)
   int swing_count_for_scan = g_swings[tf_idx].Count();
   int start_idx = MathMax(0, swing_count_for_scan - 10);  // Only scan last 10 swings
   int zones_detected = g_B2BDetector.DetectB2B_5Pointer(tf, g_swings[tf_idx], g_b2b_zones[tf_idx].items, start_idx);
   g_b2b_zone_count[tf_idx] = g_b2b_zones[tf_idx].Count(); // V5.7.2: Sync count
   
   // V5.1 FIX: Validate zones against history BEFORE drawing
   // This ensures zones that are already invalidated don't get drawn
   if(zones_detected > 0)
     {
      g_B2BDetector.ValidateZonesInBuffer(g_b2b_zones[tf_idx].items, g_b2b_zone_count[tf_idx]);
      
      // V5.1: Consolidate overlapping zones (DISABLED for testing invalidation)
      // int consolidated = CB2BZoneManager::ConsolidateOverlappingZones(g_b2b_zones[tf_idx], 50.0);
      // if(consolidated > 0 && InpLogSystem)
      //    PrintFormat("[B2B] Consolidated %d overlapping zones for %s", consolidated, EnumToString(tf));
     }
   
   // V5.7.3: Clean up dead zones to prevent O(n²) slowdown in long backtests
   // Only removes zones that are invalidated AND never traded (preserves ML data)
   int cleaned = CB2BZoneManager::RemoveDeadZones(g_b2b_zones[tf_idx].items, g_b2b_zone_count[tf_idx]);
   // Commented out: too verbose
   // if(cleaned > 0 && InpLogSystem)
   //    PrintFormat("[CLEANUP] Removed %d dead zones for %s (remaining: %d)", 
   //                cleaned, EnumToString(tf), g_b2b_zone_count[tf_idx]);
   
   if(zones_detected > 0)
     {
      // V5.0.1 FIX: Redraw zones from ALL TFs (not just this one)
      // Because DrawAllB2BZones clears ALL zones first
      B2BZoneInfo zones_to_draw[];
      B2BZoneInfo filtered_zones[]; // V6 Filter
      int total_zone_count = 0;
      
      // 1. Collect ALL zones first for validation context
      B2BZoneInfo temp_all_zones[];
      int temp_count = 0;
      for(int tf_idx = 0; tf_idx < TOTAL_TIMEFRAMES; tf_idx++)
         temp_count += g_b2b_zone_count[tf_idx];
         
      ArrayResize(temp_all_zones, temp_count);
      int tidx = 0;
      for(int tf_idx = 0; tf_idx < TOTAL_TIMEFRAMES; tf_idx++)
        {
         for(int i = 0; i < g_b2b_zone_count[tf_idx]; i++)
            temp_all_zones[tidx++] = g_b2b_zones[tf_idx].items[i];
        }
      
      if(InpShowMultiTFZones)
        {
         // Collect zones from ALL TFs
         for(int tfi = 0; tfi < TOTAL_TIMEFRAMES; tfi++)
           {
            int tfi_zone_count = g_b2b_zone_count[tfi];
            int old_size = total_zone_count;
            ArrayResize(zones_to_draw, total_zone_count + tfi_zone_count);
            for(int j = 0; j < tfi_zone_count; j++)
               zones_to_draw[old_size + j] = g_b2b_zones[tfi].items[j];
            total_zone_count += tfi_zone_count;
           }
        }
      else
        {
         // Only current chart TF
         int current_tf_idx = TFEnumToIndex(ChartPeriod());
         if(current_tf_idx >= 0)
           {
            total_zone_count = g_b2b_zone_count[current_tf_idx];
            ArrayResize(zones_to_draw, total_zone_count);
            for(int j = 0; j < total_zone_count; j++)
               zones_to_draw[j] = g_b2b_zones[current_tf_idx].items[j];
           }
        }
      
      // Show all zones
      g_Visualizer.DrawAllB2BZones(zones_to_draw, total_zone_count, 0, 0);
     }
   
   ChartRedraw();
  }

//+------------------------------------------------------------------+
//| DetectHistoricalSignals                                          |
//| Runs detection on historical bars for all enabled timeframes     |
//| TWO-PASS APPROACH: First detect all swings, then detect breakouts|
//+------------------------------------------------------------------+
void DetectHistoricalSignals()
  {
   Print("[V5.0] Starting historical signal detection...");
   
   for(int tf_idx = 0; tf_idx < TOTAL_TIMEFRAMES; tf_idx++)
     {
      if(!g_tf_enabled[tf_idx])
         continue;
      
      ENUM_TIMEFRAMES tf = g_timeframes[tf_idx];
      
      // Load historical data
      MqlRates rates[];
      int bars_copied = CopyRates(_Symbol, tf, 0, InpHistoricalBars, rates);
      
      // Adaptive minimum bars - use what's available for HTF like MN1/W1
      // V5.0 FIX: Lowered requirement to allow detection on limited history (e.g. 12 MN1 bars)
      int min_bars_required = InpSwingWindow + 2; 
      if(bars_copied < min_bars_required)
        {
         PrintFormat("[V5.0] Insufficient data for TF=%s, got %d bars (need %d)", 
                    TFToString(tf), bars_copied, min_bars_required);
         continue;
        }
      
      ArraySetAsSeries(rates, true);
      
      // Store in cache
      ArrayFree(g_rate_cache[tf_idx].rates);
      ArrayResize(g_rate_cache[tf_idx].rates, bars_copied);
      for(int i = 0; i < bars_copied; i++)
         g_rate_cache[tf_idx].rates[i] = rates[i];
      g_rate_cache[tf_idx].loaded_bars_count = bars_copied;
      g_rate_cache[tf_idx].last_loaded_bar_time = rates[0].time;
      
      // PrintFormat("[V5.0] Loaded %d bars for TF=%s", bars_copied, TFToString(tf));
      
      //=================================================================
      // PASS 1: DETECT ALL SWINGS FIRST (from oldest to newest)
      //=================================================================
      int window_radius = InpSwingWindow / 2;
      
      for(int bar_idx = bars_copied - window_radius - 1; bar_idx >= window_radius; bar_idx--)
        {
         // Check for swing high
         SwingPointInfo high_result = g_SwingDetector.CheckForSwingHigh(tf, InpSwingWindow, InpSwingLookback, 
                                                                        rates[bar_idx].time, rates, bars_copied);
         if(high_result.type == SWING_HIGH)
           {
            g_swings[tf_idx].Add(high_result);  // V5.0.4: Unified buffer
            g_Visualizer.DrawSwingPoint(high_result.time, high_result.price, high_result.close_price, DIRECTION_BEARISH, tf);
           }
         
         // Check for swing low
         SwingPointInfo low_result = g_SwingDetector.CheckForSwingLow(tf, InpSwingWindow, InpSwingLookback, 
                                                                      rates[bar_idx].time, rates, bars_copied);
         if(low_result.type == SWING_LOW)
           {
            g_swings[tf_idx].Add(low_result);  // V5.0.4: Unified buffer
            g_Visualizer.DrawSwingPoint(low_result.time, low_result.price, low_result.close_price, DIRECTION_BULLISH, tf);
           }
        }
      
      //=================================================================
      // PASS 2: DETECT ALL BREAKOUTS (using ALL swings from Pass 1)
      //=================================================================
      // V5.0.4: Build single unified swing array from buffer
      SwingPointInfo swings_arr[];
      int swings_count = g_swings[tf_idx].Count();
      ArrayResize(swings_arr, swings_count);
      
      for(int i = 0; i < swings_count; i++)
         swings_arr[i] = g_swings[tf_idx].Get(i);
      
      // Now check each bar for breakouts against ALL known swings
      for(int bar_idx = bars_copied - 2; bar_idx >= 1; bar_idx--)
        {
         RawBreakoutInfo found_breakouts[];
         int bo_count = g_BreakoutDetector.Detect(found_breakouts, rates[bar_idx], rates, InpMaxBreakoutAge,
                                                  swings_arr, swings_count, tf, false, false);
         
         for(int i = 0; i < bo_count; i++)
           {
            g_breakouts[tf_idx].Add(found_breakouts[i]);
            g_Visualizer.DrawRawBreakout(found_breakouts[i]);
           }
        }
      
      // Write back updated has_been_broken flags to circular buffer
      for(int i = 0; i < swings_count; i++)
         g_swings[tf_idx].Update(i, swings_arr[i]);
      
      //=================================================================
      // DETECT B2B ZONES (after all swings/breakouts processed)
      // V5.1: Use 5-Pointer detection - P1(L2) → P2(L1) → P3(structure) → P4 → P5
      // NOTE: Uses full scan (start_index=0) for historical detection
      //=================================================================
      int zones_detected = g_B2BDetector.DetectB2B_5Pointer(tf, g_swings[tf_idx], g_b2b_zones[tf_idx].items);
      g_b2b_zone_count[tf_idx] = g_b2b_zones[tf_idx].Count(); // V5.7.2: Sync count
      
      PrintFormat("[V5.1] TF=%s: Detected %d B2B zones", TFToString(tf), zones_detected);
     }
   
   // V5.0.1: Validate zones in each TF buffer against history
   // This sets historical touch states (T0/T1/T2/T3) and invalidation
   int total_invalidated = 0;
   int total_consolidated = 0;
   for(int tf_idx = 0; tf_idx < TOTAL_TIMEFRAMES; tf_idx++)
     {
      if(g_b2b_zone_count[tf_idx] > 0)
         {
          total_invalidated += g_B2BDetector.ValidateZonesInBuffer(g_b2b_zones[tf_idx].items, g_b2b_zone_count[tf_idx]);
         
         // V5.1: Consolidate overlapping zones (DISABLED for testing invalidation)
         // total_consolidated += CB2BZoneManager::ConsolidateOverlappingZones(g_b2b_zones[tf_idx], 50.0);
        }
     }
   PrintFormat("[V5.1] Zone validation: %d invalidated", total_invalidated);
   
   //=================================================================
   // V5.2: CALCULATE GOD DATA METRICS for all zones
   // This must happen AFTER all zones are detected and validated
   //=================================================================
   // Collect all zones into single array for metric calculation
   B2BZoneInfo metric_zones[];
   int metric_zone_count = 0;
   for(int tf_idx = 0; tf_idx < TOTAL_TIMEFRAMES; tf_idx++)
     {
      int tf_zone_count = g_b2b_zone_count[tf_idx];
      int old_size = metric_zone_count;
      ArrayResize(metric_zones, metric_zone_count + tf_zone_count);
      for(int j = 0; j < tf_zone_count; j++)
         metric_zones[old_size + j] = g_b2b_zones[tf_idx].items[j];
      metric_zone_count += tf_zone_count;
     }
   
   // Set confluence flags (parent_count, can_trade, is_pioneer)
   CB2BConfluence::SetConfluenceFlags(metric_zones, metric_zone_count); // Ensure parent IDs are set
   CB2BConfluence::SetMultiParentFlags(metric_zones, metric_zone_count);
   CB2BConfluence::SetPioneerFlags(metric_zones, metric_zone_count);
   
   // Calculate God Data metrics for each zone
   for(int i = 0; i < metric_zone_count; i++)
     {
      metric_zones[i].fractal_depth_score = CMetricCalculator::CalculateFractalDepth(metric_zones[i], metric_zones, metric_zone_count);
      metric_zones[i].tf_dominance_score = CMetricCalculator::CalculateTFDominance(metric_zones[i], metric_zones, metric_zone_count);
      metric_zones[i].cluster_density = CMetricCalculator::CalculateClusterDensity(metric_zones[i], metric_zones, metric_zone_count);
     }
   
   // Write back to dynamic arrays
    int write_idx = 0;
    for(int tf_idx = 0; tf_idx < TOTAL_TIMEFRAMES; tf_idx++)
      {
       int tf_zone_count = g_b2b_zone_count[tf_idx];
       for(int j = 0; j < tf_zone_count; j++)
         {
          g_b2b_zones[tf_idx].items[j] = metric_zones[write_idx]; // V5.7.2: Direct array assignment
          write_idx++;
         }
      }
   PrintFormat("[V5.2] God Data calculated for %d zones", metric_zone_count);
   
   // V5.0.1: Draw zones (respecting multi-TF visibility setting)
   // Collect zones from TF arrays into one array for visualization
   B2BZoneInfo all_zones[];
   B2BZoneInfo filtered_zones[]; // V6: Filtered list
   int total_zone_count = 0;
   
   // 1. Collect ALL zones first (needed for Anchor Logic validation)
   B2BZoneInfo temp_all_zones[];
   int temp_count = 0;
   for(int tf_idx = 0; tf_idx < TOTAL_TIMEFRAMES; tf_idx++)
      temp_count += g_b2b_zone_count[tf_idx];
      
   ArrayResize(temp_all_zones, temp_count);
   int tidx = 0;
   for(int tf_idx = 0; tf_idx < TOTAL_TIMEFRAMES; tf_idx++)
     {
      for(int i = 0; i < g_b2b_zone_count[tf_idx]; i++)
         temp_all_zones[tidx++] = g_b2b_zones[tf_idx].items[i];
     }
   
   if(InpShowMultiTFZones)
     {
      // Show zones from ALL TFs (with dimming for non-active TFs)
      for(int tf_idx = 0; tf_idx < TOTAL_TIMEFRAMES; tf_idx++)
        {
         int tf_zone_count = g_b2b_zone_count[tf_idx];
         int old_size = total_zone_count;
         ArrayResize(all_zones, total_zone_count + tf_zone_count);
         
         for(int i = 0; i < tf_zone_count; i++)
            all_zones[old_size + i] = g_b2b_zones[tf_idx].items[i];
         
         total_zone_count += tf_zone_count;
        }
     }
   else
     {
      // Show zones from CURRENT chart TF only
      int current_tf_idx = TFEnumToIndex(ChartPeriod());
      if(current_tf_idx >= 0 && current_tf_idx < TOTAL_TIMEFRAMES)
        {
         int tf_zone_count = g_b2b_zone_count[current_tf_idx];
         ArrayResize(all_zones, tf_zone_count);
         for(int i = 0; i < tf_zone_count; i++)
            all_zones[i] = g_b2b_zones[current_tf_idx].items[i];
         total_zone_count = tf_zone_count;
        }
     }
   
   // V8: Initial Market Flow GPS Update (Historical)
   // Use temp_all_zones which contains ALL zones from ALL TFs (required for GPS)
   double current_price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   // g_SignalGenerator.UpdateGPS(temp_all_zones, temp_count, current_price); // REMOVED
   
   //=== V10.3 FIX: Log ALL Historical Zones (After Confluence & God Data) ===
   // Logic moved from B2BDetector to ensure Parent IDs are captured
   if(InpLogDetection)
     {
      Print("[V10.3] Logging historical zones to CSV (Safe Mode)...");
      for(int tf_idx = 0; tf_idx < TOTAL_TIMEFRAMES; tf_idx++)
        {
         for(int i = 0; i < g_b2b_zone_count[tf_idx]; i++)
           {
            g_QuantLogger.LogZoneCreated(g_b2b_zones[tf_idx].items[i]);
           }
        }
     }
   
      // V8 Update: Prepare GPS IDs for piggyback visualization
      ulong gps_origin = 0;
      ulong gps_target = 0;
      
       // if(InpShowMarketFlow) { ... } // REMOVED
      
      // Update GPS visualization via DrawAllB2BZones (piggyback with Scalar IDs)
      g_Visualizer.DrawAllB2BZones(all_zones, total_zone_count, gps_origin, gps_target);
      
      PrintFormat("DEBUG [OnTimer]: Piggyback Draw Called - Origin: %I64u, Target: %I64u", gps_origin, gps_target);
      
   PrintFormat("[V5.0] Historical detection complete. Total B2B zones: %d", total_zone_count);
      
   ChartRedraw();
  }


//+------------------------------------------------------------------+
//| UpdateGlobalConfluence                                           |
//| V5.2: Calculates O(N^2) geometric relationships once per bar     |
//| V16: In-place update on flattened array + single write-back      |
//+------------------------------------------------------------------+
void UpdateGlobalConfluence(B2BZoneInfo &all_zones[], int total_zones, bool any_major_bar, int change_mask)
  {
    if(total_zones == 0) return;
     
    // 1. Run Hierarchy & Metric Logic (O(N^2) gated)
    static bool force_metrics = true;
    
    // REFINEMENT V17.5: Only recalculate heavy confluence if NEW zones were created or old ones Bulldozed.
    // We REMOVE the any_new_bar/any_major_bar trigger to stop the "Minute-by-Minute" tax.
    bool structural_change = (force_metrics || ((change_mask & ZONE_CHANGE_STRUCTURAL) != 0));
    
    // Safety: If detection logging is disabled in tester, skip metrics entirely (they are purely for CSV)
    bool skip_metrics_in_tester = (MQLInfoInteger(MQL_TESTER) && !InpLogDetection);
    
    if(structural_change && !skip_metrics_in_tester) {
       CB2BConfluence::SetConfluenceFlags(all_zones, total_zones);
       CB2BConfluence::SetMultiParentFlags(all_zones, total_zones);
       CB2BConfluence::SetPioneerFlags(all_zones, total_zones);

       for(int i = 0; i < total_zones; i++) {
          all_zones[i].fractal_depth_score = (int)CMetricCalculator::CalculateFractalDepth(all_zones[i], all_zones, total_zones);
          all_zones[i].tf_dominance_score = CMetricCalculator::CalculateTFDominance(all_zones[i], all_zones, total_zones);
          all_zones[i].cluster_density = CMetricCalculator::CalculateClusterDensity(all_zones[i], all_zones, total_zones);
       }
       
       // 2. Optimized Write-Back (Direct indexing) to TF-specific buffers
       // This ensures the Source of truth is updated after calculations
       int idx = 0;
       for(int tf_idx = 0; tf_idx < TOTAL_TIMEFRAMES; tf_idx++) {
          int count = g_b2b_zone_count[tf_idx];
          for(int i = 0; i < count; i++)
             g_b2b_zones[tf_idx].items[i] = all_zones[idx++];
       }
       
       force_metrics = false;
    }
  }

//+------------------------------------------------------------------+
//| RebuildActiveParentCache                                          |
//| V5.2: Scans open positions and caches parent zone IDs             |
//| Called ONLY when positions change - not every tick                 |
//+------------------------------------------------------------------+
void RebuildActiveParentCache()
  {
   // Clear existing cache
   ArrayResize(g_active_parent_ids, 0);
   g_active_parent_count = 0;
   
   int total_positions = PositionsTotal();
   if(total_positions == 0)
      return;
   
   // Temporary array to collect parent IDs
   ulong temp_parents[];
   ArrayResize(temp_parents, total_positions);
   int found_count = 0;
   
   for(int i = 0; i < total_positions; i++)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket <= 0) continue;
      
      // Check if this is our EA's position
      if(PositionGetInteger(POSITION_MAGIC) != InpMagicNumber) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      
      // Extract zone_id from comment (supported: B2B_Z123, B2B_M5_Z123)
      string comment = PositionGetString(POSITION_COMMENT);
      int pos_z = StringFind(comment, "_Z");
      if(pos_z < 0) continue;
      
      string id_str = StringSubstr(comment, pos_z + 2);
      ulong entry_zone_id = (ulong)StringToInteger(id_str);
      if(entry_zone_id == 0) continue;
      
      // Find this zone's parent in global buffers
        for(int tf_idx = 0; tf_idx < TOTAL_TIMEFRAMES; tf_idx++)
         {
          int zone_count = g_b2b_zone_count[tf_idx];
          for(int z = 0; z < zone_count; z++)
            {
             B2BZoneInfo zone = g_b2b_zones[tf_idx].items[z];
             if(zone.zone_id == entry_zone_id && zone.parent_zone_id != 0)
               {
                // Found the zone! Add its parent to cache
                temp_parents[found_count++] = zone.parent_zone_id;
                break;
               }
            }
         }
      }
   
   // Copy to global cache
   if(found_count > 0)
     {
      ArrayResize(g_active_parent_ids, found_count);
      for(int i = 0; i < found_count; i++)
         g_active_parent_ids[i] = temp_parents[i];
      g_active_parent_count = found_count;
     }
   else
     {
      // Ensure it's empty
      ArrayResize(g_active_parent_ids, 0);
      g_active_parent_count = 0;
     }
  }

//+------------------------------------------------------------------+
//| V5.3: CheckSwitchEvent                                            |
//| Monitors H1 zone direction for switch events                       |
//| Called after zone detection. Triggers force close when:            |
//| - New H1 zone detected with different direction                    |
//| - H1 zone direction aligns with D1 (Navigator)                     |
//+------------------------------------------------------------------+
void CheckSwitchEvent()
  {
   // V5 Switch Logic is disabled in V6
   return;
   
   // if(!InpEnableSwitchLogic)
   //    return;
   
   // Get H1 zone buffer index
   int h1_idx = TFEnumToIndex(PERIOD_H1);
   if(h1_idx < 0 || g_b2b_zone_count[h1_idx] == 0)
       return;
    
    // Get the most recent H1 zone
    B2BZoneInfo latest_h1_zone;
    datetime latest_time = 0;
    
    for(int i = 0; i < g_b2b_zone_count[h1_idx]; i++)
      {
       B2BZoneInfo zone = g_b2b_zones[h1_idx].items[i];
       if(zone.IsValid() && zone.zone_created_time > latest_time)
         {
          latest_time = zone.zone_created_time;
          latest_h1_zone = zone;
         }
      }
   
   // If no valid H1 zone found
   if(latest_time == 0)
      return;
   
   ENUM_SIGNAL_DIRECTION h1_direction = latest_h1_zone.direction;
   
   // Check if H1 direction changed
   if(h1_direction == g_last_h1_direction)
      return;  // No change
   
   // H1 direction changed - check D1 alignment
   int d1_idx = TFEnumToIndex(PERIOD_D1);
   ENUM_SIGNAL_DIRECTION d1_direction = DIRECTION_NONE;
   
   if(d1_idx >= 0 && g_b2b_zone_count[d1_idx] > 0)
     {
      // Get most recent D1 zone direction
      datetime latest_d1_time = 0;
      for(int i = 0; i < g_b2b_zone_count[d1_idx]; i++)
        {
         B2BZoneInfo zone = g_b2b_zones[d1_idx].items[i];
         if(zone.IsValid() && zone.zone_created_time > latest_d1_time)
           {
            latest_d1_time = zone.zone_created_time;
            d1_direction = zone.direction;
           }
        }
     }
   
   // Check D1 alignment condition
   bool d1_aligned = (h1_direction == d1_direction);
   
   if(d1_aligned)
     {
      // SWITCH EVENT! H1 changed direction and is now aligned with D1
      ENUM_SIGNAL_DIRECTION opposite = (h1_direction == DIRECTION_BULLISH) ? 
                                        DIRECTION_BEARISH : DIRECTION_BULLISH;
      
      PrintFormat("[SWITCH] H1 switched to %s (D1-aligned). Force closing %s trades...",
                  (h1_direction == DIRECTION_BULLISH) ? "BUY" : "SELL",
                  (opposite == DIRECTION_BULLISH) ? "BUY" : "SELL");
      
      // Force close opposite trades
      int closed_count = g_OrderManager.ForceCloseByDirection(opposite);
      
      // Block opposite direction entries
      g_switch_blocked_direction = opposite;
      
      PrintFormat("[SWITCH] Blocked direction: %s | Trades closed: %d",
                  (opposite == DIRECTION_BULLISH) ? "BUY" : "SELL", closed_count);
     }
   else
     {
      // H1 changed but NOT D1-aligned - reset blocking
      g_switch_blocked_direction = DIRECTION_NONE;
      PrintFormat("[SWITCH] H1 changed to %s (NOT D1-aligned). No switch action.",
                  (h1_direction == DIRECTION_BULLISH) ? "BUY" : "SELL");
     }
   
   // Save the new H1 direction
   g_last_h1_direction = h1_direction;
  }

//+------------------------------------------------------------------+
//| ManageDynamicTP                                                   |
//| V5.5.1: For positions without TP (TP=0), monitor for opposite    |
//| H1 zones. When an opposite H1 zone touches L1/T1, set TP there.  |
//| This is the "ATH TP" logic - positions at ATH have no TP until   |
//| an opposite H1 zone forms and gets touched.                       |
//+------------------------------------------------------------------+
// DELETED: Unified with ManageDynamicTP(all_zones, count)
/*
void ManageDynamicTP()
  {
   ...
  }
*/

//+------------------------------------------------------------------+
//| CheckZoneInvalidation                                             |
//| V5.5.2: Close positions immediately when entry zone is invalidated|
//| Zone invalidation = price broke through L2 (trade thesis failed)  |
//+------------------------------------------------------------------+
void CheckZoneInvalidation()
  {
   int total = PositionsTotal();
   if(total == 0) return;
   
   // Collect all zones for lookup
   B2BZoneInfo all_zones[];
   int zone_count = 0;
   for(int tf_idx = 0; tf_idx < TOTAL_TIMEFRAMES; tf_idx++)
     {
      int tf_count = g_b2b_zone_count[tf_idx];
      ArrayResize(all_zones, zone_count + tf_count);
      for(int j = 0; j < tf_count; j++)
         all_zones[zone_count + j] = g_b2b_zones[tf_idx].items[j];
      zone_count += tf_count;
     }
   
   if(zone_count == 0) return;
   
   // Check each open position (reverse loop for safe closing)
   for(int i = total - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      
      if(PositionGetInteger(POSITION_MAGIC) != InpMagicNumber) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      
      // Extract zone_id from comment (format: B2B_M5_Z{zone_id}_D{num}_{level})
      string comment = PositionGetString(POSITION_COMMENT);
      int pos_z = StringFind(comment, "_Z");
      if(pos_z < 0) continue;
      
      string after_z = StringSubstr(comment, pos_z + 2);
      int pos_underscore = StringFind(after_z, "_");
      if(pos_underscore < 0) continue;
      
      ulong zone_id = (ulong)StringToInteger(StringSubstr(after_z, 0, pos_underscore));
      if(zone_id == 0) continue;
      
      // Look up the zone to check if invalidated
      for(int z = 0; z < zone_count; z++)
        {
         if(all_zones[z].zone_id == zone_id)
           {
            // Check if zone is invalidated
            if(all_zones[z].is_invalidated)
              {
               // Close the position immediately
               double exit_price = PositionGetDouble(POSITION_PRICE_CURRENT);
               double entry_price = PositionGetDouble(POSITION_PRICE_OPEN);
               double profit = PositionGetDouble(POSITION_PROFIT);
               ENUM_POSITION_TYPE pos_type = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
               
               // Calculate PnL in points
               double pnl_points = (pos_type == POSITION_TYPE_BUY)
                                   ? (exit_price - entry_price) / _Point
                                   : (entry_price - exit_price) / _Point;
               
               PrintFormat("[ZONE INVALIDATED] ❌ Closing position #%I64u | Zone: %I64u | PnL: %.2f (%.1f pts)",
                           ticket, zone_id, profit, pnl_points);
               
               // Close position
               if(g_OrderManager.ClosePosition(ticket))
                 {
                  // Log to FractalDomino
                  // Extract display_num and level_offset for FD tracking
                  int display_num = 0;
                  int level_offset = 1;
                  int pos_d = StringFind(comment, "_D");
                  if(pos_d >= 0)
                    {
                     string after_d = StringSubstr(comment, pos_d + 2);
                     int pos_ul = StringFind(after_d, "_");
                     if(pos_ul >= 0)
                       {
                        display_num = (int)StringToInteger(StringSubstr(after_d, 0, pos_ul));
                        string level = StringSubstr(after_d, pos_ul + 1);
                        if(level == "L1") level_offset = 1;
                        else if(level == "FIFTY") level_offset = 2;
                        else if(level == "L2") level_offset = 3;
                       }
                    }
                  
                  // V6.0: QuantLogger.ReconcileHistory will handle outcome updates at backtest end.
                 }
              }
            break; // Found the zone, stop searching
           }
        }
     }
  }


//+------------------------------------------------------------------+
//| UploadToAPI                                                      |
//| Reads trades.json and POSTs it to the local Python ML Server     |
//+------------------------------------------------------------------+
void UploadToAPI()
  {
   string filename = "Impact\\trades.json"; // Path relative to MQL5/Files
   
   // 1. Read JSON file content
   int handle = FileOpen(filename, FILE_READ|FILE_TXT|FILE_ANSI|FILE_COMMON); // Read as ANSI text from Common folder
   if(handle == INVALID_HANDLE)
     {
      PrintFormat("[AutoUpload] ❌ Failed to open %s. Error: %d", filename, GetLastError());
      return;
     }
   
   string json_content = "";
   while(!FileIsEnding(handle))
     {
      json_content += FileReadString(handle); 
     }
   FileClose(handle);
   
   // Check if content valid
   if(StringLen(json_content) < 10)
     {
      Print("[AutoUpload] ❌ CSV/JSON file appears empty. Skipping upload.");
      return;
     }

   // 2. Prepare WebRequest
   string url = "http://127.0.0.1:8000/train";
   char post_data[];
   char result_data[];
   string result_headers;
   string headers = "Content-Type: application/json\r\nX-API-Key: sigma-ml-2026";
   
   // Convert string to char array
   StringToCharArray(json_content, post_data, 0, WHOLE_ARRAY, CP_UTF8);
   
   // 3. Send POST Request with reduced timeout (5 sec)
   int timeout = 5000; 
   int res = WebRequest("POST", url, headers, timeout, post_data, result_data, result_headers);
   
   // 4. Handle Result
   if(res == 200)
     {
      string response = CharArrayToString(result_data);
      PrintFormat("[AutoUpload] ✅ SUCCESS! Python Brain updated. Response: %s", response);
     }
   else
     {
      // If WebRequest not allowed
      if(res == -1)
        {
         int err = GetLastError();
         if(err == 4060) // ERR_FUNCTION_NOT_ALLOWED
           {
            Print("[AutoUpload] ⚠️ WebRequest failed. Please enable 'Allow WebRequest' for 'http://127.0.0.1:8000' in Tools->Options->Expert Advisors");
           }
         else
           {
            PrintFormat("[AutoUpload] ❌ Request Error %d. LastError: %d", res, err);
           }
        }
      else
        {
         PrintFormat("[AutoUpload] ❌ Server Error %d. Response: %s", res, CharArrayToString(result_data));
        }
     }
  }

//+------------------------------------------------------------------+
//| OnTesterDeinit                                                   |
//| Called when backtest ends. Saves the Protocol Audit Card.        |
//+------------------------------------------------------------------+
void OnTesterDeinit()
  {
   g_QuantLogger.LogParameters();
  }
