# OrderManager.mqh

## Purpose
The execution arm of the EA — the only module that places real trades on the broker. Implements the "Sniper Protocol" (motto: "One Shot, One Kill"): strict 1-trade-per-zone policy with zone-based deduplication to prevent repeat entries on the same signal. Wraps MT5's `CTrade` library with additional safety checks before each order.

## Layer
Trading

## Key Classes & Functions

| Name | Type | Description |
|------|------|-------------|
| `COrderManager` | Class | Trade execution with safety gates |
| `Initialize()` | Method | Setup CTrade wrapper, wire dependencies |
| `ExecuteSignal(signal)` | Method | **Core**: Execute a fully validated, risk-calculated `TradeSignal`. Includes survival gate, zone deduplication, order send, and logging. |
| `PassesSurvivalGate(signal)` | Method | Pre-execution check: signal direction matches HTF narrative |
| `IsWithinSurvivalSession(time)` | Method | Check if current time is within allowed trading session |
| `TradeExistsForZone(zone_id)` | Method | Returns true if a trade is already open for this zone_id — prevents duplicate entries |
| `SetMagicNumber(magic)` | Method | Set EA magic number for order tagging |
| `CloseAllTrades()` | Method | Emergency: close all open positions |
| `CloseAllPositions()` | Method | Alias for CloseAllTrades |
| `GetOpenPositionCount()` | Method | Returns count of open positions tagged with EA's magic number |
| `ModifyPosition(ticket, sl, tp)` | Method | Modify SL/TP of existing position |
| `ClosePosition(ticket)` | Method | Close specific position by ticket |
| `ForceCloseByDirection(direction)` | Method | Close all positions in a given direction |

## Execution Flow (ExecuteSignal)

```
1. PassesSurvivalGate()    → reject if HTF narrative disagrees
2. IsWithinSurvivalSession() → reject if outside allowed hours
3. TradeExistsForZone()    → reject if zone already has open trade
4. RiskManager.CanOpenNewPosition() → reject if risk limits hit
5. RiskManager.CalculateRiskBasedLot() → compute position size
6. CTrade.Buy() / CTrade.Sell() → send order to broker
7. B2BTradeTracker.RecordTradeOpen() → stamp zone with trade data
8. QuantLogger.LogTrade() → write to CSV
```

## Inputs / Outputs
- **`ExecuteSignal`**: Takes `TradeSignal` struct → attempts broker order → returns bool (success/failure)
- **`TradeExistsForZone`**: Takes zone_id (long) → returns bool

## Dependencies
- `Trade.mqh` (MT5 standard library)
- `TradingParameters.mqh`
- `TradeSignalGenerator.mqh`
- `QuantLogger.mqh`
- `MetricCalculator.mqh`

## Python Equivalent
`core/execution/trade_manager.py` — `TradeManager.execute(signal)`. Same pattern: validation → sizing → position creation → ledger update. Python version simulates execution against bar data rather than sending to a broker; deduplication uses a `set` of active zone_ids.

## Notes
- **Magic number tagging**: All orders are tagged with the EA's magic number so `GetOpenPositionCount` counts only this EA's trades, not manual positions
- The 1-trade-per-zone rule is enforced by `TradeExistsForZone()` — this prevents the signal generator from re-entering a zone that's already being traded, even if the zone reaches a deeper touch level
- Slippage tolerance is set in `TradingParameters.mqh` — if the broker fills at a price worse than `entry ± slippage`, the order is rejected
