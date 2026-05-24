# QUANT RESEARCH PIPELINE
### A strategy-validation framework for systematic trading

---

## 0. THE OBJECTIVE

Everything in this pipeline serves one goal:

> **A smooth, rising equity curve that stays smooth out-of-sample and cannot blow up the account.**

That is the entire target. Low drawdown, low profit volatility, and a straight upward climb are not three separate goals — they are one property of one curve, viewed three ways.

Every metric below exists for exactly one reason: **to prove the curve is real and not a fluke, and that it will not ruin us.** Nothing more. We never optimize a metric for its own sake; we optimize the curve and use metrics to keep ourselves honest about it.

The hard truth that shapes the whole design: **a smooth in-sample curve is the easiest thing in the world to fake.** Curve-fitting produces beautiful equity curves on purpose. So smoothness is what we *want*, but it is never what we *trust*. Trust comes only from the validation stack.

---

## 1. METRIC PHILOSOPHY — THREE TIERS

Metrics are not a flat checklist. They answer three different questions, **in order**, and a failure at each tier means something different.

| Tier | Question | If it fails... | Action |
|---|---|---|---|
| **Tier 0 — Validity** | *Can I trust this number at all?* | The **test** is broken | Discard result, rerun |
| **Tier 1 — Survival** | *Will the curve survive reality?* | The **strategy** is dead | Kill strategy |
| **Tier 2 — Edge** | *Does it have the edge I claimed?* | The **thesis** is wrong | Kill strategy |

The distinction between Tier 0 and the rest is what protects a solo researcher with no second pair of eyes. A failed survival metric means a bad strategy. A failed validity check means a bad *experiment* — the number on the screen is meaningless, regardless of how good it looks. **Tier 0 is the tier that saves you from yourself.**

### Tier 0 — Validity (preconditions, not thresholds)
- **Minimum sample (`N_min`):** results below it are void, not failed. Default: ≥100 independent trades for trade-based stats; ≥250 daily observations for IC-based stats. Tune to frequency.
- **In-sample isolation:** all structure/diagnostic stats computed on the IS window only; OOS never touched until Step 4.
- **Honest trial count (`N_trials`):** every strategy + parameter combination ever tested is logged and carried forward, never reset. This number feeds the snooping math in Step 4. *Lying here invalidates every downstream statistic.*

### Tier 1 — Survival (universal, idea-independent)
The curve, measured four ways:
- **Net Sharpe** (after full costs) — is the climb smooth?
- **Calmar > 2.0** — are the dips shallow enough to sit through?
- **Ruin probability < 5%** — can the dips kill the account?
- **OOS Sharpe > 1.0, IS/OOS > 0.5** — does the smoothness persist out-of-sample?
- **DSR / PSR pass** (using full `N_trials`) — is the smoothness real, not the best of many tries?

Fail any → dead. No idea type is exempt.

### Tier 2 — Edge (idea-specific, the locked primary metric)
| Idea type | Primary metric |
|---|---|
| Return-predictive | IC, ICIR, IC decay |
| Timing / entry | Hit rate, predictive accuracy |
| Microstructure | Order-flow imbalance, fill rate |
| Mean reversion | Half-life, z-score stability |
| Momentum / breakout | MAE/MFE ratio, trend consistency |

**Verdict rule:** a strategy ships only if it passes **Tier 0 (valid) → ALL of Tier 1 (survives) → its Tier 2 metric (has edge).** Never survival without edge; never edge without survival.

---

## 2. THE FUNNEL

**Two counters run the length of the pipeline and never reset:**
- `N_trials` — every strategy + param combo tested (Tier 0).
- `Primary metric` — the Tier 2 number locked in Step 1; it must reappear in every later gate.

---

### STEP 1 — IDEATION + METRIC + DATA + STRUCTURE

**L1 — Ideation.** Define the edge and the structural reason it must exist. Kill if there's no reason it *should* work. State the expected market structure now as part of the thesis ("this edge implies the series is mean-reverting / trending / neither").

**L2 — Lock the primary metric.** Pick the Tier 2 metric for this idea type. It is locked permanently and must appear in every gate below.

**L3 — Metric→Sharpe bridge (the keystone).** Write one sentence: *"A primary-metric value of X, at my turnover and cost level, should produce a Sharpe of roughly Y."* This is the join between Tier 2 (edge) and Tier 1 (survival). When a later Sharpe gate and the primary metric disagree, **the primary metric wins** — a healthy Sharpe with a dead edge is luck or sizing, not alpha. Spend real time here; a lazy estimate weakens every downstream gate.

**L4 — Data + structure gate.** Retrieve, clean, normalize, tag sessions, store. Then Hurst / Variance Ratio / ADF on the **IS window only**.
- Kill if the series is a random walk.
- Kill if measured structure **contradicts the L1 thesis** — the reasoning was wrong.
- **Confirm, don't tune:** measuring structure to confirm a prior is clean; measuring it and then adding/tuning a filter to match it on the same data is snooping. The thesis predicts the structure; the test only confirms it.

---

### STEP 2 — SIGNAL CONSTRUCTION

**L1** — Build signals from the L1 hypothesis only.
**L2 — Parameter log.** Every parameter combination tried increments `N_trials`. Tested 40 lookbacks and kept the best? That's 40 trials, not 1. An invisible optimization step is the most common silent overfit.
**L3** — Validate signals on the **primary metric only**. No Sharpe yet.

---

### STEP 3 — IN-SAMPLE TESTING
*(Tier 0 `N_min` applies to every layer — a result below it is void.)*

**L1 — Vectorized, no kill.** Record Sharpe, PF, Expectancy. Label this `BASELINE_GROSS`. Observe only.
**L2 — First cost haircut.** Apply rough costs + slippage → `BASELINE_NET`. Kill if `BASELINE_NET` Sharpe < 1.0. (For high-turnover/microstructure ideas, costs *are* the edge — don't chase a gross mirage.)
**L3 — Vectorized w/ structure context.** Pass: **Sharpe ≥ 1.5 AND PF ≥ 1.5** on `BASELINE_NET`. Treat 1.5 as a floor, not a pass — the IS/OOS ratio in Step 4 does the real work.
**L4 — Event-based (survivors only).** MAE/MFE, turnover-adjusted Sharpe, slippage distribution. **Kill if turnover-adjusted Sharpe drops > 30% vs `BASELINE_NET`** (never vs `BASELINE_GROSS` — that drop is expected and meaningless).

---

### STEP 4 — VALIDATION + STRESS TESTING

**L1 — OOS + Walk-Forward + CPCV.** OOS Sharpe > 1.0; IS/OOS > 0.5. **CPCV is the primary verdict; walk-forward supports it.** On disagreement, CPCV wins; require WF within ~30% of CPCV. Confirm the **primary metric still holds OOS**, not just Sharpe. Kill if any fail.
**L2 — Full costs + spread.** Double-spread test; Calmar > 2.0; Omega > 1.5. **Require Sharpe-family AND Calmar both pass.** If exactly one fails, **Calmar is the tiebreaker** — a curve you can't sit through is undeployable however good its Sharpe.
**L3 — Monte Carlo ×3.** Trade shuffle, param perturbation ±20%, synthetic paths. Kill if ruin probability > 5% on **any** path.
**L4 — Snooping audit.** DSR, PSR, t-stat > 2.5, White's Reality Check, Bonferroni — **using the full `N_trials` from Step 1 onward**, not just survivors. Kill if DSR fails.

---

### STEP 5 — FORWARD TEST + DEPLOY + LOOP

**L1 — Paper trade.** Duration = **minimum 30 trades, not a fixed calendar window** (sample size, not the clock, decides when the result is readable). Compare live primary-metric, MAE/MFE, slippage vs **Step 4 modeled values**. Kill if primary-metric divergence > 20%.
**L2 — Deploy.** Daily PnL attribution, rolling primary-metric monitoring. **Kill switch: rolling expectancy turns negative over the last `N_min` trades** — never win-rate, which would shut off momentum/breakout systems that win <50% by design and earn on the tails.
**L3 — Reloop → Step 1.** Carry `N_trials` forward into the next idea. The counter never resets across your research lifetime — that is what keeps the whole funnel honest over time.

---

## 3. WHY THIS IS BOTH USABLE AND RIGOROUS

| For running the pod (usable) | For the research portfolio (world-class) |
|---|---|
| One-line objective: the curve | Three-tier metric epistemics (validity / survival / edge) |
| Clear single kill rule per gate | Full-funnel `N_trials` feeding DSR — the snooping discipline most retail pipelines miss |
| Expectancy kill-switch you can run solo | CPCV-primary validation with stated tiebreakers |
| Costs caught early, not after weeks | "Confirm don't tune" guardrail against in-sample snooping |
| Simple to read at a glance | Every gate states metric + baseline + sample minimum + pass-logic |

The same rigor that protects you operationally is what reads as senior-grade methodology on paper. They are not a trade-off — they are the same thing written clearly.
