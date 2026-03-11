# Research Queue
Last Updated: 2026-03-11
Owner: Quant Researcher + Memory Curator

## Active Queue

| Priority | Task | Assigned To | Status | Added |
|----------|------|-------------|--------|-------|
| HIGH | Evaluate MT5 B2B cluster fix — option A vs B vs C from B2B_CLUSTER_FIX_PLAN.md | Quant Researcher → Quant Developer | Pending | 2026-03-11 |
| HIGH | Validate Test 13A OOS results for production readiness (slippage, live fills assumption) | Quant Researcher | Pending | 2026-03-11 |
| MEDIUM | Compare SAMTC performance on BTC vs ETH vs SOL perps | Quant Researcher | Pending | 2026-03-11 |
| MEDIUM | Stress test: What happens to Test 10C under 2022-style bear market conditions? | Quant Researcher + Quant Developer | Pending | 2026-03-11 |
| LOW | Research whether SAMTC signal can be adapted for intraday (M15/M30 timeframes) | Quant Researcher | Backlog | 2026-03-11 |
| LOW | Evaluate whether sigma-linkedin posts correlate with any traffic/opportunity metrics | Quant Researcher | Backlog | 2026-03-11 |

## Completed Research

| Task | Outcome | Date |
|------|---------|------|
| sigma-brain architecture design | 6-tier enterprise architecture documented in Braindump/ | Pre 2026-03-11 |
| Phase 1 installation | Paperclip + OpenFang installed, company configured as Baysix | 2026-03-07 |
| 7-year backtest validation | Monte Carlo 10,000-iteration convergence validated | Pre 2026-03-11 |

## Research Principles
- Every hypothesis must have a falsifiable test
- OOS validation required before any live deployment
- Monte Carlo convergence (10,000 iterations) required for new strategies
- Document all findings in `sigma-crypto/research/reports/` or `sigma-mt5/Documentation/`
