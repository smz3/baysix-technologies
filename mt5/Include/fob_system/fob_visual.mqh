//+------------------------------------------------------------------+
//|                                                    fob_visual.mqh  |
//|  FOB chart visualizer — eyeball layer for the classifier.         |
//|                                                                    |
//|  Pure drawing, ZERO detection: the EA owns break/label state;     |
//|  this just renders it. Each classified event is drawn as a        |
//|  direction arrow + a text tag, COLOURED BY ROLE:                  |
//|     PBO = blue · VR = purple · HRCF = orange · CF = green.        |
//|                                                                    |
//|  Current-chart-TF only — every draw is gated on event_tf ==       |
//|  ChartPeriod(), so the 8 TFs never collide on one chart. Switch    |
//|  the chart period and OnChartEvent rebuilds the layer. The label   |
//|  carries the SETUP tf (e.g. "VR H4 #3"), so on the H1 chart you    |
//|  can see which H4 setup a VR belongs to while tracing a sequence.  |
//|                                                                    |
//|  Needs tester model = Visual Mode (NOT "Open prices only") to see  |
//|  it paint live; otherwise objects appear on the chart at OnDeinit. |
//+------------------------------------------------------------------+
#ifndef FOB_VISUAL_MQH
#define FOB_VISUAL_MQH
#property strict

#include "fob_types.mqh"

//--- master toggle (draw chart objects; turn OFF for a long headless emit)
input bool InpVisualize = true;

//--- font sizes (hidden from inputs — tweak in source)
const int  InpFobArrowSize = 12;
const int  InpFobLabelSize = 9;

#define FOB_VIS_PREFIX "FOB_"
#define FOB_VIS_FONT   "Calibri Light"

//+------------------------------------------------------------------+
//| CFobVisual                                                       |
//+------------------------------------------------------------------+
class CFobVisual
  {
private:
   string   m_tf;                 // chart's TF name ("M5".."MN1"); "" if unmapped

   string   PeriodName(const ENUM_TIMEFRAMES p) const;
   bool     Active(const int event_tf) const
              { return InpVisualize && m_tf != "" && FobTfName(event_tf) == m_tf; }

   void     Arrow(const string name, const datetime t, const double p,
                  const int dir, const color clr);
   void     Label(const string name, const datetime t, const double p,
                  const string txt, const color clr);
   string   EventStem(const FobEvent &e) const
              { return FOB_VIS_PREFIX + FobTfName(e.event_tf) + "_" +
                       FobLabelName(e.label) + "_s" + FobTfName(e.setup_tf) + "_" +
                       (string)e.bar_time; }
   void     DrawEvent(const FobEvent &e);

public:
            CFobVisual(void) { m_tf = ""; }

   void     SyncChartTF() { m_tf = PeriodName((ENUM_TIMEFRAMES)ChartPeriod()); }
   void     ClearAll()    { ObjectsDeleteAll(0, FOB_VIS_PREFIX); }

   //--- live hook: one classified event just fired
   void     OnEvent(const FobEvent &e) { if(Active(e.event_tf)) DrawEvent(e); }

   //--- full rebuild for the current chart TF (CHARTEVENT_CHART_CHANGE)
   void     RedrawCurrentTF(const FobEvent &ev[], const int n);
  };

//+------------------------------------------------------------------+
string CFobVisual::PeriodName(const ENUM_TIMEFRAMES p) const
  {
   switch(p)
     {
      case PERIOD_M5:  return "M5";
      case PERIOD_M15: return "M15";
      case PERIOD_M30: return "M30";
      case PERIOD_H1:  return "H1";
      case PERIOD_H4:  return "H4";
      case PERIOD_D1:  return "D1";
      case PERIOD_W1:  return "W1";
      case PERIOD_MN1: return "MN1";
     }
   return "";   // chart on a TF FOB doesn't track -> draw nothing
  }

//+------------------------------------------------------------------+
//| Primitives — create-or-update so redraws never duplicate.        |
//+------------------------------------------------------------------+
void CFobVisual::Arrow(const string name, const datetime t, const double p,
                       const int dir, const color clr)
  {
   //--- Wingdings: 233 = up arrow (bull), 234 = down arrow (bear)
   int code = (dir == BRC_BULL) ? 233 : 234;
   if(ObjectFind(0, name) < 0)
      ObjectCreate(0, name, OBJ_ARROW, 0, t, p);
   ObjectMove(0, name, 0, t, p);
   ObjectSetInteger(0, name, OBJPROP_ARROWCODE, code);
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, InpFobArrowSize);
   ObjectSetInteger(0, name, OBJPROP_ANCHOR, (dir == BRC_BULL) ? ANCHOR_TOP : ANCHOR_BOTTOM);
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
   ObjectSetInteger(0, name, OBJPROP_BACK, false);
  }

void CFobVisual::Label(const string name, const datetime t, const double p,
                       const string txt, const color clr)
  {
   if(ObjectFind(0, name) < 0)
      ObjectCreate(0, name, OBJ_TEXT, 0, t, p);
   ObjectMove(0, name, 0, t, p);
   ObjectSetString (0, name, OBJPROP_TEXT, txt);
   ObjectSetString (0, name, OBJPROP_FONT, FOB_VIS_FONT);
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, InpFobLabelSize);
   ObjectSetInteger(0, name, OBJPROP_ANCHOR, ANCHOR_LEFT);
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
   ObjectSetInteger(0, name, OBJPROP_BACK, false);
  }

//+------------------------------------------------------------------+
//| Draw one event: direction arrow at the broken level + role tag.   |
//| Tag = "<LABEL> <setupTF> #<seq>" (e.g. "VR H4 #3").              |
//+------------------------------------------------------------------+
void CFobVisual::DrawEvent(const FobEvent &e)
  {
   color  clr  = FobLabelColor(e.label);
   string stem = EventStem(e);
   string tag  = StringFormat("  %s %s #%d", FobLabelName(e.label),
                              FobTfName(e.setup_tf), e.seq);
   Arrow(stem + "_a", e.bar_time, e.level, e.dir, clr);
   Label(stem + "_t", e.bar_time, e.level, tag, clr);
  }

//+------------------------------------------------------------------+
//| Full rebuild for the current chart TF (on period switch).         |
//+------------------------------------------------------------------+
void CFobVisual::RedrawCurrentTF(const FobEvent &ev[], const int n)
  {
   ClearAll();
   if(!InpVisualize || m_tf == "")
      return;
   for(int i = 0; i < n; i++)
      if(Active(ev[i].event_tf))
         DrawEvent(ev[i]);
  }

#endif // FOB_VISUAL_MQH
