# Handover — July 2, 2026 Evening

## State
- **VR-before-PBO causality bug FIXED** (task 221 done): [fob_sequence.mqh:104](../mt5/Include/fob_system/fob_sequence.mqh#L104) VR-lock now gates on **confirmation time** (`vr_confirm > pbo_confirm`, `confirm = bar_open + FobTfSeconds(TF)`), was bar-OPEN times. Added `FobTfSeconds(i)` ladder helper in [fob_types.mqh](../mt5/Include/fob_system/fob_types.mqh). CF-vs-VR gate untouched (same TF → open-order==close-order). v1.30.0, commit 85a7003, strategy_log id=87.
- **Dim twitch FIXED** (v1.30.1, commit 58882c5): [fob_visual.mqh:579](../mt5/Include/fob_system/fob_visual.mqh#L579) `dimmed = !zone.alive` — dim on close-based invalidation only. Reverted task-216 intrabar price-vs-L2 dim (re-checked every tick → wick chop across L2 twitched the band). Removed IntrabarDead from dim decision + repaint hash. LIVE-chart only, CSV byte-identical.
- Both compile **0 err, 1 benign** MQL5-Market format warning (MetaEditor stale-quotes "1.28.0"; file is 1.30.1).
- **NOT yet re-emitted** — VR fix changes emitted VRs; no fresh EMIT run.

## Next
1. **(task 220, P1) Re-emit + re-test both modes** on real ticks with v1.30.1, re-ingest via `ingest_fob`, verify CSV↔DB contract. Now unblocked (221 done).
2. **(task 222, P1) VR contamination audit** — diff old-CSV VRs vs v1.30.1 re-emit (per-cycle `vr_time`/`vr_swing`), quantify the real acausal-VR rate. Addresses Syafiq's distrust; run with/after 220.
3. Then resume entry-logic spec phase (tasks 214/215, v0.2) — still parked.

## Blockers
- None — task 220 was blocked by 221; 221 now done, re-emit is clear to run.

## Why
- **VR fix (task 221, strategy_log id=87):** a PBO is only a KNOWN fact at its bar CLOSE, not open. `bt`/`pbo_time` are bar OPENs ([fob_engine.mqh:114,127](../mt5/Include/fob_system/fob_engine.mqh#L114)); a higher-TF PBO bar spans a long window, so a lower-TF opposite break firing INSIDE the still-forming PBO bar passed the old `bt > pbo_time` gate and got stamped VR before the PBO ever confirmed = look-ahead (VR predating its cause). Confirm-time gate closes it. Only the ONE cross-TF gate was wrong; VR and CF share a TF so their relative order was already causal.
- **Dim revert (v1.30.1):** Syafiq's ruling — "if a sequence zone is invalidated then dim it if the cycle is still active." Invalidation is inherently a CLOSE event (`z.alive`), so the intrabar per-tick price term was the sole twitch source; deleting it *is* the fix (one line). Task-216's "don't stay bright for days" benefit was traded away deliberately (twitch > staleness for Syafiq).

## Ruled-Out
- **Latch dim (dim on first intrabar cross, never un-dim until close)** — I proposed it as a twitch-free way to keep task-216's prompt dimming; Syafiq rejected the framing as over-complicated. Dim = close-based invalidation, full stop. Do not re-propose intrabar dimming.
- **"9-TF mining is a total waste"** — NO. Only VR-conditioned screens (vr_fresh, RT, CF, htf_state cf-counts) are suspect; PBO detection + pipeline + EA + schema all stand, and prior mined numbers were already ~0 / flagged artifact (result: net −0.0776 usd/trade, aligned lifts −1.1/+0.1pp — see [[fob_storyline_alignment_finding]]). Re-emit is a cheap redo, not a rebuild — no validated edge was lost.

## Live-Threads
- **Syafiq distrusts the "not wasted" claim** — task 222 audit exists to REPLACE the assurance with a measured acausal-VR rate. Until that number lands, treat every prior VR-based result as unverified, not "probably fine."
- **CSV contamination extent still unquantified** — all pre-1.30.0 emit CSVs have acausal VRs baked in; the audit (222) tells us the fraction. Flag before trusting tasks 207/208 (vr_fresh) or any VR-conditioned screen.
- **Dim revert not eyeballed on a live JM chart** — compiled only; confirm the band no longer twitches when price wicks across L2, and still dims on a genuine close-through. Needs a chart Refresh/re-attach.
- **Unused code left in place:** `IntrabarDead()` method + `curPx` plumbing through StateSignature/DrawZones are now dead (harmless, no compile warning). Left to avoid signature churn across EA call sites; remove in a future cleanup if touching that file.
