# Research-Infra Consolidation — LdP + Carver + AQR → Protocol 3.3 + one migration

**Date:** 2026-06-15
**Author:** Claude (co-founder)
**Status:** ADOPTED — keystone spec. Migration 028 shipped; Protocol 3.2 → 3.3; code-wiring tasks (87–93) unblocked.
**Task:** 96 (follows 85/86 LdP dissect+gap, 94 Carver, 95 AQR)
**Source dissects (META-001):** LdP papers 16–21 (call_id 55–60); Carver paper 23 (call_id 64); AQR papers 24, 26 (call_id 66, 65). Carver `backtesting.md` (paper 22) + AQR Craftsmanship Alpha (paper 25) intentionally NOT full-dissected — covered by FIND + adjacent dissects (see §6).

---

## 0. Why this document

Three authorities were harvested to lock Baysix's backtest/research infrastructure *once*:
- **López de Prado** — the mathematics of *not fooling yourself* (deflation, overfitting probability, leakage-free CV).
- **Carver** — the *systematic pipeline*: forecast scaling, vol-target sizing, cost-aware turnover budgeting, sim↔live consistency.
- **AQR** — *cost/capacity realism* (measure, don't model) and *craftsmanship* (implementation choices are alpha, if pre-committed).

Sequencing was deliberate: gather all three, then **one** protocol revision + **one** DB migration, to avoid migrating the schema twice. This is that consolidation. Source-of-record formulas live in the dissects (`log_dissect_result`, META-001) — this doc decides what changes.

---

## 1. Headline findings (grounded)

1. **Our "DSR" is silently PSR.** `gate5_report.dsr(returns, var_sr, n_trials)` is mathematically correct, but `Gate5Report.evaluate_pnl` only computes it when `var_sr` **and** `n_trials` are passed ([gate5_report.py:153](../../research/code/gate5_report.py#L153)). Nothing assembles the per-trial Sharpe series, so DSR degrades to `psr(sr_benchmark=0)` — **zero penalty for how many configs were tried.** Fix is a ledger + a reader, not new math.
2. **Schema was closer than feared.** `step4_results` already had `n_trials`, `trial_family_id`, `cost_adjusted`, `seed`, `data_hash`. Most of the LdP gap is *code wiring + a protocol rule*, not new tables. The migration is small and additive.
3. **Trial scope is per-idea, not global.** N = the number of configs compared to select *this* idea's winner (one sweep = one family). ORB's deflation never pools with HMM's. Re-running the *same* idea on the *same* IS data across sessions does accrue to that idea's family.
4. **Carver and AQR sizing share one ancestor.** TSMOM's ex-ante EWMA vol + inverse-vol-to-constant-target (call_id 65) is the mathematical core of Carver's `subsystem_position` — adopt once as the sizing layer.
5. **LdP vs AQR reconcile, not conflict.** LdP: deflate for the trials you ran. AQR: pre-commit reasonable implementation choices and *harvest* craftsmanship alpha. Lock = **do both** — pre-commit choices in an ADR AND count each as a trial in the ledger.

---

## 2. DB migration (028 — shipped)

Additive, idempotent, no rebuild. (`db_init.py` synced for fresh builds.)

| Change | What | Why |
|---|---|---|
| **NEW `trial_family`** | `family_id, idea_id, description, n_configs (=N), var_sr (=V[SR_n]), selected_config_hash, data_start/end, timestamps` | The N_trials ledger. One row per selection decision; feeds true DSR + CSCV. Per-idea scope. |
| `step4_results.config_hash` | identifies each swept config | links a result row to its family; counts distinct trials; names the winner |
| `step4_results.cost_bps` | realized cost in bps | AQR measure-don't-model: B-book half-spread + IS-minus-MI slippage |
| `step4_results.cost_basis` | `'measured'`/`'modeled'` | flags which discipline produced the cost number (enforced in code layer) |

Not added (deliberately): an `events` table for triple-barrier labels — kept ephemeral in code until a model needs them persisted.

---

## 3. Protocol changes (3.2 → 3.3)

### ADD
- **Gate 3 — speed-limit cost gate (Carver).** Reject a signal if `cost_per_trade(SR units) × turnover > SR_precost / 3`. Turnover budgeting *before* a signal earns IS spend. On XAUUSD (JM spread ~$0.35–0.50) this is binding; it would have killed high-turnover ORB variants early.
- **Gate 3 — measure-don't-model cost (AQR).** Cost = realized fill slippage (signal-bar-close vs actual fill) + B-book half-spread, logged to `cost_bps` with `cost_basis='measured'`. At $50 the market-impact term ≈ 0 — we are spread-dominated, never impact-dominated.
- **Gate 5 — N_trials ledger rule (LdP, HARD).** Every swept config logs a `step4_results` row under one `trial_family_id`; the family's `n_configs` + `var_sr` feed `dsr()`. Promotion is **blocked** if a sweep reached Gate 5 with an empty/absent family. The Gate-5 report must state whether it ran **PSR (N<2)** or **DSR (N≥2)** — no silent degradation.
- **Gate 5b — PBO/CSCV.** For any multi-config idea, run Combinatorially-Symmetric Cross-Validation on the retained config PnLs (losers kept) → probability of backtest overfitting. A point-Sharpe cannot see what CSCV measures (worked case: PSR 2.83 passed a PBO=55% rule).
- **Gate 0/1 — Minimum Backtest Length guard.** Cap configs-tried vs IS length: `2·ln(N)/E[max]²`. Cheap front-gate sanity on how many configs may be tried before Sharpe-1 is chance.
- **Dev-CV = purged + embargoed K-fold (LdP).** Standard dev-loop CV with `h ≈ 0.01T` embargo. The OOS seal protects only the *final* test; overlapping-label leakage is injected in the dev loop the seal never sees.
- **Triple-barrier event labels + uniqueness weighting (LdP).** Recast ORB/B2B/breakout tests as PT/SL/time events with label lifespans; prerequisite for purged CV and for down-weighting concurrent overlapping trades.
- **Sizing & normalization layer (Carver/AQR), between Gate 4 and 5.** Forecast scalar (`10/median|raw|`, cap ±20) → ex-ante EWMA vol (center-of-mass ≈ 60d, lagged) → inverse-vol to a constant vol-target. Single-asset XAUUSD: IDM is moot; FDM only when ≥2 signals are blended. Config lives in `log_strategy.params_json` (no new column).
- **Craftsmanship-ADR rule (AQR × LdP lock).** Implementation choices (signal construction, blending, rebalancing/cost discipline) are pre-committed in an ADR with alternatives **AND** each materially-tried alternative is counted as a trial in the DSR ledger. Harvest craftsmanship alpha (AQR) without hiding researcher degrees of freedom (LdP).

### MODIFY
- **Gate 5 wording:** "DSR" is **PSR until a trial family is supplied**. The report labels which test actually ran.
- **Weighting default (Carver):** combine signals by **equal-weight / handcrafting blend** (DM = 1/√(wᵀ·corr·w)) by default; a *fitted* weight scheme must beat the blend OOS to earn its place.

### REMOVE / STOP
- **Backtest grid-search for SL/TP** → replace with O-U Monte-Carlo per HMM regime (grid-search manufactured the ORB edge). *(opportunity, task 91)*
- **Bar-return-only testing** for event strategies → must be event-labeled.
- **Fitted forecast/instrument weights as default** → see MODIFY above.
- *(opportunity)* d=1 return features → frac-differentiation d≈0.3. *(task 92)*

### KEEP (corpus validates these)
PSR (per-period) at Gate 5; one-shot OOS seal; Gate-2 causal-cleanliness/look-ahead guard; ≥2-FALSIFIED kill rule; theory-first Gate 0/1; Gate-7 fidelity = Carver's sim↔live consistency (already have it via `tester_runs`).

---

## 4. Build sequence (code wiring — AFTER this migration)

Ordered; the ledger unblocks the rest.

| # | Task | Gate | Priority |
|---|---|---|---|
| 1 | trial-family reader → auto-feed `var_sr`+`n_configs` to `gate5_report`; report PSR vs DSR honestly | 5 | **P1 (87)** |
| 2 | CSCV / PBO module (retain losers' PnL) | 5b | **P1 (88)** |
| 3 | purged + embargoed K-fold CV module | dev-CV | P2 (89) |
| 4 | triple-barrier event labeler + uniqueness weights | labels | P2 (90) |
| 5 | speed-limit gate + AQR cost decomposition in the cost layer | 3 | P2 (new) |
| 6 | sizing layer (forecast scalar + EWMA vol + inverse-vol target) | 4→5 | P2 (new) |
| 7 | O-U OTR stops · frac-diff features · meta-labeling | strategy | P2 (91/92/93) |

---

## 5. Decision

- **ADOPT.** Migration 028 shipped; Protocol bumped to 3.3. Tasks 87/88 are now **unblocked** (were held pending this consolidation).
- **Trigger to enforce #1/#2 as blocking:** the first time any idea sweeps >1 config into Gate 5.
- The schema migration is intentionally minimal — the heavy lift is code (§4), done incrementally, no further migrations expected for this corpus.

## 6. Scope notes

- **Carver `backtesting.md` (paper 22) not full-dissected:** sizing components captured via call_id 64 (forecast scalar, handcrafting/DM) + call_id 65 (inverse-vol core). Only gap = the assembled `subsystem_position` equation + FDM — low value for single-asset XAUUSD (IDM moot). Grab via a targeted dissect only if §4-item-6 needs it.
- **AQR Craftsmanship Alpha (paper 25) not full-dissected:** conceptual, no formulas; thesis + the LdP×AQR tension captured in FIND (call_id 63). The §3 craftsmanship-ADR rule is the deliverable.
