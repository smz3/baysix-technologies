//+------------------------------------------------------------------+
//|                                             fob_visual_prims.mqh  |
//|  PART of fob_visual.mqh — out-of-line CFobVisual method bodies.    |
//|  DO NOT #include directly: no include guard by design; it is       |
//|  pulled in by fob_visual.mqh AFTER the class declaration.          |
//|                                                                    |
//|  Scope: TF mapping (LadderIndex/SyncChartTF) + drawing primitives  |
//|  (Bullet/Label/Line). Zero detection, zero state.                  |
//+------------------------------------------------------------------+

//+------------------------------------------------------------------+
int CFobVisual::LadderIndex(const ENUM_TIMEFRAMES p) const
  {
   switch(p)
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
     }
   return -1;   // chart on a TF FOB doesn't track -> draw nothing
  }

void CFobVisual::SyncChartTF()
  {
   m_idx = LadderIndex((ENUM_TIMEFRAMES)ChartPeriod());
   m_tf  = (m_idx >= 0) ? FobTfName(m_idx) : "";
  }

//+------------------------------------------------------------------+
//| Primitives                                                        |
//+------------------------------------------------------------------+
void CFobVisual::Bullet(const string name, const datetime t, const double p, const color clr)
  {
   ObjectCreate(0, name, OBJ_TEXT, 0, t, p);
   ObjectSetString (0, name, OBJPROP_TEXT, "•");
   ObjectSetString (0, name, OBJPROP_FONT, FOB_VIS_FONT);
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, InpFobBulletSize);
   ObjectSetInteger(0, name, OBJPROP_ANCHOR, ANCHOR_CENTER);
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
   ObjectSetInteger(0, name, OBJPROP_BACK, false);
  }

void CFobVisual::Label(const string name, const datetime t, const double p, const string txt, const color clr,
                       const ENUM_ANCHOR_POINT anchor)
  {
   ObjectCreate(0, name, OBJ_TEXT, 0, t, p);
   ObjectSetString (0, name, OBJPROP_TEXT, txt);
   ObjectSetString (0, name, OBJPROP_FONT, FOB_VIS_FONT);
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, InpFobLabelSize);
   ObjectSetInteger(0, name, OBJPROP_ANCHOR, anchor);
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
   ObjectSetInteger(0, name, OBJPROP_BACK, false);
  }

//--- trend-line segment (zone L1/L2/mid + vertical connector); BACK so it sits
//--- behind candles. ray => extends right (alive zones); else a fixed segment.
void CFobVisual::Line(const string name, const datetime t0, const double p0, const datetime t1,
                      const double p1, const color clr, const ENUM_LINE_STYLE st,
                      const bool ray, const int width)
  {
   ObjectCreate(0, name, OBJ_TREND, 0, t0, p0, t1, p1);
   ObjectMove(0, name, 0, t0, p0);
   ObjectMove(0, name, 1, t1, p1);
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, name, OBJPROP_STYLE, st);
   ObjectSetInteger(0, name, OBJPROP_WIDTH, width);
   ObjectSetInteger(0, name, OBJPROP_RAY_RIGHT, ray);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
   ObjectSetInteger(0, name, OBJPROP_BACK, true);
  }
