# Broker Execution Contexts

Each sub-folder represents one deployment target for Baysix signals.
Agents reading this: check the CONTEXT.md inside each folder before doing
any broker-specific work. Rules differ significantly per broker.

## Execution Architecture

```
Python Signal Engine (sigma-are)
  │
  ├── MT5 path → DWX Connect (file-based) → MT5 EA (thin executor)
  │     ├── darwinex-zero/     ← primary target, income engine
  │     ├── retail-prop-firm/  ← FTMO etc., future state
  │     └── high-leverage-broker/ ← JustMarkets etc.
  │
  └── Direct API path → Python broker SDK
        ├── ikbr/              ← equities strategy deployment
        └── moomoo-webull/     ← APAC retail, future state
```

## Status Summary

| Broker | Type | Connection | Status |
|--------|------|------------|--------|
| Darwinex Zero | Prop (performance fee) | DWX Connect → MT5 | Primary target |
| Retail Prop Firm (FTMO) | Prop (challenge) | ONNX in MQL5 | Future state |
| High Leverage Broker (JustMarkets) | Retail | DWX Connect → MT5 | Re-strategizing |
| IKBR | Institutional retail | Python IBKR API | Future — equities |
| Moomoo / Webull | Retail APAC | Python API | Future — APAC |

## Key Rule: Never Mix Broker Logic

Signal generation (sigma-are) is broker-agnostic. All broker-specific rules
(DD limits, D-Leverage, position sizing constraints) live inside this
brokers/ folder ONLY. The Python signal engine sends the same signal packet
to all brokers. Each broker adapter applies its own rules before execution.
