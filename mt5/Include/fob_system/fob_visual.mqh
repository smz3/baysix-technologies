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
#include "fob_lifecycle.mqh"   // FobReplayZoneLife — BRC-parity T-touch + invalidation

//--- master toggle (ACTIVE cycle only — no prior-cycle retention, task 157)
input bool InpVisualize    = true;        // MASTER: draw chart objects
//--- independent layers under the master (task 158/178) — each gated alone
input bool InpShowSequence = true;        // PBO/VR/CF classification role dots
input bool InpShowSwings   = false;        // FOB swing pivots (carets)
input bool InpShowRawBreaks= false;        // FOB raw breakouts (dotted lines)
input bool InpShowZones    = true;         // L1/L2 band + mid + [Tn] labels (BRC-style, task 178)
input bool InpShowPoints   = false;        // P1/P3 skeleton dots (split out of the zone, task 178)
input bool InpShowRetests  = true;         // T1/T2/T3 retest touch dots (BRC-style, task 178)

//--- font sizes (hidden from inputs — tweak in source)
const int   InpFobBulletSize = 12;
const int   InpFobLabelSize  = 9;

//--- structure-layer colours (mirror of BRC swings/breaks; tweak in source)
const color InpFobClrSwingHigh = clrTomato;
const color InpFobClrSwingLow  = clrDodgerBlue;
const color InpFobClrSwingDead = clrDimGray;
const color InpFobClrBreakBull = clrLimeGreen;
const color InpFobClrBreakBear = clrOrangeRed;
//--- zone-layer colours (role colour from FobLabelColor stays the live hue;
//--- these are the shared mid/retest/point accents). Dead zones are DROPPED,
//--- not greyed — no dead colour (task: delete gray zones, 2026-06-26).
const color InpFobClrMid       = clrGoldenrod;   // 50% line
const color InpFobClrRetest    = clrWhite;       // T1/T2/T3 touch dots
const color InpFobClrPoint     = clrSilver;      // P1/P3 skeleton dots

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
   void     Line  (const string name, const datetime t0, const double p0, const datetime t1,
                   const double p1, const color clr, const ENUM_LINE_STYLE st,
                   const bool ray, const int width = 1);
   //--- deepest retest reached, for the L2 label tag (mirror BRC TouchTag)
   string   TouchTag(const FobZone &z) const
              { return z.t3_time>0 ? "T3" : (z.t2_time>0 ? "T2" : (z.t1_time>0 ? "T1" : "T0")); }

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

   //--- STAMP the retest ladder + alive/invalidation onto every event whose
   //--- break fired on THIS chart TF, recomputed STATELESSLY from the chart-TF
   //--- OHLC buffer (bt/bh/bl/bc, index 0 = OLDEST, length nb). Mutates `ev`
   //--- (touch fields only; recomputed every redraw). Call BEFORE RedrawCurrentTF
   //--- so the dot labels can carry the [Tn] tag, and before DrawZones so the
   //--- geometry knows which zones are still alive.
   void     UpdateZoneLifecycles(FobEvent &ev[], const int n,
                                 const datetime &bt[], const double &bh[],
                                 const double &bl[], const double &bc[], const int nb);

   //--- draw zone GEOMETRY only (L1/L2 dashed lines + mid dotted + left vertical
   //--- connector + optional P1/P3 + retest dots) for every active-cycle, ALIVE,
   //--- valid zone that fired on this chart TF. NO text labels — the role text +
   //--- [Tn] live on the sequence dot (RedrawCurrentTF). Touches must already be
   //--- stamped (UpdateZoneLifecycles). Dual-purpose breaks share one band (label-
   //--- less stem -> idempotent). Call AFTER RedrawCurrentTF (it ClearAll's first).
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

         //--- retest tag for THIS physical break's zone (stamped by
         //--- UpdateZoneLifecycles). Shared by both fanned roles — one break =
         //--- one zone = one touch ladder. Shown on EVERY role so each FOB
         //--- sequence step carries its own [Tn] (entry-strategy data, 2026-06-26).
         string tnTag = ev[i].zone.valid ? (" [" + TouchTag(ev[i].zone) + "]") : "";

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
            parTxt += tnTag;
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
            ownTxt += tnTag;
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
//| Stamp the retest ladder + alive/invalidation onto every event      |
//| whose break fired on THIS chart TF (data only, no drawing). Run    |
//| BEFORE RedrawCurrentTF (so dot labels carry [Tn]) and DrawZones.   |
//| Dual-purpose breaks emit two events with identical geometry — both  |
//| get stamped (cheap), keeping label + geometry consistent.          |
//+------------------------------------------------------------------+
void CFobVisual::UpdateZoneLifecycles(FobEvent &ev[], const int n,
                                      const datetime &bt[], const double &bh[],
                                      const double &bl[], const double &bc[], const int nb)
  {
   if(m_idx < 0)
      return;
   int E = m_idx;
   for(int i = 0; i < n; i++)
      if(ev[i].event_tf == E)
         FobReplayZoneLife(ev[i].zone, ev[i].dir, ev[i].level, ev[i].bar_time, bt, bh, bl, bc, nb);
  }

//+------------------------------------------------------------------+
//| ZONE GEOMETRY layer (task 178) — lines only, NO text (the role     |
//| label + [Tn] live on the sequence dot, RedrawCurrentTF). For every |
//| active-cycle, ALIVE, valid zone fired on this chart TF:            |
//|   • L1 + L2 dashed lines from P2 (the broken swing) running right   |
//|     as a RAY (alive zones only — dead zones are DROPPED, not greyed)|
//|   • mid dotted 50% line + a left vertical connector L1<->L2.        |
//|   • InpShowPoints  -> P1 / P3 skeleton dots.                       |
//|   • InpShowRetests -> T1@L1 / T2@mid / T3@L2 touch dots.           |
//| Colour follows the event role (PBO blue / VR yellow / CF green).   |
//| DUAL-PURPOSE: the two events of one physical break carry identical  |
//| geometry; the object stem omits the role -> they collapse to ONE    |
//| idempotent band (last write wins, = the parent role, matching the   |
//| dot's bullet colour). Touches must be pre-stamped                  |
//| (UpdateZoneLifecycles). Invalid zones are NEVER drawn (no zone ->   |
//| no trade).                                                         |
//+------------------------------------------------------------------+
void CFobVisual::DrawZones(const FobEvent &ev[], const int n)
  {
   if(m_idx < 0 || !InpVisualize || !InpShowZones)
      return;
   int E = m_idx;

   //--- ACTIVE-CYCLE-ONLY (mirror RedrawCurrentTF PASS 1): only the latest seq
   //--- per setup TF is live; a superseded cycle's zones must NOT linger.
   int curSeq[FOB_N_TF];
   for(int z = 0; z < FOB_N_TF; z++) curSeq[z] = -1;
   for(int z = 0; z < n; z++)
      if(ev[z].label == FOB_PBO)
         curSeq[ev[z].setup_tf] = ev[z].seq;

   datetime tR0 = TimeCurrent() + PeriodSeconds((ENUM_TIMEFRAMES)ChartPeriod()) * 50;

   for(int i = 0; i < n; i++)
     {
      if(ev[i].event_tf != E)                  continue;
      if(!ev[i].zone.valid)                    continue;
      if(!ev[i].zone.alive)                    continue;   // dead -> dropped (no gray)
      if(ev[i].seq != curSeq[ev[i].setup_tf])  continue;   // active cycle only

      color  c    = FobLabelColor(ev[i].label);
      double l1   = ev[i].level;        // P2 price = trigger/entry edge
      double l2   = ev[i].zone.l2;      // extreme(P1,P3) = far/invalidation edge
      double mid  = ev[i].zone.mid;
      //--- label-LESS stem -> dual-purpose roles collapse to one shared band.
      string stem = FOB_VIS_PREFIX + "Z_" + (string)ev[i].swing_time + "_" + (string)ev[i].bar_time;

      datetime t0 = ev[i].swing_time;   // L1 origin (P2), band runs right as a ray
      datetime tR = tR0;
      if(tR <= t0) tR = t0 + PeriodSeconds((ENUM_TIMEFRAMES)ChartPeriod());

      //--- L1 / L2 dashed lines + mid dotted + left vertical connector
      Line(stem + "_L1",  t0, l1,  tR, l1,  c, STYLE_DASH, true, 2);
      Line(stem + "_L2",  t0, l2,  tR, l2,  c, STYLE_DASH, true, 2);
      Line(stem + "_mid", t0, mid, tR, mid, InpFobClrMid, STYLE_DOT, true, 1);
      Line(stem + "_LV",  t0, l1,  t0, l2,  c, STYLE_SOLID, false, 1);

      //--- P1 / P3 skeleton dots (own toggle)
      if(InpShowPoints)
        {
         Bullet(stem + "_p1", ev[i].zone.p1_time, ev[i].zone.p1_price, InpFobClrPoint);
         Label (stem + "_p1t", ev[i].zone.p1_time, ev[i].zone.p1_price, "p1  ", InpFobClrPoint, ANCHOR_RIGHT);
         Bullet(stem + "_p3", ev[i].zone.p3_time, ev[i].zone.p3_price, InpFobClrPoint);
         Label (stem + "_p3t", ev[i].zone.p3_time, ev[i].zone.p3_price, "p3  ", InpFobClrPoint, ANCHOR_RIGHT);
        }

      //--- retest touch dots (timing the label can't show): T1@L1, T2@mid, T3@L2
      if(InpShowRetests)
        {
         if(ev[i].zone.t1_time > 0) Bullet(stem + "_t1", ev[i].zone.t1_time, l1,  InpFobClrRetest);
         if(ev[i].zone.t2_time > 0) Bullet(stem + "_t2", ev[i].zone.t2_time, mid, InpFobClrRetest);
         if(ev[i].zone.t3_time > 0) Bullet(stem + "_t3", ev[i].zone.t3_time, l2,  InpFobClrRetest);
        }
     }
  }

#endif // FOB_VISUAL_MQH
