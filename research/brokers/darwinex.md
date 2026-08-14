# Darwinex Zero — Execution Context

## What Is This

Darwinex Zero is a performance-fee prop account. You trade your own capital,
Darwinex allocates investor funds on top once you reach SILVER/GOLD tier.
No challenge to pass — you deploy and they assess your Darwin (track record).

## Why This Is Primary Target

- No challenge fee risk (unlike FTMO)
- Income scales with track record quality
- Officially supports Python bridge trading (they built DWX Connect)
- B2B XAUUSD strategy directly deployable here
- √Time scoring rewards H4/D1 hold periods — compatible with B2B architecture

## Connection Method

**DWX Connect** (official Darwinex library, file-based)
- GitHub: https://github.com/darwinex/dwxconnect
- No ZeroMQ dependency (old connector archived Feb 2022)
- MT5 EA: dwx_server_mt5.mq5 installed in Experts folder
- Python client: reads/writes files in MQL5/Files/ directory
- Same machine: Python process + MT5 terminal on same VPS

## Key Rules (confirmed via Darwinex support, 2026-05-15)

| Rule | Detail |
|------|--------|
| √Time scoring | Dynamic over position lifespan — M5 entry, H4/D1 target = meaningful score |
| Homogeneity | Assessed from executed profile only — multi-TF confluence compatible |
| D-Leverage | VaR-based — must stay within limits at all times |
| Correlation | <95% with other Darwin strategies to qualify for allocation |
| Copy trading | Banned across accounts |
| EAs | Fully allowed |
| Python bridge | Officially supported (Darwinex built DWX Connect) |

## Progression

SILVER → GOLD progression based on track record length and consistency.
Do NOT rush to open account before Phase 0 B2B rebuild is complete.
The underlying detection engine must be OOS-validated (Sharpe >1.0, DD <15%)
before live deployment. A broken strategy on Darwinex damages the Darwin track
record permanently — there is no reset.

## Signal Packet (what Python sends)

```json
{
  "instrument": "XAUUSD",
  "direction": "BUY",
  "zone_score": 0.82,
  "entry_price": 2341.50,
  "stop_loss": 2328.00,
  "take_profit": 2368.00,
  "position_size_lots": 0.12,
  "regime": "risk_off",
  "ic_confidence": 0.71,
  "signal_id": "B2B-YYYYMMDD-NNN"
}
```

The Darwinex MT5 adapter applies D-Leverage check before executing.
If D-Leverage would breach limits, it reduces position size or skips the trade.

## Build Dependencies (in order)

1. Phase 0: Fix B2B cluster bug, validate OOS (alpha-engine + sigma-lean)
2. Phase 1: Build adapters/gold/ in alpha-engine (IC measurement)
3. Phase 2: Build DWX Connect bridge (b2b-mt5/brokers/darwinex-zero/)
4. Phase 3: Open Darwinex Zero account, paper trade first
5. Phase 4: Go live

## Status

NOT LIVE. Awaiting Phase 0 completion.
