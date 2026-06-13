# Handover — June 14, 2026 Morning2

## State
- **MSM-001 KILLED @ Gate 2** (strategy_log #43). 3 FALSIFIED exhausted the close-only ALIGNMENT thesis: symmetric (#39), magnitude (#40), dumb 2-TF confluence D1×H1 (#42, result_id 130 — AGREE net -0.000094 HAC t -2.20 vs CONFLICT -0.000102, A-C +0.000008 = alignment buys nothing). Tasks 63 done, 67–70 dropped.
- **Reframe (key):** real edge was never close-only momentum agreement — it's **multi-TF STRUCTURAL breakout** (Syafiq's 7yr method: MN1/W1/D1 breakouts of prior CLOSE, sequenced HTF-bias→LTF-pullback entry). MSM cache is close-only (no OHLC) so could never test it. → **BRK-001 spec-birth** (human call 52).
- **STRUCT-001 created** (infra, human call 54) — detection primitive is its own idea (shared layer; BRK-001 = first consumer; also basis to re-examine killed ORB). Detector ALREADY EXISTS — live B2B Sigma EA (MQL5, STABLE freeze) + Python port [b2b/sigma_core/b2b/detectors/](b2b/sigma_core/b2b/detectors/): **close-based** swings, **close-confirmed** per-TF breakouts, 5-pointer L1/L2 geometry. Lift, don't rebuild.
- **AUDIT (task 71) DONE — PASS** (human call 53). Rerunnable: [research/models/struct/audit_detector_causality.py](research/models/struct/audit_detector_causality.py) — 3106 D1 bars / 1528 swings / 1416 breakouts, **0 violations / 5 checks**. Causal (swing stamped at pivot but breakouts.py time-gate makes it actionable only from confirm bar i+1; no look-ahead). Parity CONFIRMED at live `InpSwingWindow=3` (MQL5 radius=3//2=1 = Python 3-bar pivot). Safe AS-IS at window=3.
- Task 72 done: fixed wrong [SwingPointDetector.md](mt5/Documentation/modules/Detection/SwingPointDetector.md) (claimed wick-based; source proves close-based).

## Next
1. **Spec BRK-001 mechanism** (discuss-only first, [[feedback_discuss_before_build]]): nail Syafiq's sequencing (W1 sell confirm → MN1 sell confirm → wait D1 *opposite* breakout = pullback → entry on resumption vs exhaustion?) + 5-pointer entry-level def. Then `pipeline.open_gate('BRK-001', 0, ...)`.
2. Build **MN1/W1/D1 OHLC** by resampling canonical Arctic ticks (`arctic_io.daily_bars` exists; W1/MN1 = resample). Do NOT import broker bars (weak B-book feed).
3. **Task 74 (P2, STRUCT-001)** — HARDEN Python primitive (honor `config.swing_window`; gate breakout on confirmation index not pivot+1) BEFORE widening window past 3. Python-only; don't touch frozen MQL5; re-run audit script after.

## Blockers
None. Detector audited + safe at window=3 (rerun audit anytime). BRK-001 + STRUCT-001 rows exist (ideation); Gates 0–1 not yet opened.
