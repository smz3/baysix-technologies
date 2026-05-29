# Handover — May 29, 2026 Night

## State
HMM-001 (XAUUSD D1) passed **Gates 0–4**. The 10-step hedge-fund method is built across [markov_baseline.py](research/models/hmm/markov_baseline.py) (G2 rule-based Markov), [gate3_markov_signal.py](research/models/hmm/gate3_markov_signal.py) (G3, null rejected χ²=2778 V=0.75), [gate4_relabel.py](research/models/hmm/gate4_relabel.py) (G4 HMM asymmetric relabel), [gate4_calibration.py](research/models/hmm/gate4_calibration.py) (regime-change probability accuracy). Key truth: Gaussian HMM on daily returns = vol regimes (useless for direction); on **20d cumulative return** = directional regimes that beat the ±5% rule. Regime-change P has real-but-modest skill (AUC 0.57–0.64), made honestly calibrated via recalibration. Full audit in research.db: gates (9), results (#1–18), agent_log (calls 1–8). Open variables → [hmm001_open_variables.md](../.claude/projects/c--Users-User-Desktop-baysix-technologies/memory/hmm001_open_variables.md).

## Next (decided this session)
1. **Sweep the lookback window** {10,20,40,60} — the one unexamined assumption (still 20d everywhere). Express threshold in **σ-units of the window** (couples to window; collapses the 2-D grid). Re-derive HMM cut per window; pick by OUT-OF-FOLD Brier/AUC. New file e.g. `research/models/hmm/gate4_window_sweep.py`.
2. **Then decide calibration (item 3):** Platt-adaptive (Z=0.59 calibrated, AUC 0.573) vs iso-fixed (AUC 0.641, Z=4.27 under-warns). Syafiq leans Platt for a risk filter, but DEFER until after the sweep — a better window may dominate both.
3. **Then freeze ONE config + count n_trials (deflate) before Gate 6** — OOS sealed 2024-05-02 is one-shot (protocol rule 6).

## Blockers
None. Stay at Gate 4 until the sweep + freeze are done; do not touch OOS data yet.
