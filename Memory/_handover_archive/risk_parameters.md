# Risk Parameters
Last Updated: 2026-03-11
Authority: Risk Manager Agent + Human Confirmation Required to Change

## Fund-Level Hard Limits

| Parameter | Limit | Current Status |
|-----------|-------|----------------|
| Max Portfolio Drawdown | 20% | Monitoring |
| Max Single Position Size | 5% of equity | Enforced via sizing.py |
| Max Leverage | 3x | Config enforced |
| Max Consecutive Losses | 5 | Alert threshold |
| Daily Loss Limit | 5% of equity | Kill trigger |
| Max Correlated Positions | 3 | Manual review |

## Kill Switch Conditions

Halt all new entries immediately if ANY of the following:
1. Portfolio drawdown exceeds **20%** from equity high
2. Daily loss exceeds **5%** of equity
3. **5 consecutive losing trades** on the same instrument
4. EA/system heartbeat gap > **4 hours** during market hours
5. Slippage on any single trade exceeds **3x** expected slippage

## Position Sizing Rules
- Base risk per trade: **1% of equity**
- Max risk per trade: **2% of equity** (only with CIO approval)
- Sizing method: Fixed fractional (not Kelly without explicit approval)
- Source of truth: `sigma-crypto/core/risk/sizing.py`

## Instrument-Specific Limits

### Crypto (Binance Futures — BTCUSDT)
- Max position: 5% equity
- Max leverage: 3x
- Minimum R:R required: 1.5:1

### Forex (MT5)
- Max position: 5% equity
- Max leverage: 10:1 (standard forex leverage, not retail max)
- Minimum R:R required: 1.5:1

## Escalation Protocol
- Any breach → quant-trader escalates to risk-manager immediately
- risk-manager assesses and recommends: pause / reduce / stop
- Human confirmation required before resuming after a kill event
- All kill events logged to: `Audit/security_alerts.log`

## Approval History
- [2026-03-11] Initial parameters set — baseline configuration
- [NEXT UPDATE] — Update after first live trading session review
