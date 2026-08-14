# QuantLogger.mqh

## Purpose
Writes trade and zone lifecycle events to CSV files so a Python loader can push them to Supabase. This is the primary data pipeline between the MT5 EA and the external data science stack. Version 6.0 added "Phase 0 Zone Logging" — every zone creation, touch, survival, and invalidation is now logged in addition to trade outcomes.

## Layer
Data

## Key Classes & Functions

| Name | Type | Description |
|------|------|-------------|
| `CQuantLogger` | Class | CSV writer for trade and zone events |
| `Initialize()` | Method | Open/create CSV files, write headers |
| `LogTrade(export)` | Method | Write a completed `QuantTradeExport` to trades CSV |
| `ReconcileHistory()` | Method | Sync backtest trade history from MT5 account history (avoids missed trades) |
| `ExportCSV()` | Method | Flush buffers to disk |
| `LogParameters()` | Method | Snapshot current EA input parameters to CSV |
| `GetTradingSession(time)` | Method | Map datetime to `ENUM_TRADING_SESSION` (ASIA/LONDON/NY/OVERLAP) |
| `GetTradingSessionZone(time)` | Method | Return session string label |
| `GetTouchQuarterZone(touch_pct)` | Method | Map touch percentage to zone quarter (T1/mid/T3) |
| `ToCSV(export)` | Method | Serialize `QuantTradeExport` struct to a CSV row string |
| `LogZoneCreated(zone)` | Method | Log new zone detection event |
| `LogZoneTouched(zone, touch_type)` | Method | Log T1/T2/T3 touch event |
| `LogZoneSurvived(zone)` | Method | Log that zone survived a touch (price bounced) |
| `LogZoneBulldozed(zone)` | Method | Log that zone was invalidated (price blew through L2) |

## Inputs / Outputs
- **`LogTrade`**: Takes `QuantTradeExport` struct, appends one CSV row to `sigma_trades.csv`
- **`LogZone*`**: Takes `B2BZoneInfo`, appends one row to `sigma_zones.csv`
- **`GetTradingSession`**: Takes datetime, returns `ENUM_TRADING_SESSION`
- **Output files**: `sigma_trades.csv`, `sigma_zones.csv`, `sigma_params.csv`

## Dependencies
- `QuantTypes.mqh`
- `TradingParameters.mqh`
- `Structures.mqh`

## Python Equivalent
`scripts/supabase_push.py` in sigma-crypto reads from the CSV files this module generates and pushes rows to Supabase. The Python side of this pipeline is the consumer; `QuantLogger` is the producer. Session detection logic mirrors `core/system/timeframe_mgr.py`.

## Notes
- Zone logging (V6.0) generates `sigma_zones.csv` which tracks the full lifecycle of every zone — invaluable for hit-rate analysis (what % of zones get touched, what % survive, what % get bulldozed)
- `ReconcileHistory()` is called on EA init in backtest mode to catch trades that completed before the EA was loaded mid-session
- `LogParameters()` creates a timestamped parameter snapshot so every backtest run can be reproduced by matching its parameter CSV
