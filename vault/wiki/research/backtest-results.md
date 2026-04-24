---
type: wiki
domain: research
status: stable
tags:
  - backtesting
  - results
  - samtc
related:
  - "[[samtc-overview]]"
  - "[[hypothesis-board]]"
  - "[[sigma-engine-map]]"
source_files:
  - "Memory/strategy_state.md"
last_updated: 2026-04-14
maintained_by: ai
ai_summary: "All SAMTC backtest results: 9G (Max Alpha IS, Sharpe 1.90), 10C (Governance baseline, Calmar 3.90), 13A (OOS Alpha Sentinel 2024-2025, Sharpe 1.16). 13A is the current production candidate awaiting CIO approval."
---

# Backtest Results

> This page is the canonical record of all SAMTC and B2B test results. Update this page after every new backtest run.
> 
> **Dataview note:** Frontmatter on individual result notes (when created) will feed a live Dataview table here. For now, results are recorded manually.

---

## Current Production Candidate

**Test 13A — OOS Alpha Sentinel (2024-2025)**

| Metric | Value |
|--------|-------|
| Period | 2024–2025 (Out-of-Sample) |
| Sharpe | **1.16** |
| Payoff Ratio | **1.65** |
| Return Skewness | **3.43** |
| Status | OOS Validation — awaiting CIO review for production approval |

**Key finding:** Positive skew (3.43) confirms the strategy has asymmetric return distribution — more large wins than large losses. Payoff 1.65 means winners average 65% larger than losers. Sharpe 1.16 is acceptable for a crypto strategy with this skew profile.

**Open question:** Does performance hold under live slippage conditions vs clean backtest fills? See [[hypothesis-board]] — HYP-001.

---

## All Test Results

```dataview
TABLE
  period as "Period",
  sharpe as "Sharpe",
  calmar as "Calmar",
  sortino as "Sortino",
  cagr as "CAGR",
  status as "Status"
FROM "vault/research/backtests"
SORT sharpe DESC
```

*Note: Dataview table above populates when individual backtest notes exist in `vault/research/backtests/`. Until then, use the manual table below.*

---

### Manual Results Table

| Test | System | Period | Sharpe | Calmar | Sortino | CAGR | Payoff | Skew | Status |
|------|--------|--------|--------|--------|---------|------|--------|------|--------|
| **13A** | SAMTC (sigma-crypto) | 2024–2025 OOS | 1.16 | — | — | — | 1.65 | 3.43 | OOS — awaiting CIO approval |
| **10C** | SAMTC (sigma-crypto) | 3yr Governance | — | 3.90 | 3.06 | TBC | — | — | Approved governance baseline |
| **9G** | SAMTC (sigma-crypto) | In-Sample (Max Alpha) | 1.90 | — | — | 432.3% | — | — | Research reference only — IS |

---

## Test Descriptions

### Test 9G — Max Alpha (In-Sample)
- **Purpose:** Establish the theoretical maximum alpha the strategy can extract with optimal parameters
- **Period:** In-sample (training data — exact dates TBC)
- **Key result:** 432.3% CAGR, Sharpe 1.90
- **Status:** Research reference only. Not for production — in-sample results are biased by parameter optimization.
- **Lesson:** Confirms the strategy concept has strong alpha potential; provides the ceiling for realistic expectations.

### Test 10C — Governance / Structural Gasket (3-Year)
- **Purpose:** Validate the strategy is structurally sound under a longer walk-forward governance window
- **Period:** 3-year (dates TBC — update when confirmed)
- **Key results:** Calmar 3.90, Recovery Factor 13.21, Sortino 3.06
- **Status:** ✅ Approved governance baseline — this is the minimum bar all future strategies must clear
- **Why Calmar matters here:** Calmar = CAGR / Max Drawdown. 3.90 means the strategy recovers its drawdown quickly. Recovery Factor 13.21 reinforces this.

### Test 13A — OOS Alpha Sentinel (2024-2025)
- **Purpose:** True out-of-sample validation — data the strategy has never seen
- **Period:** 2024–2025 (post-optimization period)
- **Key results:** Sharpe 1.16, Payoff 1.65, Return Skewness 3.43
- **Status:** Awaiting CIO sign-off for production approval
- **What needs validation:** Live slippage impact (backtest uses clean fills). Hypothesis HYP-001 tracks this.

---

## Decision Gate: Production Approval Checklist

For any strategy to move from OOS to production:

- [ ] Sharpe ≥ 1.0 on OOS data ✅ (13A: 1.16)
- [ ] Payoff ratio > 1.3 ✅ (13A: 1.65)
- [ ] Positive return skewness ✅ (13A: 3.43)
- [ ] Clears 10C governance baseline metrics *(pending comparison)*
- [ ] CIO review and sign-off *(pending)*
- [ ] Risk manager sign-off on position sizing *(pending)*
- [ ] Live slippage simulation confirms edge holds *(pending — HYP-001)*

---

## Related Pages

- [[samtc-overview]] — What SAMTC is and how it generates signals
- [[hypothesis-board]] — Open research questions (HYP-001: slippage impact)
- [[sigma-engine-map]] — How sigma_core feeds into the backtester
