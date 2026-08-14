# RiskManager.mqh

## Purpose
Controls position sizing and pre-trade risk checks. Calculates how many lots to trade given a risk percentage of account equity, the SL distance in price, and the instrument's tick value. Also enforces hard limits: max open positions, minimum free margin, and margin level floor. No trade enters the market without passing through this module's `CanOpenNewPosition()` gate.

## Layer
Trading

## Key Classes & Functions

| Name | Type | Description |
|------|------|-------------|
| `CRiskManager` | Class | Position sizing and account safety checker |
| `Initialize()` | Method | Query account info, set starting balance for daily tracking |
| `CalculateRiskBasedLot(signal, entry, sl)` | Method | **Core**: Computes lot size from risk% × equity ÷ (SL distance × tick value) |
| `NormalizeLotSize(lots)` | Method | Rounds to broker lot_step, clamps to min_lot/max_lot |
| `CanOpenNewPosition()` | Method | Returns bool — checks position count, margin level, daily loss cap |
| `GetCurrentMarginLevel()` | Method | Returns margin level % from MT5 account API |
| `GetCurrentPositionCount()` | Method | Returns count of open positions |
| `GetAccountBalance()` / `GetAccountEquity()` | Methods | Account value queries |
| `GetFreeMargin()` | Method | Free margin query |
| `GetAccountLeverage()` | Method | Broker leverage query |
| `GetPositionSummary(out_string)` | Method | Format position count + P&L as display string |
| `PrintAccountInfo()` | Method | Log full account snapshot to MT5 journal |

## Position Sizing Formula
```
lot_size = (equity × risk_pct) / (sl_distance_in_points × point_value × lot_units)
```
- `risk_pct` from `TradingParameters.mqh` (e.g., 1% = 0.01)
- `sl_distance_in_points` = abs(entry - sl) / symbol point size
- Result normalized via `UniversalSymbolManager.NormalizeLotSize()`

## Inputs / Outputs
- **`CalculateRiskBasedLot`**: Takes signal struct, entry price, SL price → returns normalized lot as double
- **`CanOpenNewPosition`**: No inputs → returns bool (true = trade allowed)

## Dependencies
- `UniversalSymbolManager.mqh`
- `TradingParameters.mqh`
- `Structures.mqh`

## Python Equivalent
`sigma_core/sigma_core/b2b/...` → `core/risk/sizing.py` — `RiskCalculator.calculate_sl_and_size(symbol, entry, L2, direction, balance)`. Same formula. Python version also has `check_exposure(positions)` for the position count gate. No margin level check (Python backtester does not simulate margin).

## Notes
- Daily balance is stored at EA init — `CanOpenNewPosition` checks if current equity has dropped more than `max_daily_loss_pct` below that starting value
- Margin level floor is configurable in `TradingParameters.mqh` (default: 200% margin level required before opening)
- This module never places orders — it only calculates and gates. `OrderManager` is responsible for actual execution.
