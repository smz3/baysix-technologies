# Handover — July 2, 2026 Afternoon3

## State
- **RT-ladder redefine SHIPPED** (task 219 done): single L2-only `rt_count`/`rt_time` replaced by mirror ladder **rt1/rt2/rt3_time** (L2→mid→L1 on the return path after invalidation). v1.29.0, commit 57fe7b3.
- **Live-chart RT backfill SHIPPED**: v1.29.1, commit 15d636e — pre-attach invalidated VRs now show `[RTn]` + dots at bar resolution (`FobBackfillRtTimes` / `BackfillChartRt`).
- Both compile **0 err, 1 benign** MQL5-Market version-format warning.
- Schema migrated in lockstep: `fob_zones` + `ingest_fob` loader ([tester.py](../research/code/io/tester.py)) + [migration 035](../research/migrations/035_fob_payload_schema.py) → cols `rt1_time,rt2_time,rt3_time`.
- **🚨 NEW CRITICAL BUG (task 221, unfixed):** VR detection is **acausal** — when a parent-TF PBO confirms, the classifier picks the nearest opposite breakout that happened BEFORE the PBO confirmed. A VR cannot predate its PBO. Look-ahead → contaminates live AND emitted CSV.
- **NOT yet re-emitted** — RT schema changed but no fresh EMIT run (task 220).

## Next
1. **(task 221, P1) FIX the VR-before-PBO causality bug** — gate VR search so the VR's `bar_time`/swing is STRICTLY AFTER the PBO confirmation `bar_time`. Audit `FobClassifyBreak` + `FobSetupState` VR-lock in the FOB detection/sequence code. Trust-critical; fix BEFORE any re-emit.
2. **(task 220, P1) Re-emit + re-test both modes** on real ticks (v1.29.1 RT schema) — only AFTER task 221, else CSV re-bakes the acausal VRs. Re-ingest via `ingest_fob`, verify CSV↔DB contract.
3. Then resume entry-logic spec phase (tasks 214/215, v0.2) — still parked.

## Blockers
- Task 220 (re-emit) is blocked by task 221 — re-emitting before the VR fix would just re-contaminate the data.

## Why
- **RT redefine (call_id 93, strategy_log id=86):** a break-and-retest re-touches L2→mid→L1 mirroring the T-ladder; the old single-L2 count couldn't express return *depth*. Dropped the distinct-return count + re-arm hysteresis (`FobZoneAcc.armed` removed) — the ladder IS the signal.
- **RT backfill scope:** on live attach the close-path bar-replay sets `invalidation_time` for within-window VRs, but the tick-path saw no pre-attach ticks → RT stayed empty. `FobBackfillRtTimes` fills it bar-res, fill-only, LIVE-gated. Tester untouched → CSV byte-identical, data tick-exact.
- **T backfill left as-is on purpose:** already bar-res truthful. A single bar sweeping all 3 levels genuinely stamps them together; spreading them would INVENT intra-bar timing we don't have (Syafiq's trust concern → do not fake data).
- **Trust boundary (the key reassurance):** all backfills are `live = !MQLInfoInteger(MQL_TESTER)` gated → never run in the tester. Data mining/backtest = tester emits on real ticks 2016→, which the accumulator stamps tick-exact. Chart bar-res history ≠ the data path.

## Ruled-Out
- **CopyTicks for sub-bar historical "when"** — considered, rejected for now: JustMarkets keeps ticks only ~weeks, heavy call, unreliable. Bar-resolution live history is the accepted ceiling.
- **Faking intra-bar T-dot spread to avoid same-bar collapse** — rejected: it invents timing; the collapse is truthful at bar-res.
- **Keeping RT distinct-return count** — dropped by task 219; the 3-level ladder supersedes it. (Reopen only if a return *frequency* signal is wanted separately.)

## Live-Threads
- **VR-before-PBO bug (task 221) needs a scoping decision:** is it (a) same-bar tie-break picking a pre-PBO opposite break, or (b) the VR search window genuinely starting before PBO confirmation? Read `FobClassifyBreak` VR branch + `FobSetupState.vr_swing`/`vr_ev_idx` logic to pin which. Likely the VR-lock accepts an opposite break whose `bar_time < pbo.bar_time`.
- **CSV contamination extent:** all prior FOB emit runs have acausal VRs baked in → any VR-conditioned screen (tasks 207/208, vr_fresh, etc.) is suspect until a post-fix re-emit. Flag before trusting any VR-based result.
- **RT backfill correctness unverified on a live chart** — compiled but not eyeballed on MT5; confirm historical VRs now show `[RT1/2/3]` + dots next session.
