//+------------------------------------------------------------------+
//|                                                    fob_visual.mqh  |
//|  FOB chart visualizer — ZONE-PRIMARY LENS (rewritten 2026-06-26).  |
//|                                                                    |
//|  Pure drawing, ZERO detection: the classifier owns all state; this |
//|  is a replayable PROJECTION of the event log. The picture can never |
//|  drift from the detector.                                          |
//|                                                                    |
//|  ONE CHART PER TIMEFRAME: a chart draws breaks that FIRED on its    |
//|  own TF (event_tf == ChartPeriod), on their NATIVE bars.           |
//|                                                                    |
//|  ONE UNIFIED ZONE LAYER (InpShowZones) — the old split of           |
//|  InpShowSequence (dots) vs InpShowZones (geometry) is GONE. Every   |
//|  active-cycle, ALIVE, VALID break is now drawn as a BRC-style band  |
//|  with all text OUTSIDE the box, on the L1/L2 edges:                 |
//|                                                                    |
//|    L1  <ROLE> <TF> #<id> <DIR>  <l1price>     ← above/below L1 line  |
//|   ┌ ── L1 ── ►                                                      |
//|   │ ·· mid ·· ►                                                     |
//|   └ ── L2 ── ►                                                      |
//|    L2  <ROLE> <TF> #<id> <DIR> [Tn] <l2price> ← below/above L2 line  |
//|                                                                    |
//|  PARENT-PRIMARY (task 2026-06-26): one physical break can be its    |
//|  OWN PBO (setup_tf E) and ALSO a VR/CF for the TF above (setup_tf    |
//|  E+1) — ONE shared band. When a parent role exists it is the        |
//|  PURPOSE, so the band lines + edge labels take the PARENT identity   |
//|  and colour (CF green / VR yellow, VR flips DIR). The own PBO is     |
//|  DEMOTED to a lowercase secondary fan pinned to the SAME L1/L2       |
//|  origin, rendering to the RIGHT (the primary fans LEFT) — two        |
//|  colours on one visual row, stable under zoom (MT5 caps one colour  |
//|  per text object, so a two-colour line = two objects pinned to one  |
//|  point). PBO-only breaks are all-blue, no fan; the lifecycle badge   |
//|  (pending/live {E-1} VR/CF) rides their L2 label.                   |
//|                                                                    |
//|  Visibility: ACTIVE CYCLE ONLY — a superseded cycle VOIDS and        |
//|  vanishes, unless it still has a LIVE open position (liveTf/liveSeq).|
//|  INVALIDATION (v1.17.0): a dead parent VR/CF is NOT dropped — it is   |
//|  RETAINED as a FADED role-colour "failed zone" (CF green / VR yellow),|
//|  drawn with the SAME full geometry as a live band (only the colour    |
//|  fades), until the cycle supersedes (then wiped). A dead PBO-only band |
//|  still drops; valid=false (no geometry) always drops.                |
//|                                                                    |
//|  Needs tester model = Visual Mode to paint live.                   |
//+------------------------------------------------------------------+
#ifndef FOB_VISUAL_MQH
#define FOB_VISUAL_MQH
#property strict

#include "fob_types.mqh"
#include "fob_lifecycle.mqh"   // FobReplayZoneLife — BRC-parity T-touch + invalidation

//--- master toggle (ACTIVE cycle only — no prior-cycle retention)
input bool InpVisualize    = true;        // MASTER: draw chart objects
//--- ONE unified zone layer (sequence + geometry merged, 2026-06-26)
input bool InpShowZones    = true;        // L1/L2 band + mid + edge labels (role text + [Tn])
input bool InpShowSwings   = false;       // FOB swing pivots (carets)
input bool InpShowRawBreaks= false;       // FOB raw breakouts
input bool InpShowPoints   = false;       // P1/P3 skeleton dots
input bool InpShowRetests  = true;        // T1/T2/T3 retest touch dots
input bool InpShowParentPBO= true;        // dimmed HTF parent (E+1) PBO zone — context overlay only

//--- font sizes (hidden from inputs — tweak in source)
const int   InpFobBulletSize = 12;
const int   InpFobLabelSize  = 8;

//--- structure-layer colours (mirror of BRC swings/breaks; tweak in source)
const color InpFobClrSwingHigh = clrTomato;
const color InpFobClrSwingLow  = clrDodgerBlue;
const color InpFobClrSwingDead = clrDimGray;
const color InpFobClrBreakBull = clrLimeGreen;
const color InpFobClrBreakBear = clrOrangeRed;
//--- zone accents (the band/label hue is the ROLE colour from FobLabelColor;
//--- these are the shared mid/retest/point accents). Dead zones are DROPPED.
const color InpFobClrMid       = clrDimGray;   // 50% line
const color InpFobClrRetest    = clrWhite;       // T1/T2/T3 touch dots
const color InpFobClrRT         = clrOrange;      // RT (broken-VR retouch / entry) dot
const color InpFobClrPoint     = clrSilver;      // P1/P3 skeleton dots
const color InpFobClrCfSell    = clrRed;         // CF whose thesis is SELL -> red band+label (CF BUY keeps the role green)

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
   //--- deepest RT MIRROR level reached on the return path: RT1=L2, RT2=mid, RT3=L1
   string   RtTag(const FobZone &z) const
              { return z.rt3_time>0 ? "RT3" : (z.rt2_time>0 ? "RT2" : (z.rt1_time>0 ? "RT1" : "RT0")); }
   bool     SameBreak(const FobEvent &a, const FobEvent &b) const
              { return a.event_tf == b.event_tf && a.bar_time == b.bar_time && a.swing_time == b.swing_time; }
   int      OppDir(const int d) const { return d == FOB_BULL ? FOB_BEAR : FOB_BULL; }
   //--- fade a colour toward black by factor f (0=black .. 1=unchanged) — the
   //--- "dimmed/failed zone" look: SAME role hue (CF green / VR yellow), lower
   //--- intensity. MQL5 packs colour as 0x00BBGGRR (low byte = R).
   color    DimColor(const color c, const double f) const
              { int r=(int)((double)( c        & 0xFF)*f);
                int g=(int)((double)((c >>  8) & 0xFF)*f);
                int b=(int)((double)((c >> 16) & 0xFF)*f);
                return (color)(r | (g << 8) | (b << 16)); }
   //--- (setup_tf, seq) cycle has a LIVE open position -> keep its band past supersession
   bool     IsLiveCycle(const int tf, const int seq, const int &ltf[], const int &lseq[], const int nl) const
              { for(int i = 0; i < nl; i++) if(ltf[i] == tf && lseq[i] == seq) return true; return false; }

   //--- outside-the-box anchor for an edge label.
   //---   edgeTop = is this edge the geometric TOP of the band? (bull L1 / bear L2)
   //---   fanLeft = render to the LEFT of the origin (primary) vs RIGHT (secondary)
   ENUM_ANCHOR_POINT EdgeAnchor(const bool edgeTop, const bool fanLeft) const
              { return fanLeft ? (edgeTop ? ANCHOR_RIGHT_LOWER : ANCHOR_RIGHT_UPPER)
                               : (edgeTop ? ANCHOR_LEFT_LOWER  : ANCHOR_LEFT_UPPER); }

   //--- price delta equal to `lines` rendered text rows, so a STACKED label sits
   //--- one row OUTSIDE the previous (vertical gap, NOT horizontal — keeps the
   //--- secondary in its own object so its role colour survives). Zoom-stable:
   //--- recomputed every redraw from the chart's price<->pixel scale (OnChartEvent
   //--- repaints). Both rows are left-anchored at the same x, so they can never
   //--- collide horizontally — worst case the vertical gap just breathes.
   double VertOffset(const int lines) const
     {
      long   hpx  = ChartGetInteger(0, CHART_HEIGHT_IN_PIXELS);
      double pmax = ChartGetDouble(0, CHART_PRICE_MAX);
      double pmin = ChartGetDouble(0, CHART_PRICE_MIN);
      double rowPx = (double)lines * (double)InpFobLabelSize * 1.6;        // row height + spacing
      if(hpx <= 0 || pmax <= pmin)
         return (double)lines * 100.0 * _Point;                           // fallback (~rough)
      return rowPx * (pmax - pmin) / (double)hpx;
     }

   //--- own-PBO lifecycle phase badge ("" for M1 / no own PBO).
   string   LifecycleBadge(const int E, const bool ownActive,
                           const bool vrLocked, const int cfCount) const;

   //--- PASS 1: reconstruct per-setup-TF state from the whole event log.
   void     ReconstructState(const FobEvent &ev[], const int n,
                             int &curSeq[], bool &vrLocked[], int &cfCount[]) const;
   //--- PASS 2 worker: resolve one physical break's roles, gate on active cycle,
   //--- draw its band + edge labels (parent-primary). [i,j) = the break's events.
   void     DrawZoneForBreak(const FobEvent &ev[], const int i, const int j, const int E,
                             const int &curSeq[], const bool &vrLocked[], const int &cfCount[],
                             const int &liveTf[], const int &liveSeq[], const int nLive,
                             const datetime tR0, const bool live, const double curPx);
   //--- CONTEXT overlay: the ACTIVE parent-TF (E+1) own-PBO zone, drawn dimmed +
   //--- dotted on THIS chart so a lower-TF execution shows where its HTF breakout
   //--- sits. Read-only projection (no touch/RT stamping, no cycle interaction) —
   //--- pure absolute-price geometry off the parent's PBO event row.
   void     DrawParentPbo(const FobEvent &ev[], const int n, const int E,
                          const int parSeq, const datetime tR0);

public:
            CFobVisual(void) { m_tf = ""; m_idx = -1; }

   void     SyncChartTF();
   int      ChartIdx() const { return m_idx; }   // chart TF ladder index (-1 if unmapped)
   void     ClearAll() { ObjectsDeleteAll(0, FOB_VIS_PREFIX); }

   //--- STAMP the retest ladder + alive/invalidation onto every event whose break
   //--- fired on THIS chart TF, recomputed STATELESSLY from the chart-TF OHLC
   //--- buffer (bt/bh/bl/bc, index 0 = OLDEST, length nb). Mutates `ev` (touch
   //--- fields only). MUST run BEFORE DrawZones so the labels carry [Tn] and the
   //--- geometry knows which zones are still alive.
   void     UpdateZoneLifecycles(FobEvent &ev[], const int n,
                                 const datetime &bt[], const double &bh[],
                                 const double &bl[], const double &bc[], const int nb);

   //--- LIVE intrabar touch: stamp T1/T2/T3 off the chart-TF FORMING bar so the
   //--- [Tn] label flips the instant a wick crosses, not only at bar close.
   //--- Touch-only (invalidation stays close-only). Call AFTER UpdateZoneLifecycles
   //--- and BEFORE DrawZones. Live-chart nicety — caller MUST tester-guard it.
   void     LiveTouchForming(FobEvent &ev[], const int n,
                             const datetime fbt, const double fbh, const double fbl);

   //--- LIVE-only, chart-TF, FILL-ONLY touch-ladder backfill (task 217). The causal
   //--- accumulator never saw pre-attach ticks, so historical zones read [T0]. This
   //--- fills only still-empty t1/t2/t3 off the chart-TF closed-bar wicks — never
   //--- resets, never touches counts/rt/invalidation, so it can't clobber the causal
   //--- lifecycle (unlike UpdateZoneLifecycles, which recomputes from scratch).
   void     BackfillChartLadder(FobEvent &ev[], const int n,
                                const datetime &bt[], const double &bh[],
                                const double &bl[], const int nb);

   //--- LIVE-only, chart-TF, FILL-ONLY RT-ladder backfill (task 219). Sibling of
   //--- BackfillChartLadder for the RETURN path: an invalidated VR whose RT (rt1/rt2/
   //--- rt3) never formed live (invalidated pre-attach) gets its mirror ladder filled
   //--- off the chart-TF closed-bar wicks AFTER invalidation_time. VR rows only; fills
   //--- only still-empty rt times — never resets, never touches T/counts/invalidation.
   void     BackfillChartRt(FobEvent &ev[], const int n,
                            const datetime &bt[], const double &bh[],
                            const double &bl[], const int nb);

   //--- cheap FNV-1a hash of the CURRENTLY-stamped chart-TF zone state (touch
   //--- ladder + alive/valid + count). The EA repaints ONLY when this changes —
   //--- a full ClearAll+redraw every tick is what makes the bands TWITCH. BRC
   //--- parity: it surgically updates a zone only when its touch actually advances.
   //--- INTRABAR-DEAD (v1.27.0, task 216) — LIVE visual only. Invalidation proper is
   //--- CLOSE-only (a W1 zone won't formally die until its weekly bar closes), so a
   //--- higher-TF zone price has ALREADY blown through still renders bright for days.
   //--- This mirrors the close-only kill (bull dies below L2, bear above) off the
   //--- CURRENT price so the band dims the instant price is beyond L2 — without ever
   //--- touching z.alive (that stays close-only, feeding a pristine CSV). px<=0 = no
   //--- price yet -> not dead.
   bool     IntrabarDead(const int dir, const double l2, const double px) const
              { return px > 0.0 && (dir == FOB_BULL ? (px < l2) : (px > l2)); }

   ulong    StateSignature(const FobEvent &ev[], const int n, const double curPx = 0.0) const
     {
      if(m_idx < 0)
         return 0;
      ulong h = 1469598103934665603ULL ^ (ulong)n;
      for(int i = 0; i < n; i++)
         if(ev[i].event_tf == m_idx)
           {
            h = (h ^ (ulong)ev[i].zone.t1_time) * 1099511628211ULL;
            h = (h ^ (ulong)ev[i].zone.t2_time) * 1099511628211ULL;
            h = (h ^ (ulong)ev[i].zone.t3_time) * 1099511628211ULL;
            h = (h ^ (ulong)ev[i].zone.rt1_time) * 1099511628211ULL;  // RT ladder flips repaint
            h = (h ^ (ulong)ev[i].zone.rt2_time) * 1099511628211ULL;
            h = (h ^ (ulong)ev[i].zone.rt3_time) * 1099511628211ULL;
            h = (h ^ (ulong)((ev[i].zone.alive ? 1 : 2) + (ev[i].zone.valid ? 4 : 8))) * 1099511628211ULL;
            //--- intrabar-dead flip must trigger a repaint too (else the dim only shows
            //--- on the NEXT unrelated state change) — hash it against the live price.
            bool vd = ev[i].zone.valid && ev[i].zone.alive
                      && IntrabarDead(ev[i].dir, ev[i].zone.l2, curPx);
            h = (h ^ (ulong)(vd ? 16 : 32)) * 1099511628211ULL;
           }
      return h;
     }

   //--- UNIFIED zone layer: ClearAll + draw every active-cycle, ALIVE, VALID band
   //--- (lines + edge labels + optional P1/P3 + retest dots) for the chart TF.
   //--- liveTf/liveSeq = (setup_tf, seq) cycles with an OPEN position: drawn even
   //--- when superseded, so a live trade keeps its band. Touches must already be
   //--- stamped (UpdateZoneLifecycles). Call BEFORE DrawStructure (it ClearAll's).
   void     DrawZones(const FobEvent &ev[], const int n,
                      const int &liveTf[], const int &liveSeq[], const int nLive,
                      const bool live = false, const double curPx = 0.0);
   //--- emitter overload (read-only, no positions -> no live cycles) that still
   //--- forwards the LIVE flag + current price for intrabar-dead dimming (task 216)
   void     DrawZones(const FobEvent &ev[], const int n, const bool live, const double curPx)
              { int empty[]; DrawZones(ev, n, empty, empty, 0, live, curPx); }
   //--- bare 2-arg overload (static redraw, no live price)
   void     DrawZones(const FobEvent &ev[], const int n)
              { int empty[]; DrawZones(ev, n, empty, empty, 0, false, 0.0); }

   //--- draw the chart TF's OWN detected structure (swing pivots + raw breakouts).
   //--- Call AFTER DrawZones (which ClearAll's first), with the chart-TF's own
   //--- g_tf[ChartIdx()] swing/break arrays.
   void     DrawStructure(const FobSwing &sw[], const FobBreak &br[]);
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
//| Own-PBO lifecycle badge (mirror of the old dot badge).            |
//|  ACTIVE cycle: pending {E-1} VR -> pending {E-1} CF -> live {E-1}  |
//|  CFc, advancing with cf_count. A retained-but-superseded live      |
//|  cycle gets a frozen "held" badge. M1 (E==0) has no own PBO -> "". |
//+------------------------------------------------------------------+
string CFobVisual::LifecycleBadge(const int E, const bool ownActive,
                                  const bool vrLocked, const int cfCount) const
  {
   if(E <= 0)        return "";                                     // M1 — no own PBO
   if(!ownActive)    return " · held (open trade)";                 // retained live cycle
   if(!vrLocked)     return " · pending " + FobTfName(E - 1) + " VR";
   if(cfCount == 0)  return " · pending " + FobTfName(E - 1) + " CF";
   return " · live " + FobTfName(E - 1) + " CF" + (string)cfCount;
  }

//+------------------------------------------------------------------+
//| PASS 1 — reconstruct each setup TF's ACTIVE (latest) seq, whether  |
//| its VR is locked, and how many CFs it has developed. A PBO resets   |
//| the cycle; VR/CF only advance the cycle they belong to.            |
//+------------------------------------------------------------------+
void CFobVisual::ReconstructState(const FobEvent &ev[], const int n,
                                  int &curSeq[], bool &vrLocked[], int &cfCount[]) const
  {
   for(int i = 0; i < FOB_N_TF; i++) { curSeq[i] = -1; vrLocked[i] = false; cfCount[i] = 0; }
   for(int i = 0; i < n; i++)
     {
      int s  = ev[i].setup_tf;
      int sq = ev[i].seq;
      if(ev[i].label == FOB_PBO)
        { curSeq[s] = sq; vrLocked[s] = false; cfCount[s] = 0; }
      else if(sq == curSeq[s])
        {
         if(ev[i].label == FOB_VR)                                   vrLocked[s] = true;
         else if(ev[i].label == FOB_CF && ev[i].cf_idx > cfCount[s]) cfCount[s] = ev[i].cf_idx;
        }
     }
  }

//+------------------------------------------------------------------+
//| Stamp the retest ladder + alive/invalidation onto every event      |
//| whose break fired on THIS chart TF (data only, no drawing).        |
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
         FobReplayZoneLife(ev[i].zone, ev[i].dir, ev[i].level, ev[i].bar_time, bt, bh, bl, bc, nb,
                           ev[i].label == FOB_VR);   // track RT (broken-L2 retouch) on VRs only
  }

//+------------------------------------------------------------------+
//| Fill-only touch-ladder backfill for the chart TF's zones (task     |
//| 217). Delegates to FobBackfillLadderTimes, which only fills empty  |
//| Tn — safe to call every redraw, safe alongside the live tick        |
//| accumulator (never resets, never touches counts/invalidation).     |
//+------------------------------------------------------------------+
void CFobVisual::BackfillChartLadder(FobEvent &ev[], const int n,
                                     const datetime &bt[], const double &bh[],
                                     const double &bl[], const int nb)
  {
   if(m_idx < 0)
      return;
   int E = m_idx;
   for(int i = 0; i < n; i++)
      if(ev[i].event_tf == E)
         FobBackfillLadderTimes(ev[i].zone, ev[i].dir, ev[i].level, ev[i].bar_time, bt, bh, bl, nb);
  }

//+------------------------------------------------------------------+
//| RT-ladder backfill wrapper (task 219): fill the mirror RT ladder   |
//| of every chart-TF, INVALIDATED VR off the chart-TF bars, so a       |
//| VR that invalidated pre-attach shows its [RTn] + dots at bar        |
//| resolution instead of a permanent [RT0]. VR rows only (RT is        |
//| stamped only on the VR, mirror of the accumulator's track_rt).      |
//+------------------------------------------------------------------+
void CFobVisual::BackfillChartRt(FobEvent &ev[], const int n,
                                 const datetime &bt[], const double &bh[],
                                 const double &bl[], const int nb)
  {
   if(m_idx < 0)
      return;
   int E = m_idx;
   for(int i = 0; i < n; i++)
      if(ev[i].event_tf == E && ev[i].label == FOB_VR)
         FobBackfillRtTimes(ev[i].zone, ev[i].dir, ev[i].level, ev[i].zone.invalidation_time, bt, bh, bl, nb);
  }

//+------------------------------------------------------------------+
//| LIVE intrabar touch pass — stamp T1/T2/T3 off the chart-TF FORMING |
//| bar (mirror of BRC's OnTick forming-bar pass). Runs AFTER the      |
//| closed-bar UpdateZoneLifecycles (which resets the ladder), so it    |
//| only fills a still-empty Tn from the live wick. Touch-only.        |
//+------------------------------------------------------------------+
void CFobVisual::LiveTouchForming(FobEvent &ev[], const int n,
                                  const datetime fbt, const double fbh, const double fbl)
  {
   if(m_idx < 0)
      return;
   int E = m_idx;
   for(int i = 0; i < n; i++)
      if(ev[i].event_tf == E)
         FobLiveTouch(ev[i].zone, ev[i].dir, ev[i].level, ev[i].bar_time, fbt, fbh, fbl,
                      ev[i].label == FOB_VR);       // live RT on VRs only (parity with closed-bar)
  }

//+------------------------------------------------------------------+
//| UNIFIED zone layer (one toggle, one path). ClearAll + reconstruct  |
//| state + draw one band per physical break that fired on this TF.    |
//+------------------------------------------------------------------+
void CFobVisual::DrawZones(const FobEvent &ev[], const int n,
                           const int &liveTf[], const int &liveSeq[], const int nLive,
                           const bool live, const double curPx)
  {
   ClearAll();
   if(!InpVisualize || m_idx < 0 || !InpShowZones)
      return;
   int E = m_idx;

   int  curSeq[FOB_N_TF]; bool vrLocked[FOB_N_TF]; int cfCount[FOB_N_TF];
   ReconstructState(ev, n, curSeq, vrLocked, cfCount);

   datetime tR0 = TimeCurrent() + PeriodSeconds((ENUM_TIMEFRAMES)ChartPeriod()) * 50;

   int i = 0;
   while(i < n)
     {
      int j = i + 1;
      while(j < n && SameBreak(ev[j], ev[i]))
         j++;
      if(ev[i].event_tf == E)
         DrawZoneForBreak(ev, i, j, E, curSeq, vrLocked, cfCount, liveTf, liveSeq, nLive, tR0, live, curPx);
      i = j;
     }

   //--- CONTEXT overlay: the ACTIVE parent-TF PBO zone (dimmed), so this chart
   //--- shows where the HTF breakout it lives inside sits. Off by toggle.
   if(InpShowParentPBO && E + 1 < FOB_N_TF && curSeq[E + 1] >= 0)
      DrawParentPbo(ev, n, E, curSeq[E + 1], tR0);
  }

//+------------------------------------------------------------------+
//| CONTEXT overlay — the ACTIVE parent-TF (E+1) own-PBO zone, faded  |
//| + dotted on this chart. The parent's PBO fires on parent bars     |
//| (event_tf == E+1); its L1/L2/mid are ABSOLUTE prices, so the band |
//| renders on any lower TF unchanged. Read-only: no touch/RT/cycle    |
//| logic — it can never perturb this chart's own detection.          |
//+------------------------------------------------------------------+
void CFobVisual::DrawParentPbo(const FobEvent &ev[], const int n, const int E,
                               const int parSeq, const datetime tR0)
  {
   int P = E + 1;                                   // parent TF ladder index
   for(int k = 0; k < n; k++)
     {
      //--- the parent's OWN PBO row for its ACTIVE cycle (fired on the parent TF)
      if(ev[k].event_tf != P || ev[k].label != FOB_PBO || ev[k].setup_tf != P)
         continue;
      if(ev[k].seq != parSeq || !ev[k].zone.valid)
         continue;

      int      bdir  = ev[k].dir;
      double   l1    = ev[k].level;                 // trigger/entry edge
      double   l2    = ev[k].zone.l2;               // far/invalidation edge
      double   mid   = ev[k].zone.mid;
      bool     l1Top = (bdir == FOB_BULL);
      bool     l2Top = (bdir == FOB_BEAR);
      datetime t0    = ev[k].swing_time;
      datetime tR    = (tR0 <= t0) ? t0 + PeriodSeconds((ENUM_TIMEFRAMES)ChartPeriod()) : tR0;

      color  clr  = DimColor(FobLabelColor(FOB_PBO), 0.50);   // parent context = faded PBO hue
      color  midC = DimColor(InpFobClrMid, 0.50);
      string id   = StringFormat("PBO %s #%d %s \x2022 context",
                                 FobTfName(P), parSeq, FobDirName(bdir));
      string stem = FOB_VIS_PREFIX + "PP_" + (string)ev[k].swing_time + "_" + (string)ev[k].bar_time;

      //--- DOTTED edges (own zones are DASHED) so parent context reads apart at a glance
      Line(stem + "_L1",  t0, l1,  tR, l1,  clr,  STYLE_DOT, true, 2);
      Line(stem + "_L2",  t0, l2,  tR, l2,  clr,  STYLE_DOT, true, 2);
      Line(stem + "_mid", t0, mid, tR, mid, midC, STYLE_DOT, true, 1);
      Line(stem + "_LV",  t0, l1,  t0, l2,  clr,  STYLE_SOLID, false, 1);

      ENUM_ANCHOR_POINT aL1 = EdgeAnchor(l1Top, false);
      ENUM_ANCHOR_POINT aL2 = EdgeAnchor(l2Top, false);
      Label(stem + "_L1p", t0, l1, "L1  " + id + "  " + DoubleToString(l1, _Digits), clr, aL1);
      Label(stem + "_L2p", t0, l2, "L2  " + id + "  " + DoubleToString(l2, _Digits), clr, aL2);
      return;                                        // one active parent PBO — done
     }
  }

//+------------------------------------------------------------------+
//| PASS 2 worker — one physical break: split into own PBO + optional  |
//| parent VR/CF, gate on the active cycle, then (if the band is VALID  |
//| and ALIVE) draw the lines + parent-primary edge labels.            |
//+------------------------------------------------------------------+
void CFobVisual::DrawZoneForBreak(const FobEvent &ev[], const int i, const int j, const int E,
                                  const int &curSeq[], const bool &vrLocked[], const int &cfCount[],
                                  const int &liveTf[], const int &liveSeq[], const int nLive,
                                  const datetime tR0, const bool live, const double curPx)
  {
   //--- split the group into own PBO (setup_tf E) + optional parent (setup_tf E+1)
   int  pOwn = -1, ownDir = -1;
   bool hasPar = false; int parLab = -1, parSeq = -1, parDir = -1, parCf = 0, parIdx = -1;
   for(int k = i; k < j; k++)
     {
      if(ev[k].label == FOB_PBO && ev[k].setup_tf == E)
        { pOwn = ev[k].seq; ownDir = ev[k].dir; }
      else if((ev[k].label == FOB_VR || ev[k].label == FOB_CF) && ev[k].setup_tf == E + 1)
        { hasPar = true; parLab = ev[k].label; parSeq = ev[k].seq; parDir = ev[k].dir; parCf = ev[k].cf_idx; parIdx = k; }
     }

   //--- ACTIVE-CYCLE-ONLY gate (per role): active cycle OR a superseded cycle
   //--- that still has a LIVE open position (don't wipe a cycle whose trade is on).
   bool parentQual = hasPar && (parSeq == curSeq[E + 1] || IsLiveCycle(E + 1, parSeq, liveTf, liveSeq, nLive));
   bool ownActive  = (pOwn >= 0 && pOwn == curSeq[E]);
   bool anchorQual = (pOwn >= 0 && (ownActive || IsLiveCycle(E, pOwn, liveTf, liveSeq, nLive)));
   if(!parentQual && !anchorQual)
      return;                                       // superseded -> vanish (clears dimmed corpses too)

   //--- valid=false => no zone geometry at all -> nothing to draw.
   if(!ev[i].zone.valid)
      return;

   //--- DIMMED-FAILURE retention (v1.17.1): an INVALIDATED VR/CF no longer
   //--- vanishes — it stays drawn in a FADED role colour (CF green / VR yellow),
   //--- full geometry (only the hue fades). This is the "failed zone" record a
   //--- break-of-VR/CF (RT) strategy reads off. SCOPE = parent VR/CF only; a dead
   //--- PBO-only band still drops (a PBO's death begins a fresh cycle). Cleanup
   //--- is automatic: when the cycle supersedes, the gate above wipes the corpse.
   //--- dim on FORMAL death (close beyond L2) OR, LIVE only, the instant price is
   //--- intrabar beyond L2 (task 216 — a higher-TF zone shouldn't stay bright for
   //--- days waiting for its bar to close). z.alive is untouched (CSV stays pure).
   //--- The WIPE decision stays keyed on FORMAL death only: an intrabar cross is
   //--- transient (price may return before close), so wiping a PBO-only band on it
   //--- would flicker — dim it instead, and let the formal close drive the wipe.
   bool formalDead  = !ev[i].zone.alive;
   bool dimmed      = formalDead
                      || (live && IntrabarDead(ev[i].dir, ev[i].zone.l2, curPx));
   bool dimEligible = parentQual && (parLab == FOB_VR || parLab == FOB_CF);
   if(formalDead && !dimEligible)
      return;                                       // PBO-only / non-parent death -> wipe

   //--- geometry (shared by every role of this physical break)
   int      bdir = ev[i].dir;                       // physical break dir -> anchoring/colours
   double   l1   = ev[i].level;                     // P2 = trigger/entry edge
   double   l2   = ev[i].zone.l2;                   // extreme(P1,P3) = far/invalidation edge
   double   mid  = ev[i].zone.mid;
   bool     l1Top = (bdir == FOB_BULL);             // bull: L1 is the TOP edge; bear: bottom
   bool     l2Top = (bdir == FOB_BEAR);
   string   tn   = " [" + TouchTag(ev[i].zone) + "]";
   //--- RT (VR-only): deepest MIRROR-ladder level reached rides the L2 label next to
   //--- [Tn]. [RT0] = invalidated, not yet returned; [RT1]=back to L2, [RT2]=mid,
   //--- [RT3]=full return to L1 (the break-and-retest depth).
   //--- NOTE: the RT ladder is stamped ONLY on the VR event row (track_rt=label==VR),
   //--- which is the PARENT row (ev[parIdx]) — NOT ev[i] (= the own-PBO row, ROLE 1,
   //--- appended first). Read RT off the parent VR zone or it is permanently [RT0]. (task 183)
   bool     isVR  = parentQual && (parLab == FOB_VR);
   string   rtTag = isVR ? (" [" + RtTag(ev[parIdx].zone) + "]") : "";

   datetime t0 = ev[i].swing_time;                  // L1 origin (P2); band runs right as a ray
   datetime tR = (tR0 <= t0) ? t0 + PeriodSeconds((ENUM_TIMEFRAMES)ChartPeriod()) : tR0;

   //--- PRIMARY role = parent (the PURPOSE) when present, else own PBO. The band
   //--- lines + edge labels take its identity + colour.
   color  priClr;
   string priId;                                    // role identity, reused on L1 + L2
   string l2extra = "";                             // PBO-only lifecycle badge rides L2
   if(parentQual)
     {
      int parThesis = (parLab == FOB_VR) ? OppDir(parDir) : parDir;   // VR=opp, CF=same
      if(parLab == FOB_CF)
         priId = StringFormat("%s%d %s #%d %s", FobLabelName(parLab), parCf, FobTfName(E + 1), parSeq, FobDirName(parThesis));
      else
         priId = StringFormat("%s %s #%d %s",    FobLabelName(parLab), FobTfName(E + 1), parSeq, FobDirName(parThesis));
      priClr = FobLabelColor(parLab);
      //--- CF direction tint: a SELL-thesis CF turns RED (band lines + edge labels,
      //--- both ride priClr); a BUY-thesis CF keeps the role green. VR untouched.
      if(parLab == FOB_CF && parThesis == FOB_BEAR) priClr = InpFobClrCfSell;
     }
   else
     {
      priId   = StringFormat("PBO %s #%d %s", FobTfName(E), pOwn, FobDirName(ownDir));
      l2extra = LifecycleBadge(E, ownActive, vrLocked[E], cfCount[E]);
      priClr  = FobLabelColor(FOB_PBO);
     }
   if(dimmed) priClr = DimColor(priClr, 0.45);      // failed VR/CF -> faded role hue

   string stem = FOB_VIS_PREFIX + "Z_" + (string)ev[i].swing_time + "_" + (string)ev[i].bar_time;

   //--- L1/L2 dashed rays + mid dotted + left vertical connector. A DIMMED dead
   //--- zone draws the SAME full-width geometry as a live one (ray right) — only
   //--- the colour fades, so it never looks half-drawn next to live zones.
   color midClr = dimmed ? DimColor(InpFobClrMid, 0.45) : InpFobClrMid;
   Line(stem + "_L1",  t0, l1,  tR, l1,  priClr, STYLE_DASH, true, 2);
   Line(stem + "_L2",  t0, l2,  tR, l2,  priClr, STYLE_DASH, true, 2);
   Line(stem + "_mid", t0, mid, tR, mid, midClr, STYLE_DOT, true, 1);
   Line(stem + "_LV",  t0, l1,  t0, l2,  priClr, STYLE_SOLID, false, 1);

   //--- PRIMARY edge labels (CAPS), anchored LEFT -> render RIGHT into the empty
   //--- ray area (off the candles). Anchor reused by the trailing secondary.
   ENUM_ANCHOR_POINT aL1 = EdgeAnchor(l1Top, false);
   ENUM_ANCHOR_POINT aL2 = EdgeAnchor(l2Top, false);
   string l1Txt = "L1  " + priId + "  " + DoubleToString(l1, _Digits);
   string l2Txt = "L2  " + priId + l2extra + tn + rtTag + "  " + DoubleToString(l2, _Digits);
   Label(stem + "_L1p", t0, l1, l1Txt, priClr, aL1);
   Label(stem + "_L2p", t0, l2, l2Txt, priClr, aL2);

   //--- SECONDARY (own PBO local view): CAPS, demoted, only when a parent is
   //--- primary AND the own PBO is itself active/held. Kept in its OWN blue object so
   //--- the role colour survives; STACKED one row OUTSIDE the L1 primary (above for a
   //--- bull top-edge, below for a bear bottom-edge), same x. Both PBO bits — the id
   //--- and the lifecycle badge — share this single blue row; L2 carries no secondary.
   if(parentQual && anchorQual)
     {
      color  subClr = dimmed ? DimColor(FobLabelColor(FOB_PBO), 0.45) : FobLabelColor(FOB_PBO);
      string sub    = "pbo " + FobTfName(E) + " #" + (string)pOwn;
      string badge  = LifecycleBadge(E, ownActive, vrLocked[E], cfCount[E]);  // already " · ..."
      if(StringLen(badge) > 0) sub += badge;
      StringToUpper(sub);
      double l1sP = l1 + (l1Top ? 1.0 : -1.0) * VertOffset(1);
      Label(stem + "_L1s", t0, l1sP, sub, subClr, aL1);
     }

   //--- P1 / P3 skeleton dots (own toggle)
   if(InpShowPoints)
     {
      color ptClr = dimmed ? DimColor(InpFobClrPoint, 0.55) : InpFobClrPoint;
      Bullet(stem + "_p1", ev[i].zone.p1_time, ev[i].zone.p1_price, ptClr);
      Label (stem + "_p1t", ev[i].zone.p1_time, ev[i].zone.p1_price, "p1  ", ptClr, ANCHOR_RIGHT);
      Bullet(stem + "_p3", ev[i].zone.p3_time, ev[i].zone.p3_price, ptClr);
      Label (stem + "_p3t", ev[i].zone.p3_time, ev[i].zone.p3_price, "p3  ", ptClr, ANCHOR_RIGHT);
     }

   //--- retest touch dots (timing the label can't show): T1@L1, T2@mid, T3@L2
   if(InpShowRetests)
     {
      color rtClr = dimmed ? DimColor(InpFobClrRetest, 0.55) : InpFobClrRetest;
      if(ev[i].zone.t1_time > 0) Bullet(stem + "_t1", ev[i].zone.t1_time, l1,  rtClr);
      if(ev[i].zone.t2_time > 0) Bullet(stem + "_t2", ev[i].zone.t2_time, mid, rtClr);
      if(ev[i].zone.t3_time > 0) Bullet(stem + "_t3", ev[i].zone.t3_time, l2,  rtClr);
      //--- RT MIRROR-ladder dots (VR-only): RT1@L2, RT2@mid, RT3@L1 — the return path
      //--- after invalidation, in a distinct hue so they read apart from the white T-dots.
      if(isVR)
        {
         if(ev[parIdx].zone.rt1_time > 0) Bullet(stem + "_rt1", ev[parIdx].zone.rt1_time, l2,  InpFobClrRT);
         if(ev[parIdx].zone.rt2_time > 0) Bullet(stem + "_rt2", ev[parIdx].zone.rt2_time, mid, InpFobClrRT);
         if(ev[parIdx].zone.rt3_time > 0) Bullet(stem + "_rt3", ev[parIdx].zone.rt3_time, l1,  InpFobClrRT);
        }
     }
  }

//+------------------------------------------------------------------+
//| Draw the chart TF's OWN detected structure (FOB detection output). |
//|  Faithful mirror of BRC's swing/break visuals:                     |
//|    • SWING -> "•" bullet at the pivot + "High/Low <price>" label.   |
//|    • BREAK -> "•" bullet at the BROKEN swing + "Bob/Bos <swing>     |
//|              (<close>)" label, anchored RIGHT.                      |
//|  FOB_-prefixed so DrawZones()->ClearAll() wipes + repaints.        |
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

#endif // FOB_VISUAL_MQH
