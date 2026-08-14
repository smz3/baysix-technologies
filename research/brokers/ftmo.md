# Retail Prop Firm — Execution Context

## What Is This

Prop firms that run a challenge model (pay a fee, pass DD/profit targets,
get funded). Primary example: FTMO. Others: The5ers, MyForexFunds (defunct),
Funded Engineer, etc.

## Status

FUTURE STATE. Do not build this until Darwinex Zero is live and profitable.
Rationale: prop challenge fees are sunk cost if strategy is not proven.
Prove it on Darwinex first, then use that track record to de-risk the challenge.

## Connection Method — ONNX Preferred

**ONNX inside MQL5 EA** (self-contained, no external dependency)

Why ONNX over DWX Connect here:
- FTMO rules are ambiguous on external signal bridges
- ONNX is fully self-contained inside the EA — no grey area
- Train HMM/ML models in Python → export .onnx → embed in MQL5 EA
- MQL5 OnnxRun() handles inference natively (microsecond latency)
- FTMO cannot object: there is no external signal service

DWX Connect is a grey area for FTMO because it depends on an external
Python process. FTMO's rule: trading must be replicable on live accounts
and must not resemble copy trading / external signal services.

## Key FTMO Rules (research as of 2025-2026)

| Rule | Detail |
|------|--------|
| Daily DD limit | 5% of account balance |
| Max DD limit | 10% of account balance (trailing or fixed, check account type) |
| Profit target | 10% (Challenge Phase 1), 5% (Phase 2) |
| Minimum trading days | 4 days (Phase 1), 4 days (Phase 2) |
| News trading | Allowed on most accounts — verify before deploying |
| Hyperactivity | Max 2,000 server requests/day — irrelevant at H4/D1 |
| EAs | Fully allowed |
| External signals | Grey area — use ONNX to avoid ambiguity |
| Weekend holding | Some accounts restrict — verify |

## Build Dependencies (in order)

1. Darwinex Zero must be live and profitable first
2. HMM regime model trained in Python and exported to ONNX
3. MQL5 EA loads .onnx model natively
4. DD monitor built into MQL5 EA (5% daily, 10% max)
5. Paper test on FTMO demo before challenge

## ONNX Workflow

```
Python (alpha-engine):
  train HMM regime model
  → export model.onnx

b2b-mt5/brokers/retail-prop-firm/:
  MQL5 EA loads model.onnx via OnnxCreate()
  → runs OnnxRun() at each bar
  → applies DD checks
  → executes signal internally
```

## Firms To Evaluate (when ready)

- FTMO — most established, strict rules, good reputation
- The5ers — more flexible scaling, less strict challenge
- Funded Engineer — newer, check current standing before applying

## Status

FUTURE STATE. No active challenge. No active account.
