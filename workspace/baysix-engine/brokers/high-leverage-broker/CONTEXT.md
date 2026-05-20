# High Leverage Broker — Execution Context

## What Is This

Standard retail brokers offering high leverage (1:100 to 1:500) on CFDs/forex.
Primary example: JustMarkets (current broker for XAUUSD B2B live trading).
Others: Exness, FP Markets, IC Markets, Pepperstone.

## Current Status

RE-STRATEGIZING. No live MT5 running as of 2026-05-16.
Previously live on JustMarkets XAUUSD with semi-automated B2B EA.

## Role In Architecture

This broker tier is the lowest-stakes live trading environment:
- Fewest rules and restrictions
- Good for initial live deployment after OOS validation
- First place to go live AFTER paper trading confirms bridge works
- Before Darwinex (which has D-Leverage and homogeneity requirements)

Suggested sequence: Paper → JustMarkets live → Darwinex Zero

## Connection Method

**DWX Connect** (preferred) or standard MQL5 EA
- Since there are no restrictions here, DWX Connect is safe and clean
- Alternatively, run standard self-contained MQL5 EA
- For initial live test of bridge architecture, use this broker first

## Key Considerations

| Factor | Detail |
|--------|--------|
| Leverage | Up to 1:3000 on XAUUSD — use with care, position size via Python |
| Regulation | Check jurisdiction — JustMarkets is offshore (Seychelles/SVG) |
| Slippage | Higher than institutional, especially during news |
| Overnight swap | XAUUSD carries significant overnight financing — model in cost_registry |
| Restrictions | Minimal — EAs, bridging, all allowed |
| Reliability | Monitor uptime — some offshore brokers have server issues |

## JustMarkets Specific

- Account: Standard or Pro (tighter spread)
- XAUUSD spread: ~3 bps typical (modeled in cost_registry as cfd_gold)
- Overnight financing: ~3.5% annual (already in cost_registry)
- MT5 platform: standard MT5 build

## Build Dependencies

1. DWX Connect bridge built and tested (paper mode)
2. B2B Python signal engine validated (Phase 0 + Phase 1)
3. Start small: 0.01 lots minimum position
4. Scale up only after 20+ live trades confirm signal integrity

## Status

RE-STRATEGIZING. Will re-deploy after Phase 0 B2B rebuild completes.
