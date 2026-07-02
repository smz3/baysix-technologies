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
//| OUT-OF-LINE method bodies, split by concern (2026-07-02). MQL5 has  |
//| no partial classes, but method bodies may live in separate files    |
//| as long as they compile AFTER this declaration. These parts carry   |
//| NO include guard and MUST be pulled in only here — never directly.  |
//+------------------------------------------------------------------+
#include "fob_visual_prims.mqh"       // LadderIndex/SyncChartTF + Bullet/Label/Line
#include "fob_visual_lifecycle.mqh"   // ReconstructState + touch/RT stampers (data only)
#include "fob_visual_draw.mqh"        // LifecycleBadge + DrawZones/ParentPbo/ZoneForBreak/Structure

#endif // FOB_VISUAL_MQH
