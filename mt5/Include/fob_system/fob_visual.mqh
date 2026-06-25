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
//|  ONE JOB PER DOT (task 2, 2026-06-25): a break is a PBO for its own  |
//|  TF and MAY also be a VR/CF for the TF above — but a dot shows ONLY  |
//|  ONE role, by precedence: if it serves an ACTIVE parent VR/CF it is  |
//|  drawn as THAT (the higher-TF setup is the live story); otherwise it |
//|  is drawn as its own PBO. So a setup spans two charts — its pbo on   |
//|  its own TF, its vr/cf on the TF below — joined by #id. No dual tag. |
//|                                                                    |
//|  Label grammar (E = this TF, E-1 = below, E+1 = above). DIR =        |
//|  thesis direction. A dot is exactly one of:                        |
//|    PBO E #p DIR · pending {E-1} VR   (own PBO, no VR yet)            |
//|    PBO E #p DIR                       (own PBO, VR locked)            |
//|    VR  {E+1} #q DIR                   (serves the TF-above setup)     |
//|    CF  {E+1} #q DIR                   (serves the TF-above setup)     |
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

//--- font sizes (hidden from inputs — tweak in source)
const int   InpFobBulletSize = 12;
const int   InpFobLabelSize  = 9;

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
   void     Label (const string name, const datetime t, const double p, const string txt, const color clr);

   bool     SameBreak(const FobEvent &a, const FobEvent &b) const
              { return a.event_tf == b.event_tf && a.bar_time == b.bar_time && a.swing_time == b.swing_time; }
   int      OppDir(const int d) const { return d == BRC_BULL ? BRC_BEAR : BRC_BULL; }

public:
            CFobVisual(void) { m_tf = ""; m_idx = -1; }

   void     SyncChartTF();
   void     ClearAll() { ObjectsDeleteAll(0, FOB_VIS_PREFIX); }

   //--- full rebuild of the current chart's lens from the event log
   void     RedrawCurrentTF(const FobEvent &ev[], const int n);
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

void CFobVisual::Label(const string name, const datetime t, const double p, const string txt, const color clr)
  {
   ObjectCreate(0, name, OBJ_TEXT, 0, t, p);
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
//| Full rebuild for the current chart TF.                            |
//|  PASS 1 (all events): reconstruct per-setup state from the log —   |
//|    the ACTIVE (latest) seq per TF and whether its VR is locked.     |
//|  PASS 2 (this-TF breaks only): merge each physical break's roles    |
//|    into one labelled dot, keep only the ACTIVE cycle, draw.         |
//+------------------------------------------------------------------+
void CFobVisual::RedrawCurrentTF(const FobEvent &ev[], const int n)
  {
   ClearAll();
   if(!InpVisualize || m_idx < 0)
      return;

   int E = m_idx;

   //--- PASS 1 : reconstruct state -----------------------------------
   int  curSeq[FOB_N_TF];
   bool vrLocked[FOB_N_TF];
   for(int i = 0; i < FOB_N_TF; i++) { curSeq[i] = -1; vrLocked[i] = false; }

   for(int i = 0; i < n; i++)
     {
      int s  = ev[i].setup_tf;
      int sq = ev[i].seq;
      if(ev[i].label == FOB_PBO)
        { curSeq[s] = sq; vrLocked[s] = false; }
      else if(ev[i].label == FOB_VR && sq == curSeq[s])
         vrLocked[s] = true;
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
         bool   hasPar = false; int parLab = -1, parSeq = -1, parDir = -1;

         for(int k = i; k < j; k++)
           {
            if(ev[k].label == FOB_PBO && ev[k].setup_tf == E)
              { pOwn = ev[k].seq; ownDir = ev[k].dir; }
            else if((ev[k].label == FOB_VR || ev[k].label == FOB_CF) && ev[k].setup_tf == E + 1)
              { hasPar = true; parLab = ev[k].label; parSeq = ev[k].seq; parDir = ev[k].dir; }
           }

         //--- ACTIVE-CYCLE-ONLY gate (task 157) + ONE-JOB-PER-DOT
         //--- precedence (task 2, 2026-06-25): if this break serves an
         //--- ACTIVE parent VR/CF, draw it as THAT role only; else draw it
         //--- as its own active PBO. No dual labels. (M1 has no own PBO —
         //--- task 1 — so the M1 chart shows only parent vr/cf dots.)
         bool parentQual = hasPar && (parSeq == curSeq[E + 1]);
         bool anchorQual = (pOwn >= 0 && pOwn == curSeq[E]);

         string txt = "";
         color  clr = clrNONE;

         if(parentQual)
           {
            //--- thesis dir: VR = OPP(break), CF = same-as(break)
            int parThesis = (parLab == FOB_VR) ? OppDir(parDir) : parDir;
            txt = StringFormat("  %s %s #%d %s",
                               FobLabelName(parLab), FobTfName(E + 1), parSeq, FobDirName(parThesis));
            clr = FobLabelColor(parLab);
           }
         else if(anchorQual)
           {
            txt = StringFormat("  PBO %s #%d %s", FobTfName(E), pOwn, FobDirName(ownDir));
            if(!vrLocked[E] && E > 0)   // "still forming" badge
               txt += StringFormat(" · pending %s VR", FobTfName(E - 1));
            clr = FobLabelColor(FOB_PBO);
           }

         if(clr != clrNONE)
           {
            StringToLower(txt);   // small-caps display (task 3, 2026-06-25)
            string base = FOB_VIS_PREFIX + (string)swt + "_" + (string)ev[i].bar_time;
            Bullet(base + "_b", swt, lvl, clr);
            Label (base + "_t", swt, lvl, txt, clr);
           }
        }
      i = j;
     }
  }

#endif // FOB_VISUAL_MQH
