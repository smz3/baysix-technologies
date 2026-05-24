# UNIFIED QUANT TRADING FRAMEWORK
### One system, correctly nested

---

## THE STRUCTURE

The framework has two halves and three positions relative to the validation engine:

```
                    ═══════════ RESEARCH ═══════════        ══════ TRADING / EXECUTION ══════

  UPSTREAM (inputs)          CORE (validation)              DOWNSTREAM (live)
  ┌──────────────┐                                          ┌──────────────┐
  │ B. SIZING    │──┐                                    ┌─▶│ C. PORTFOLIO │
  │ D. COSTS/    │  │      ┌────────────────────┐        │  │    RISK      │
  │   CAPACITY   │──┼─────▶│   A. QR PIPELINE    │────────┤  └──────────────┘
  └──────────────┘  │      │   (validation)      │        │  ┌──────────────┐
                    │      └────────────────────┘        └─▶│ E. LIVE      │
                    │                                        │   MONITORING │
                    │                                        └──────┬───────┘
                    └────────────── reloop ◀─────────────────────────┘
```

**Key correction:** sizing (B) and costs/capacity (D) are **upstream inputs** — the validation engine *consumes* them. You cannot compute Sharpe, Calmar, or ruin without first knowing position size and cost assumptions. Portfolio risk (C) and monitoring (E) are **downstream** — they only exist once a validated, sized strategy is running.

---

## WHY B AND D ARE UPSTREAM, NOT AFTER

A backtest produces no survival metric until it knows how big you bet and what trading costs.
- **Drawdown, Sharpe, ruin** are all functions of position size → **B must feed in before Stage A runs.**
- **Step 3 L2 cost haircut** and **Step 4 full-cost test** need the cost/impact model → **D must feed in before those gates.**

So B and D are not stages that follow validation. They are **parameters of the validation.** Validation answers "is this edge real *at this size, under these costs*?"

---

# ═══════════ PART 1: RESEARCH ═══════════

## UPSTREAM — Inputs into validation

### B. SIZING (feeds into Stage A before any backtest)
The position-sizing rule the backtest runs at.
- **B1 Vol-targeting (base):** size for fixed annual vol (10–15%); exposure scales inverse to realized vol. This is what keeps the curve smooth.
- **B2 Fractional Kelly (cap, not target):** ¼–½ Kelly as a ceiling. Full Kelly assumes a perfect edge estimate, which never holds. If vol-target asks for more than the cap, the cap wins.
- **B3 Conviction scaling:** size ∝ signal strength, within the B1/B2 envelope.
- **Rule:** `size = min(vol-target, Kelly cap) × conviction`.

### D. COSTS & CAPACITY (feeds into Stage A's cost gates)
The cost and impact assumptions the validation tests against.
- **D1 Capacity:** capital ceiling before market impact eats the edge (where impact > per-trade alpha).
- **D2 Impact model:** slippage as a function of order size vs liquidity (square-root first approximation). Feeds back into B — large desired positions cost more.
- **D3 Execution logic:** order types, timing, order splitting.
- **D4 Crowding:** is the edge already crowded? Proxy via correlation to public factors and live-IC decay.

→ B and D set the conditions. Now the engine runs.

## CORE — The QR Pipeline (Stage A, validation engine)

The 5-step kill-gate funnel, run **at the sizing from B and costs from D**:

1. **Ideation + metric + data + structure** — lock primary metric; metric→Sharpe bridge; structure gate (confirm, don't tune).
2. **Signal construction** — build from hypothesis; log every param into `N_trials`.
3. **In-sample** — gross baseline → cost haircut (uses D) → structure-context → event-based. *(All run at B's sizing.)*
4. **Validation/stress** — OOS + CPCV-primary; full costs (uses D); Monte Carlo; full-trial DSR.
5. **Forward test** — paper trade ≥30 trades; expectancy kill-switch.

**Three-tier metrics:** Tier 0 Validity (`N_min`, IS-isolation, honest `N_trials`) → Tier 1 Survival (net Sharpe, Calmar, ruin, OOS/IS, DSR) → Tier 2 Edge (locked primary metric). Ship only if valid → survives → has edge.

**Output:** a validated, sized strategy with known expected Sharpe, drawdown, and capacity.

---

# ══════ PART 2: TRADING / EXECUTION ══════

## DOWNSTREAM — Consumes the validated strategy

### C. PORTFOLIO RISK (only exists with 2+ strategies)
- **C1 Correlation control:** two strategies at 0.8 corr ≈ one at double size. Cap pairwise (~0.6); size correlated clusters as one unit.
- **C2 Exposure limits:** caps on gross, net, per-asset, and per-strategy risk share (e.g. ≤25% each).
- **C3 Portfolio drawdown switch:** above per-strategy switches — total DD > ~15% de-risks everything (correlations spike in crises).
- **C4 Risk budgeting:** allocate *risk*, not dollars. Capital follows the vol budget.

### E. LIVE MONITORING (the deployed strategy, day to day)
- **E1 Rolling primary-metric:** decay shows in live IC before it hits PnL.
- **E2 Regime detection:** rolling Hurst/VR vs the regime the edge was validated in; pause when that regime disappears.
- **E3 Live-vs-modeled divergence:** slippage/fill/metric vs Stage-A models; >20% → investigate.
- **E4 Kill switch:** rolling expectancy negative over last `N_min` trades (never win-rate).
- **E5 Attribution:** daily PnL by signal/regime/cost — separates decay from luck.

→ **Reloop:** decay detected (E) → back to ideation, carrying `N_trials` forward.

---

## ONE-GLANCE MAP

| Position | Component | Half | Role |
|---|---|---|---|
| Upstream | **B. Sizing** | Research | Input to validation |
| Upstream | **D. Costs/Capacity** | Research | Input to validation |
| Core | **A. QR Pipeline** | Research | Validation engine |
| Downstream | **C. Portfolio risk** | Trading | Consumes validated strategy |
| Downstream | **E. Monitoring** | Trading | Runs the live strategy |

**Research half** = everything that decides whether and how to bet (B, D, A).
**Trading/execution half** = everything that happens once capital is live (C, E).
The boundary is deployment: left of it you're proving an edge at a size; right of it you're running it.

**Scale note:** solo / minimal capital → B + A are daily work, D light, C dormant until 2+ strategies, E essential the moment you go live. All five named = complete framework on paper.
