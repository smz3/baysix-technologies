//+------------------------------------------------------------------+
//|                                                     brc_visual.mqh |
//|     BRC chart visualizer — eyeball layer for the emitter.          |
//|                                                                    |
//|  Pure drawing, ZERO detection: the EA owns swing/break/zone state  |
//|  (brc_baysix.mq5); this just renders it. Mirrors Sigma             |
//|  Visualizer.mqh conventions (TF-gated objects, "•" bullets,        |
//|  ObjectsDeleteAll-by-prefix cleanup).                              |
//|                                                                    |
//|  DESIGN (locked 2026-06-18):                                       |
//|   • Current-chart-TF only — every draw is gated on tf==ChartPeriod()|
//|     so the 8 TFs never collide. Switch the chart period and        |
//|     OnChartEvent->RedrawCurrentTF() rebuilds from stored state, so  |
//|     the layer swaps live with no restart.                          |
//|   • Rolling window cap (InpBrcMaxZones) per visible TF: a FIFO of   |
//|     zone object-stems; oldest zone's objects are pruned as new      |
//|     ones confirm, so a 10yr Visual run never blows the object cap.  |
//|   • Invalidated zones are NOT deleted (you lose the funnel history) |
//|     — recoloured grey + thin, frozen at invalidation_time, with an  |
//|     ✕ marker. Hidden behind InpBrcShowInvalid.                      |
//|                                                                    |
//|  ⚠️ Needs tester model = Visual Mode (NOT "Open prices only").      |
//|  ⚠️ COMPILE-UNTESTED (authored without an MT5 toolchain present).   |
//+------------------------------------------------------------------+
#ifndef BRC_VISUAL_MQH
#define BRC_VISUAL_MQH
#property strict

#include "brc_types.mqh"

//--- master + per-layer toggles -------------------------------------
input bool  InpVisualize      = false;       // MASTER: draw chart objects (off for the 10yr emit run)
input bool  InpBrcShowSwings  = true;        // swing pivots
input bool  InpBrcShowBreaks  = true;        // raw breakouts (+ broken-swing line)
input bool  InpBrcShowZones   = true;        // 5-pointer zone rect + P1..P5
input bool  InpBrcShowMid     = true;        // zone 50% mid line
input bool  InpBrcShowRetests = true;        // T1/T2/T3 retest touches
input bool  InpBrcShowInvalid = true;        // keep invalidated (dead) zones on chart
input int   InpBrcMaxZones    = 50;          // rolling cap: zones kept on chart per TF
//--- colours --------------------------------------------------------
input color InpBrcClrSwingHigh = clrTomato;
input color InpBrcClrSwingLow  = clrDodgerBlue;
input color InpBrcClrBreakBull = clrLimeGreen;
input color InpBrcClrBreakBear = clrOrangeRed;
input color InpBrcClrZoneBull  = clrSeaGreen;
input color InpBrcClrZoneBear  = clrFireBrick;
input color InpBrcClrZoneDead  = clrDimGray;
input color InpBrcClrMid       = clrGoldenrod;
input color InpBrcClrRetest    = clrWhite;

#define BRC_VIS_PREFIX "BRC_"      // every object name starts here -> one-shot ClearAll

//+------------------------------------------------------------------+
//| CBrcVisual                                                       |
//|  One instance, owned by the EA. Fed events as detection runs;    |
//|  draws only when the fed TF == the current chart period.         |
//+------------------------------------------------------------------+
class CBrcVisual
  {
private:
   string   m_tf;                 // chart's TF name ("M5".."MN1"); "" if chart period unmapped
   string   m_zstems[];           // FIFO of drawn zone stems (for rolling prune)

   //--- mapping ----------------------------------------------------
   string   PeriodName(const ENUM_TIMEFRAMES p) const;
   bool     Active(const string tf) const { return InpVisualize && tf == m_tf && m_tf != ""; }

   //--- object plumbing -------------------------------------------
   void     SetCommon(const string name, const color clr, const int width=1);
   void     Text(const string name, const datetime t, const double p,
                 const string txt, const color clr, const int size=8,
                 const ENUM_ANCHOR_POINT anchor=ANCHOR_CENTER);
   void     Dot(const string name, const datetime t, const double p, const color clr, const int size=8);
   void     HLineSeg(const string name, const datetime t0, const datetime t1,
                     const double p, const color clr, const ENUM_LINE_STYLE st, const int width=1);
   void     Trend(const string name, const datetime t0, const double p0,
                  const datetime t1, const double p1, const color clr,
                  const ENUM_LINE_STYLE st=STYLE_DOT, const int width=1);

   //--- zone helpers ----------------------------------------------
   string   ZoneStem(const string tf, const BrcZone &z) const
              { return BRC_VIS_PREFIX + "Z_" + tf + "_" + (string)z.p4_time; }
   void     PruneZones();         // enforce InpBrcMaxZones FIFO
   void     DrawZoneFull(const string tf, const BrcZone &z);  // full redraw from current zone state

public:
            CBrcVisual(void) { m_tf = ""; }

   void     SyncChartTF()    { m_tf = PeriodName((ENUM_TIMEFRAMES)ChartPeriod()); }
   void     ClearAll()       { ObjectsDeleteAll(0, BRC_VIS_PREFIX); ArrayResize(m_zstems, 0); }

   //--- live event hooks (called from BrcIngestBar) ----------------
   void     OnSwing(const string tf, const BrcSwing &sw);
   void     OnBreak(const string tf, const BrcBreak &br);
   void     OnZoneConfirmed(const string tf, const BrcZone &z) { if(Active(tf)) DrawZoneFull(tf, z); }
   //--- advance only UPDATES an already-drawn zone; if it was FIFO-pruned we
   //    leave it gone (re-drawing would thrash an old-but-alive zone every bar).
   void     OnZoneAdvanced (const string tf, const BrcZone &z)
              { if(Active(tf) && ObjectFind(0, ZoneStem(tf, z) + "_rect") >= 0) DrawZoneFull(tf, z); }

   //--- full rebuild for the current chart TF (on CHARTEVENT_CHART_CHANGE)
   void     RedrawCurrentTF(const string tf,
                            const BrcSwing &sw[], const int nsw,
                            const BrcBreak &br[], const int nbr,
                            const BrcZone  &zn[], const int nz);
  };

//+------------------------------------------------------------------+
string CBrcVisual::PeriodName(const ENUM_TIMEFRAMES p) const
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
   return "";   // chart on a TF the emitter doesn't track -> draw nothing
  }

//+------------------------------------------------------------------+
//| Common object props.                                             |
//+------------------------------------------------------------------+
void CBrcVisual::SetCommon(const string name, const color clr, const int width)
  {
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, name, OBJPROP_WIDTH, width);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);   // keep out of the object list
   ObjectSetInteger(0, name, OBJPROP_BACK, false);
  }

void CBrcVisual::Text(const string name, const datetime t, const double p,
                      const string txt, const color clr, const int size,
                      const ENUM_ANCHOR_POINT anchor)
  {
   if(ObjectFind(0, name) < 0)
      ObjectCreate(0, name, OBJ_TEXT, 0, t, p);
   ObjectMove(0, name, 0, t, p);
   ObjectSetString (0, name, OBJPROP_TEXT, txt);
   ObjectSetString (0, name, OBJPROP_FONT, "Calibri");
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, size);
   ObjectSetInteger(0, name, OBJPROP_ANCHOR, anchor);
   SetCommon(name, clr);
  }

void CBrcVisual::Dot(const string name, const datetime t, const double p, const color clr, const int size)
  {
   if(ObjectFind(0, name) < 0)
      ObjectCreate(0, name, OBJ_ARROW, 0, t, p);
   ObjectMove(0, name, 0, t, p);
   ObjectSetInteger(0, name, OBJPROP_ARROWCODE, 159);    // small filled dot
   ObjectSetInteger(0, name, OBJPROP_ANCHOR, ANCHOR_CENTER);
   SetCommon(name, clr, size/4 > 0 ? size/4 : 1);
  }

void CBrcVisual::HLineSeg(const string name, const datetime t0, const datetime t1,
                          const double p, const color clr, const ENUM_LINE_STYLE st, const int width)
  { Trend(name, t0, p, t1, p, clr, st, width); }

void CBrcVisual::Trend(const string name, const datetime t0, const double p0,
                       const datetime t1, const double p1, const color clr,
                       const ENUM_LINE_STYLE st, const int width)
  {
   if(ObjectFind(0, name) < 0)
      ObjectCreate(0, name, OBJ_TREND, 0, t0, p0, t1, p1);
   ObjectMove(0, name, 0, t0, p0);
   ObjectMove(0, name, 1, t1, p1);
   ObjectSetInteger(0, name, OBJPROP_RAY_RIGHT, false);
   ObjectSetInteger(0, name, OBJPROP_STYLE, st);
   SetCommon(name, clr, width);
  }

//+------------------------------------------------------------------+
//| Swing pivot — "•" bullet, dim once broken (Sigma style).         |
//+------------------------------------------------------------------+
void CBrcVisual::OnSwing(const string tf, const BrcSwing &sw)
  {
   if(!InpBrcShowSwings || !Active(tf))
      return;
   bool  high = (sw.type == BRC_SWING_HIGH);
   color clr  = sw.broken ? InpBrcClrZoneDead
                          : (high ? InpBrcClrSwingHigh : InpBrcClrSwingLow);
   string nm = BRC_VIS_PREFIX + "SW_" + tf + "_" + (string)sw.time + "_" + (high ? "H" : "L");
   Text(nm, sw.time, sw.price, high ? "▾" : "▴", clr, 11,
        high ? ANCHOR_LOWER : ANCHOR_UPPER);
  }

//+------------------------------------------------------------------+
//| Raw breakout — dot at the breakout bar + dotted line back to the  |
//| broken swing so you can see WHAT broke.                          |
//+------------------------------------------------------------------+
void CBrcVisual::OnBreak(const string tf, const BrcBreak &br)
  {
   if(!InpBrcShowBreaks || !Active(tf))
      return;
   color clr = (br.dir == BRC_BULL) ? InpBrcClrBreakBull : InpBrcClrBreakBear;
   string stem = BRC_VIS_PREFIX + "BO_" + tf + "_" + (string)br.bar_time;
   Dot  (stem + "_d", br.bar_time, br.bar_close, clr, 8);
   Trend(stem + "_l", br.swing_time, br.swing_price, br.bar_time, br.bar_close, clr, STYLE_DOT, 1);
  }

//+------------------------------------------------------------------+
//| Full zone render from current state — idempotent (ObjectMove on   |
//| re-call), so OnZoneConfirmed and OnZoneAdvanced share one path.   |
//+------------------------------------------------------------------+
void CBrcVisual::DrawZoneFull(const string tf, const BrcZone &z)
  {
   if(!InpBrcShowZones)
      return;
   bool dead = !z.alive;
   if(dead && !InpBrcShowInvalid)
     { ObjectsDeleteAll(0, ZoneStem(tf, z)); return; }

   string stem = ZoneStem(tf, z);
   bool   first = (ObjectFind(0, stem + "_rect") < 0);
   if(first)
     {
      ArrayResize(m_zstems, ArraySize(m_zstems) + 1);
      m_zstems[ArraySize(m_zstems) - 1] = stem;
      PruneZones();
     }

   bool   bull = (z.direction == BRC_BULL);
   color  clr  = dead ? InpBrcClrZoneDead : (bull ? InpBrcClrZoneBull : InpBrcClrZoneBear);
   int    w    = dead ? 1 : 2;
   //--- right edge: frozen at death, else open to "now" (sim clock in tester)
   datetime tR = dead ? z.invalidation_time : TimeCurrent();
   if(tR <= z.p4_time) tR = z.p4_time + PeriodSeconds((ENUM_TIMEFRAMES)ChartPeriod());

   //--- 1. the L1<->L2 box ---------------------------------------
   string rn = stem + "_rect";
   if(ObjectFind(0, rn) < 0)
      ObjectCreate(0, rn, OBJ_RECTANGLE, 0, z.p4_time, z.l1, tR, z.l2);
   ObjectMove(0, rn, 0, z.p4_time, z.l1);
   ObjectMove(0, rn, 1, tR,        z.l2);
   ObjectSetInteger(0, rn, OBJPROP_FILL, !dead);
   ObjectSetInteger(0, rn, OBJPROP_STYLE, dead ? STYLE_DOT : STYLE_SOLID);
   SetCommon(rn, clr, w);
   ObjectSetInteger(0, rn, OBJPROP_BACK, true);            // box behind candles

   //--- 2. mid line ----------------------------------------------
   if(InpBrcShowMid)
      HLineSeg(stem + "_mid", z.p4_time, tR, z.mid, InpBrcClrMid, STYLE_DASH, 1);

   //--- 3. the 5 skeleton points ---------------------------------
   color pclr = dead ? InpBrcClrZoneDead : InpBrcClrMid;
   Text(stem + "_p1", z.p1_time, z.p1_price, "P1", pclr, 8, ANCHOR_RIGHT);
   Text(stem + "_p2", z.p2_time, z.p2_price, "P2", pclr, 8, ANCHOR_RIGHT);
   Text(stem + "_p3", z.p3_time, z.p3_price, "P3", pclr, 8, ANCHOR_RIGHT);
   Text(stem + "_p4", z.p4_time, z.p4_price, "P4", pclr, 8, ANCHOR_LEFT);
   Text(stem + "_p5", z.p5_time, z.p5_price, "P5", pclr, 8, ANCHOR_RIGHT);

   //--- 4. retest ladder T1=L1 / T2=mid / T3=L2 ------------------
   if(InpBrcShowRetests)
     {
      if(z.t1_time > 0) Dot(stem + "_t1", z.t1_time, z.l1,  InpBrcClrRetest, 10);
      if(z.t2_time > 0) Dot(stem + "_t2", z.t2_time, z.mid, InpBrcClrRetest, 8);
      if(z.t3_time > 0) Dot(stem + "_t3", z.t3_time, z.l2,  InpBrcClrRetest, 8);
     }

   //--- 5. invalidation ✕ ----------------------------------------
   if(dead)
      Text(stem + "_inv", z.invalidation_time, z.l2, "✕", InpBrcClrZoneDead, 12, ANCHOR_CENTER);
  }

//+------------------------------------------------------------------+
//| Rolling FIFO: keep only the InpBrcMaxZones most-recent zones.    |
//+------------------------------------------------------------------+
void CBrcVisual::PruneZones()
  {
   int over = ArraySize(m_zstems) - InpBrcMaxZones;
   if(over <= 0)
      return;
   for(int i = 0; i < over; i++)
      ObjectsDeleteAll(0, m_zstems[i]);          // drop every sub-object of the oldest zones
   //--- compact the FIFO
   for(int i = 0; i + over < ArraySize(m_zstems); i++)
      m_zstems[i] = m_zstems[i + over];
   ArrayResize(m_zstems, ArraySize(m_zstems) - over);
  }

//+------------------------------------------------------------------+
//| Wipe + rebuild the whole picture for the chart's current TF.     |
//| Called on CHARTEVENT_CHART_CHANGE so switching period swaps the   |
//| layer live. Zones carry their final lifecycle state already.     |
//+------------------------------------------------------------------+
void CBrcVisual::RedrawCurrentTF(const string tf,
                                 const BrcSwing &sw[], const int nsw,
                                 const BrcBreak &br[], const int nbr,
                                 const BrcZone  &zn[], const int nz)
  {
   ClearAll();
   if(!Active(tf))
      return;
   for(int i = 0; i < nsw; i++) OnSwing(tf, sw[i]);
   for(int i = 0; i < nbr; i++) OnBreak(tf, br[i]);
   for(int i = 0; i < nz;  i++) DrawZoneFull(tf, zn[i]);
  }

#endif // BRC_VISUAL_MQH
