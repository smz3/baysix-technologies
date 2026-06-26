//+------------------------------------------------------------------+
//|                                                    fob_visual.mqh  |
//|  FOB chart visualizer — EVENT-TF LENS (rewritten 2026-06-25).      |
//|                                                                    |
//|  Pure drawing, ZERO detection: the classifier owns all state; this |
//|  is a replayable PROJECTION of the event log + a tiny view-state   |
//|  it rebuilds ITSELF from that log (never reads live st[]). So the   |
//|  picture can never drift from the detector.                        |
//|                                                                    |
//|  ONE CHART PER TIMEFRAME: a chart draws breaks that FIRED on its    |
//|  own TF (event_tf == ChartPeriod), on their NATIVE bars (no cross-  |
//|  TF projection). The #id is the cross-chart link: "vr h1 #1" on the  |
//|  M30 chart <-> "pbo h1 #1" on the H1 chart.                         |
//|                                                                    |
//|  DUAL-PURPOSE DOT (task 2 rev 2026-06-25): a break is a PBO for its  |
//|  own TF and MAY ALSO be a VR/CF for the TF above. When BOTH roles     |
//|  qualify, ONE bullet carries TWO fanned labels — own PBO anchored     |
//|  RIGHT (renders LEFT of the dot), parent VR/CF anchored LEFT (renders |
//|  RIGHT) — so they splay apart, never stack. Bullet colour = parent    |
//|  role if present (the live higher-TF story), else own PBO. A setup    |
//|  still spans two charts (its pbo on its own TF, its vr/cf on the TF   |
//|  below) joined by #id; the dual tag only appears where one physical   |
//|  bar serves both at once.                                            |
//|                                                                    |
//|  Label grammar (E = this TF, E-1 = below, E+1 = above). DIR =        |
//|  thesis direction. A dot carries one or both of:                    |
//|    PBO E #p DIR · pending {E-1} VR   (own PBO, no VR yet)            |
//|    PBO E #p DIR · pending {E-1} CF   (VR locked, no CF yet)          |
//|    PBO E #p DIR · live {E-1} CFc     (c CFs developed; task 160)     |
//|    VR  {E+1} #q DIR                   (serves the TF-above setup)     |
//|    CF  {E+1} #q.c DIR                 (serves the TF-above setup)     |
//|  Parent DIR is DERIVED: VR = OPP(break), CF = same-as(break).        |
//|  M1 has NO own PBO (task 1) — the M1 chart shows only vr/cf for M5.  |
//|                                                                    |
//|  Colour follows the shown role: PBO blue / VR yellow / CF green.    |
//|                                                                    |
//|  Visibility (ACTIVE CYCLE ONLY, task 157): a superseded cycle is    |
//|  VOIDED and must vanish. The own PBO shows only if it is the active  |
//|  (latest) seq for E; a parent VR/CF shows only if it belongs to the  |
//|  active cycle of the TF above (parSeq == its current seq).          |
//|                                                                    |
//|  Needs tester model = Visual Mode to paint live.                   |
//+------------------------------------------------------------------+
#ifndef FOB_VISUAL_MQH
#define FOB_VISUAL_MQH
#property strict

#include "fob_types.mqh"

//--- master toggle (ACTIVE cycle only — no prior-cycle retention, task 157)
input bool InpVisualize    = true;        // MASTER: draw chart objects
//--- 3 independent layers under the master (task 158) — each gated alone
input bool InpShowSequence = true;        // PBO/VR/CF classification dots
input bool InpShowSwings   = false;        // FOB swing pivots (carets)
input bool InpShowRawBreaks= false;        // FOB raw breakouts (dotted lines)
input bool InpShowZones    = true;         // 4-pointer L1/L2 band + P1/P3 dots (v1.14.0 sanity-check)

//--- font sizes (hidden from inputs — tweak in source)
const int   InpFobBulletSize = 12;
const int   InpFobLabelSize  = 9;

//--- structure-layer colours (mirror of BRC swings/breaks; tweak in source)
const color InpFobClrSwingHigh = clrTomato;
const color InpFobClrSwingLow  = clrDodgerBlue;
const color InpFobClrSwingDead = clrDimGray;
const color InpFobClrBreakBull = clrLimeGreen;
const color InpFobClrBreakBear = clrOrangeRed;

#define FOB_VIS_PREFIX "FOB_"
#define FOB_VIS_FONT   "Calibri Light"

//+------------------------------------------------------------------+
//| CFobVisual                                                       |
//+------------------------------------------------------------------+
class CFobVisual
  {
private:
   string   m_tf;        // chart TF name ("M1".."MN1"); "" if unmapped
   int      m_idx;       // chart TF ladder index; -1 if unmapped

   int      LadderIndex(const ENUM_TIMEFRAMES p) const;

   void     Bullet(const string name, const datetime t, const double p, const color clr);
   void     Label (const string name, const datetime t, const double p, const string txt, const color clr,
                   const ENUM_ANCHOR_POINT anchor = ANCHOR_LEFT);

   bool     SameBreak(const FobEvent &a, const FobEvent &b) const
              { return a.event_tf == b.event_tf && a.bar_time == b.bar_time && a.swing_time == b.swing_time; }
   int      OppDir(const int d) const { return d == FOB_BULL ? FOB_BEAR : FOB_BULL; }
   //--- (setup_tf, seq) cycle has a LIVE open position -> keep its dots past supersession
   bool     IsLiveCycle(const int tf, const int seq, const int &ltf[], const int &lseq[], const int nl) const
              { for(int i = 0; i < nl; i++) if(ltf[i] == tf && lseq[i] == seq) return true; return false; }

public:
            CFobVisual(void) { m_tf = ""; m_idx = -1; }

   void     SyncChartTF();
   int      ChartIdx() const { return m_idx; }   // chart TF ladder index (-1 if unmapped)
   void     ClearAll() { ObjectsDeleteAll(0, FOB_VIS_PREFIX); }

   //--- full rebuild of the current chart's lens from the event log.
   //--- liveTf/liveSeq = (setup_tf, seq) cycles with an OPEN position: drawn
   //--- even when superseded, so a live trade keeps its sequence dots.
   void     RedrawCurrentTF(const FobEvent &ev[], const int n,
                            const int &liveTf[], const int &liveSeq[], const int nLive);
   //--- 2-arg overload for the emitter (read-only, no positions -> no live cycles)
   void     RedrawCurrentTF(const FobEvent &ev[], const int n)
              { int empty[]; RedrawCurrentTF(ev, n, empty, empty, 0); }

   //--- draw the chart TF's OWN detected structure (swing pivots + raw
   //--- breakouts). Call AFTER RedrawCurrentTF (which ClearAll's first),
   //--- with the chart-TF's own g_tf[ChartIdx()] swing/break arrays.
   void     DrawStructure(const FobSwing &sw[], const FobBreak &br[]);

   //--- draw the 4-pointer zone (L1/L2 band + P1/P3 markers) for every event
   //--- that FIRED on this chart TF. Sanity-check layer (v1.14.0). Call AFTER
   //--- RedrawCurrentTF (it ClearAll's first). Only valid zones are drawn.
   void     DrawZones(const FobEvent &ev[], const int n);
  };

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

//+------------------------------------------------------------------+
//| Full rebuild for the current chart TF.                            |
//|  PASS 1 (all events): reconstruct per-setup state from the log —   |
//|    the ACTIVE (latest) seq per TF and whether its VR is locked.     |
//|  PASS 2 (this-TF breaks only): merge each physical break's roles    |
//|    into one labelled dot, keep only the ACTIVE cycle, draw.         |
//+------------------------------------------------------------------+
void CFobVisual::RedrawCurrentTF(const FobEvent &ev[], const int n,
                                 const int &liveTf[], const int &liveSeq[], const int nLive)
  {
   ClearAll();
   if(!InpVisualize || m_idx < 0)
      return;
   if(!InpShowSequence)   // sequence layer off — ClearAll already wiped the dots
      return;

   int E = m_idx;

   //--- PASS 1 : reconstruct state -----------------------------------
   int  curSeq[FOB_N_TF];
   bool vrLocked[FOB_N_TF];
   int  cfCount[FOB_N_TF];   // CFs developed in the ACTIVE cycle (task 160 lifecycle)
   for(int i = 0; i < FOB_N_TF; i++) { curSeq[i] = -1; vrLocked[i] = false; cfCount[i] = 0; }

   for(int i = 0; i < n; i++)
     {
      int s  = ev[i].setup_tf;
      int sq = ev[i].seq;
      if(ev[i].label == FOB_PBO)
        { curSeq[s] = sq; vrLocked[s] = false; cfCount[s] = 0; }
      else if(sq == curSeq[s])
        {
         if(ev[i].label == FOB_VR)                              vrLocked[s] = true;
         else if(ev[i].label == FOB_CF && ev[i].cf_idx > cfCount[s]) cfCount[s] = ev[i].cf_idx;
        }
     }

   //--- PASS 2 : draw this TF's breaks -------------------------------
   int i = 0;
   while(i < n)
     {
      //--- gather one physical break (its adjacent role events)
      int j = i + 1;
      while(j < n && SameBreak(ev[j], ev[i]))
         j++;

      if(ev[i].event_tf == E)
        {
         //--- split the group into own-PBO + optional parent role
         int    pOwn = -1, ownDir = -1;
         datetime swt = ev[i].swing_time;
         double   lvl = ev[i].level;
         bool   hasPar = false; int parLab = -1, parSeq = -1, parDir = -1, parCf = 0;

         for(int k = i; k < j; k++)
           {
            if(ev[k].label == FOB_PBO && ev[k].setup_tf == E)
              { pOwn = ev[k].seq; ownDir = ev[k].dir; }
            else if((ev[k].label == FOB_VR || ev[k].label == FOB_CF) && ev[k].setup_tf == E + 1)
              { hasPar = true; parLab = ev[k].label; parSeq = ev[k].seq; parDir = ev[k].dir; parCf = ev[k].cf_idx; }
           }

         //--- ACTIVE-CYCLE-ONLY gate (task 157) + DUAL-PURPOSE DOT (task 2 rev
         //--- 2026-06-25): a single break can be its OWN PBO *and* a VR/CF for
         //--- the TF above. When BOTH qualify, draw ONE bullet with the two
         //--- labels FANNED off it — own PBO to the LEFT (ANCHOR_RIGHT), parent
         //--- VR/CF to the RIGHT (ANCHOR_LEFT) — so they splay instead of
         //--- stacking. Bullet colour follows the parent (the live higher-TF
         //--- story) when present, else the own PBO. (M1 has no own PBO — task
         //--- 1 — so the M1 chart shows only the parent dot.)
         //--- active cycle OR a superseded cycle that still has a LIVE position
         //--- (task: visual retention — don't wipe a cycle whose trade is open).
         bool parentQual = hasPar && (parSeq == curSeq[E + 1] || IsLiveCycle(E + 1, parSeq, liveTf, liveSeq, nLive));
         bool ownActive  = (pOwn >= 0 && pOwn == curSeq[E]);
         bool anchorQual = (pOwn >= 0 && (ownActive || IsLiveCycle(E, pOwn, liveTf, liveSeq, nLive)));

         string parTxt = "";  color parClr = clrNONE;
         string ownTxt = "";  color ownClr = clrNONE;

         if(parentQual)
           {
            //--- thesis dir: VR = OPP(break), CF = same-as(break)
            int parThesis = (parLab == FOB_VR) ? OppDir(parDir) : parDir;
            //--- CF carries its per-cycle ordinal (#seq.cf): "cf h1 #1.2" = 2nd
            //--- CF of cycle 1 — the layering count the entry test keys on.
            if(parLab == FOB_CF)
               parTxt = StringFormat("  %s %s #%d.%d %s",
                                     FobLabelName(parLab), FobTfName(E + 1), parSeq, parCf, FobDirName(parThesis));
            else
               parTxt = StringFormat("  %s %s #%d %s",
                                     FobLabelName(parLab), FobTfName(E + 1), parSeq, FobDirName(parThesis));
            parClr = FobLabelColor(parLab);
           }

         if(anchorQual)
           {
            //--- trailing pad (not leading): this label anchors RIGHT, so it
            //--- renders to the LEFT of the bullet and the pad pushes it clear.
            ownTxt = StringFormat("PBO %s #%d %s", FobTfName(E), pOwn, FobDirName(ownDir));
            //--- lifecycle badge (task 160): the dot tells its cycle phase at a
            //--- glance — pending VR -> pending CF (VR locked) -> live CF1/2/...
            //--- advancing with cf_idx. {E-1} = the TF below that supplies VR/CF.
            //--- ONLY valid for the ACTIVE cycle (vrLocked/cfCount track it); a
            //--- retained-but-superseded live cycle gets a frozen "held" badge.
            if(E > 0 && ownActive)
              {
               if(!vrLocked[E])
                  ownTxt += StringFormat(" · pending %s VR", FobTfName(E - 1));
               else if(cfCount[E] == 0)
                  ownTxt += StringFormat(" · pending %s CF", FobTfName(E - 1));
               else
                  ownTxt += StringFormat(" · live %s CF%d", FobTfName(E - 1), cfCount[E]);
              }
            else if(E > 0)
               ownTxt += " · held (open trade)";
            ownTxt += "  ";
            ownClr = FobLabelColor(FOB_PBO);
           }

         if(parClr != clrNONE || ownClr != clrNONE)
           {
            color  bulletClr = (parClr != clrNONE) ? parClr : ownClr;
            string base = FOB_VIS_PREFIX + (string)swt + "_" + (string)ev[i].bar_time;
            Bullet(base + "_b", swt, lvl, bulletClr);
            if(ownClr != clrNONE)   // own PBO label — fan LEFT
              {
               StringToLower(ownTxt);   // small-caps display (task 3, 2026-06-25)
               Label(base + "_to", swt, lvl, ownTxt, ownClr, ANCHOR_RIGHT);
              }
            if(parClr != clrNONE)   // parent VR/CF label — fan RIGHT
              {
               StringToLower(parTxt);
               Label(base + "_tp", swt, lvl, parTxt, parClr, ANCHOR_LEFT);
              }
           }
        }
      i = j;
     }
  }

//+------------------------------------------------------------------+
//| Draw the chart TF's OWN detected structure (FOB detection output). |
//|  Faithful mirror of BRC's swing/break visuals (brc_visual.mqh):    |
//|    • SWING  -> "•" bullet at the pivot + "High/Low <price>" label   |
//|               (high=Tomato, low=DodgerBlue, dimmed once broken).    |
//|    • BREAK  -> "•" bullet at the BROKEN swing + "Bob/Bos <swing>    |
//|               (<close>)" label (bull=LimeGreen, bear=OrangeRed),    |
//|               anchored RIGHT. Keyed on broken-swing + break-bar so  |
//|               one bar breaking several swings keeps every dot.      |
//|  FOB_-prefixed so RedrawCurrentTF()->ClearAll() wipes + repaints.   |
//+------------------------------------------------------------------+
void CFobVisual::DrawStructure(const FobSwing &sw[], const FobBreak &br[])
  {
   if(m_idx < 0)
      return;

   int ns = InpShowSwings ? ArraySize(sw) : 0;
   for(int i = 0; i < ns; i++)
     {
      bool   high = (sw[i].type == FOB_SWING_HIGH);
      color  c    = sw[i].broken ? InpFobClrSwingDead
                                  : (high ? InpFobClrSwingHigh : InpFobClrSwingLow);
      string stem = FOB_VIS_PREFIX + "SW_" + (string)sw[i].time + "_" + (high ? "H" : "L");
      Bullet(stem + "_b", sw[i].time, sw[i].price, c);
      Label (stem + "_t", sw[i].time, sw[i].price,
             "  " + (high ? "High " : "Low ") + DoubleToString(sw[i].price, _Digits),
             c, ANCHOR_LEFT);
     }

   int nb = InpShowRawBreaks ? ArraySize(br) : 0;
   for(int i = 0; i < nb; i++)
     {
      bool   bull = (br[i].dir == FOB_BULL);
      color  c    = bull ? InpFobClrBreakBull : InpFobClrBreakBear;
      string tag  = bull ? "Bob" : "Bos";   // Break-of-bull / Break-of-bear (Sigma/BRC naming)
      string stem = FOB_VIS_PREFIX + "RB_" + (string)br[i].swing_time + "_" + (string)br[i].bar_time;
      Bullet(stem + "_b", br[i].swing_time, br[i].swing_price, c);
      Label (stem + "_t", br[i].swing_time, br[i].swing_price,
             StringFormat("  %s %s (%s)", tag, DoubleToString(br[i].swing_price, _Digits),
                          DoubleToString(br[i].bar_close, _Digits)),
             c, ANCHOR_RIGHT);
     }
  }

//+------------------------------------------------------------------+
//| 4-POINTER ZONE layer (v1.14.0) — sanity-check picture.            |
//|  For every event that fired on THIS chart TF with a valid zone:   |
//|    • a dotted L1..L2 rectangle from P2 (the broken swing) to the   |
//|      break bar — the structural band the stop would sit beyond.    |
//|    • P1 (origin) and P3 (pullback) pivot markers, labelled.        |
//|    • an "L2" tag at the far/invalidation edge.                     |
//|  Colour follows the event role (PBO blue / VR yellow / CF green).  |
//|  Invalid zones are NOT drawn (foolproof: no zone -> no trade).     |
//+------------------------------------------------------------------+
void CFobVisual::DrawZones(const FobEvent &ev[], const int n)
  {
   if(m_idx < 0 || !InpVisualize || !InpShowZones)
      return;
   int E = m_idx;

   for(int i = 0; i < n; i++)
     {
      if(ev[i].event_tf != E)   continue;
      if(!ev[i].zone.valid)     continue;

      color  c    = FobLabelColor(ev[i].label);
      double l1   = ev[i].level;        // P2 price = entry/trigger edge
      double l2   = ev[i].zone.l2;      // extreme(P1,P3) = far/invalidation edge
      string stem = FOB_VIS_PREFIX + "Z_" + (string)ev[i].swing_time + "_" +
                    (string)ev[i].bar_time + "_" + FobLabelName(ev[i].label);

      //--- L1..L2 band (dotted outline, behind candles)
      string box = stem + "_box";
      ObjectCreate(0, box, OBJ_RECTANGLE, 0, ev[i].swing_time, l1, ev[i].bar_time, l2);
      ObjectSetInteger(0, box, OBJPROP_COLOR, c);
      ObjectSetInteger(0, box, OBJPROP_STYLE, STYLE_DOT);
      ObjectSetInteger(0, box, OBJPROP_WIDTH, 1);
      ObjectSetInteger(0, box, OBJPROP_FILL, false);
      ObjectSetInteger(0, box, OBJPROP_BACK, true);
      ObjectSetInteger(0, box, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, box, OBJPROP_HIDDEN, true);

      //--- P1 / P3 pivot markers
      Bullet(stem + "_p1", ev[i].zone.p1_time, ev[i].zone.p1_price, c);
      Label (stem + "_p1t", ev[i].zone.p1_time, ev[i].zone.p1_price, "p1  ", c, ANCHOR_RIGHT);
      Bullet(stem + "_p3", ev[i].zone.p3_time, ev[i].zone.p3_price, c);
      Label (stem + "_p3t", ev[i].zone.p3_time, ev[i].zone.p3_price, "p3  ", c, ANCHOR_RIGHT);

      //--- L2 tag at the invalidation edge
      Label (stem + "_l2t", ev[i].bar_time, l2,
             "  L2 " + DoubleToString(l2, _Digits), c, ANCHOR_LEFT);
     }
  }

#endif // FOB_VISUAL_MQH
