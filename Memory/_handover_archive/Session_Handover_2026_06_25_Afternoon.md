# Handover — June 25, 2026 Afternoon

## State (FOB-001 visuals + cycle-model clarified; G1 still open)

**This session was visuals-first, then turned into a detector-model correction. Code compiles 0 err throughout. FOB_VERSION 0.2.1 → 0.4.0. NOT committed-with-eyeball yet — Syafiq never did the Visual-Mode eyeball pass.**

### Shipped + compiling (0 err headless)
1. **BUY/SELL on labels (v0.2.2):** thesis direction stamped on every role. `m_pboDir[]` cache + `FobDirName()` (BULL→BUY/BEAR→SELL). Decision (a) thesis: VR/CF carry the PBO's direction, NOT the break's own.
2. **HRCF removed from classifier (v0.3.0):** core now PBO→VR→CF (2-TF pair). `cf_done`/`hrcf_done`… `hrcf_done` field dropped; `FOB_HRCF` enum/colour kept as PARKED scaffolding. Reason: HRCF labelled the faster n-2 TF independently of CF, so it could print AFTER CF (backwards vs its "early confirmation" intent). NOTE: manual ([FOB_breakout_system.dissect.md](research/papers/fob/FOB_breakout_system.dissect.md) line 64) treats HRCF as the legit **skip-one-TF "high-risk discounted CF"** — re-add later as an overlay, it's not junk.
3. **Event-TF lens — [fob_visual.mqh](mt5/Include/fob_system/fob_visual.mqh) REWRITTEN from scratch (v0.4.0):** ONE CHART PER TF (gate on `event_tf==ChartPeriod`, native bars, NO projection, NO connector line). Each dot = one physical break merged from its role-events. `#id` = cross-chart link. Pure projection: two-pass replay of the event log (Pass1 rebuild state, Pass2 draw), never reads live `st[]`. Emitter live path switched to redraw-from-log ([fob_baysix.mq5:208-217](mt5/Experts/fob_system/fob_baysix.mq5#L208-L217)); dead `OnEvent` removed.

### Label grammar (signed off)
- A `PBO E #p DIR · pending {E-1} VR` (forming, no VR yet — pending badge is **consistent**: any drawn PBO w/o locked VR shows it)
- B `PBO E #p DIR` (VR locked = confirmed)
- C `PBO E #p DIRe | VR {E+1} #q DIRp` (also parent retrace) — dual dot coloured by PARENT role
- D `PBO E #p DIRe | CF {E+1} #q DIRp` (also parent confirm)
- Parent DIR derived from break: VR=OPP(break), CF=same. BUY/SELL clash on a dual dot is CORRECT (two setups, two theses).

## ⚠️ CYCLE-MODEL CORRECTION (Syafiq, end of session) — drives next work
Verified Syafiq's model against the manual — **his model is right, code diverges:**
- **VR's ONLY job = validate the PBO trend direction.** It is NOT a "zone to break." (I was wrong earlier tying cycle-end to "VR broken" — retracted.)
- **Cycle supersede = a NEW breakout on the SETUP TF** (opposite OR fresh same-dir) → **voids the prior VR, restarts the cycle (new PBO).** Only the **active (latest) cycle** per setup TF is alive; superseded = VOIDED/closed.
- Detector's supersede-on-every-setup-TF-break ([fob_sequence.mqh:60](mt5/Include/fob_system/fob_sequence.mqh#L60)) is therefore **CORRECT** under this model.
- **Phantom "old cycle" = a VISUAL retention bug**, not over-minting: the cap keeps last-2 *developed* cycles, but a voided cycle must vanish → show ACTIVE cycle ONLY.
- **Real detector fix still needed:** MULTIPLE CFs per cycle — `cf_done` single-lock ([fob_sequence.mqh:88](mt5/Include/fob_system/fob_sequence.mqh#L88)) contradicts manual's 2nd-CF/layering (Images 4.10-4.11, 7.5-7.6).

## Next (tasks in research.db)
1. **(task 156, P1)** Detector: allow multiple CFs per cycle (drop `cf_done` lock); confirm supersede=new-setup-TF-breakout voids VR. Keep VR-once.
2. **(task 157, P1)** Visual: show ACTIVE cycle ONLY per setup TF (voided cycle vanishes); drop the +1-prior retention. Depends on 156.
3. **(task 154)** Eyeball the v0.4.0 event-TF lens in Visual Mode — never done. After 156/157 land.
4. **(task 155)** Python ingester + edge test (after visuals locked).

## Blockers
None. All compiles. Pending: Syafiq's first Visual-Mode eyeball of the event-TF lens (do AFTER 156/157, else you'll eyeball soon-obsolete behaviour).

## Caveat
Pre-existing compile warning `version '0.21' incompatible with MQL5 Market` is the `#property version` string in [fob_baysix.mq5:24](mt5/Experts/fob_system/fob_baysix.mq5#L24) — harmless, Market protection deferred. Not from this session's edits.
