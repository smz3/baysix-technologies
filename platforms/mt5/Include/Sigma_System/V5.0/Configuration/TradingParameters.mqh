//+------------------------------------------------------------------+
//|                                            TradingParameters.mqh |
//|                             Copyright 2025, Sigma Trading System |
//+------------------------------------------------------------------+
//| V5.0 CLEAN SLATE - B2B ONLY                                      |
//| CENTRALIZED CONFIGURATION - ALL INPUT PARAMETERS IN ONE PLACE    |
//+------------------------------------------------------------------+
#ifndef V50_TRADINGPARAMETERS_MQH
#define V50_TRADINGPARAMETERS_MQH

#property strict

#include "../Common/Defines.mqh"

//+------------------------------------------------------------------+
//| GENERAL SETTINGS                                                  |
//+------------------------------------------------------------------+
//+------------------------------------------------------------------+
//| NEW ENUMS (CLEANUP)                                               |
//+------------------------------------------------------------------+
enum ENUM_EXECUTION_PROFILE
{
   PROFILE_INTRADAY_M15  = 1, // Preset: M15 Execution (Fast, M1 Disabled)
   PROFILE_FULL_MANUAL   = 3  // Custom: Use 'Manual TF Overrides' below
};
//+------------------------------------------------------------------+
//| 1. STRATEGY & PHYSICS KERNEL                                      |
//+------------------------------------------------------------------+
input string    _Sep_Core_      = "=== STRATEGY & PHYSICS KERNEL ==="; // ---------
// Strategy Mode: Hardcoded to RUSSIAN DOLL (Unified)
// Momentum: Hardcoded to FRACTAL
input ENUM_EXECUTION_PROFILE InpExecutionProfile = PROFILE_FULL_MANUAL; // Timeframe Profile

// [PURGED] Physics Kernel
// input string    _Sep_Physics_   = "--- QUANT PHYSICS SETTINGS ---";

// LIFO FLOW SETTINGS - REMOVED (Legacy)

//+------------------------------------------------------------------+
//| GENERAL SETTINGS                                                  |
//+------------------------------------------------------------------+
input string    _Sep_General_ = "=== GENERAL SETTINGS ==="; // ---------
input string    InpEASuffix = "_V50";            // EA Suffix for object names
// Order Execution
input int       InpMagicNumber = 50000;          // Magic number for trades
input int       InpSlippage = 30;                // Maximum slippage (points)
input int       InpHistoricalBars = 5000;        // Initial bar load
input int       InpQuantMinAgeBars = 8;          // B2B: Minimum bars for structural validation
input int       InpMaxZoneAgeBars = 5000;        // Max bars before zone expires
input int       InpZonePruningAgeSeconds = 86400; // [Optimization] Prune dead zones older than X seconds (0=Disable)

//+------------------------------------------------------------------+
//| B2B DETECTION PARAMETERS                                          |
//+------------------------------------------------------------------+
input string    _Sep_B2B_ = "=== B2B DETECTION ==="; // ---------
input bool      InpEnableB2BDetection = true;    // Enable B2B Detection
//+------------------------------------------------------------------+
//| TRADE SIGNAL SETTINGS                                              |
//+------------------------------------------------------------------+
input string    _Sep_Trading_ = "=== TRADE SIGNAL SETTINGS ==="; // ---------
input bool      InpEnableTradeSignals = true;   // Enable trade signal generation
input bool      InpEnableOrderExecution = true; // Enable Trades Execution (ACTIVATED FOR PHASE 1)

//+------------------------------------------------------------------+
//| INTRADAY STRATEGY (V6.3)                                          |
//+------------------------------------------------------------------+
input string    _Sep_Intraday_ = "=== INTRADAY STRATEGY ==="; // ---------
input bool      InpEnableIntraday      = false;  // Enable Intraday Strategy
input double    InpIntradayMinRR       = 1.5;    // Minimum R:R for Intraday Trades
input string    InpIntradaySessionStart = "08:00"; // Intraday Entry Window Start (UTC)
input string    InpIntradaySessionEnd   = "20:00"; // Intraday Entry Window End (UTC)

//+------------------------------------------------------------------+
//| MASTER TIMEFRAME CONTROL (Detection, Execution, Visibility)        |
//+------------------------------------------------------------------+
// Global Controls
input bool      InpOnlyShowConfluenceZones = false; // Only show zones with parent

//+------------------------------------------------------------------+
//| RISK ENGINE CONFIGURATION                                         |
//+------------------------------------------------------------------+
input string    _Sep_Risk_ = "=== RISK CONFIGURATION ==="; // ---------
input double    InpBaseRisk       = 1.0;          // Base Risk % Per Trade (Swing)
input double    InpDayTradeRiskPct = 0.3;         // V6.3: Day Trade / Intraday Risk %
input double    InpMaxLotsPerTrade = 100.0;       // Max Lot Cap
input int       InpMaxOpenPositions = 200;        // Max Position Cap
input double    InpMinMarginLevel = 150.0;        // Min Margin Level (%)

//+------------------------------------------------------------------+
//| ORDER PROTOCOL (TOUCH ALLOCATION)                                 |
//+------------------------------------------------------------------+
input string    _Sep_Touch_ = "=== ORDER PROTOCOL (TOUCH) ==="; // ---------

// T1 (PROBE): Shallow touch at L1
input bool      InpEnableEntry_T1 = true;
input double    InpAllocation_T1  = 0.2;          // Multiplier of Base Risk (0.2 = 20% of 1%)

// T2 (PRIME): 50% retracement
input bool      InpEnableEntry_T2 = true;
input double    InpAllocation_T2  = 0.4;          // Multiplier (0.4 = 40% of 1%)

// T3 (SNIPER): Deep L2 touch
input bool      InpEnableEntry_T3 = true;
input double    InpAllocation_T3  = 0.4;          // Multiplier (0.4 = 40% of 1%)

//+------------------------------------------------------------------+
//| EXIT MANAGEMENT ENGINE                                            |
//+------------------------------------------------------------------+
input string    _Sep_Exit_ = "=== EXIT MANAGEMENT ==="; // ---------

// 1. STOP LOSS
input double    InpSLBufferPoints = 350.0;        // Stop Loss Buffer (Points)

// 2. BREAK EVEN
input bool      InpEnableBreakEven     = true;    // Enable Break-Even
input double    InpBEActivationPoints  = 150;     // BE Activation (Points)
input double    InpBELockInPoints      = 50;      // BE Lock-in (Points)

// 3. TRAILING STOP
input bool      InpEnableTrailing      = true;    // Enable Trailing Stop
input double    InpTrailStartPoints    = 450.0;   // Trail Start (Points)
input double    InpTrailStepPoints     = 250.0;   // Trail Step (Points)

// 4. TAKE PROFIT
input bool      InpUseFixedTarget      = false;   // Enable Fixed R-Multiple
input double    InpTarget_R            = 1.5;     // Fixed Target R

//+------------------------------------------------------------------+
//| SESSION MANAGEMENT                                                |
//+------------------------------------------------------------------+
input string    _Sep_Session_ = "=== SESSION CONTROL ==="; // ---------
input string    InpSessionStart = "00:00";       // Global Start Time (HH:MM) - PHASE 0: All Hours
input string    InpSessionEnd   = "23:59";       // Global End Entry Time (HH:MM) - PHASE 0: All Hours
input bool      InpEnableEODExit = false;        // Enable Hard End-of-Day Exit (OFF for harvest)
input string    InpEODExitTime  = "20:45";       // Hard Market Exit Time (HH:MM) - Pre-Rollover

//+------------------------------------------------------------------+
//| SURVIVAL GATE (Live Execution Protocol)                           |
//+------------------------------------------------------------------+
input string    _Sep_Survival_ = "=== SURVIVAL GATE (LIVE ONLY) ==="; // ---------
input bool      InpEnableSurvivalGate = false;   // Enable Survival Gate (OFF for harvest mode)
input string    InpSurvivalSessionStart = "00:00"; // Live Entry Start (HH:MM) - PHASE 0: All Hours
input string    InpSurvivalSessionEnd   = "23:59"; // Live Entry End (HH:MM) - PHASE 0: All Hours
input bool      InpSurvivalAllowT1     = true;   // Allow T1 (L1 Probe) for Logging (ON for harvest)


//+------------------------------------------------------------------+
//| EXECUTION PARAMETERS                                             |
//+------------------------------------------------------------------+
input string    _Sep_Detection_ = "=== DETECTION PARAMETERS ==="; // ---------
input int       InpSwingWindow = 3;              // Swing detection window size
input int       InpSwingLookback = 20;           // Swing lookback bars (for live detection)
input int       InpMaxBreakoutAge = 0;          // Max breakout age in bars (0 = no limit)
//+------------------------------------------------------------------+
//| SWING & BREAKOUT VISUALIZATION                                    |
//+------------------------------------------------------------------+
input string    _Sep_Swing_ = "=== SWING & BREAKOUT DISPLAY ==="; // ---------
input bool      InpShowSwingPoints = false;       // Show Swing Points
input bool      InpShowRawBreakouts = false;      // Show Raw Breakout markers (Bob/Bos)
input int       InpBulletFontSize = 12;          // Swing bullet size
input int       InpLabelFontSize = 8;            // Swing label size

//+------------------------------------------------------------------+
//| B2B ZONE VISUALIZATION                                            |
//+------------------------------------------------------------------+
input string    _Sep_B2BVis_ = "=== B2B ZONE DISPLAY ==="; // ---------
input bool      InpShowB2BZones = true;          // Show B2B Zones
input bool      InpShowB2BFiftyLine = true;      // Show 50% line
input bool      InpShowB2BBarrierMarkers = true; // Show 2nd barrier markers
input bool      InpShowMultiTFZones = true;      // Global toggle for all TF zones
// input bool InpShowManifoldRadar REMOVED
input int       InpB2BLabelFontSize = 8;         // Font size for zone labels

// Dedicated Timeframe Visibility
input bool      InpShowB2BZonesMN1 = true; // [MN1] Show on Chart
input bool      InpShowB2BZonesW1  = true; // [W1] Show on Chart
input bool      InpShowB2BZonesD1  = true; // [D1] Show on Chart
input bool      InpShowB2BZonesH4  = true; // [H4] Show on Chart
input bool      InpShowB2BZonesH1  = true; // [H1] Show on Chart
input bool      InpShowB2BZonesM30 = true; // [M30] Show on Chart
input bool      InpShowB2BZonesM15 = true; // [M15] Show on Chart
input bool      InpShowB2BZonesM5  = true; // [M5] Show on Chart
input bool      InpShowB2BZonesM1  = true; // [M1] Show on Chart

//+------------------------------------------------------------------+
//| ADVANCED: MANUAL TIMEFRAME OVERRIDES (MOVED TO BOTTOM)        |
//| (Controlled by Execution Profile by default)                     |
//+------------------------------------------------------------------+
input string    _Sep_TF_Hub_ = "=== ADVANCED: MANUAL TF OVERRIDES ==="; // ---------

// 1. NARRATIVE LAYER (Context & Bias)
input string    _Sep_MN1_ = ">>> MONTHLY (MN1)";
input bool      InpEnableMN1  = true;  //   [MN1] Detect Zones
input bool      InpExecuteMN1 = false; //   [MN1] Execute Trades

input string    _Sep_W1_ = ">>> WEEKLY (W1)";
input bool      InpEnableW1   = true;  //   [W1] Detect Zones
input bool      InpExecuteW1  = false; //   [W1] Execute Trades

input string    _Sep_D1_ = ">>> DAILY (D1)";
input bool      InpEnableD1   = true;  //   [D1] Detect Zones
input bool      InpExecuteD1  = false; //   [D1] Execute Trades

// 2. CONTROL LAYER (The Radar Walls)
input string    _Sep_H4_ = ">>> 4-HOUR (H4)";
input bool      InpEnableH4   = true;  //   [H4] Detect Zones
input bool      InpExecuteH4  = true;  //   [H4] Execute Trades (Generals Unleashed)

input string    _Sep_H1_ = ">>> 1-HOUR (H1)";
input bool      InpEnableH1   = true;  //   [H1] Detect Zones
input bool      InpExecuteH1  = true;  //   [H1] Execute Trades (Generals Unleashed)

// 3. SNIPER LAYER (Surgical Execution)
input string    _Sep_M30_ = ">>> 30-MINUTE (M30)";
input bool      InpEnableM30  = true;  //   [M30] Detect Zones
input bool      InpExecuteM30 = true;  //   [M30] Execute Trades (Generals Unleashed)

input string    _Sep_M15_ = ">>> 15-MINUTE (M15)";
input bool      InpEnableM15  = false; //   [M15] Detect Zones
input bool      InpExecuteM15 = false; //   [M15] Execute Trades

input string    _Sep_M5_ = ">>> 5-MINUTE (M5)";
input bool      InpEnableM5   = true;  //   [M5] Detect Zones
input bool      InpExecuteM5   = true;  //   [M5] Execute Trades

input string    _Sep_M1_ = ">>> 1-MINUTE (M1)";
input bool      InpEnableM1   = false; //   [M1] Detect Zones
input bool      InpExecuteM1   = false; //   [M1] Execute Trades



//+------------------------------------------------------------------+
//| V5.6: INDIVIDUAL TIMEFRAME COLORS                                 |
//| Each TF has distinct Buy/Sell colors (Active + Dim)               |
//+------------------------------------------------------------------+
input string    _Sep_TFColors_ = "=== INDIVIDUAL TF COLORS ==="; // ---------

// MN1 Colors (Purple theme)
input color     InpB2BMN1BuyColor = clrOrchid;
input color     InpB2BMN1SellColor = clrMediumOrchid;
input color     InpB2BMN1BuyDimColor = clrDarkOrchid;
input color     InpB2BMN1SellDimColor = clrDarkViolet;

// W1 Colors (Green theme)
input color     InpB2BW1BuyColor = clrLime;
input color     InpB2BW1SellColor = clrSpringGreen;
input color     InpB2BW1BuyDimColor = clrDarkGreen;
input color     InpB2BW1SellDimColor = clrForestGreen;

// D1 Colors (Magenta/Pink theme)
input color     InpB2BD1BuyColor = clrMagenta;
input color     InpB2BD1SellColor = clrDeepPink;
input color     InpB2BD1BuyDimColor = clrDarkMagenta;
input color     InpB2BD1SellDimColor = clrMediumVioletRed;

// H4 Colors (Blue theme)
input color     InpB2BH4BuyColor = clrDodgerBlue;
input color     InpB2BH4SellColor = clrRed;
input color     InpB2BH4BuyDimColor = clrNavy;
input color     InpB2BH4SellDimColor = clrMaroon;

// H1 Colors (Royal Blue theme)
input color     InpB2BH1BuyColor = clrRoyalBlue;
input color     InpB2BH1SellColor = clrCrimson;
input color     InpB2BH1BuyDimColor = clrMidnightBlue;
input color     InpB2BH1SellDimColor = clrDarkRed;

// M30 Colors (Cyan theme)
input color     InpB2BM30BuyColor = clrCyan;
input color     InpB2BM30SellColor = clrOrangeRed;
input color     InpB2BM30BuyDimColor = clrTeal;
input color     InpB2BM30SellDimColor = clrSaddleBrown;

// M15 Colors (Turquoise theme)
input color     InpB2BM15BuyColor = clrTurquoise;
input color     InpB2BM15SellColor = clrTomato;
input color     InpB2BM15BuyDimColor = clrDarkCyan;
input color     InpB2BM15SellDimColor = clrBrown;

// M5 Colors (Aqua theme)
input color     InpB2BM5BuyColor = clrAqua;
input color     InpB2BM5SellColor = clrCoral;
input color     InpB2BM5BuyDimColor = clrDarkSlateGray;
input color     InpB2BM5SellDimColor = clrSienna;

// M1 Colors (Gold theme)
input color     InpB2BM1BuyColor = clrGold;
input color     InpB2BM1SellColor = clrOrange;
input color     InpB2BM1BuyDimColor = clrDarkGoldenrod;
input color     InpB2BM1SellDimColor = clrChocolate;

// Label Colors
input color     InpB2BNarrativeLabelColor = clrYellow;
input color     InpB2BControlLabelColor = clrWhite;
input color     InpB2BSniperLabelColor = clrWhite;

// Other B2B colors
input color     InpB2BFiftyLineColor = clrGray;
input color     InpB2BDimLabelColor = clrDarkGray;



// Swing & Breakout Colors (V3.2 Style)
input color     InpClrSwingHigh = clrMistyRose;  // Color for Swing High
input color     InpClrSwingLow = clrMistyRose;   // Color for Swing Low
input color     InpClrBob = clrSlateGray;        // Color for Breakout Buy (Bob)
input color     InpClrBos = clrSlateGray;        // Color for Breakout Sell (Bos)

//+------------------------------------------------------------------+
//| LOGGING PARAMETERS                                                |
//+------------------------------------------------------------------+
input string    _Sep_Logging_ = "=== LOGGING ==="; // ---------
input bool      InpLogSystem = true;             // Log system events
input bool      InpLogDetection = true;          // Log detection events
input bool      InpLogTrading          = true;    // Log execution events
input bool      InpVerbosePhysics      = false;   // Log detailed Physics/Perception rejections

//+------------------------------------------------------------------+
//| UI PARAMETERS                                                      |
//+------------------------------------------------------------------+
input string    _Sep_UI_ = "=== UI SETTINGS ==="; // ---------
input bool      InpShowFeedbackPanel = false;      // Show Feedback Panel (disable for faster backtest)





#endif // V50_TRADINGPARAMETERS_MQH
