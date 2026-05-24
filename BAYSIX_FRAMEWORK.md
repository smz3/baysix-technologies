# BAYSIX QUANT FRAMEWORK
### One Research + Trading pipeline, parameterized for any context, agnostic to any asset

---

## 0. WHAT THIS IS

A single validation-and-deployment pipeline that serves **three deployment contexts** and **any asset structure** without forking the logic:

| Context | What you are paid for |
|---|---|
| **Solo / Baysix** (independent pod) | A smooth, rising equity curve that cannot blow up |
| **Hedge fund** | Capacity-weighted return — return that survives at size |
| **Pod shop** (Balyasny / Millennium style) | Low correlation to the house book + tight drawdown discipline |

It is **asset-agnostic**: the same funnel validates a single-asset timing edge (XAUUSD B2B) and a cross-sectional multi-asset factor. The asset structure decides *which metrics are legal*, not whether the pipeline applies.

The framework splits into two halves around one boundary — **deployment**:

- **Upstream = RESEARCH** — proving an edge is real, at a size, under real costs.
- **Downstream = TRADING** — running a validated, sized edge as part of a live book.

One idea makes all of this work without three separate frameworks: a **Deployment Profile** set once at the top, read by every gate and every agent.

---

## LAYER 0 · THE DEPLOYMENT PROFILE
*The parametric switch. Set before any test runs. Every gate reads its thresholds from here, so the same funnel behaves correctly in all three contexts.*

| Field | Solo / Baysix | Hedge Fund | Pod Shop |
|---|---|---|---|
| **Binding kill constraint** | Ruin-to-zero | Capacity floor | Drawdown stop-out (−5% to −8%) |
| **Paid for** | Smooth curve | Capacity-weighted return | Low correlation to house book |
| **Asset mode** | single ↔ cross-sectional multi — *sets which Tier-2 edge metric is legal* | | |
| **Venue + cost model** | Just Markets CFD / Darwinex futures / IBKR equities — *sets the cost gates in §A-D* | | |
| **Benchmark book** | null | fund book | platform book — *drives the §C correlation gate* |
| **Targets** | target vol, target Sharpe, capacity floor, max drawdown — all numeric, all context-set | | |

**Two rules this layer enforces:**
1. **No agent acts without a loaded profile.** A gate with no profile cannot know its threshold, so it must refuse. This is what structurally prevents forcing the wrong metric on the wrong asset.
2. **Profile-driven, not forked.** There is one funnel. Context only swaps thresholds and toggles which gates fire (e.g. §C is trivial for a solo single-strategy book, mandatory for a fund).

---

# ═══════════ PART 1 · RESEARCH (Upstream) ═══════════

## §A · INPUTS — consumed before the engine runs

The validation engine cannot compute a single survival metric until it knows how big you bet and what trading costs. So these are not stages that follow validation — they are **parameters of it.**

- **B. Sizing** — the position-sizing rule the backtest runs at.
  `size = min(vol-target, Kelly cap) × conviction`
  - Vol-targeting (base): size for fixed annual vol; exposure scales inverse to realized vol. This is what keeps the curve smooth.
  - Fractional Kelly (cap, not target): ¼–½ Kelly as a ceiling; the cap wins over vol-target.
  - Conviction scaling: size ∝ signal strength, within the envelope.
- **D. Costs / Capacity / Venue** — the cost and impact assumptions the validation tests against, **read from the profile's venue.**
  - Capacity: capital ceiling before impact eats the edge.
  - Impact model: slippage as a function of order size vs liquidity (square-root first approximation).
  - Execution logic: order types, timing, splitting.
  - Crowding: correlation to public factors + live-IC decay.

→ B and D set the conditions. Now the engine runs.

## §B · THE FUNNEL — governed by the 3-tier metric stack

Metrics answer three different questions **in order**, and a failure at each tier means something different:

```
Tier 0 · VALIDITY    Can I trust this number at all?   → the TEST is broken    → discard, rerun
   N_min · in-sample isolation · honest N_trials · PIT / no-lookahead audit

Tier 1 · SURVIVAL    Will the curve survive reality?   → the STRATEGY is dead  → kill
   net Sharpe · Calmar · ruin (@ profile horizon + level) · OOS/IS stability · DSR · capacity

Tier 2 · EDGE        Does it have the edge I claimed?  → the THESIS is wrong   → kill
   idea-specific primary metric — LEGALITY SET BY ASSET MODE
```

**Tier 0 is the tier that saves a solo researcher from himself.** A failed survival metric means a bad strategy; a failed validity check means the number on the screen is meaningless however good it looks.

**Tier 2 legality (asset mode gates this — the category error becomes structurally impossible):**

| Idea type | Primary metric | Legal when |
|---|---|---|
| Return-predictive (cross-sectional) | IC, ICIR, IC decay | asset mode = multi |
| Timing / entry | Hit rate, predictive accuracy | any |
| Momentum / breakout | MAE/MFE ratio, trend consistency | any |
| Mean reversion | Half-life, z-score stability | any |
| Microstructure | Order-flow imbalance, fill rate | any |

**Verdict rule:** a strategy ships only if it passes **Tier 0 (valid) → ALL of Tier 1 (survives) → its Tier 2 metric (has edge).** Never survival without edge; never edge without survival.

**Two counters run the length of the funnel and never reset within a research family:**
- `N_trials` — every trial ever compared within the family. Feeds the snooping math in Step 4. Lying here invalidates every downstream statistic.
- `Primary metric` — the Tier-2 number locked in Step 1; it must reappear in every later gate.

**Definition of a research family (LOCKED 2026-05-24).** A family is **the set of trials you compared against each other to pick the winner.** The multiple-testing penalty corrects for selecting the best of many tries on the same data, so everything you compared is penalized together; things you never compared are separate families.
- **Family key** = `idea-type × asset-universe-searched`, at **asset-class granularity** (`metals-momentum`, not `XAUUSD-momentum`) — honest the moment you scan a basket; collapses to a single instrument when you only ever touch one.
- **Platform / venue is NOT in the key.** Same signal under two venues is re-pricing, not re-discovery; adding it would fragment `N_trials` and weaken the correction. Venue lives in the profile.
- **Searched dimensions increment `N_trials` inside the family — they do not fork a new one:** timeframe (same series resampled), parameters / lookbacks, regime conditioning (which HMM state the edge lives in), signal variants, individual instruments inside the searched basket, and venue-specific re-optimization of signal parameters.
- **`family_key` is declared by the researcher at Step 1 ideation** — you commit to the search space up front and cannot shrink it later to dodge the penalty.
- **Agent operational test at every new trial:** *"Did I compare this against the existing family to pick a winner? Yes → same family, increment `N_trials`. No → new family."*

### Steps — each gate states: metric · baseline · N_min · pass-logic

1. **Ideation + metric-lock + data/structure.** Define the edge and why it must exist; lock the Tier-2 metric (asset-mode-gated); write the **metric→Sharpe bridge** ("a primary-metric value of X, at this turnover and cost, should produce a Sharpe of ~Y"); data + structure gate (Hurst / Variance Ratio / ADF on the in-sample window only; *confirm, don't tune*).
2. **Signal construction.** Build from the hypothesis only; **every parameter combination tried increments `N_trials`**; validate on the primary metric only — no Sharpe yet.
3. **In-sample testing.** Gross baseline → first cost haircut (uses venue D) → structure-context (Sharpe & PF floors) → event-based (MAE/MFE, turnover-adjusted Sharpe).
4. **Validation / stress.** Out-of-sample + walk-forward + **CPCV-primary** (CPCV wins on disagreement); full venue costs; Monte Carlo ×3 (trade shuffle, param perturbation, synthetic paths); **snooping audit** (DSR, PSR, t-stat, White's Reality Check) on the *full* `N_trials`; **bridge-residual check** — realized Sharpe vs bridge-predicted Sharpe; a large gap in *either* direction means the edge mechanism is not understood, even if both numbers pass.
5. **Forward test.** Paper trade — duration = **minimum 30 trades, not a calendar window**; compare live primary-metric / MAE-MFE / slippage vs Step-4 modeled values; expectancy kill-switch.

*(Tier-0 `N_min` applies to every layer of every step — a result below it is void, not failed.)*

## §C · PORTFOLIO-FIT GATE — the promotion gate

A strategy that survives §B is **valid in isolation.** It is not promoted to live until it clears the existing book. This is the gate that makes the framework pod/fund-worthy — a great standalone edge that adds nothing to the book does not deploy.

- **Marginal Sharpe contribution > 0** vs the existing book.
- **Correlation to benchmark book < profile cap** (~0.6). Skipped if profile = solo with a single strategy.
- **Capacity sufficient at the profile's AUM.** Skipped if solo; binding for a fund.

→ Solo with one strategy passes trivially. Fund / pod must clear it. Same gate, profile decides the teeth.

---

# ══════ PART 2 · TRADING (Downstream) ══════

*Consumes a validated, sized strategy. These only exist once capital is live.*

## §D · PORTFOLIO RISK *(binds with 2+ strategies)*
- **Correlation control:** two strategies at 0.8 correlation ≈ one at double size; cap pairwise, size correlated clusters as one unit.
- **Exposure limits:** caps on gross, net, per-asset, per-strategy risk share.
- **Portfolio drawdown switch:** above per-strategy switches — total drawdown breach de-risks everything (correlations spike in crises).
- **Risk budgeting:** allocate *risk*, not dollars; capital follows the vol budget.

## §E · LIVE MONITORING *(the deployed strategy, day to day)*
- **Rolling primary-metric:** decay shows in the live metric before it hits PnL.
- **Regime detection:** rolling Hurst/VR vs the regime the edge was validated in; pause when that regime disappears.
- **Live-vs-modeled divergence:** slippage / fill / metric vs Step-4 models; breach → investigate.
- **Kill switch:** rolling expectancy negative over the last `N_min` trades — **never win-rate** (that would shut off momentum systems that win <50% by design and earn on the tails).
- **Attribution:** daily PnL by signal / regime / cost — separates decay from luck.

## §F · RELOOP → LEDGER
- Decay or kill (§E) → back to §B Ideation.
- **Failed / decayed hypotheses are written to the honesty ledger** so dead ideas are not re-tested and `N_trials` is not re-inflated on answered questions.
- `N_trials` carried forward across the family — that is what keeps the funnel honest over a research lifetime.

---

## THE BOUNDARY

| Position | Component | Half | Role |
|---|---|---|---|
| Layer 0 | **Deployment Profile** | — | Parameterizes everything |
| Upstream | **§A Sizing + Costs/Venue** | Research | Inputs to validation |
| Upstream | **§B The Funnel** | Research | Validation engine |
| Upstream | **§C Portfolio-fit gate** | Research | Promotion gate |
| Downstream | **§D Portfolio risk** | Trading | Runs the live book |
| Downstream | **§E Monitoring** | Trading | Runs the live strategy |
| Downstream | **§F Reloop → ledger** | Trading→Research | Compounds learning |

Left of deployment you are proving an edge at a size; right of it you are running it.

---

## AGENT ROUTING — who owns what, and how they know when

**Routing model: Chief-of-Staff-routed.** Agents do not self-trigger or poll. The Chief of Staff holds the strategy state, reads the gate, and dispatches the one owning agent for that gate — handing it the profile + state. This is deterministic, single-source-of-truth, and cheapest to run.

| Framework zone | Owning agent | Cross-cutting |
|---|---|---|
| Layer 0 profile | Chief of Staff + risk-manager | — |
| §A Sizing / Costs | risk-manager (size), quant-developer (cost model) | — |
| §B Funnel Tier 0/1/2 | quant-researcher | **/quant-modeller discipline at every measurement** |
| Step 6 backtest run (LEAN) | quant-developer | **code-reviewer signoff required before run** |
| §C Portfolio-fit gate | risk-manager + quant-researcher | — |
| §D Portfolio risk | risk-manager | — |
| §E Live monitoring | quant-trader (observer only) | escalates → risk-manager |
| §F Reloop / ledger | memory-curator + quant-researcher | — |

**Two mandatory signoffs on transitions (not gate-owners):** code-reviewer before any code runs; risk-manager before any capital moves.

**How an agent knows "when and what":** three artifacts make every move unambiguous —
1. **Deployment Profile** — the *what-context* (which thresholds, which legal metrics). Lives in `risk_parameters.md`.
2. **Per-strategy State Manifest** — the *when-trigger* (current funnel step, last gate pass/fail, locked metric, running `N_trials`, profile ID). Lives in `strategy_state.md`.
3. **This ownership map** — the *who*.

Without the profile + manifest loaded, a spawned agent re-derives context cold and drifts. With them, the next gate's owner is obvious and the Chief of Staff dispatches it.

---

## TWO DESIGN RULES HOLDING IT TOGETHER

1. **Profile-driven, not forked** — one funnel; context only swaps thresholds and toggles §C.
2. **Asset mode gates Tier-2** — single-asset cannot select IC; cross-sectional cannot select half-life. The category error is structurally impossible.

---

*Source detail (gate-level thresholds, full pass-logic) currently lives in [QR_pipeline_v3.md](QR_pipeline_v3.md) and [QT_framework_unified.md](QT_framework_unified.md). Those remain authoritative for thresholds until folded into this document.*
