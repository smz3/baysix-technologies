# Handover — June 14, 2026 Morning

## State
- **MSM-001 KILLED @ Gate 2** (strategy_log #43). 3 FALSIFIED exhausted the close-only ALIGNMENT thesis: symmetric (#39), magnitude (#40), dumb 2-TF confluence D1×H1 (#42, result_id 130 — AGREE net -0.000094 HAC t -2.20 vs CONFLICT -0.000102, A-C +0.000008 = alignment buys nothing). Tasks 63 done, 67–70 dropped.
- **The reframe (key):** the real edge was never close-only momentum-sign agreement — it's **multi-TF STRUCTURAL breakout** (Syafiq's 7yr manual method: MN1/W1/D1 breakouts of prior CLOSE, sequenced HTF-bias→LTF-pullback entry). MSM cache is close-only (no OHLC) so it could never test this. Migrated → **BRK-001 spec-birth** (human call 52).
- **Detector ALREADY EXISTS** — live B2B Sigma EA (MQL5, STABLE freeze) + Python port [b2b/sigma_core/b2b/detectors/](b2b/sigma_core/b2b/detectors/). Source-verified: **close-based** swings, **close-confirmed** per-TF breakouts, 5-pointer L1/L2 entry geometry. Lift this into the shared structure layer — do NOT rebuild.
- **AUDIT (task 71) DONE — PASS** (human call 53). Empirical on 3106 D1 bars / 1528 swings / 1416 breakouts: **0 violations across 5 checks**. Causality=PASS (swing stamped at pivot but breakouts.py time-gate makes it actionable only from confirmation bar i+1; no look-ahead). Parity=CONFIRMED at live `InpSwingWindow=3` (MQL5 radius=3/2=1 = Python 3-bar pivot). Safe to use AS-IS at window=3.
- Task 72 done: fixed wrong [SwingPointDetector.md](mt5/Documentation/modules/Detection/SwingPointDetector.md) (claimed wick-based; source proves close-based).

## Next
1. **Decide BRK-001 mechanism spec** before coding (discuss-only first, [[feedback_discuss_before_build]]): nail the sequencing rule from Syafiq's example (W1 sell confirm → MN1 sell confirm → wait D1 *opposite* breakout = pullback → entry on resumption vs exhaustion?) + the 5-pointer entry-level definition. Then `pipeline.open_gate('BRK-001', 0, ...)`.
2. Build **MN1/W1/D1 OHLC** by resampling canonical Arctic ticks (`arctic_io.daily_bars` exists; W1/MN1 = resample). Do NOT import broker bars (weak B-book feed).
3. **Task 73 (P2)** — HARDEN the Python primitive (honor `config.swing_window`; gate breakout on confirmation index, not pivot+1) BEFORE ever widening window past 3. Python-only; don't touch frozen MQL5; re-verify parity after.

## Blockers
None. Detector audited + safe at window=3. BRK-001 idea row exists (ideation); Gates 0–1 not yet opened.
