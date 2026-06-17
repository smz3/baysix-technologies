//+------------------------------------------------------------------+
//|                                                     brc_visual.mqh |
//|     BRC chart visualizer — eyeball layer for the emitter.          |
//|                                                                    |
//|  Pure drawing, ZERO detection: the EA owns swing/break/zone state  |
//|  (brc_baysix.mq5); this just renders it. Styling is a faithful     |
//|  mirror of Sigma_System V5.0 Visualizer.mqh:                       |
//|    • swings    -> "•" bullet + "High/Low <price>" label            |
//|    • breakouts -> "•" bullet + "Bob/Bos <swing> (<close>)" label   |
//|                   at the BROKEN SWING point                        |
//|    • zones     -> L1 / L2 dashed lines + 50% dotted line + left    |
//|                   vertical connector + L1/L2 labels carrying the    |
//|                   touch status [T0..T3].  NO filled rectangle.      |
//|  Glyphs are ASCII + "•" ONLY (the MT5 tester font renders unicode  |
//|  arrows/✕ as "?").                                                 |
//|                                                                    |
//|  DESIGN (locked 2026-06-18):                                       |
//|   • Current-chart-TF only — every draw gated on tf==ChartPeriod()  |
//|     so the 8 TFs never collide. Switch period -> OnChartEvent       |
//|     rebuilds the layer live.                                        |
//|   • Rolling window cap (InpBrcMaxZones) per visible TF: FIFO of     |
//|     zone object-stems; oldest pruned as new ones confirm.           |
//|   • Invalidated zones are kept (dimmed, lines frozen at the         |
//|     invalidation bar) unless InpBrcShowInvalid is off.              |
//|                                                                    |
//|  ⚠️ Needs tester model = Visual Mode (NOT "Open prices only").      |
//+------------------------------------------------------------------+
#ifndef BRC_VISUAL_MQH
#define BRC_VISUAL_MQH
#property strict

#include "brc_types.mqh"

//--- master + per-layer toggles -------------------------------------
input bool  InpVisualize      = false;       // MASTER: draw chart objects (off for the 10yr emit run)
input bool  InpBrcShowSwings  = true;        // LAYER 1: swing pivots (validate this first)
input bool  InpBrcShowBreaks  = true;        // LAYER 2: raw breakouts
input bool  InpBrcShowZones   = true;        // LAYER 3: 5-pointer zone (L1/L2/50 lines + labels)
input bool  InpBrcShowMid     = true;        // zone 50% line
input bool  InpBrcShowPoints  = true;        // P1..P5 skeleton bullets
input bool  InpBrcShowRetests = true;        // T1/T2/T3 retest touch dots (status is always in the label)
input bool  InpBrcShowInvalid = true;        // keep invalidated (dead) zones on chart (dimmed)
input int   InpBrcMaxZones    = 50;          // rolling cap: zones kept on chart per TF
input int   InpBrcBulletSize  = 12;          // "•" bullet font size
input int   InpBrcLabelSize   = 7;           // label font size
//--- colours (Sigma-style) ------------------------------------------
input color InpBrcClrSwingHigh = clrTomato;
input color InpBrcClrSwingLow  = clrDodgerBlue;
input color InpBrcClrBreakBull = clrLimeGreen;
input color InpBrcClrBreakBear = clrOrangeRed;
input color InpBrcClrZoneBull  = clrMediumSeaGreen;
input color InpBrcClrZoneBear  = clrIndianRed;
input color InpBrcClrZoneDead  = clrDimGray;
input color InpBrcClrMid       = clrGoldenrod;
input color InpBrcClrRetest    = clrWhite;
input color InpBrcClrPoint     = clrSilver;

#define BRC_VIS_PREFIX "BRC_"          // every object name starts here -> one-shot ClearAll
#define BRC_VIS_FONT   "Calibri Light"

//+------------------------------------------------------------------+
//| CBrcVisual                                                       |
//+------------------------------------------------------------------+
class CBrcVisual
  {
private:
   string   m_tf;                 // chart's TF name ("M5".."MN1"); "" if chart period unmapped
   string   m_zstems[];           // FIFO of drawn zone stems (rolling prune)

   string   PeriodName(const ENUM_TIMEFRAMES p) const;
   bool     Active(const string tf) const { return InpVisualize && tf == m_tf && m_tf != ""; }

   //--- low-level object primitives (idempotent: create-or-move) ---
   void     Bullet(const string name, const datetime t, const double p, const color clr, const int size);
   void     Label (const string name, const datetime t, const double p, const string txt,
                    const color clr, const ENUM_ANCHOR_POINT anchor);
   void     Line  (const string name, const datetime t0, const double p0, const datetime t1,
                    const double p1, const color clr, const ENUM_LINE_STYLE st,
                    const bool ray, const int width=1);

   string   ZoneStem(const string tf, const BrcZone &z) const
              { return BRC_VIS_PREFIX + "Z_" + tf + "_" + (string)z.p4_time; }
   string   TouchTag(const BrcZone &z) const
              { return z.t3_time>0 ? "T3" : (z.t2_time>0 ? "T2" : (z.t1_time>0 ? "T1" : "T0")); }
   void     PruneZones();
   void     DrawZoneFull(const string tf, const BrcZone &z);

public:
            CBrcVisual(void) { m_tf = ""; }

   void     SyncChartTF()    { m_tf = PeriodName((ENUM_TIMEFRAMES)ChartPeriod()); }
   void     ClearAll()       { ObjectsDeleteAll(0, BRC_VIS_PREFIX); ArrayResize(m_zstems, 0); }

   //--- live event hooks (called from BrcIngestBar) ----------------
   void     OnSwing(const string tf, const BrcSwing &sw);
   void     OnBreak(const string tf, const BrcBreak &br);
   void     OnZoneConfirmed(const string tf, const BrcZone &z) { if(Active(tf)) DrawZoneFull(tf, z); }
   //--- advance only UPDATES an already-drawn zone; if FIFO-pruned, leave it gone
   void     OnZoneAdvanced (const string tf, const BrcZone &z)
              { if(Active(tf) && ObjectFind(0, ZoneStem(tf, z) + "_L1") >= 0) DrawZoneFull(tf, z); }

   //--- full rebuild for the current chart TF (CHARTEVENT_CHART_CHANGE)
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
//| Primitives — all create-or-update so redraws never duplicate.    |
//+------------------------------------------------------------------+
void CBrcVisual::Bullet(const string name, const datetime t, const double p, const color clr, const int size)
  {
   if(ObjectFind(0, name) < 0)
      ObjectCreate(0, name, OBJ_TEXT, 0, t, p);
   ObjectMove(0, name, 0, t, p);
   ObjectSetString (0, name, OBJPROP_TEXT, "•");
   ObjectSetString (0, name, OBJPROP_FONT, BRC_VIS_FONT);
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, size);
   ObjectSetInteger(0, name, OBJPROP_ANCHOR, ANCHOR_CENTER);
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
   ObjectSetInteger(0, name, OBJPROP_BACK, false);
  }

void CBrcVisual::Label(const string name, const datetime t, const double p, const string txt,
                       const color clr, const ENUM_ANCHOR_POINT anchor)
  {
   if(ObjectFind(0, name) < 0)
      ObjectCreate(0, name, OBJ_TEXT, 0, t, p);
   ObjectMove(0, name, 0, t, p);
   ObjectSetString (0, name, OBJPROP_TEXT, txt);
   ObjectSetString (0, name, OBJPROP_FONT, BRC_VIS_FONT);
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, InpBrcLabelSize);
   ObjectSetInteger(0, name, OBJPROP_ANCHOR, anchor);
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
   ObjectSetInteger(0, name, OBJPROP_BACK, false);
  }

void CBrcVisual::Line(const string name, const datetime t0, const double p0, const datetime t1,
                      const double p1, const color clr, const ENUM_LINE_STYLE st,
                      const bool ray, const int width)
  {
   if(ObjectFind(0, name) < 0)
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

//+------------------------------------------------------------------+
//| LAYER 1 — swing pivot: bullet at the close + "High/Low <price>".  |
//+------------------------------------------------------------------+
void CBrcVisual::OnSwing(const string tf, const BrcSwing &sw)
  {
   if(!InpBrcShowSwings || !Active(tf))
      return;
   bool  high = (sw.type == BRC_SWING_HIGH);
   color clr  = sw.broken ? InpBrcClrZoneDead
                          : (high ? InpBrcClrSwingHigh : InpBrcClrSwingLow);
   string stem = BRC_VIS_PREFIX + "SW_" + tf + "_" + (string)sw.time + "_" + (high ? "H" : "L");
   Bullet(stem + "_b", sw.time, sw.price, clr, InpBrcBulletSize);
   Label (stem + "_t", sw.time, sw.price,
          "  " + (high ? "High " : "Low ") + DoubleToString(sw.price, _Digits),
          clr, ANCHOR_LEFT);
  }

//+------------------------------------------------------------------+
//| LAYER 2 — raw breakout: bullet + label at the BROKEN swing,       |
//| label shows Bob/Bos, the broken-swing price and the breakout close|
//| (mirrors Sigma DrawRawBreakout exactly).                          |
//+------------------------------------------------------------------+
void CBrcVisual::OnBreak(const string tf, const BrcBreak &br)
  {
   if(!InpBrcShowBreaks || !Active(tf))
      return;
   bool   bull = (br.dir == BRC_BULL);
   color  clr  = bull ? InpBrcClrBreakBull : InpBrcClrBreakBear;
   string tag  = bull ? "Bob" : "Bos";       // Break-of-bull / Break-of-bear (Sigma naming)
   //--- key on the BROKEN SWING (unique — a swing breaks once); bar_time alone
   //    collides when one bar's close breaks several swings, dropping all but one.
   string stem = BRC_VIS_PREFIX + "BO_" + tf + "_" + (string)br.swing_time + "_" + (string)br.bar_time;
   Bullet(stem + "_b", br.swing_time, br.swing_price, clr, InpBrcBulletSize);
   Label (stem + "_t", br.swing_time, br.swing_price,
          StringFormat("  %s %s (%s)", tag, DoubleToString(br.swing_price, _Digits),
                       DoubleToString(br.bar_close, _Digits)),
          clr, ANCHOR_RIGHT);
  }

//+------------------------------------------------------------------+
//| LAYER 3 — full zone: L1/L2 dashed lines + 50% dotted + left       |
//| vertical connector + L1/L2 labels (with touch status). Lines run  |
//| from P2 (L1 origin) to the right; alive => ray, dead => frozen at |
//| invalidation bar and dimmed. Idempotent.                          |
//+------------------------------------------------------------------+
void CBrcVisual::DrawZoneFull(const string tf, const BrcZone &z)
  {
   if(!InpBrcShowZones)
      return;
   bool dead = !z.alive;
   if(dead && !InpBrcShowInvalid)
     { ObjectsDeleteAll(0, ZoneStem(tf, z)); return; }

   string stem  = ZoneStem(tf, z);
   bool   first = (ObjectFind(0, stem + "_L1") < 0);
   if(first)
     {
      ArrayResize(m_zstems, ArraySize(m_zstems) + 1);
      m_zstems[ArraySize(m_zstems) - 1] = stem;
      PruneZones();
     }

   bool   bull = (z.direction == BRC_BULL);
   color  clr  = dead ? InpBrcClrZoneDead : (bull ? InpBrcClrZoneBull : InpBrcClrZoneBear);
   //--- timing: start at L1 origin (P2), run right. Alive => ray; dead => stop at death.
   datetime t0 = z.p2_time;
   datetime tR = dead ? z.invalidation_time : (TimeCurrent() + PeriodSeconds((ENUM_TIMEFRAMES)ChartPeriod()) * 50);
   bool     ray = !dead;
   if(tR <= t0) tR = t0 + PeriodSeconds((ENUM_TIMEFRAMES)ChartPeriod());

   //--- L1 / L2 lines + 50% + left vertical connector
   Line(stem + "_L1", t0, z.l1, tR, z.l1, clr, STYLE_DASH, ray, dead ? 1 : 2);
   Line(stem + "_L2", t0, z.l2, tR, z.l2, clr, STYLE_DASH, ray, dead ? 1 : 2);
   if(InpBrcShowMid)
      Line(stem + "_50", t0, z.mid, tR, z.mid, dead ? InpBrcClrZoneDead : InpBrcClrMid, STYLE_DOT, ray, 1);
   Line(stem + "_LV", t0, z.l1, t0, z.l2, clr, STYLE_SOLID, false, 1);

   //--- L1 / L2 labels (touch status + price + dir), anchored off the box edge
   string dir = bull ? "Buy" : "Sell";
   ENUM_ANCHOR_POINT aL2 = bull ? ANCHOR_LEFT_UPPER : ANCHOR_LEFT_LOWER;   // L2 sits outside the box
   ENUM_ANCHOR_POINT aL1 = bull ? ANCHOR_LEFT_LOWER : ANCHOR_LEFT_UPPER;
   Label(stem + "_L2t", t0, z.l2,
         StringFormat("L2 BRC %s %s [%s] %s", tf, dir, TouchTag(z), DoubleToString(z.l2, _Digits)),
         clr, aL2);
   Label(stem + "_L1t", t0, z.l1,
         StringFormat("L1 BRC %s %s %s", tf, dir, DoubleToString(z.l1, _Digits)),
         clr, aL1);

   //--- P1..P5 skeleton bullets (BRC-specific; small)
   if(InpBrcShowPoints)
     {
      color pclr = dead ? InpBrcClrZoneDead : InpBrcClrPoint;
      Bullet(stem + "_p1", z.p1_time, z.p1_price, pclr, InpBrcBulletSize - 3);
      Label (stem + "_p1t", z.p1_time, z.p1_price, "P1", pclr, ANCHOR_RIGHT);
      Bullet(stem + "_p2", z.p2_time, z.p2_price, pclr, InpBrcBulletSize - 3);
      Label (stem + "_p2t", z.p2_time, z.p2_price, "P2", pclr, ANCHOR_RIGHT);
      Bullet(stem + "_p3", z.p3_time, z.p3_price, pclr, InpBrcBulletSize - 3);
      Label (stem + "_p3t", z.p3_time, z.p3_price, "P3", pclr, ANCHOR_RIGHT);
      Bullet(stem + "_p4", z.p4_time, z.p4_price, pclr, InpBrcBulletSize - 3);
      Label (stem + "_p4t", z.p4_time, z.p4_price, "P4", pclr, ANCHOR_LEFT);
      Bullet(stem + "_p5", z.p5_time, z.p5_price, pclr, InpBrcBulletSize - 3);
      Label (stem + "_p5t", z.p5_time, z.p5_price, "P5", pclr, ANCHOR_RIGHT);
     }

   //--- retest touch dots (timing the label can't show)
   if(InpBrcShowRetests)
     {
      if(z.t1_time > 0) Bullet(stem + "_t1", z.t1_time, z.l1,  InpBrcClrRetest, InpBrcBulletSize - 2);
      if(z.t2_time > 0) Bullet(stem + "_t2", z.t2_time, z.mid, InpBrcClrRetest, InpBrcBulletSize - 4);
      if(z.t3_time > 0) Bullet(stem + "_t3", z.t3_time, z.l2,  InpBrcClrRetest, InpBrcBulletSize - 4);
     }
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
   for(int i = 0; i + over < ArraySize(m_zstems); i++)
      m_zstems[i] = m_zstems[i + over];
   ArrayResize(m_zstems, ArraySize(m_zstems) - over);
  }

//+------------------------------------------------------------------+
//| Wipe + rebuild the whole picture for the chart's current TF.     |
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
