# Handover — June 18, 2026 Afternoon

## State (task 122 — BRC↔B2B zone parity)
- **Levels now MATCH B2B on the live chart (Syafiq confirmed "working").** Rewrote BRC detection to a 1:1 port of Sigma's `CB2BDetector::DetectB2B_5Pointer` (forward scan). Commit **a1ccce0**.
  - FORWARD selection: P2 = first opposite-swing AFTER P1, P3 = first same-type AFTER P2 (was backward "last-before").
  - **Dropped the `P3<P1` gate** → `L2 = extreme(P1,P3)` (may now resolve to P3, not always P1) — matches [CreateZoneFrom5Pointer](mt5/Include/Sigma_System/V5.0/Detection/B2BDetector.mqh#L395).
  - Newest-P1 winner per P5; B2B freshness gate (no swing strictly in P3..P4) now a real reject; `IsSwingUsedInZones` (alive same-dir only) + duplicate `(dir,L1,L2)` dedup.
  - Why safe (Syafiq's call): event-driven tester swing buffer only holds swings confirmed up to the current bar → forward scan carries NO look-ahead (the Python vectorized scan was the only leak). This is why we went straight to MT5, not Python.
  - Files: [brc_zones.mqh](mt5/Include/brc_system/brc_zones.mqh) (rewritten), [brc_types.mqh](mt5/Include/brc_system/brc_types.mqh) (comments), [brc_baysix.mq5](mt5/Experts/brc_system/brc_baysix.mq5) (call passes `s.zones`). Compiles 0/0.
- **Death-bar touch fix** (commit **9638ed2**): retest ladder was gated `if(!dead)`, so a zone wicking L1 on the same bar it closed beyond L2 logged T0. B2B stamps touches BEFORE invalidation. Removed the guard in [brc_lifecycle.mqh](mt5/Include/brc_system/brc_lifecycle.mqh) (kept it on `continued`). **This was NOT the symptom Syafiq meant** (see Open Bug) but is a correct parity fix.

## Open Bug (P1) — T-touches don't update on live ticks
- **Symptom:** on the live chart, price visibly touches a BRC zone level but the `[Tn]` label does NOT update instantly — only when the bar closes.
- **Root cause:** the emitter is **close-only by design** — [OnTick](mt5/Experts/brc_system/brc_baysix.mq5#L163) does `CopyRates(..., 1, 64, r)` (index 1 = last CLOSED bar) and `BrcAdvanceZone` runs per closed bar using that bar's high/low. The forming bar (index 0) is never evaluated, so a wick touch on the current bar isn't seen until it closes.
- **B2B does it per-tick:** [UpdateZoneStatusInBuffer](mt5/Include/Sigma_System/V5.0/Detection/B2BZoneStatus.mqh#L211) detects touches every tick off `current_high/current_low`; only INVALIDATION is bar-close-gated.
- **Fix direction for next agent:** add an intrabar/live touch pass — on each tick, evaluate the FORMING bar's running high/low (or the tick bid) against alive zones' L1/mid/L2 and update `t1/t2/t3_time` + the visual, WHILE keeping detection + invalidation close-only (don't let a forming-bar wick invalidate). Essentially mirror B2B: touches=tick, invalidation=bar-close. Keep it visual/lifecycle only; the CSV emit semantics for the 10yr run stay close-only (tester is "Open prices only" anyway, so this is a LIVE-chart eyeball nicety — confirm whether Syafiq wants it in the emitted ledger too).

## Deferred (decide before "done")
- **`ConsolidateOverlappingZones`** (50%-overlap → keep biggest, [B2BZoneManager.mqh:230](mt5/Include/Sigma_System/V5.0/Detection/B2BZoneManager.mqh#L230)) — the last B2B dedup BRC lacks. NOT added because it DELETES zones, thinning the task-120 funnel dataset. Decision: add for strict 1:1, or treat as a downstream Python filter and keep all zones.

## Notes
- [brc_visual.mqh](mt5/Include/brc_system/brc_visual.mqh) has **uncommitted local test toggles** (`InpVisualize=true`, label size 8) — left deliberately so the chart draws; do not commit.
- Compile workflow unchanged — see [[brc_compile_workflow]] (MetaEditor64 CLI, `/inc`=`mt5/`, log UTF-16, delete after).
- Context hit 168k (hard threshold) → handover written directly, not via /handover skill.
