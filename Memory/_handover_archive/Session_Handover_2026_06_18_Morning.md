# Handover — June 18, 2026 Morning

## State
- **`brc_baysix` compiles clean (0/0) WITH the visualizer wired.** I now own MT5 compilation — headless MetaEditor64 CLI; `/inc` MUST be `mt5/` (the MQL5 root containing `Include/`), NOT `mt5/Include` (else error-106 cascade). Log is UTF-16. See [[brc_compile_workflow]].
- **`brc_visual.mqh` built + rewritten Sigma-style this session** ([brc_visual.mqh](mt5/Include/brc_system/brc_visual.mqh), wired into [brc_baysix.mq5](mt5/Experts/brc_system/brc_baysix.mq5)). Master `InpVisualize` (default OFF) + per-layer toggles. Current-chart-TF gating (switch period → `OnChartEvent` rebuilds); rolling FIFO cap `InpBrcMaxZones`.
- **Validated on the strategy tester this session:**
  - ✅ **Layer 1 swings** — correct (Syafiq confirmed).
  - ✅ **Layer 2 raw breakouts** — were dropping same-bar multi-breaks; FIXED by keying break objects on `swing_time`+`bar_time` (a swing breaks once). Re-run to confirm all show.
  - ❌ **Layer 3 BRC zones** — Syafiq says "currently wrong" vs live Sigma B2B. Needs parity work → **task 122**.
- **Three bugs fixed + pushed this session:** (1) killed the filled red/gray rectangle "band" — zones now draw Sigma-style (L1/L2 dashed + 50% dotted + left vertical + `[Tn]` labels), (2) unicode glyphs (`▾▴✕`) rendered as `?` in the tester font → now ASCII + `•` only, (3) breakout same-bar collision, (4) visuals lingered on EA detach → `OnDeinit` now `g_vis.ClearAll()`.

## Next
1. **TASK 122 (P1) — BRC↔B2B zone parity.** Next agent MUST first read all 5 Sigma detection modules (now in this session's context, but re-read fresh): [B2BDetector.mqh](mt5/Include/Sigma_System/V5.0/Detection/B2BDetector.mqh) · [B2BZoneManager.mqh](mt5/Include/Sigma_System/V5.0/Detection/B2BZoneManager.mqh) · [B2BZoneStatus.mqh](mt5/Include/Sigma_System/V5.0/Detection/B2BZoneStatus.mqh) · [B2BConfluence.mqh](mt5/Include/Sigma_System/V5.0/Detection/B2BConfluence.mqh) · [B2BTradeTracker.mqh](mt5/Include/Sigma_System/V5.0/Detection/B2BTradeTracker.mqh). Full divergence notes in the task detail.
2. **Pin the zone symptom** (couldn't this session): wrong levels? wrong P1–P5 placement? too many/few? bad line span? — drives the fix.
3. **Then** the original chain: Phase-3 fidelity-diff EA-D1 vs Python `detect_zones('D1')` → 10-yr emit run → ingest (task 119) → Python L2 funnel (task 120).

## Divergences already spotted (BRC [brc_zones.mqh](mt5/Include/brc_system/brc_zones.mqh) vs B2B doctrine)
- **Detection is spec-faithful** on geometry/levels/invalidation. The ONLY designed difference is forward-vs-backward freshness (the documented oracle delta the fidelity-diff measures) — likely NOT the "wrong".
- **P2:** B2B = FIRST low after P1; BRC = LAST low before P3 (differ only on non-alternating swings).
- **P3:** B2B = FIRST high after P2 **+ strict no-swing-between-P3↔P4 REJECT**; BRC = last-swing-before-P4 (reconstructs a fresher P3 instead of rejecting).
- **B2B has, BRC lacks:** winner-per-P5 dedup across multiple candidates, `IsSwingUsedInZones` cross-zone swing exclusivity, `ConsolidateOverlappingZones` (50% overlap → keep biggest). These could explain a count/duplication mismatch.
- **Retest ladder:** B2B is ORDER-GATED (50% only after L1, L2 only after 50%) — BRC lifecycle is also gated; verify it matches.
- **Drawing:** brc_visual already mirrors Sigma `DrawB2BZone` (L1/L2 dashed RAY + 50% dot + left vertical + L2 label `[Tn]`).

## Blockers
None. All code compiles clean. Zone "wrong" symptom not yet pinned (needs Syafiq's eyes on the chart). Context hit the 145k hard threshold → this handover written directly (not via /handover skill) to beat auto-compact.
