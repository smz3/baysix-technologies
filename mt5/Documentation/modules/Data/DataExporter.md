# DataExporter.mqh

## Purpose
Exports zone and account data to JSON files so external tools (dashboards, Python analysis scripts) can read the current EA state without connecting to MT5 directly. Handles backtest and live modes differently — in backtest, it writes versioned snapshots; in live, it writes the current active zone set.

## Layer
Data

## Key Classes & Functions

| Name | Type | Description |
|------|------|-------------|
| `CDataExporter` | Class | Writes structured JSON to MT5's file sandbox |
| `Initialize(path)` | Method | Set output directory path |
| `ExportZoneData(zones[], stats)` | Method | Backtest zone export (basic) |
| `ExportZoneDataWithStats(zones[], stats)` | Method | Enhanced backtest export including performance metrics |
| `ExportActiveZones(zones[])` | Method | Live mode: export current active (non-invalidated) zones |
| `ExportAccountInfo()` | Method | Snapshot of account equity, balance, margin, open P&L |
| `IsBacktest()` | Method | Returns true if EA is in Strategy Tester |
| `IsOptimization()` | Method | Returns true if running an optimisation pass |
| `IsLive()` | Method | Returns true if running on a live/demo account |

## Inputs / Outputs
- **`ExportZoneData`**: Reads zone array, writes `zones_v{version}.json`
- **`ExportActiveZones`**: Filters invalidated zones, writes `active_zones.json`
- **`ExportAccountInfo`**: Queries MT5 account API, writes `account.json`
- Version scheme: `1a → 1b → ... → 1z → 2a → ...` (26-per-cycle alphabetic versioning)

## Dependencies
- `Defines.mqh`
- `Structures.mqh`
- `MetricCalculator.mqh`

## Python Equivalent
No direct equivalent. In sigma-crypto, backtest results are pushed to Supabase via `scripts/supabase_push.py`. The DataExporter is MT5-specific — its JSON output is what the sigma-quant dashboard reads from a local path during backtests.

## Notes
- **Safety**: Only writes to files — no network calls. MT5's file sandbox limits paths to `MQL5/Files/`.
- Versioned file naming prevents overwriting previous snapshots during long backtests, enabling replay analysis
- The live `ExportActiveZones()` is called on a timer (not every tick) to avoid I/O overhead on fast symbols
- `IsOptimization()` check allows the exporter to skip writes during parameter optimization runs (would generate thousands of files)
