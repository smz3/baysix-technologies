# TrailingStopManager.mqh

## Purpose
Manages Break-Even (BE) and Trailing Stop (TS) adjustments for open positions. Called from `OnTick()`, it checks every active position and moves the stop-loss automatically once defined profit thresholds are hit. Version 7.0 added milestone tracking to avoid redundant SL modification calls on every tick.

## Layer
Trading

## Key Classes & Functions

| Name | Type | Description |
|------|------|-------------|
| `CTrailingStopManager` | Class | Position SL management |
| `Initialize()` | Method | Setup internal state arrays |
| `UpdateAllPositions()` | Method | **Core (call from OnTick)**: Loop through all open positions, apply BE and trailing stop logic to each |
| `ProcessPosition(position_info)` | Method | Per-position logic: determine if BE or TS should be applied |
| `ApplyBreakEven(ticket, entry_price)` | Method | Move SL to entry price (breakeven), tagged so it is not re-applied |
| `ApplyTrailingStop(ticket, current_price, sl_price)` | Method | Move SL toward current price by configured step |
| `IsBEApplied(ticket)` | Method | Returns true if breakeven has already been applied to this ticket |
| `MarkBEApplied(ticket)` | Method | Record that BE has been applied — prevents re-application |
| `GetProfitInPoints(ticket)` | Method | Returns current unrealized profit in points for a position |

## Break-Even Logic

```
IF GetProfitInPoints(ticket) >= be_trigger_points:
    IF NOT IsBEApplied(ticket):
        ApplyBreakEven(ticket, entry_price)
        MarkBEApplied(ticket)
```

## Trailing Stop Logic

```
IF IsBEApplied(ticket):
    new_sl = current_price - trailing_distance (for long)
    IF new_sl > current_sl:  // only move SL in profit direction
        ApplyTrailingStop(ticket, current_price, new_sl)
```

## Inputs / Outputs
- **`UpdateAllPositions`**: No inputs; queries MT5 position list directly. Modifies open position SL/TP via broker API.
- **`ApplyBreakEven`**: Takes ticket + entry price → sends `CTrade.PositionModify()` to broker

## Dependencies
- `Trade.mqh` (MT5 standard library)
- `TradingParameters.mqh`

## Python Equivalent
No equivalent in sigma-crypto backtester — trailing stop is simulated as a fixed parameter in `VectorizedBacktester.run()` rather than as a live management module. In a LEAN-based live system, this logic would be implemented as a `RiskManagementModel`.

## Notes
- **V17 milestone tracking**: Instead of checking profit on every tick (expensive), the manager tracks profit milestones (e.g., 10pts, 20pts, 30pts) and only re-evaluates when a new milestone is crossed
- BE trigger and trailing step distance are both configurable in `TradingParameters.mqh`
- Trailing stop only moves in the profitable direction — it never widens the stop loss
- `IsBEApplied` uses a ticket-keyed array — this state survives across ticks but not across EA restarts (resets on init)
