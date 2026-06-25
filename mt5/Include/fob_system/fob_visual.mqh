//+------------------------------------------------------------------+
//|                                                    fob_visual.mqh  |
//|  FOB chart visualizer — eyeball layer for the classifier.         |
//|                                                                    |
//|  Pure drawing, ZERO detection: the EA owns break/label state;     |
//|  this just renders it. Styling mirrors brc_visual:                 |
//|     • every classified event -> "•" bullet at the BROKEN level     |
//|       + a text tag, COLOURED BY ROLE:                              |
//|          PBO = blue · VR = purple · HRCF = orange · CF = green.    |
//|       (No arrows — same dot idiom as BRC/STRUCT.)                  |
//|                                                                    |
//|  SETUP-TF LENS (locked 2026-06-25): every draw is gated on         |
//|  e.setup_tf == ChartPeriod(), NOT the event TF. So a chart shows   |
//|  the COMPLETE chains whose *setup* is that TF — the PBO (on this    |
//|  TF) plus its VR/CF (one TF below) and HRCF (two below), which are  |
//|  lower-TF breaks PROJECTED onto this chart by their absolute        |
//|  bar_time + level. A thin connector links PBO->VR->CF->HRCF of one  |
//|  (setup_tf, seq) so you can read one setup at a glance. Switch the  |
//|  chart period and OnChartEvent rebuilds the lens for the new TF.    |
//|                                                                    |
//|  The label carries the EVENT tf (the TF the break fired on), e.g.  |
//|  "VR H1 #3" on the H4 chart = an H1 break serving H4 setup #3.     |
//|                                                                    |
//|  Needs tester model = Visual Mode (NOT "Open prices only") to see  |
//|  it paint live; otherwise objects appear on the chart at OnDeinit. |
//+------------------------------------------------------------------+
#ifndef FOB_VISUAL_MQH
#define FOB_VISUAL_MQH
#property strict

#include "fob_types.mqh"

//--- master toggle (draw chart objects; turn OFF for a long headless emit)
input bool InpVisualize    = true;        // MASTER: draw chart objects
input bool InpFobConnect   = true;        // draw the per-chain PBO->VR->CF->HRCF connector
input int  InpFobMaxChains = 50;          // rolling cap: chains kept per setup-TF lens

//--- font sizes / connector colour (hidden from inputs — tweak in source)
const int   InpFobBulletSize = 12;
const int   InpFobLabelSize  = 9;
const color InpFobConnClr    = clrSlateGray;

#define FOB_VIS_PREFIX "FOB_"
#define FOB_VIS_FONT   "Calibri Light"

//+------------------------------------------------------------------+
//| CFobVisual                                                       |
//+------------------------------------------------------------------+
class CFobVisual
  {
private:
   string   m_tf;                    // chart's TF name ("M1".."MN1"); "" if unmapped
   string   m_chains[];              // FIFO of chain prefixes drawn on the current lens
   int      m_lastSeq[FOB_N_TF];     // per setup_tf: seq of the chain currently being extended
   datetime m_lastT[FOB_N_TF];       // per setup_tf: last linked point (time)
   double   m_lastP[FOB_N_TF];       // per setup_tf: last linked point (price)

   string   PeriodName(const ENUM_TIMEFRAMES p) const;
   bool     Active(const FobEvent &e) const
              { return InpVisualize && m_tf != "" && FobTfName(e.setup_tf) == m_tf; }

   void     Bullet(const string name, const datetime t, const double p, const color clr, const int size);
   void     Label (const string name, const datetime t, const double p, const string txt, const color clr);
   void     Line  (const string name, const datetime t0, const double p0,
                   const datetime t1, const double p1, const color clr);

   //--- chain = one (setup_tf, seq); every object for it shares this prefix
   string   ChainPrefix(const FobEvent &e) const
              { return FOB_VIS_PREFIX + FobTfName(e.setup_tf) + "_s" + (string)e.seq + "_"; }
   void     PruneChains();
   void     ResetTracking();
   void     RenderEvent(const FobEvent &e);

public:
            CFobVisual(void) { m_tf = ""; ResetTracking(); }

   void     SyncChartTF() { m_tf = PeriodName((ENUM_TIMEFRAMES)ChartPeriod()); }
   void     ClearAll()    { ObjectsDeleteAll(0, FOB_VIS_PREFIX); ArrayResize(m_chains, 0); ResetTracking(); }

   //--- live hook: one classified event just fired
   void     OnEvent(const FobEvent &e) { if(Active(e)) RenderEvent(e); }

   //--- full rebuild for the current chart TF (CHARTEVENT_CHART_CHANGE)
   void     RedrawCurrentTF(const FobEvent &ev[], const int n);
  };

//+------------------------------------------------------------------+
string CFobVisual::PeriodName(const ENUM_TIMEFRAMES p) const
  {
   switch(p)
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
     }
   return "";   // chart on a TF FOB doesn't track -> draw nothing
  }

//+------------------------------------------------------------------+
void CFobVisual::ResetTracking()
  {
   for(int i = 0; i < FOB_N_TF; i++)
     { m_lastSeq[i] = -1; m_lastT[i] = 0; m_lastP[i] = 0.0; }
  }

//+------------------------------------------------------------------+
//| Primitives — create-or-update so redraws never duplicate.        |
//+------------------------------------------------------------------+
void CFobVisual::Bullet(const string name, const datetime t, const double p, const color clr, const int size)
  {
   if(ObjectFind(0, name) < 0)
      ObjectCreate(0, name, OBJ_TEXT, 0, t, p);
   ObjectMove(0, name, 0, t, p);
   ObjectSetString (0, name, OBJPROP_TEXT, "•");
   ObjectSetString (0, name, OBJPROP_FONT, FOB_VIS_FONT);
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, size);
   ObjectSetInteger(0, name, OBJPROP_ANCHOR, ANCHOR_CENTER);
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
   ObjectSetInteger(0, name, OBJPROP_BACK, false);
  }

void CFobVisual::Label(const string name, const datetime t, const double p, const string txt, const color clr)
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

void CFobVisual::Line(const string name, const datetime t0, const double p0,
                      const datetime t1, const double p1, const color clr)
  {
   if(ObjectFind(0, name) < 0)
      ObjectCreate(0, name, OBJ_TREND, 0, t0, p0, t1, p1);
   ObjectMove(0, name, 0, t0, p0);
   ObjectMove(0, name, 1, t1, p1);
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, name, OBJPROP_STYLE, STYLE_DOT);
   ObjectSetInteger(0, name, OBJPROP_WIDTH, 1);
   ObjectSetInteger(0, name, OBJPROP_RAY_RIGHT, false);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
   ObjectSetInteger(0, name, OBJPROP_BACK, true);
  }

//+------------------------------------------------------------------+
//| Draw one event into its setup-TF chain: dot at the broken level + |
//| role tag, plus the connector segment from the prior chain point.   |
//| Tag = "<LABEL> <eventTF> #<seq>" (e.g. "VR H1 #3").              |
//+------------------------------------------------------------------+
void CFobVisual::RenderEvent(const FobEvent &e)
  {
   int    s    = e.setup_tf;
   color  clr  = FobLabelColor(e.label);
   string cp   = ChainPrefix(e);
   string base = cp + FobTfName(e.event_tf) + "_" + (string)e.bar_time;

   //--- PBO = chain start (supersede -> fresh seq): register for FIFO prune
   if(e.label == FOB_PBO && e.seq != m_lastSeq[s])
     {
      int k = ArraySize(m_chains);
      ArrayResize(m_chains, k + 1);
      m_chains[k] = cp;
      PruneChains();
      m_lastSeq[s] = e.seq;
      m_lastT[s]   = 0;          // anchor set at the end of this call
     }

   //--- connector: link from the previous point in THIS same chain
   if(InpFobConnect && m_lastSeq[s] == e.seq && m_lastT[s] > 0)
      Line(base + "_ln", m_lastT[s], m_lastP[s], e.bar_time, e.level, InpFobConnClr);

   //--- the dot + role tag (role · the TF the break fired on · chain seq)
   Bullet(base + "_b", e.bar_time, e.level, clr, InpFobBulletSize);
   Label (base + "_t", e.bar_time, e.level,
          StringFormat("  %s %s #%d", FobLabelName(e.label), FobTfName(e.event_tf), e.seq), clr);

   //--- advance the chain anchor to this point
   m_lastSeq[s] = e.seq;
   m_lastT[s]   = e.bar_time;
   m_lastP[s]   = e.level;
  }

//+------------------------------------------------------------------+
//| Rolling FIFO: keep only the InpFobMaxChains most-recent chains.   |
//+------------------------------------------------------------------+
void CFobVisual::PruneChains()
  {
   int over = ArraySize(m_chains) - InpFobMaxChains;
   if(over <= 0)
      return;
   for(int i = 0; i < over; i++)
      ObjectsDeleteAll(0, m_chains[i]);            // drop every object of the oldest chains
   for(int i = 0; i + over < ArraySize(m_chains); i++)
      m_chains[i] = m_chains[i + over];
   ArrayResize(m_chains, ArraySize(m_chains) - over);
  }

//+------------------------------------------------------------------+
//| Full rebuild for the current chart TF (on period switch).         |
//| Events arrive in append (= chronological) order, so replaying     |
//| them through RenderEvent rebuilds the chains + connectors exactly. |
//+------------------------------------------------------------------+
void CFobVisual::RedrawCurrentTF(const FobEvent &ev[], const int n)
  {
   ClearAll();
   if(!InpVisualize || m_tf == "")
      return;
   for(int i = 0; i < n; i++)
      if(Active(ev[i]))
         RenderEvent(ev[i]);
  }

#endif // FOB_VISUAL_MQH
