# Handover — June 27, 2026 Morning

## State
- **FOB visual layer now v1.18.3** (was v1.18.1). 2 commits pushed: `300a9d1` (RT row-read fix v1.18.2), `00b73bd` (CF direction tint v1.18.3). Both EAs compile clean (0 errors; only the benign warning-68 MQL5-Market version-format note).
- **Task 183 RESOLVED** — the universal `[RT0]`-stuck bug. Root cause was NOT the L1-vs-L2 probe Syafiq suspected: the `[RTn]` label + orange dot read `rt_count`/`rt_time` off `ev[i]` = the own-**PBO** row (ROLE 1, appended first), but RT is only computed where `label==FOB_VR` = the **parent** row. Fix: capture `parIdx` in the parent loop, read `ev[parIdx].zone` ([fob_visual.mqh:446,531](mt5/Include/fob_system/fob_visual.mqh#L446)).
- **CF direction tint (v1.18.3)** — a SELL-thesis CF (`parThesis==FOB_BEAR`) draws `priClr=clrRed` → tints band lines AND edge labels (both ride `priClr`). BUY CF keeps role green; VR untouched. New `InpFobClrCfSell` ([fob_visual.mqh:77](mt5/Include/fob_system/fob_visual.mqh#L77)).
- **Version drift cleared** — `#property version` on both `.mq5` was stale at 1.16.2; now synced to `FOB_VERSION` (1.18.3).
- **KNOWN RESIDUAL (task 184, P2):** D1 broken-VR RT dot still not firing on the rebuilt EA, though the same retouch fires on M30. Deferred — see Live-Threads.

## Next
1. **(strategy fork — Syafiq's call)** Session ended pivoting OFF FOB visual polish onto actual strategy. Open P1 lines to choose from: **RT VR entry** (task 181 → stat study 182, but gated on task 184 D1 fix), **FOB exit/TP asymmetry — THE LEVER** (task 167), or **FOB trader SL→zone.l2 + opposite-PBO close** (task 179).
2. **(task 184, P2)** FIX D1 RT not firing (fires on M30) — chase the higher-TF live forming-bar / `z.alive` gate. DO before any VR-RT entry testing (181/182).
3. **(task 182, P1)** RT stat study: export `rt_count/rt_time` → emitter CSV → tester_zones, measure RT-entry edge vs CF by setup-TF.

## Blockers
- **GitHub push needs the new cached token** — GCM token had expired; Syafiq created a classic PAT (repo scope) and pushed once from his own VS Code terminal → token now cached, auto-push works again. Sandbox bash still cannot pop the GCM dialog, so if the cache clears, push from his terminal.

## Why
- **CF tint = Syafiq's request for at-a-glance directional read** — red SELL / green BUY on the CF band+label, so the chart's directional bias reads without parsing text. Driven off the CF *thesis* (`parThesis`, CF=same dir), not the raw break dir.
- **183 was a wiring bug, not a logic bug** — the retouch DETECTION (L1-vs-L2, armed/hysteresis) was correct all along; only the row the label *read from* was wrong. `[Tn]` worked because the T-ladder is recomputed for EVERY row (PBO row coincides); RT is the only field gated VR-rows-only, so it was the only one that broke.
- **The D1-vs-M30 asymmetry Syafiq saw yesterday is a SYMPTOM of 183, not separate** — the old code read `ev[i]`; whether that's PBO or VR depends on whether the PBO-newest gate suppressed the PBO for that break. M30 VR happened to have ev[i]=VR (worked); D1 VR had a PBO row ahead (broke). Same bug, intermittent.
- **Version `#property` is cosmetic (MT5 UI only)** — runtime uses the `FOB_VERSION` `#define` everywhere; the stale 1.16.2 stamp was harmless drift, fixed for provenance hygiene.

## Ruled-Out
- **Syafiq's L1-vs-L2 live-probe hunch for 183 — DISPROVEN.** Both closed-replay and live paths correctly reference `z.l2`; the levels were never the issue. Don't re-investigate the probe direction.
- **183 fix as a complete RT cure — NO.** The `parIdx` fix resolved the *universal* `[RT0]`, but D1 specifically still misses on the live rebuild (task 184). So the row-read bug was real and fixed, but there is a *second* D1-specific cause underneath.

## Live-Threads
- **Task 184 (the open thread): D1 VR RT still dead post-fix.** Leading hypothesis — the D1 retouch lands intrabar on the still-FORMING daily bar, so (a) the closed replay misses it (no closed D1 bar wicked L2 yet) AND (b) the live RT block in `FobLiveTouch` is skipped because it requires `!z.alive`, and/or `OnChartEvent` (TF-switch) runs no forming pass. M30 works because the same calendar retouch spans CLOSED M30 bars. Repro on Syafiq's exact D1 VR before touching code. DEFERRED until VR-setup testing begins.
- **Strategy direction unconfirmed.** Syafiq explicitly wants to leave FOB visual polish and "focus on the actual strategies" — but the specific next line (RT VR vs B2B revive vs FOB exit-asymmetry 167) was not locked before handover. Confirm priority at session start.
- **`/handover` filename snippet still scans only `memory/` root, not `_handover_archive/`** (carried from prior sessions, still unticketed minor).
