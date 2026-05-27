//+------------------------------------------------------------------+
//|                                                   Visualizer.mqh |
//|                             Copyright 2025, Sigma Trading System |
//+------------------------------------------------------------------+
//| V5.0 CLEAN SLATE - B2B ONLY                                      |
//| Handles drawing B2B zones, swing points, and breakouts on chart  |
//| PRESERVES EXACT VISUAL STYLING FROM V3.2                         |
//| - TF-specific visibility (no cross-contamination)                |
//| - Proper redraw/clear logic                                      |
//| NOTE: All input parameters are in TradingParameters.mqh          |
//+------------------------------------------------------------------+
#ifndef V50_VISUALIZER_MQH
#define V50_VISUALIZER_MQH

#property strict

#include "../Common/Defines.mqh"
#include "../Data/Structures.mqh"
#include "../Common/Utils.mqh"
#include "../Configuration/TradingParameters.mqh"
// #include "../MarketFlow/MarketFlowTypes.mqh" // REMOVED

//+------------------------------------------------------------------+
//| CVisualizer Class                                                |
//+------------------------------------------------------------------+
class CVisualizer
  {
public:
                     CVisualizer(void) {}

   // --- Swing Point Methods ---
   void              DrawSwingPoint(datetime time, double price, double close_price, ENUM_SIGNAL_DIRECTION direction, ENUM_TIMEFRAMES tf);
   void              DeleteSwingPoint(const SwingPointInfo &sp_info, ENUM_TIMEFRAMES tf);
   void              ClearSwingPoints();
   void              ClearSwingPointsForTF(ENUM_TIMEFRAMES tf);
   void              RedrawAllSwingPoints(const SwingPointInfo &highs[], int highs_count,
                                          const SwingPointInfo &lows[], int lows_count,
                                          ENUM_TIMEFRAMES tf);

   // --- Breakout Methods ---
   void              DrawRawBreakout(const RawBreakoutInfo &bo_info);
   void              ClearRawBreakouts();
   void              ClearRawBreakoutsForTF(ENUM_TIMEFRAMES tf);
   void              RedrawAllBreakouts(const RawBreakoutInfo &breakouts[], int count, ENUM_TIMEFRAMES tf);

   // --- B2B Zone Methods ---
   void              DrawB2BZone(const B2BZoneInfo &zone, ulong origin_id=0, ulong target_id=0);
   void              ClearB2BZone(const B2BZoneInfo &zone);
   void              ClearAllB2BZones();
   void              DrawAllB2BZones(const B2BZoneInfo &zones[], int zone_count, ulong origin_id=0, ulong target_id=0);
   
   // --- Manifold Visuals (Phase Delta) - REMOVED ---
   
   // V5.0.1: Efficient label update (no redraw)
   void              UpdateB2BZoneLabel(const B2BZoneInfo &zone);
   void              UpdateAllZoneLabels(const B2BZoneInfo &zones[], int zone_count);
   
   // V18: Targeted Visual Pruning (Zero-Twitch)
   void              PruneMissingZones(const B2BZoneInfo &active_zones[], int zone_count);
   void              SyncB2BZones(const B2BZoneInfo &zones[], int zone_count, ulong origin_id=0, ulong target_id=0);
   
   // V8: GPS-based Zone-to-Zone Flow Visualization (replaces old Origin logic)
   // V8: GPS-based Zone-to-Zone Flow Visualization - REMOVED
   // void              DrawGPSFlowVisualization(const MarketFlowGPSData &gps);
   // void              ClearGPSFlowVisualization();
   // void              DrawMTFGPSFlowVisualization(...);

   // --- Clear All ---
   void              ClearAllVisuals(const string reason = "Unknown");



private:
   string            GetObjectName(datetime time, string suffix, ENUM_TIMEFRAMES tf, ENUM_SWING_TYPE type = SWING_NONE);
   bool              ShouldShowForCurrentTF(ENUM_TIMEFRAMES obj_tf);
  };

//+------------------------------------------------------------------+
//| GetObjectName (Helper)                                           |
//+------------------------------------------------------------------+
string CVisualizer::GetObjectName(datetime time, string suffix, ENUM_TIMEFRAMES tf, ENUM_SWING_TYPE type)
  {
   string name = _Symbol + InpEASuffix + "_" + suffix + "_" + EnumToString(tf);
   if(type != SWING_NONE)
     {
      name += "_" + EnumToString(type);
     }
   name += "_" + (string)time;
   return name;
  }

//+------------------------------------------------------------------+
//| ShouldShowForCurrentTF                                           |
//| Returns true if object's TF matches current chart TF             |
//+------------------------------------------------------------------+
bool CVisualizer::ShouldShowForCurrentTF(ENUM_TIMEFRAMES obj_tf)
  {
   return (obj_tf == ChartPeriod());
  }

//+------------------------------------------------------------------+
//| DrawSwingPoint - TF-SPECIFIC (V3.2 Style)                        |
//+------------------------------------------------------------------+
void CVisualizer::DrawSwingPoint(datetime time, double price, double close_price, ENUM_SIGNAL_DIRECTION direction, ENUM_TIMEFRAMES tf)
  {
   // Only draw if visibility enabled AND TF matches chart
   if(!InpShowSwingPoints) return;
   if(!ShouldShowForCurrentTF(tf)) return;
   
   string obj_name_bullet = GetObjectName(time, "SP_Bullet", tf);
   string obj_name_label = GetObjectName(time, "SP_Label", tf);

   // V3.2 color scheme
   color object_color;
   string label_text_content;
   
   if(direction == DIRECTION_BEARISH) // Swing High
     {
      object_color = InpClrSwingHigh;
      label_text_content = "  High " + DoubleToString(price, _Digits);
     }
   else // Swing Low (DIRECTION_BULLISH)
     {
      object_color = InpClrSwingLow;
      label_text_content = "  Low " + DoubleToString(price, _Digits);
     }

   // Create bullet at swing price
   if(ObjectCreate(0, obj_name_bullet, OBJ_TEXT, 0, time, price))
     {
      ObjectSetString(0, obj_name_bullet, OBJPROP_TEXT, "•");
      ObjectSetString(0, obj_name_bullet, OBJPROP_FONT, "Calibri Light");
      ObjectSetInteger(0, obj_name_bullet, OBJPROP_FONTSIZE, InpBulletFontSize);
      ObjectSetInteger(0, obj_name_bullet, OBJPROP_ANCHOR, ANCHOR_CENTER);
      ObjectSetInteger(0, obj_name_bullet, OBJPROP_COLOR, object_color);
      ObjectSetInteger(0, obj_name_bullet, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, obj_name_bullet, OBJPROP_BACK, true);
     }

   // Create label at swing price
   if(ObjectCreate(0, obj_name_label, OBJ_TEXT, 0, time, price))
     {
      ObjectSetString(0, obj_name_label, OBJPROP_TEXT, label_text_content);
      ObjectSetString(0, obj_name_label, OBJPROP_FONT, "Calibri Light");
      ObjectSetInteger(0, obj_name_label, OBJPROP_FONTSIZE, InpLabelFontSize);
      ObjectSetInteger(0, obj_name_label, OBJPROP_ANCHOR, ANCHOR_LEFT);
      ObjectSetInteger(0, obj_name_label, OBJPROP_COLOR, object_color);
      ObjectSetInteger(0, obj_name_label, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, obj_name_label, OBJPROP_BACK, true);
     }
  }

//+------------------------------------------------------------------+
//| DeleteSwingPoint                                                 |
//+------------------------------------------------------------------+
void CVisualizer::DeleteSwingPoint(const SwingPointInfo &sp_info, ENUM_TIMEFRAMES tf)
  {
   if(sp_info.time == 0) return;
   
   string obj_name_bullet = GetObjectName(sp_info.time, "SP_Bullet", tf);
   string obj_name_label = GetObjectName(sp_info.time, "SP_Label", tf);
   
   ObjectDelete(0, obj_name_bullet);
   ObjectDelete(0, obj_name_label);
  }

//+------------------------------------------------------------------+
//| ClearSwingPoints - All TFs                                       |
//+------------------------------------------------------------------+
void CVisualizer::ClearSwingPoints()
  {
   string prefix = _Symbol + InpEASuffix + "_SP_";
   ObjectsDeleteAll(0, prefix);
  }

//+------------------------------------------------------------------+
//| ClearSwingPointsForTF - TF-specific                              |
//+------------------------------------------------------------------+
void CVisualizer::ClearSwingPointsForTF(ENUM_TIMEFRAMES tf)
  {
   string prefix = _Symbol + InpEASuffix + "_SP_Bullet_" + EnumToString(tf);
   ObjectsDeleteAll(0, prefix);
   
   prefix = _Symbol + InpEASuffix + "_SP_Label_" + EnumToString(tf);
   ObjectsDeleteAll(0, prefix);
  }

//+------------------------------------------------------------------+
//| RedrawAllSwingPoints - Clear and redraw for specific TF          |
//+------------------------------------------------------------------+
void CVisualizer::RedrawAllSwingPoints(const SwingPointInfo &highs[], int highs_count,
                                        const SwingPointInfo &lows[], int lows_count,
                                        ENUM_TIMEFRAMES tf)
  {
   // Clear existing swing points for this TF
   ClearSwingPointsForTF(tf);
   
   // Only redraw if current chart TF matches
   if(!ShouldShowForCurrentTF(tf)) return;
   if(!InpShowSwingPoints) return;
   
   // Draw swing highs
   for(int i = 0; i < highs_count; i++)
     {
      if(highs[i].type == SWING_HIGH && highs[i].time > 0)
        {
         DrawSwingPoint(highs[i].time, highs[i].price, highs[i].close_price, DIRECTION_BEARISH, tf);
        }
     }
   
   // Draw swing lows
   for(int i = 0; i < lows_count; i++)
     {
      if(lows[i].type == SWING_LOW && lows[i].time > 0)
        {
         DrawSwingPoint(lows[i].time, lows[i].price, lows[i].close_price, DIRECTION_BULLISH, tf);
        }
     }
  }

//+------------------------------------------------------------------+
//| DrawRawBreakout - TF-SPECIFIC (V3.2 Style)                       |
//+------------------------------------------------------------------+
void CVisualizer::DrawRawBreakout(const RawBreakoutInfo &bo_info)
  {
   static int s_bo_counter = 0;  // Static counter for unique names
   
   if(bo_info.breakout_bar_time == 0) return;
   
   // Only draw if visibility enabled AND TF matches chart
   if(!InpShowRawBreakouts) return;
   if(!ShouldShowForCurrentTF(bo_info.timeframe_occurred)) return;

   // FIX: Use counter + all time values to ensure truly unique names
   s_bo_counter++;
   string unique_suffix = "_" + IntegerToString(s_bo_counter) + "_" + 
                          (string)bo_info.breakout_bar_time + "_" + 
                          (string)bo_info.broken_swing_time;
   string obj_name_bullet = _Symbol + InpEASuffix + "_RAW_BO_Bullet_" + EnumToString(bo_info.timeframe_occurred) + unique_suffix;
   string obj_name_label = _Symbol + InpEASuffix + "_RAW_BO_Label_" + EnumToString(bo_info.timeframe_occurred) + unique_suffix;

   // V3.2 color scheme: Bob = Bullish breakout, Bos = Bearish breakout
   color object_color = (bo_info.direction == DIRECTION_BULLISH) ? InpClrBob : InpClrBos;
   
   string swing_price_str = DoubleToString(bo_info.broken_swing_price, _Digits);
   string close_price_str = DoubleToString(bo_info.breakout_bar_close_price, _Digits);
   string bo_direction_str = (bo_info.direction == DIRECTION_BULLISH) ? "Bob" : "Bos";
   string label_text_content = StringFormat("  %s %s (%s)", bo_direction_str, swing_price_str, close_price_str);

   // Create bullet at broken swing's price and time
   bool bullet_ok = ObjectCreate(0, obj_name_bullet, OBJ_TEXT, 0, bo_info.broken_swing_time, bo_info.broken_swing_price);
   if(bullet_ok)
     {
      ObjectSetString(0, obj_name_bullet, OBJPROP_TEXT, "•");
      ObjectSetString(0, obj_name_bullet, OBJPROP_FONT, "Calibri Light");
      ObjectSetInteger(0, obj_name_bullet, OBJPROP_FONTSIZE, InpBulletFontSize);
      ObjectSetInteger(0, obj_name_bullet, OBJPROP_ANCHOR, ANCHOR_CENTER);
      ObjectSetInteger(0, obj_name_bullet, OBJPROP_COLOR, object_color);
      ObjectSetInteger(0, obj_name_bullet, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, obj_name_bullet, OBJPROP_BACK, true);
     }

   // Create label at broken swing's price and time
   bool label_ok = ObjectCreate(0, obj_name_label, OBJ_TEXT, 0, bo_info.broken_swing_time, bo_info.broken_swing_price);
   if(label_ok)
     {
      ObjectSetString(0, obj_name_label, OBJPROP_TEXT, label_text_content);
      ObjectSetString(0, obj_name_label, OBJPROP_FONT, "Calibri Light");
      ObjectSetInteger(0, obj_name_label, OBJPROP_FONTSIZE, InpLabelFontSize);
      ObjectSetInteger(0, obj_name_label, OBJPROP_ANCHOR, ANCHOR_RIGHT);
      ObjectSetInteger(0, obj_name_label, OBJPROP_COLOR, object_color);
      ObjectSetInteger(0, obj_name_label, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, obj_name_label, OBJPROP_BACK, true);
     }
   
   // Log failures for debugging (uncomment for debugging)
   // if(!label_ok)
   //    PrintFormat("[DRAW-FAIL] Label failed: swing=%.2f, bar=%s, err=%d", 
   //               bo_info.broken_swing_price, TimeToString(bo_info.breakout_bar_time), GetLastError());
  }

//+------------------------------------------------------------------+
//| ClearRawBreakouts - All TFs                                      |
//+------------------------------------------------------------------+
void CVisualizer::ClearRawBreakouts()
  {
   string prefix = _Symbol + InpEASuffix + "_RAW_BO_";
   ObjectsDeleteAll(0, prefix);
  }

//+------------------------------------------------------------------+
//| ClearRawBreakoutsForTF - TF-specific                             |
//+------------------------------------------------------------------+
void CVisualizer::ClearRawBreakoutsForTF(ENUM_TIMEFRAMES tf)
  {
   string prefix = _Symbol + InpEASuffix + "_RAW_BO_Bullet_" + EnumToString(tf);
   ObjectsDeleteAll(0, prefix);
   
   prefix = _Symbol + InpEASuffix + "_RAW_BO_Label_" + EnumToString(tf);
   ObjectsDeleteAll(0, prefix);
  }

//+------------------------------------------------------------------+
//| RedrawAllBreakouts - Clear and redraw for specific TF            |
//+------------------------------------------------------------------+
void CVisualizer::RedrawAllBreakouts(const RawBreakoutInfo &breakouts[], int count, ENUM_TIMEFRAMES tf)
  {
   // Clear existing breakouts for this TF
   ClearRawBreakoutsForTF(tf);
   
   // Only redraw if current chart TF matches
   if(!ShouldShowForCurrentTF(tf)) return;
   if(!InpShowRawBreakouts) return;
   
   // Draw all breakouts
   for(int i = 0; i < count; i++)
     {
      if(breakouts[i].breakout_bar_time > 0)
        {
         DrawRawBreakout(breakouts[i]);
        }
     }
  }

//+------------------------------------------------------------------+
//| DrawB2BZone - EXACT V3.2 STYLING + V8 MARKET FLOW PIGGYBACK       |
//+------------------------------------------------------------------+
void CVisualizer::DrawB2BZone(const B2BZoneInfo &zone, ulong origin_id=0, ulong target_id=0)
  {
   if(!zone.IsValid()) return;
   if(!InpShowB2BZones) return;
   
   // V7: Multi-TF visibility check
   // If InpShowMultiTFZones is false, ONLY draw zones matching current chart TF
   bool is_active_tf = (zone.timeframe == ChartPeriod());
   if(!InpShowMultiTFZones && !is_active_tf) return;
   
   // Generate object names
   string zone_prefix = _Symbol + InpEASuffix + "_B2B_" + (string)zone.zone_id;
   string L2_line_name = zone_prefix + "_L2";
   string L1_line_name = zone_prefix + "_L1";
   string fifty_line_name = zone_prefix + "_50";
   string left_vert_name = zone_prefix + "_LV";
   string L2_label_name = zone_prefix + "_L2_Label";
   string L1_label_name = zone_prefix + "_L1_Label";
   
   string dir_text = (zone.direction == DIRECTION_BEARISH) ? "Sell" : "Buy";
   string tf_text = TFToString(zone.timeframe);
   
   // is_active_tf already declared above for multi-TF check
   
   // Determine zone layer (3 layers now: Control, Intermediate, Narrative)
   // CONTROL: H4, H1
   // INTERMEDIATE: M30, M15 (Strategy B specific visuals)
   // SNIPER: M5, M1
   // NARRATIVE: D1, W1, MN1
   bool is_narrative = (zone.timeframe == PERIOD_MN1 || zone.timeframe == PERIOD_W1 || zone.timeframe == PERIOD_D1);
   bool is_control = (zone.timeframe == PERIOD_H4 || zone.timeframe == PERIOD_H1);
   bool is_intermediate = (zone.timeframe == PERIOD_M30 || zone.timeframe == PERIOD_M15);
   bool is_sniper_tf = (zone.timeframe == PERIOD_M5 || zone.timeframe == PERIOD_M1);
   
   // V5.6: Individual TF visibility - each timeframe has its own toggle
   if(zone.timeframe == PERIOD_MN1 && !InpShowB2BZonesMN1) return;
   if(zone.timeframe == PERIOD_W1 && !InpShowB2BZonesW1) return;
   if(zone.timeframe == PERIOD_D1 && !InpShowB2BZonesD1) return;
   if(zone.timeframe == PERIOD_H4 && !InpShowB2BZonesH4) return;
   if(zone.timeframe == PERIOD_H1 && !InpShowB2BZonesH1) return;
   if(zone.timeframe == PERIOD_M30 && !InpShowB2BZonesM30) return;
   if(zone.timeframe == PERIOD_M15 && !InpShowB2BZonesM15) return;
   if(zone.timeframe == PERIOD_M5 && !InpShowB2BZonesM5) return;
   if(zone.timeframe == PERIOD_M1 && !InpShowB2BZonesM1) return;
   
   // Confluence filter
   if(InpOnlyShowConfluenceZones)
     {
      if((is_control || is_intermediate) && !zone.has_narrative_parent) return;
     }
   
   // V5.6: Individual TF colors - each timeframe has distinct colors
   color line_color, label_color, fifty_color;
   
   switch(zone.timeframe)
     {
      case PERIOD_MN1:
         if(is_active_tf)
           {
            line_color = (zone.direction == DIRECTION_BEARISH) ? InpB2BMN1SellColor : InpB2BMN1BuyColor;
            label_color = InpB2BNarrativeLabelColor;
           }
         else
           {
            line_color = (zone.direction == DIRECTION_BEARISH) ? InpB2BMN1SellDimColor : InpB2BMN1BuyDimColor;
            label_color = InpB2BDimLabelColor;
           }
         break;
         
      case PERIOD_W1:
         if(is_active_tf)
           {
            line_color = (zone.direction == DIRECTION_BEARISH) ? InpB2BW1SellColor : InpB2BW1BuyColor;
            label_color = InpB2BNarrativeLabelColor;
           }
         else
           {
            line_color = (zone.direction == DIRECTION_BEARISH) ? InpB2BW1SellDimColor : InpB2BW1BuyDimColor;
            label_color = InpB2BDimLabelColor;
           }
         break;
         
      case PERIOD_D1:
         if(is_active_tf)
           {
            line_color = (zone.direction == DIRECTION_BEARISH) ? InpB2BD1SellColor : InpB2BD1BuyColor;
            label_color = InpB2BNarrativeLabelColor;
           }
         else
           {
            line_color = (zone.direction == DIRECTION_BEARISH) ? InpB2BD1SellDimColor : InpB2BD1BuyDimColor;
            label_color = InpB2BDimLabelColor;
           }
         break;
         
      case PERIOD_H4:
         if(is_active_tf)
           {
            line_color = (zone.direction == DIRECTION_BEARISH) ? InpB2BH4SellColor : InpB2BH4BuyColor;
            label_color = InpB2BControlLabelColor;
           }
         else
           {
            line_color = (zone.direction == DIRECTION_BEARISH) ? InpB2BH4SellDimColor : InpB2BH4BuyDimColor;
            label_color = InpB2BDimLabelColor;
           }
         break;
         
      case PERIOD_H1:
         if(is_active_tf)
           {
            line_color = (zone.direction == DIRECTION_BEARISH) ? InpB2BH1SellColor : InpB2BH1BuyColor;
            label_color = InpB2BControlLabelColor;
           }
         else
           {
            line_color = (zone.direction == DIRECTION_BEARISH) ? InpB2BH1SellDimColor : InpB2BH1BuyDimColor;
            label_color = InpB2BDimLabelColor;
           }
         break;
         
      case PERIOD_M30:
         if(is_active_tf)
           {
            line_color = (zone.direction == DIRECTION_BEARISH) ? InpB2BM30SellColor : InpB2BM30BuyColor;
            label_color = InpB2BControlLabelColor;
           }
         else
           {
            line_color = (zone.direction == DIRECTION_BEARISH) ? InpB2BM30SellDimColor : InpB2BM30BuyDimColor;
            label_color = InpB2BDimLabelColor;
           }
         break;
         
      case PERIOD_M15:
         if(is_active_tf)
           {
            line_color = (zone.direction == DIRECTION_BEARISH) ? InpB2BM15SellColor : InpB2BM15BuyColor;
            label_color = InpB2BControlLabelColor;
           }
         else
           {
            line_color = (zone.direction == DIRECTION_BEARISH) ? InpB2BM15SellDimColor : InpB2BM15BuyDimColor;
            label_color = InpB2BDimLabelColor;
           }
         break;
         
      case PERIOD_M5:
         if(is_active_tf)
           {
            line_color = (zone.direction == DIRECTION_BEARISH) ? InpB2BM5SellColor : InpB2BM5BuyColor;
            label_color = InpB2BSniperLabelColor;
           }
         else
           {
            line_color = (zone.direction == DIRECTION_BEARISH) ? InpB2BM5SellDimColor : InpB2BM5BuyDimColor;
            label_color = InpB2BDimLabelColor;
           }
         break;
         
      case PERIOD_M1:
         if(is_active_tf)
           {
            line_color = (zone.direction == DIRECTION_BEARISH) ? InpB2BM1SellColor : InpB2BM1BuyColor;
            label_color = InpB2BSniperLabelColor;
           }
         else
           {
            line_color = (zone.direction == DIRECTION_BEARISH) ? InpB2BM1SellDimColor : InpB2BM1BuyDimColor;
            label_color = InpB2BDimLabelColor;
           }
         break;
         
      default:
         line_color = (zone.direction == DIRECTION_BEARISH) ? clrRed : clrBlue;
         label_color = clrWhite;
         break;
     }
   fifty_color = InpB2BFiftyLineColor;
   
   // Zone timing - START from L1 (first barrier/1st breakout), NOT from 2nd breakout
   // L1 = 1st breakout (entry), 2nd breakout confirms pattern, L2 = swing (invalidation)
   datetime zone_end_time = TimeCurrent() + PeriodSeconds(zone.timeframe) * 100;
   datetime zone_start_time = zone.first_barrier_time;  // Use L1 time, not zone_created_time
   
   // --- L2 Line ---
   if(ObjectFind(0, L2_line_name) < 0)
   {
      if(ObjectCreate(0, L2_line_name, OBJ_TREND, 0, zone_start_time, zone.L2_price, zone_end_time, zone.L2_price))
      {
         ObjectSetInteger(0, L2_line_name, OBJPROP_COLOR, line_color);
         ObjectSetInteger(0, L2_line_name, OBJPROP_STYLE, STYLE_DASH);
         ObjectSetInteger(0, L2_line_name, OBJPROP_WIDTH, 1);
         ObjectSetInteger(0, L2_line_name, OBJPROP_RAY_RIGHT, true);
         ObjectSetInteger(0, L2_line_name, OBJPROP_SELECTABLE, false);
         ObjectSetInteger(0, L2_line_name, OBJPROP_BACK, true);
      }
   }
   
   // --- L1 Line ---
   if(ObjectFind(0, L1_line_name) < 0)
   {
      if(ObjectCreate(0, L1_line_name, OBJ_TREND, 0, zone_start_time, zone.L1_price, zone_end_time, zone.L1_price))
      {
         ObjectSetInteger(0, L1_line_name, OBJPROP_COLOR, line_color);
         ObjectSetInteger(0, L1_line_name, OBJPROP_STYLE, STYLE_DASH);
         ObjectSetInteger(0, L1_line_name, OBJPROP_WIDTH, 1);
         ObjectSetInteger(0, L1_line_name, OBJPROP_RAY_RIGHT, true);
         ObjectSetInteger(0, L1_line_name, OBJPROP_SELECTABLE, false);
         ObjectSetInteger(0, L1_line_name, OBJPROP_BACK, true);
      }
   }
   
   // --- 50% Line ---
   if(InpShowB2BFiftyLine)
     {
      if(ObjectFind(0, fifty_line_name) < 0)
      {
         if(ObjectCreate(0, fifty_line_name, OBJ_TREND, 0, zone_start_time, zone.fifty_percent, zone_end_time, zone.fifty_percent))
         {
            ObjectSetInteger(0, fifty_line_name, OBJPROP_COLOR, fifty_color);
            ObjectSetInteger(0, fifty_line_name, OBJPROP_STYLE, STYLE_DOT);
            ObjectSetInteger(0, fifty_line_name, OBJPROP_WIDTH, 1);
            ObjectSetInteger(0, fifty_line_name, OBJPROP_RAY_RIGHT, true);
            ObjectSetInteger(0, fifty_line_name, OBJPROP_SELECTABLE, false);
            ObjectSetInteger(0, fifty_line_name, OBJPROP_BACK, true);
         }
      }
     }
   
   // --- Left Vertical Connector ---
   if(ObjectFind(0, left_vert_name) < 0)
   {
      if(ObjectCreate(0, left_vert_name, OBJ_TREND, 0, zone_start_time, zone.L1_price, zone_start_time, zone.L2_price))
      {
         ObjectSetInteger(0, left_vert_name, OBJPROP_COLOR, line_color);
         ObjectSetInteger(0, left_vert_name, OBJPROP_STYLE, STYLE_SOLID);
         ObjectSetInteger(0, left_vert_name, OBJPROP_WIDTH, 1);
         ObjectSetInteger(0, left_vert_name, OBJPROP_RAY_RIGHT, false);
         ObjectSetInteger(0, left_vert_name, OBJPROP_SELECTABLE, false);
         ObjectSetInteger(0, left_vert_name, OBJPROP_BACK, true);
      }
   }
   
   // V8: GPS Market Flow Overlays - REMOVED

   // --- L2 Label (with touch status) ---
   string touch_text = "T0";
   if(zone.L2_touched) touch_text = "T3";
   else if(zone.fifty_touched) touch_text = "T2";
   else if(zone.L1_touched) touch_text = "T1";
   
   // V8: Append GPS suffix
   string price_text = DoubleToString(zone.second_barrier_price, _Digits);
   string L2_text = StringFormat("L2 B2B %s %s [ %s ] %s #%04I64u", tf_text, dir_text, touch_text, price_text, zone.zone_id % 10000);
   
   if(ObjectFind(0, L2_label_name) < 0)
   {
      if(ObjectCreate(0, L2_label_name, OBJ_TEXT, 0, zone_start_time, zone.L2_price))
      {
         ObjectSetString(0, L2_label_name, OBJPROP_TEXT, L2_text);
         ObjectSetString(0, L2_label_name, OBJPROP_FONT, "Calibri Light");
         ObjectSetInteger(0, L2_label_name, OBJPROP_FONTSIZE, InpB2BLabelFontSize);
         ObjectSetInteger(0, L2_label_name, OBJPROP_COLOR, label_color);
         // Bullish labels go BELOW L2 (ANCHOR_LEFT_UPPER), Bearish labels stay ABOVE L2 (ANCHOR_LEFT_LOWER)
         ENUM_ANCHOR_POINT anchor = (zone.direction == DIRECTION_BULLISH) ? ANCHOR_LEFT_UPPER : ANCHOR_LEFT_LOWER;
         
         ObjectSetInteger(0, L2_label_name, OBJPROP_ANCHOR, anchor);
         ObjectSetInteger(0, L2_label_name, OBJPROP_SELECTABLE, false);
         ObjectSetInteger(0, L2_label_name, OBJPROP_BACK, true);
      }
   }
   else 
   {
      // If label exists, just update its text to reflect latest touch status
      ObjectSetString(0, L2_label_name, OBJPROP_TEXT, L2_text);
      ObjectSetInteger(0, L2_label_name, OBJPROP_COLOR, label_color);
   }
   
   // --- 2nd Barrier Marker ---
   if(InpShowB2BBarrierMarkers && zone.second_barrier_time > 0)
     {
      string barrier_marker_name = zone_prefix + "_B2M";
      string barrier_text = StringFormat("•  %.5f", zone.second_barrier_price);
      
      if(ObjectCreate(0, barrier_marker_name, OBJ_TEXT, 0, zone.second_barrier_time, zone.second_barrier_price))
        {
         ObjectSetString(0, barrier_marker_name, OBJPROP_TEXT, barrier_text);
         ObjectSetString(0, barrier_marker_name, OBJPROP_FONT, "Arial");
         ObjectSetInteger(0, barrier_marker_name, OBJPROP_FONTSIZE, 8);
         ObjectSetInteger(0, barrier_marker_name, OBJPROP_COLOR, line_color);
         ObjectSetInteger(0, barrier_marker_name, OBJPROP_ANCHOR, ANCHOR_LEFT);
         ObjectSetInteger(0, barrier_marker_name, OBJPROP_SELECTABLE, false);
         ObjectSetInteger(0, barrier_marker_name, OBJPROP_BACK, true);
        }
     }
  }

//+------------------------------------------------------------------+
//| UpdateB2BZoneLabel - UPDATE label text and handle invalidation    |
//| V5.0.1: Updates ALL visible zones, removes invalidated zones      |
//+------------------------------------------------------------------+
void CVisualizer::UpdateB2BZoneLabel(const B2BZoneInfo &zone)
  {
   string zone_prefix = _Symbol + InpEASuffix + "_B2B_" + (string)zone.zone_id;
   string L2_label_name = zone_prefix + "_L2_Label";
   
   // If zone is invalidated, clear it from chart
   if(zone.is_invalidated || !zone.is_valid)
     {
      ClearB2BZone(zone);
      return;
     }
   
   // Check if object exists
   if(ObjectFind(0, L2_label_name) < 0) return;
   
   // Build new label text with updated touch state
   string dir_text = (zone.direction == DIRECTION_BEARISH) ? "Sell" : "Buy";
   string tf_text = TFToString(zone.timeframe);
   
   // T1 = L1, T2 = 50%, T3 = L2
   string touch_text = "T0";
   if(zone.L2_touched) touch_text = "T3";
   else if(zone.fifty_touched) touch_text = "T2";
   else if(zone.L1_touched) touch_text = "T1";
   
   string price_text = DoubleToString(zone.second_barrier_price, _Digits);
   string L2_text = StringFormat("L2 B2B %s %s [ %s ] %s #%04I64u", tf_text, dir_text, touch_text, price_text, zone.zone_id % 10000);
   
   // Update the label text only (no recreate)
   ObjectSetString(0, L2_label_name, OBJPROP_TEXT, L2_text);
  }

//+------------------------------------------------------------------+
//| UpdateAllZoneLabels - Update labels for all zones (current TF)    |
//| V5.0.1: Efficient update without clearing/redrawing               |
//+------------------------------------------------------------------+
void CVisualizer::UpdateAllZoneLabels(const B2BZoneInfo &zones[], int zone_count)
{
   for(int i = 0; i < zone_count; i++)
   {
      UpdateB2BZoneLabel(zones[i]);  // Only updates current TF zones
   }
}

//+------------------------------------------------------------------+
//| PruneMissingZones: targeted visual cleanup (V18 Zero-Twitch)     |
//+------------------------------------------------------------------+
void CVisualizer::PruneMissingZones(const B2BZoneInfo &active_zones[], int zone_count)
{
   string prefix = _Symbol + InpEASuffix + "_B2B_";
   int total_objects = ObjectsTotal(0, 0, OBJ_TREND); // Check lines
   
   // We scan the chart for all B2B objects
   for(int i = ObjectsTotal(0) - 1; i >= 0; i--)
   {
      string name = ObjectName(0, i);
      if(StringFind(name, prefix) != 0) continue;
      
      // Extract ID from name (Format: SYMBOL_SUFFIX_B2B_ID_...)
      // Find the last underscore after B2B_
      int find_start = StringLen(prefix);
      int find_end = StringFind(name, "_", find_start);
      if(find_end == -1) find_end = StringLen(name);
      
      ulong obj_id = (ulong)StringToInteger(StringSubstr(name, find_start, find_end - find_start));
      if(obj_id == 0) continue;
      
      // Check if this ID is in the active memory array
      bool found = false;
      for(int j=0; j<zone_count; j++)
      {
         if(active_zones[j].zone_id == obj_id)
         {
            found = true;
            break;
         }
      }
      
      // If not in memory, kill the object (it was pruned or invalidated)
      if(!found) ObjectDelete(0, name);
   }
}

//+------------------------------------------------------------------+
//| ClearB2BZone                                                     |
//+------------------------------------------------------------------+
void CVisualizer::ClearB2BZone(const B2BZoneInfo &zone)
  {
   string zone_prefix = _Symbol + InpEASuffix + "_B2B_" + (string)zone.zone_id;
   
   ObjectDelete(0, zone_prefix + "_L2");
   ObjectDelete(0, zone_prefix + "_L1");
   ObjectDelete(0, zone_prefix + "_50");
   ObjectDelete(0, zone_prefix + "_LV");
   ObjectDelete(0, zone_prefix + "_L2_Label");
   ObjectDelete(0, zone_prefix + "_L1_Label");
   ObjectDelete(0, zone_prefix + "_B2M");
  }

//+------------------------------------------------------------------+
//| ClearAllB2BZones                                                 |
//+------------------------------------------------------------------+
void CVisualizer::ClearAllB2BZones()
  {
   string prefix = _Symbol + InpEASuffix + "_B2B_";
   ObjectsDeleteAll(0, prefix);
  }

void CVisualizer::DrawAllB2BZones(const B2BZoneInfo &zones[], int zone_count, ulong origin_id=0, ulong target_id=0)
{
   if(!InpShowB2BZones) return;
   
   // V18: Removed ClearAllB2BZones() to prevent twitching.
   // DrawB2BZone now handles individual presence checks.
   
   for(int i = 0; i < zone_count; i++)
   {
      if(zones[i].IsValid())
      {
         DrawB2BZone(zones[i], origin_id, target_id);
      }
      else
      {
         // V18.1 FIX: Explicitly clear invalidated zones to prevent "ghosting"
         // Since we no longer ClearAllB2BZones() at the start, we must 
         // actively delete objects for zones that became invalid.
         ClearB2BZone(zones[i]);
      }
   }
}



//+------------------------------------------------------------------+
//| ClearAllVisuals                                                  |
//+------------------------------------------------------------------+
void CVisualizer::ClearAllVisuals(const string reason)
  {
   ClearSwingPoints();
   ClearRawBreakouts();
   ClearAllB2BZones();
   
   Print("[V5.0] ClearAllVisuals: ", reason);
   ChartRedraw();
  }



#endif // V50_VISUALIZER_MQH

