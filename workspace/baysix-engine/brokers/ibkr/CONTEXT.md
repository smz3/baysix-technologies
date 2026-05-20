# Interactive Brokers (IKBR) — Execution Context

## What Is This

Interactive Brokers is an institutional-grade retail/semi-institutional broker.
Primary use case here: executing the equities alpha strategies (cross-sectional
momentum, stat arb) built in the ARE equity adapters.

## Why IKBR (Not MT5)

IKBR is NOT an MT5 broker. It has its own TWS (Trader Workstation) platform
and a first-class Python API. For equities strategies, IKBR is the correct
execution layer — not MT5.

This means equities signals flow:
```
sigma-are (Python) → IBKR Python API → IKBR execution
```
No MT5 involved. No DWX Connect. Pure Python end-to-end.

## Connection Method

**ib_insync** (Python library, community-maintained wrapper for IBKR TWS API)
- Clean async Python interface
- Supports: stocks, ETFs, options, futures, forex
- Requires TWS or IB Gateway running locally or on VPS
- Paper trading account available for testing

Alternative: **ibapi** (official IBKR API, lower-level, more verbose)

## Key Rules and Considerations

| Factor | Detail |
|--------|--------|
| Pattern Day Trader | US accounts: <25K USD triggers PDT rule (max 3 day trades/week) |
| Minimum account | ~10K USD practical minimum for equities |
| Margin | Reg T margin (US retail) — 50% initial, 25% maintenance |
| Commission | ~0.005 USD/share or 0.35-1.0 USD minimum per trade (tiered pricing) |
| Short selling | Available on most S&P 500 names via IB's securities lending |
| Data fees | Market data subscriptions required for real-time — ~15-30 USD/mo |
| Fractional shares | Available for certain ETFs |
| API availability | TWS must be running — schedule auto-restart |

## Relevant Strategies

- Cross-sectional momentum (11 SPDR ETFs → S&P 500)
- Statistical arbitrage pairs
- Portfolio rebalancing (weekly/monthly)

All of these are LOW frequency (daily/weekly). IKBR API latency is irrelevant.

## Account Structure Recommendation

1. Open IBKR paper account first (free, no approval needed)
2. Test full Python → IBKR API → order execution pipeline
3. Open live account with small capital (5-10K USD)
4. Scale as track record develops

## Build Dependencies

1. ARE equities adapter must be built and validated (sigma-are)
2. LEAN backtest must pass OOS validation (sigma-lean)
3. ib_insync execution adapter built and paper-tested
4. Portfolio construction layer built (signal weighting, rebalancing)
5. Go live with small capital

## Status

FUTURE STATE. Build after equities ARE is complete.
