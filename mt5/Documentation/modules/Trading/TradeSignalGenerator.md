# TradeSignalGenerator.mqh

## Purpose
The central signal orchestrator. Receives the current price, active zones, and a zone-change bitmask on every tick, then decides whether a trade signal should be generated. Routes to either the Russian Doll strategy (multi-TF confluence) or the Intraday strategy depending on configuration. Owns the `ContextMapper` and `IntradayOrchestrator` instances.

## Layer
Trading

## Key Classes & Functions

| Name | Type | Description |
|------|------|-------------|
| `CTradeSignalGenerator` | Class | Signal orchestration hub |
| `Initialize(detector, risk_mgr, order_mgr)` | Method | Wire up detector, risk, and execution dependencies |
| `SetDirty()` | Method | Flag that zones have changed — gates re-evaluation logic |
| `OnTick(price, time, ask, bid, zones[], change_mask)` | Method | **Core entry point**: Called from EA's `OnTick`. Routes to Russian Doll or Intraday. |
| `ProcessRussianDollStrategy(price, time, zones[])` | Method | Multi-TF confluence signal generation via `StrategyOrchestrator` |
| `ProcessIntradayStrategy(price, time, zones[])` | Method | Intraday-specific signal generation via `IntradayOrchestrator` |
| `SendTradeSignal(signal)` | Method | Submit validated signal to `OrderManager.ExecuteSignal()` |

## Signal Flow

```
OnTick()
├── IF change_mask has ZONE_CHANGE_STRUCTURAL → mark dirty
├── IF dirty OR new bar:
│   ├── ContextMapper.EvaluateContext()     ← update spatial map
│   ├── ProcessRussianDollStrategy() OR ProcessIntradayStrategy()
│   │   ├── For each entry zone:
│   │   │   ├── StrategyOrchestrator.IsTradeAllowed()  ← Gate 1+2+3
│   │   │   ├── IF allowed → build TradeSignal
│   │   │   └── SendTradeSignal()
│   └── Reset dirty flag
```

## Inputs / Outputs
- **`OnTick`**:
  - Input: current ask/bid, timestamp, zones array, change_mask from zone status update
  - Output: may call `OrderManager.ExecuteSignal()` — no direct return value
- **`change_mask`**: Bitmask from `CB2BZoneStatus::UpdateZoneStatus()` — used to skip re-evaluation when nothing changed

## Dependencies
- `Defines.mqh`, `Structures.mqh`
- `B2BDetector.mqh`, `SwingPointDetector.mqh`, `RawBreakoutDetector.mqh`
- `TradingParameters.mqh`, `OrderManager.mqh`
- `StrategyOrchestrator.mqh`, `RiskManager.mqh`
- `ContextMapper.mqh`, `IntradayOrchestrator.mqh`

## Python Equivalent
`core/strategy/scanner.py` — `SignalScanner.scan(symbol, zones, low, high, close, time, ...)`. Same responsibility: evaluate zones against flow state, generate `TradeSignal` objects. Python version does not have the `SetDirty()` pattern (backtester evaluates every bar by design).

## Notes
- **Logging muzzle**: A debounce mechanism prevents the same zone from generating repeated log entries on consecutive ticks — reduces journal noise
- **Last check time**: Tracks when each TF was last evaluated. Skips re-evaluation if no new bar has formed and `dirty` is false — major tick performance optimization
- The `change_mask` pattern is a key performance innovation: downstream modules only re-run expensive logic when something structurally changed, not every tick
