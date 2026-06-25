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
//|  TF projection). Every break is a PBO for its own TF and MAY also   |
//|  be a VR/CF for the TF one above — both roles on one dot. The #id   |
//|  is the cross-chart link: "VR H1 #1" on the M30 chart <-> "PBO H1   |
//|  #1" on the H1 chart.                                              |
//|                                                                    |
//|  Label grammar (E = this TF, E-1 = TF below = VR source, E+1 =      |
//|  TF above = the setup this break serves). DIR = thesis direction:  |
//|    A  PBO E #p DIR · pending {E-1} VR      (forming, no VR yet)      |
//|    B  PBO E #p DIR                          (VR locked = confirmed)  |
//|    C  PBO E #p DIRe  |  VR  {E+1} #q DIRp   (also parent retrace)    |
//|    D  PBO E #p DIRe  |  CF  {E+1} #q DIRp   (also parent confirm)    |
//|  DIR for a parent role is DERIVED from the break: VR = OPP(break),   |
//|  CF = same-as(break) — no parent-state lookup needed.              |
//|                                                                    |
//|  Colour: PBO blue / VR purple / CF green. A dual dot is coloured by |
//|  its PARENT role (the "interesting" one); PBO identity is in text.  |
//|                                                                    |
//|  Visibility: hide superseded bare PBOs. Show (1) the latest forming |
//|  PBO of this TF, (2) the last InpFobMaxChains DEVELOPED setups of   |
//|  this TF, (3) parent VR/CF dots within the last InpFobMaxChains     |
//|  developed setups of the TF above.                                 |
//|                                                                    |
//|  Needs tester model = Visual Mode to paint live.                   |
//+------------------------------------------------------------------+
#ifndef FOB_VISUAL_MQH
#define FOB_VISUAL_MQH
#property strict

#include "fob_types.mqh"

//--- master toggle + rolling cap (developed setups kept per TF lens)
input bool InpVisualize    = true;        // MASTER: draw chart objects
input int  InpFobMaxChains = 2;           // developed setups kept per TF (current + N-1 prior)

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
   bool     SeqIn(const int &arr[], const int cnt, const int sq) const;
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
bool CFobVisual::SeqIn(const int &arr[], const int cnt, const int sq) const
  {
   for(int i = 0; i < cnt; i++)
      if(arr[i] == sq)
         return true;
   return false;
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
//|    latest seq, whether its VR locked, and the list of DEVELOPED     |
//|    (VR-reached) seqs for THIS TF (E) and the TF above (E+1).        |
//|  PASS 2 (this-TF breaks only): merge each physical break's roles    |
//|    into one labelled dot, apply visibility, draw.                   |
//+------------------------------------------------------------------+
void CFobVisual::RedrawCurrentTF(const FobEvent &ev[], const int n)
  {
   ClearAll();
   if(!InpVisualize || m_idx < 0)
      return;

   int E   = m_idx;
   int cap = (InpFobMaxChains > 0) ? InpFobMaxChains : 1;

   //--- PASS 1 : reconstruct state -----------------------------------
   int  curSeq[FOB_N_TF];
   bool vrLocked[FOB_N_TF];
   for(int i = 0; i < FOB_N_TF; i++) { curSeq[i] = -1; vrLocked[i] = false; }

   int devE[];  int devECnt = 0;     // developed seqs on this TF (E)
   int devP[];  int devPCnt = 0;     // developed seqs on the TF above (E+1)

   for(int i = 0; i < n; i++)
     {
      int s  = ev[i].setup_tf;
      int sq = ev[i].seq;
      if(ev[i].label == FOB_PBO)
        { curSeq[s] = sq; vrLocked[s] = false; }
      else if(ev[i].label == FOB_VR)
        {
         if(sq == curSeq[s])
            vrLocked[s] = true;
         if(s == E)     { ArrayResize(devE, devECnt + 1); devE[devECnt++] = sq; }
         if(s == E + 1) { ArrayResize(devP, devPCnt + 1); devP[devPCnt++] = sq; }
        }
     }

   //--- rolling-cap thresholds (keep the last `cap` developed setups) -
   int keepE = (devECnt > cap) ? devE[devECnt - cap] : (devECnt > 0 ? devE[0] : 2147483647);
   int keepP = (devPCnt > cap) ? devP[devPCnt - cap] : (devPCnt > 0 ? devP[0] : 2147483647);

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

         if(pOwn >= 0)
           {
            bool ownDeveloped  = SeqIn(devE, devECnt, pOwn);
            bool latestPending = (pOwn == curSeq[E] && !vrLocked[E]);

            bool anchorQual = latestPending || (ownDeveloped && pOwn >= keepE);
            bool parentQual = hasPar && SeqIn(devP, devPCnt, parSeq) && parSeq >= keepP;

            if(anchorQual || parentQual)
              {
               //--- thesis dirs: own = break dir; parent = VR->OPP, CF->same
               int parThesis = hasPar ? ((parLab == FOB_VR) ? OppDir(parDir) : parDir) : -1;

               string txt = StringFormat("  PBO %s #%d %s",
                                         FobTfName(E), pOwn, FobDirName(ownDir));
               if(!ownDeveloped && E > 0)            // consistent "still forming" badge
                  txt += StringFormat(" · pending %s VR", FobTfName(E - 1));
               if(hasPar)
                  txt += StringFormat("  |  %s %s #%d %s",
                                      FobLabelName(parLab), FobTfName(E + 1), parSeq, FobDirName(parThesis));

               color clr = hasPar ? FobLabelColor(parLab) : FobLabelColor(FOB_PBO);

               string base = FOB_VIS_PREFIX + (string)swt + "_" + (string)ev[i].bar_time;
               Bullet(base + "_b", swt, lvl, clr);
               Label (base + "_t", swt, lvl, txt, clr);
              }
           }
        }
      i = j;
     }
  }

#endif // FOB_VISUAL_MQH
