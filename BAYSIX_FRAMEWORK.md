# BAYSIX QUANT FRAMEWORK
### One Research + Trading pipeline, parameterized for any context, agnostic to any asset

*This is the single authoritative spec. It absorbed the former `QR_pipeline_v3.md` (research funnel) and `QT_framework_unified.md` (system map) on 2026-05-24 — all gate thresholds now live here.*

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

- **Upstream = RESEARCH** — proving an edge is real, at a size, under real costs. (folder: `research-engine/`)
- **Downstream = TRADING** — running a validated, sized edge as part of a live book. (folder: `trading-engine/`)

One idea makes all of this work without three separate frameworks: a **Deployment Profile** set once at the top, read by every gate and every agent.

**The single objective the whole thing serves:** *a smooth, rising equity curve that stays smooth out-of-sample and cannot blow up the account.* Low drawdown, low profit volatility, and a straight climb are one property of one curve viewed three ways. Every metric exists only to prove the curve is real and won't ruin us — never optimized for its own sake. The hard truth that shapes the design: **a smooth in-sample curve is the easiest thing in the world to fake.** Smoothness is what we *want*; it is never what we *trust*. Trust comes only from the validation stack.

---

## LAYER 0 · THE DEPLOYMENT PROFILE
*The parametric switch. Set before any test runs. Every gate reads its thresholds from here, so the same funnel behaves correctly in all three contexts. Lives in `risk_parameters.md`.*

| Field | Solo / Baysix | Hedge Fund | Pod Shop |
|---|---|---|---|
| **Binding kill constraint** | Ruin-to-zero | Capacity floor | Drawdown stop-out (−5% to −8%) |
| **Paid for** | Smooth curve | Capacity-weighted return | Low correlation to house book |
| **Asset mode** | single ↔ cross-sectional multi — *sets which Tier-2 edge metric is legal* | | |
| **Venue + cost model** | Just Markets CFD / Darwinex futures / IBKR equities — *sets the cost gates* | | |
| **Benchmark book** | null | fund book | platform book — *drives the portfolio-fit correlation gate* |
| **Targets** | target vol, target Sharpe, capacity floor, max drawdown — all numeric, all context-set | | |

**Two rules this layer enforces:**
1. **No agent acts without a loaded profile.** A gate with no profile cannot know its threshold, so it must refuse. This is what structurally prevents forcing the wrong metric on the wrong asset.
2. **Profile-driven, not forked.** There is one funnel. Context only swaps thresholds and toggles which gates fire (e.g. the portfolio-fit gate is trivial for a solo single-strategy book, mandatory for a fund).

---

# ═══════════ PART 1 · RESEARCH (`research-engine/`) ═══════════

## THE 3-TIER METRIC STACK — *the discipline that runs through every step*

Metrics answer three different questions **in order**, and a failure at each tier means something different:

```
Tier 0 · VALIDITY    Can I trust this number at all?   → the TEST is broken    → discard, rerun
Tier 1 · SURVIVAL    Will the curve survive reality?   → the STRATEGY is dead  → kill
Tier 2 · EDGE        Does it have the edge I claimed?  → the THESIS is wrong   → kill
```

**Tier 0 is the tier that saves a solo researcher from himself.** A failed survival metric means a bad strategy; a failed validity check means the number on the screen is meaningless however good it looks.

**Tier 0 — Validity (preconditions, not thresholds):**
- **`N_min`** — results below it are *void, not failed*. Default ≥100 independent trades for trade-based stats; ≥250 daily observations for IC-based stats. Tune to frequency. *Applies to every layer of every step.*
- **In-sample isolation** — all structure/diagnostic stats on the IS window only; OOS untouched until Step 4.
- **Honest `N_trials`** — every strategy + parameter combination ever tested, logged and carried forward, never reset. Feeds the snooping math in Step 4. *Lying here invalidates every downstream statistic.*

**Tier 1 — Survival (universal, idea-independent) — the curve measured five ways:**
- **Net Sharpe** (after full costs) — is the climb smooth?
- **Calmar > 2.0** — are the dips shallow enough to sit through?
- **Ruin probability < 5%** — can the dips kill the account?
- **OOS Sharpe > 1.0, IS/OOS > 0.5** — does the smoothness persist out-of-sample?
- **DSR / PSR pass** (on full `N_trials`) — is the smoothness real, not the best of many tries?

Fail any → dead. No idea type is exempt.

**Tier 2 — Edge (idea-specific, asset-mode-gated — the category error becomes structurally impossible):**

| Idea type | Primary metric | Legal when |
|---|---|---|
| Return-predictive (cross-sectional) | IC, ICIR, IC decay | asset mode = multi |
| Timing / entry | Hit rate, predictive accuracy | any |
| Momentum / breakout | MAE/MFE ratio, trend consistency | any |
| Mean reversion | Half-life, z-score stability | any |
| Microstructure | Order-flow imbalance, fill rate | any |

*This table is the human mirror of the single source of truth in code — `METRIC_POLICY` in `research-engine/core/lib/idea_bank/signals.py` (ADR-0003). The Step-1 validator rejects any idea whose `primary_metric` is illegal for its `(idea_type, asset_mode)`, and a drift test fails if this table and the code disagree. The category error is enforced, not just documented.*

**Verdict rule:** a strategy ships only if it passes **Tier 0 (valid) → ALL of Tier 1 (survives) → its Tier 2 metric (has edge).** Never survival without edge; never edge without survival.

## TWO COUNTERS RUN THE LENGTH OF THE FUNNEL AND NEVER RESET WITHIN A FAMILY
- `N_trials` — every trial ever compared within the family. Feeds Step 4 snooping math.
- `Primary metric` — the Tier-2 number locked in Step 1; it must reappear in every later gate.

**Definition of a research family (LOCKED 2026-05-24).** A family is **the set of trials you compared against each other to pick the winner.** The multiple-testing penalty corrects for selecting the best of many tries on the same data.
- **Family key** = `idea-type × asset-universe-searched`, at **asset-class granularity** (`metals-momentum`, not `XAUUSD-momentum`) — honest the moment you scan a basket; collapses to a single instrument when you only ever touch one.
- **Platform / venue is NOT in the key.** Same signal under two venues is re-pricing, not re-discovery. Venue lives in the profile.
- **Searched dimensions increment `N_trials` inside the family — they do not fork a new one:** timeframe (same series resampled), parameters / lookbacks, regime conditioning (which HMM state the edge lives in), signal variants, individual instruments inside the searched basket, venue-specific re-optimization.
- **`family_key` is declared by the researcher at Step 1** — you commit to the search space up front and cannot shrink it later to dodge the penalty.
- **Agent test at every new trial:** *"Did I compare this against the existing family to pick a winner? Yes → same family, increment `N_trials`. No → new family."*

---

## THE 5-STEP FUNNEL
*Each step is a folder; each layer is a sub-stage inside it. Engines (cost-venue, ic, factor-model, lean) are tools in `core/engines/` that the steps **call** — they are not steps.*

### `step1_ideation/`
- **layer1 · deployment-profile** — set the active profile (above). Every downstream gate reads its thresholds from it.
- **layer2 · hypothesis + metric-lock + bridge** — define the edge and the *structural reason it must exist* (kill if there's no reason it should work); state the expected market structure as part of the thesis. Lock the Tier-2 metric (asset-mode-gated) — permanent, must appear in every later gate. Write the **metric→Sharpe bridge**: *"a primary-metric value of X, at this turnover and cost, should produce a Sharpe of ~Y."* **On later disagreement between a Sharpe gate and the primary metric, the primary metric wins** — a healthy Sharpe with a dead edge is luck or sizing, not alpha.
- **layer3 · data-structure-gate** — clean, normalize, tag sessions, store; then Hurst / Variance Ratio / ADF **on the IS window only**. Kill if random walk. Kill if measured structure **contradicts the layer-2 thesis**. **Confirm, don't tune** — the thesis predicts the structure; the test only confirms it. Measuring then adding a filter to match on the same data is snooping.

### `step2_signal/`
- **layer1 · signal-build** — build from the layer-2 hypothesis only. **Every parameter combination tried increments `N_trials`** (40 lookbacks kept-best = 40 trials, not 1 — the most common silent overfit). Validate on the **primary metric only — no Sharpe yet.**
- **layer2 · sizing** — the position-sizing rule the backtest runs at. `size = min(vol-target, Kelly cap) × conviction`.
  - Vol-targeting (base): size for fixed annual vol (10–15%); exposure scales inverse to realized vol — this keeps the curve smooth.
  - Fractional Kelly (cap, not target): ¼–½ Kelly as a ceiling; full Kelly assumes a perfect edge estimate that never holds. If vol-target asks for more than the cap, the cap wins.
  - Conviction scaling: size ∝ signal strength, within the envelope.

### `step3_in-sample/` *(Tier-0 `N_min` applies to every layer — a result below it is void)*
- **layer1 · gross-baseline** — vectorized, no kill. Record Sharpe, PF, Expectancy → label `BASELINE_GROSS`. Observe only.
- **layer2 · cost-haircut** — apply rough costs + slippage → `BASELINE_NET`. **Kill if `BASELINE_NET` Sharpe < 1.0.** (High-turnover/microstructure ideas: costs *are* the edge — don't chase a gross mirage.) Calls `core/engines/cost-venue`.
- **layer3 · event-based** (survivors only) — MAE/MFE, turnover-adjusted Sharpe, slippage distribution. **Kill if turnover-adjusted Sharpe drops > 30% vs `BASELINE_NET`** (never vs `BASELINE_GROSS` — that drop is expected and meaningless).
- **Step-3 pass gate:** **Sharpe ≥ 1.5 AND PF ≥ 1.5** on `BASELINE_NET`. Treat 1.5 as a floor, not a pass — the IS/OOS ratio in Step 4 does the real work.

### `step4_validation/`
- **layer1 · oos-walkforward-cpcv** — OOS Sharpe > 1.0; IS/OOS > 0.5. **CPCV is the primary verdict; walk-forward supports it** (require WF within ~30% of CPCV; CPCV wins on disagreement). Confirm the **primary metric still holds OOS**, not just Sharpe.
- **layer2 · full-cost** — double-spread test; Calmar > 2.0; Omega > 1.5. **Require Sharpe-family AND Calmar both pass.** If exactly one fails, **Calmar is the tiebreaker** — a curve you can't sit through is undeployable however good its Sharpe.
- **layer3 · monte-carlo** — ×3: trade shuffle, parameter perturbation ±20%, synthetic paths. **Kill if ruin probability > 5% on any path.**
- **layer4 · snooping-audit** — DSR, PSR, t-stat > 2.5, White's Reality Check, Bonferroni — **on the full `N_trials` from Step 1 onward**, not just survivors. Kill if DSR fails. **Bridge-residual check:** realized Sharpe vs bridge-predicted Sharpe — a large gap in *either* direction means the edge mechanism is not understood, even if both numbers pass.

### `step5_forward-fit/`
- **layer1 · paper-forward** — paper trade, duration = **minimum 30 trades, not a calendar window** (sample size, not the clock, decides when the result is readable). Compare live primary-metric / MAE-MFE / slippage vs **Step-4 modeled values**. **Kill if primary-metric divergence > 20%.** Expectancy kill-switch armed.
- **layer2 · portfolio-fit-gate** — the promotion gate. A strategy that survives is *valid in isolation*; it is not promoted to live until it clears the existing book:
  - **Marginal Sharpe contribution > 0** vs the existing book.
  - **Correlation to benchmark book < profile cap (~0.6).** Skipped if profile = solo with a single strategy.
  - **Capacity sufficient at the profile's AUM.** Skipped if solo; binding for a fund.
  - → Solo with one strategy passes trivially. Fund / pod must clear it. Same gate, profile decides the teeth.

**Cost / capacity model detail** (lives in `core/engines/cost-venue`, read from the profile's venue):
- Capacity: capital ceiling before market impact exceeds per-trade alpha.
- Impact model: slippage as a function of order size vs liquidity (square-root first approximation); feeds back into sizing.
- Execution logic: order types, timing, order splitting.
- Crowding: correlation to public factors + live-IC decay.

---

# ══════ PART 2 · TRADING (`trading-engine/`) ══════

*Consumes a validated, sized strategy. These only exist once capital is live.*

## `portfolio-risk/` *(binds with 2+ strategies)*
- **Correlation control:** two strategies at 0.8 correlation ≈ one at double size; cap pairwise (~0.6), size correlated clusters as one unit.
- **Exposure limits:** caps on gross, net, per-asset, per-strategy risk share (e.g. ≤25% each).
- **Portfolio drawdown switch:** above per-strategy switches — total drawdown breach (~15%) de-risks everything (correlations spike in crises).
- **Risk budgeting:** allocate *risk*, not dollars; capital follows the vol budget.

## `monitoring/` *(the deployed strategy, day to day)*
- **Rolling primary-metric:** decay shows in the live metric before it hits PnL.
- **Regime detection:** rolling Hurst/VR vs the regime the edge was validated in; pause when that regime disappears. *(Reads `context-engine` — the same regime calc research validated against, never a separate copy.)*
- **Live-vs-modeled divergence:** slippage / fill / metric vs Step-4 models; >20% → investigate.
- **Kill switch:** rolling expectancy negative over the last `N_min` trades — **never win-rate** (that would shut off momentum systems that win <50% by design and earn on the tails).
- **Attribution:** daily PnL by signal / regime / cost — separates decay from luck.

## RELOOP → LEDGER
- Decay or kill (monitoring) → back to `step1_ideation`.
- **Failed / decayed hypotheses are written to the honesty ledger** (`research-engine/research-ledger`) so dead ideas are not re-tested and `N_trials` is not re-inflated on answered questions.
- `N_trials` carried forward across the family — what keeps the funnel honest over a research lifetime.

---

## THE BOUNDARY

| Position | Component | Folder | Half |
|---|---|---|---|
| Layer 0 | **Deployment Profile** | `step1_ideation/layer1_deployment-profile` | Parameterizes everything |
| Upstream | **Funnel step1–5** (sizing + costs are layers inside) | `research-engine/step{1..5}_*` | Research |
| Upstream | **Portfolio-fit gate** | `step5_forward-fit/layer2_portfolio-fit-gate` | Research (promotion) |
| Downstream | **Portfolio risk** | `trading-engine/portfolio-risk` | Trading |
| Downstream | **Monitoring** | `trading-engine/monitoring` | Trading |
| Cross | **Reloop → ledger** | `research-engine/research-ledger` | Trading→Research |
| Shared | **Market-state + context** | `market-state-engine/`, `context-engine/` | read by both halves |

Left of deployment you are proving an edge at a size; right of it you are running it.

---

## AGENT ROUTING — who owns what, and how they know when

**Routing model: Chief-of-Staff-routed.** Agents/skills do not self-trigger or poll. The Chief of Staff holds the strategy state, reads the gate, and dispatches the one owner for that gate — handing it the profile + state. Deterministic, single-source-of-truth, cheapest to run. Owners are either **agents** (spawned, isolated context) or **skills** (`/name`, run inline by the CoS).

| Framework zone | Owner | Cross-cutting |
|---|---|---|
| Layer 0 profile | Chief of Staff + `/risk-check` | — |
| step2 sizing / cost model | `/risk-check` (size), quant-developer (cost model) | — |
| Funnel Tier 0/1/2 | quant-researcher | **/quant-modeller discipline at every measurement** |
| step4 LEAN backtest run | quant-developer + `/run-backtest` | **code-reviewer signoff required before run** |
| step5 portfolio-fit gate | `/risk-check` + quant-researcher | — |
| Portfolio risk | `/risk-check` (CoS-run) | — |
| Monitoring | `/check-mt5-health` + `/check-lean-health` (CoS-run) | escalate anomalies to user |
| Reloop / ledger | `/update-memory` + quant-researcher | — |

**Surviving agents (spawned, isolated):** code-reviewer, quant-researcher, quant-developer. Everything else is a CoS-run skill.

**Two mandatory signoffs on transitions:** code-reviewer (agent) before any code runs; a `/risk-check` pass before any capital moves.

**How an agent knows "when and what":** three artifacts make every move unambiguous —
1. **Deployment Profile** — the *what-context* (thresholds, legal metrics). `risk_parameters.md`.
2. **Per-strategy State Manifest** — the *when-trigger* (current step, last gate pass/fail, locked metric, running `N_trials`, profile ID). `strategy_state.md`.
3. **This ownership map** — the *who*.

Without the profile + manifest loaded, a spawned agent re-derives context cold and drifts.

---

## TWO DESIGN RULES HOLDING IT TOGETHER

1. **Profile-driven, not forked** — one funnel; context only swaps thresholds and toggles the portfolio-fit gate.
2. **Asset mode gates Tier-2** — single-asset cannot select IC; cross-sectional cannot select half-life. The category error is structurally impossible.
