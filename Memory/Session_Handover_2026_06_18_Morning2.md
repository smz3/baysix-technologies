# Handover — June 18, 2026 Morning2

## State (BRC-001 emitter — task 118 build complete, never run)
- **Instant per-tick T-touch FIXED + pushed** (task 123, done). The open P1 bug from the Afternoon handover is closed.
  - New [BrcLiveTouch](mt5/Include/brc_system/brc_lifecycle.mqh#L104): on every tick, stamps t1/t2/t3 off each TF's FORMING bar so `[Tn]` flips the instant price wicks a level. Mirrors B2B (touches=tick; invalidation/continuation/bars_alive stay CLOSE-only).
  - Wired in [OnTick](mt5/Experts/brc_system/brc_baysix.mq5#L184) — live pass over all 8 TFs after the closed-bar ingest. **Data-neutral for the CSV**: forming high/low only grow, so a wick-crossed level is also crossed by that bar's close → touch lands on the SAME bar either way. Open-prices tester = no spurious touches. Compiles 0/0.
- **Visual inputs curated + pushed** (task 121, done): colours + bullet/label font sizes → `const` (hidden from inputs); `InpBrcShowSwings/Breaks/Points/Invalid` default **false**. Input window now shows only master/zones/mid/retests/maxzones.
- **Task 122 (B2B parity) DONE**: detection (forward-scan port a1ccce0) + drawing (levels confirmed matching) + touch (death-bar 9638ed2 + instant per-tick) all landed.
- **Still NO trade logic** — emitter is a pure observational ledger (zones + T-touches + outcomes in R). Correct for this stage.

## Decisions locked this session (discussion only)
- **Run plan: smoke (1yr IS) → green-light → full IS-only → freeze config → OOS pass.** Physical OOS lockout (don't emit OOS until IS config frozen — researcher-peek is the leak, not the observer).
- **IS = 2016-01→2024-06, OOS = 2024-07→2026-06** (recent monster-vol = deployment regime). Report regime-conditional WITHIN IS too (IS calm / OOS wild mismatch risk).
- **One M5-base run emits all 8 TFs** to one CSV (`tf` column) — do NOT run 8 times. Dukascopy gives deep M5→MN1, so no history-depth split needed.
- **Research order: single-TF atom FIRST (task 110), then nesting/russian-doll (task 120).** Atom unproven = nesting unattributable. ⚠️ prior strike: MSM-001 `confluence_2tf_agree_t = -2.1951` (cross-TF agreement already tested negative).

## Next
1. **Task 124 (smoke):** run brc_baysix in MT5 tester on the **Dukascopy custom symbol** (NOT JM live XAUUSD — shallow M5) over a 1yr IS year (2022/2023). Then run task-119 ingest → confirm rows/schema in `research.db` tester_zones. End-to-end green-light gate.
2. **Task 125 (full IS):** after green-light, one M5-base run 2016-01→2024-06.
3. **Task 127:** decide ConsolidateOverlappingZones (strict-1:1 dedup vs keep-all for funnel) before calling parity fully closed.

## Blockers
None. Task 126 (OOS) is intentionally BLOCKED until IS config frozen (is_discipline_guards).

## Notes
- [brc_visual.mqh](mt5/Include/brc_system/brc_visual.mqh) `InpVisualize=true` committed this session (was a local-only toggle before) — flip OFF in inputs for the headless emit runs.
- Compile workflow unchanged — [[brc_compile_workflow]] (MetaEditor64 CLI, `/inc`=`mt5/`, log UTF-16, delete after).
