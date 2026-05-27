# B2BTradeTracker.mqh

## Purpose
Records and updates trade lifecycle data directly on the zone object. When a trade opens, the zone is stamped with entry price, SL, TP, and planned RR. During the trade, MAE/MFE are tracked tick-by-tick. When the trade closes, the exit price, reason, and P&L are written back. This keeps all zone metadata in one place — the zone knows its own trade history.

## Layer
Detection

## Key Classes & Functions

| Name | Type | Description |
|------|------|-------------|
| `CB2BTradeTracker` | Class | All-static trade lifecycle writer |
| `RecordTradeOpen(zone, entry, sl, tp, lot, time)` | Static | Stamp zone with trade entry details, mark `was_traded = true` |
| `RecordTradeClose(zone, exit_price, reason, pnl)` | Static | Write exit data to zone |
| `UpdateTradeExcursions(zone, current_low, current_high)` | Static | Update `max_adverse_excursion` and `max_favorable_excursion` |
| `SetZoneTraded(zone, level)` | Static | Mark zone as traded at specific touch level (T1/FIFTY/T2) |
| `CalculateRR(entry, sl, tp, direction)` | Static | Returns risk/reward ratio as double |

## Fields Updated on Zone

| Phase | Fields Written |
|-------|----------------|
| Trade Open | `was_traded`, `entry_level_used`, `entry_price`, `sl_price`, `tp_price`, `trade_open_time`, `rr_planned` |
| During Trade | `max_adverse_excursion`, `max_favorable_excursion` |
| Trade Close | `trade_close_time`, `exit_price`, `exit_reason`, `pnl` |

## Inputs / Outputs
- **`RecordTradeOpen`**: Takes zone reference + trade details → modifies zone in-place, no return value
- **`UpdateTradeExcursions`**: Takes zone reference + current bar's low/high → updates MAE/MFE if current values exceed stored values
- **`CalculateRR`**: Pure function, returns double

## Dependencies
- `Structures.mqh`

## Python Equivalent
`sigma_core/sigma_core/b2b/...` — trade tracking is handled in `core/execution/trade_manager.py` (`TradeManager.close_trade()`). In the Python version, trade data is stored in a separate trade ledger dict rather than written back to the zone object — a design difference from the MQL5 approach.

## Notes
- All methods are static — the class holds no state. It is a namespace for trade-writing functions.
- `UpdateTradeExcursions` is called on every tick while a zone has an open trade. MAE/MFE are running maximums — they only move outward, never inward.
- Writing trade data back onto the zone (rather than a separate trade object) enables the `QuantLogger` to export a complete zone+trade record in one struct — no join needed.
- `entry_level_used` distinguishes whether the trade was taken at T1 (L1), T2 (50% midpoint), or T3 (L2) — key for analysing which tier performs best.
