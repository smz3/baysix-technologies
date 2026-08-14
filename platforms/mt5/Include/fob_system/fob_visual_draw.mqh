//+------------------------------------------------------------------+
//|                                              fob_visual_draw.mqh  |
//|  PART of fob_visual.mqh — out-of-line CFobVisual method bodies.    |
//|  DO NOT #include directly: no include guard by design; it is       |
//|  pulled in by fob_visual.mqh AFTER the class declaration.          |
//|                                                                    |
//|  Scope: the DRAWING core — LifecycleBadge text + the unified zone   |
//|  layer (DrawZones -> DrawZoneForBreak), the dimmed parent-PBO       |
//|  context overlay (DrawParentPbo), and own-structure (DrawStructure).|
//|  Consumes the state stamped by fob_visual_lifecycle.mqh.           |
//+------------------------------------------------------------------+

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
   //--- dim on FORMAL death only: a close beyond L2 invalidated the zone (z.alive
   //--- false), and its cycle is still active. Task-216's intrabar price-vs-L2 dim
   //--- was REVERTED (v1.30.1) — it re-checked price every tick, so a wick crossing
   //--- L2 back and forth made the band twitch. Invalidation is a CLOSE event; the
   //--- dim follows it. z.alive already carries close-based death (CSV stays pure).
   bool formalDead  = !ev[i].zone.alive;
   bool dimmed      = formalDead;
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
