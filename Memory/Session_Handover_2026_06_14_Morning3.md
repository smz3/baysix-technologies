# Handover — June 14, 2026 Morning3

## State
- **STRUCT-001 now owns a full structure-primitive codebase** under [research/models/struct/struct001/](research/models/struct/struct001/) (mirrors orb/orb001 convention):
  - [swingpoints.py](research/models/struct/struct001/swingpoints.py) — swing entry over the shared detector (`swings_d1()`, `load_d1()`); future home for HH/HL/LH/LL labeling.
  - [rawbreakout.py](research/models/struct/struct001/rawbreakout.py) — **self-contained faithful re-port** of RawBreakoutDetector.mqh V5.0.5 (two-pass shared L2 + FindImpulseSwingPrice + confirmation gate). strategy_log #45.
  - [visual.py](research/models/struct/struct001/visual.py) — universal struct visualizer: `visual.py swings|breakouts [n] [--window k]`.
  - [audit_detector_causality.py](research/models/struct/struct001/audit_detector_causality.py) — reruns PASS (3106 D1 bars, 1528 swings, 1416 breakouts, 0 viol / 5 checks).
- **Window dial fixed** (task 74 swing half): shared [b2b/sigma_core/b2b/detectors/swing_points.py](b2b/sigma_core/b2b/detectors/swing_points.py) now honors `config.swing_window` (radius=w//2) + MQH odd/≥3 guard. No regression at live window=3 (1528 swings); 5→874, 7→597; even/<3 rejected. strategy_log #44.
- **Breakout parity PROVEN**: rawbreakout.py core set IDENTICAL to audited shared port at window=3 — 1416 breakouts, same (bar/swing/direction) tuples (in-session assert) — re-port additionally populates L2 on all 1416. window=5→793 gated. Charts: outputs/struct001/{swings,breakouts}_d1.html (gitignored).
- Sep 29 / Oct 1 "missing" swing dots = CORRECT (staircase closes, not close-pivots); MQH==Python at window=3.

## Next
1. **TASK 75 (P1, MAIN PRIORITY)** — verify `plot_breakouts` dotted level segments anchor to the ACTUAL broken swing level + the bar that broke it (not adjacent/mismatched swing); arrow on breakout-bar close. Cross-check rawbreakout.py `broken_swing_price/time` vs `breakout_bar_index` against chart + MQH semantics. Visual/anchor-correctness pass (core set already proven, n=1416).
2. Task 74 OTHER HALF (P2) — confirmation gate is in struct-local rawbreakout.py but NOT in shared breakouts.py (look-ahead at window>3; benign at live 3).
3. Optional: add L2 marker to plot_breakouts (RawBreakoutInfo carries only `impulse_start_price`, no L2 time — would need to store impulse swing time to place it).

## Blockers
None.
