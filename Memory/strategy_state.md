# Strategy State
Last Updated: 2026-03-11

## Active Systems

| System | Version | Status |
|--------|---------|--------|
| SAMTC (sigma-crypto) | Phase 13A (OOS) | Research / Validation |
| B2B EA (sigma-mt5) | V5.0 | Active Dev — cluster fix in progress |

## Active Hypothesis
- SAMTC OOS validation (Test 13A) shows Sharpe 1.16 / Payoff 1.65 / Skew 3.43 (2024-2025)
- MT5 V5.0 has a known cluster detection edge case — B2B_CLUSTER_FIX_PLAN.md has 3 proposed solutions (A/B/C)
- Research question open: Does SAMTC performance hold under live slippage conditions vs clean backtest fills?

## Last Backtest Results

### sigma-crypto — Test 13A (OOS Alpha Sentinel, 2024-2025)
- Sharpe: 1.16
- Payoff: 1.65
- Skew: 3.43
- Status: OOS Validation — awaiting review for production approval

### sigma-crypto — Test 10C (Governance / Structural Gasket, 3yr)
- CAGR: [update when confirmed]
- Calmar: 3.90
- Recovery Factor: 13.21
- Sortino: 3.06
- Status: Approved governance baseline

### sigma-crypto — Test 9G (Max Alpha, in-sample)
- CAGR: 432.3%
- Sharpe: 1.90
- Status: Research reference only (in-sample, not production)

## Strategy Decisions Log
- [2026-04-01] V3 Architecture Approved: Hybrid model (Algo core + AI overlay). LangGraph chosen as orchestrator. 
- [2026-04-01] IP Protection strategy finalized: Cython compilation of B2B logic into .pyd files.
- [2026-03-11] sigma-brain wired as Chief of Staff with 6 specialized agents
- [2026-03-07] Phase 1 installation completed — Paperclip + OpenFang installed

## Next Decision Point
- Answer 5 open environment questions (Keys, VPS, Data format, Python version, Source paths)
- Execute Phase 0 (LangGraph Foundation) and Phase 1 (Cython IP Protection).
- Review MT5 B2B cluster fix options (A/B/C) and approve one approach
