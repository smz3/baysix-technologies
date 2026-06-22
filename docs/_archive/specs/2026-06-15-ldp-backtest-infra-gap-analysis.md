# LdP Backtest-Infra Gap Analysis — Baysix Pipeline vs López de Prado Corpus

**Date:** 2026-06-15
**Author:** Claude (co-founder) · **Source dissects:** META-001 papers 16–21 (Opus, call_id 55–60)
**Status:** ADOPTED (analysis) — concrete build tasks filed (see §4)
**Task:** 86 (follows task 85 dissect)

---

## 0. Scope

- Maps the LdP backtesting prescriptions onto the Baysix 7-gate XAUUSD pipeline.
- Verdict per prescription: **HAVE** (implemented) · **PARTIAL** (present but incomplete) · **MISSING** (gap) · **N/A** (out of scope for a $50 single-instrument shop).
- Feeds §4 build tasks. Source-of-record formulas live in the dissects (`log_dissect_result`, META-001).

---

## 1. The right/wrong/missing table

| LdP prescription | Paper | Baysix status | Notes |
|---|---|---|---|
| PSR / Probabilistic Sharpe (per-period convention) | 17 | **HAVE** | Gate 5 (`gate5_report.py`, task 83). `per_period_sharpe_units_rule` memory confirms kurt term `(g4−1)/4`. |
| Deflated Sharpe Ratio (DSR) **with N + V[SR_n] in SR0** | 17, 19 | **PARTIAL → suspected MISSING** | We compute "DSR" but **SR0 almost certainly = 0** (no trial ledger) ⇒ it is PSR-vs-0, not DSR. The deflation lives entirely in `SR0 = √V[SR_n]·E[max(N)]`. **Highest-value fix.** |
| N_trials ledger (count + per-config Sharpe series) | 16, 17, 19 | **MISSING** | Framework references an `N_trials-family` schema but it is **not wired into Gate 5**. Prerequisite for both real DSR and PBO. |
| PBO / CSCV (prob. of backtest overfitting) | 16, 17 | **MISSING** | No degradation measure. A point-Sharpe (PSR/DSR) cannot see what CSCV measures. Seasonal example: PSR-stat 2.83 *passed* a rule with PBO=55%. |
| Minimum Backtest Length (config ceiling vs data) | 16 | **MISSING** | `2·ln(N)/E[max]²` ceiling: with ~8y XAUUSD IS, caps how many configs may be tried before Sharpe-1 is chance. Cheap Gate-0/1 guard. |
| One-shot OOS seal | 16 (implied) | **HAVE** | Arctic seal 2024-05-02. But protects only the *final* test, **not the dev-CV** where overfitting is injected. |
| Purged + embargoed K-fold CV (h≈0.01T) | 20 | **MISSING** | **Biggest leakage gap.** B2B/ORB/breakout labels span many bars (overlapping) ⇒ `X_t≈X_{t+1}, Y_t≈Y_{t+1}` leakage the seal does not catch. |
| Combinatorial Purged CV (CPCV) | 20 | **MISSING** | Purged CV is the prerequisite; CPCV is the multi-path generalization. Note: **paper 21 (AFML Lec.1) has NO CPCV** — cite paper 20 only. |
| Triple-barrier event labels (PT/SL/time) | 19, 20 | **PARTIAL** | ORB/B2B logic *is* PT/SL/time, but tests are run as **bar-returns without label lifespans** ⇒ purging/uniqueness undefined. Re-cast as events. |
| Uniqueness weighting (concurrent overlapping trades) | 20 | **MISSING** | ORB/B2B trades overlap heavily; unweighted samples over-count concurrent labels. |
| Causal-cleanliness / look-ahead guard | 16 (memory note) | **HAVE** | Gate 2 unsorted-tick guard (`gate2_sanity.py`, task 82) + `orb_unsorted_tick_lookahead` memory. Aligns with LdP's leakage warnings. |
| ≥2-FALSIFIED kill rule / falsification-first | 21 | **HAVE** | `kill_idea` ≥2-FALSIFIED (rule 8b). Paper 21's **86%-false-at-p=0.05** is the citation-of-record for *why*. |
| Theory-before-backtest (Gate 0/1 ordering) | 21 | **HAVE** | Gate 0/1 = novelty + pre-registered null before model code. Paper 21 is the formal justification. |
| Optimal Trading Rules (O-U Monte-Carlo for SL/TP) | 18 | **MISSING (opportunity)** | Set SL/TP by fitting O-U → MC the mesh, **per HMM regime**, instead of backtest grid-search (which manufactured the ORB edge). |
| Fractional differentiation (stationary + memory) | 20 | **MISSING (opportunity)** | Gold (GC1) stationary at **d≈0.3** retaining ~full memory; replaces d=1 returns as features. Re-fit on XAUUSD *spot*. |
| Meta-labeling (learn size on a fixed structural side) | 19 | **MISSING (opportunity)** | Detectors (B2B/ORB/BRK) emit the side; an RF secondary on F1 learns take/size. Fits STRUCT-001's shared detection layer. Limits overfit (side not learned). |
| Mean Decrease Accuracy feature importance | 21 | **MISSING (minor)** | Robust p-value-free feature selection for any HMM/meta-label layer. |
| Information / dollar / imbalance bars | 20 | **N/A → later** | Ties to `struct001` M1-base; needs derived aggressor flag b_t. Defer. |
| Nowcasting / alt-data (satellite, FIX, e-receipts) | 21 | **N/A** | Out of scope for a $50 single-instrument XAUUSD shop. |

---

## 2. Ranked gaps (by impact)

1. **No N_trials ledger ⇒ DSR is silently running as PSR.** The deflation lives entirely in `SR0`. Worked example: N 46→100 flips the *same* SR=2.5 from pass to fail. Fix unblocks DSR **and** PBO. *(papers 17, 19)*
2. **No PBO/CSCV gate** ⇒ every swept idea (ORB grids, HMM W-sweeps, B2B heatmaps) is unguarded against selection bias a point-Sharpe cannot detect. PSR 2.83 passed a PBO=55% rule. *(paper 16)*
3. **No purged/embargoed CV** ⇒ overlapping-label leakage in the *dev* loop that the one-shot seal does not cover. *(paper 20)*
4. **Labels not event-based (no triple-barrier)** ⇒ purging + uniqueness weighting are undefined. Structural prerequisite for #3. *(papers 19, 20)*
5. **Stops/targets & features still backtest-fit** ⇒ OTR (O-U MC per regime) + frac-diff d≈0.3 move parameter choice out of the overfitting-prone grid. Refinement, high alignment with HMM/structure work. *(papers 18, 20)*

---

## 3. What we already do right (keep)

- PSR (per-period) at Gate 5; one-shot OOS seal; Gate-2 causal-cleanliness/look-ahead guard; ≥2-FALSIFIED kill rule; theory-first Gate 0/1 ordering. The LdP corpus *validates* these — paper 21 is the formal citation for the falsification-first engine.

---

## 4. Concrete build tasks (filed to backlog)

| Gap | Task | Priority |
|---|---|---|
| #1 N_trials ledger + true DSR (SR0 consumes N, V[SR_n]) | wire `n_trials` + per-config Sharpe series into Gate 5; SR0 ≠ 0 | **P1** |
| #2 PBO/CSCV Gate-5b for swept ideas (retain losers' PnL) | CSCV PBO + OOS-degradation gate | **P1** |
| #3 Purged + embargoed K-fold CV (h≈0.01T) as standard dev-CV | implement purged CV module | P2 |
| #4 Triple-barrier event labels (unlocks #3 + uniqueness + meta-label) | canonical event-label layer | P2 |
| #5a OTR: fit O-U → MC SL/TP mesh **per HMM regime** | O-U optimal-stops prototype | P2 |
| #5b Frac-diff d≈0.3 features (re-fit on XAUUSD spot) | frac-diff feature module | P2 |
| meta-labeling secondary (size on fixed structural side, F1) | meta-label layer on STRUCT-001 detectors | P2 |

---

## 5. Decision

- **ADOPT** the analysis. #1 and #2 are **P1** — they make the *existing* Gate 5 honest (DSR currently ≈ PSR) and are cheap once trials are logged.
- #3/#4 (purged CV + triple-barrier) are the next infra block; #5 + meta-labeling are strategy-layer opportunities, sequenced after.
- **Trigger to revisit:** first time any idea sweeps >1 config through Gate 5 — at that point #1/#2 are blocking, not optional.
