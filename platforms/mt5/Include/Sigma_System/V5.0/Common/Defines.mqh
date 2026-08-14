//+------------------------------------------------------------------+
//|                                                      Defines.mqh |
//|                        Copyright 2025, SIGMA Systems             |
//|                                         https://www.asksigma.com |
//+------------------------------------------------------------------+
//| V5.0 CLEAN SLATE - B2B ONLY                                      |
//| Stripped of all sequence-related enums and constants             |
//+------------------------------------------------------------------+
#property copyright "Copyright 2025, SIGMA Systems"
#property link      "https://www.asksigma.com"
#property version   "5.00"
#property strict

#ifndef V50_DEFINES_MQH
#define V50_DEFINES_MQH

//+------------------------------------------------------------------+
//| GLOBAL CONSTANTS                                                  |
//+------------------------------------------------------------------+

//--- Constants for total number of timeframes
#define TOTAL_TIMEFRAMES 9       // M1, M5, M15, M30, H1, H4, D1, W1, MN1

//--- B2B Zone Storage
#define MAX_B2B_ZONES_PER_TF 600  // Maximum B2B zones per timeframe (100 days × 6 zones/day)

//--- Swing and Breakout Storage
#define MAX_HISTORICAL_SWINGS    1000 // Max number of historical swings per timeframe
#define MAX_RECENT_SWINGS        1000 // Max number of recent (live) swings per timeframe
#define MAX_HISTORICAL_BREAKOUTS 1000 // Max number of historical breakouts per timeframe
#define MAX_RECENT_BREAKOUTS     1000 // Max number of recent (live) breakouts per timeframe

//--- Live Data Fetching
#define LIVE_DATA_FETCH_COUNT    20   // Number of bars to fetch for live processing

//--- FindBarIndexByTime match type constants
#define EXACT  true
#define APPROX false

//--- B2B Zone Change Bitmask (Phase 2 Performance Gating)
#define ZONE_CHANGE_NONE        0 // No change
#define ZONE_CHANGE_STRUCTURAL  1 // Bit 0: T1/T2/T3 Touch or Bulldog/Invalidation
#define ZONE_CHANGE_METRIC      2 // Bit 1: MFE/MAE update or Age update
#define ZONE_CHANGE_HTF_TOUCHED 4 // Bit 2: W1/D1 zone received T1 touch (flip candidate)

//+------------------------------------------------------------------+
//| CORE ENUMERATIONS                                                 |
//+------------------------------------------------------------------+

//--- Enum for signal direction (Swings, Breakouts, B2B Zones)
enum ENUM_SIGNAL_DIRECTION
  {
   DIRECTION_NONE    = 0, // None
   DIRECTION_BULLISH = 1, // Bullish (BUY B2B) or Swing Low
   DIRECTION_BEARISH = 2  // Bearish (SELL B2B) or Swing High
  };

//--- Enum for Swing Type
enum ENUM_SWING_TYPE
  {
   SWING_NONE = 0, // Not a swing point
   SWING_HIGH = 1, // A swing high point
   SWING_LOW  = 2  // A swing low point
  };

//--- Enum for Trading Sessions
enum ENUM_TRADING_SESSION
  {
   SESSION_DEAD_ZONE         = 0, // Dead zone (low liquidity)
   SESSION_ASIA              = 1, // Asian session
   SESSION_LONDON            = 2, // London session
   SESSION_OVERLAP_LONDON_NY = 3, // London-NY overlap
   SESSION_NY                = 4  // New York session
  };

//--- Enum for Display Font
enum ENUM_DISPLAY_FONT
  {
   FONT_COURIER = 0,
   FONT_ARIAL = 1,
   FONT_TIMES = 2,
   FONT_CALIBRI_LIGHT = 3
  };

//--- Enum for Take Profit Depth (Dynamic TP)
enum ENUM_TP_DEPTH
  {
   TP_DEPTH_T1 = 0, // L1 (Inner Edge)
   TP_DEPTH_T2 = 1, // 50% Level
   TP_DEPTH_T3 = 2  // L2 (Outer Edge)
  };

//--- Enum for Vector Anchor TF Mode (Quantum Audit V2)
//--- Defines which HTF zones must exist for LTF trade direction
enum ENUM_VECTOR_ANCHOR
  {
    ANCHOR_OFF         = 0, // No HTF Requirement (Raw Harvesting)
    ANCHOR_H1          = 1, // H1 Anchor (LTF must align with H1)
    ANCHOR_H1_H4       = 2, // H1 + H4 Anchor (Both must align)
    ANCHOR_H4          = 3, // H4 Anchor Only
    ANCHOR_H4_D1       = 4, // H4 + D1 Anchor (Swing Trades)
    ANCHOR_D1          = 5, // D1 Anchor Only (Position Bias)
    ANCHOR_D1_W1       = 6, // D1 + W1 Anchor (Long-Term Flow)
    ANCHOR_FULL_STACK  = 7  // H1 + H4 + D1 + W1 (Maximum Confluence)
   };

//--- Enum for Fractal Anchor TF Mode (Quantum Audit V2)
//--- Defines which HTF parent zones must contain the LTF zone
enum ENUM_FRACTAL_ANCHOR
  {
    FRACTAL_OFF         = 0, // No parent required (any zone)
    FRACTAL_ANY         = 1, // Must have ANY parent (legacy behavior)
    FRACTAL_H1          = 2, // Must nest inside H1 zone
    FRACTAL_H4          = 3, // Must nest inside H4 zone
    FRACTAL_H1_H4       = 4, // Must nest inside BOTH H1 and H4
    FRACTAL_D1          = 5, // Must nest inside D1 zone
    FRACTAL_H4_D1       = 6, // Must nest inside H4 AND D1
    FRACTAL_FULL_STACK  = 7  // Must nest inside H1+H4+D1
   };

//+------------------------------------------------------------------+
//| TIMEFRAME INDEX FUNCTIONS                                         |
//+------------------------------------------------------------------+

//--- Convert ENUM_TIMEFRAMES to array index (0-8)
int TFEnumToIndex(ENUM_TIMEFRAMES tf)
  {
   switch(tf)
     {
      case PERIOD_M1:  return 0;
      case PERIOD_M5:  return 1;
      case PERIOD_M15: return 2;
      case PERIOD_M30: return 3;
      case PERIOD_H1:  return 4;
      case PERIOD_H4:  return 5;
      case PERIOD_D1:  return 6;
      case PERIOD_W1:  return 7;
      case PERIOD_MN1: return 8;
      default:
         PrintFormat("[V5.0] TFEnumToIndex: Invalid ENUM_TIMEFRAMES %d", (int)tf);
         return -1;
     }
  }

//--- Convert array index (0-8) to ENUM_TIMEFRAMES
ENUM_TIMEFRAMES IndexToTFEnum(int index)
  {
   switch(index)
     {
      case 0: return PERIOD_M1;
      case 1: return PERIOD_M5;
      case 2: return PERIOD_M15;
      case 3: return PERIOD_M30;
      case 4: return PERIOD_H1;
      case 5: return PERIOD_H4;
      case 6: return PERIOD_D1;
      case 7: return PERIOD_W1;
      case 8: return PERIOD_MN1;
      default: 
        PrintFormat("[V5.0] IndexToTFEnum: Invalid index %d", index);
        return WRONG_VALUE;
     }
  }

#endif // V50_DEFINES_MQH
