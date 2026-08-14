# Structures.mqh

## Purpose
Defines the core data types (structs) that flow through every layer of the system. Everything else — detectors, managers, visualizers, loggers — operates on these structs. Think of this as the "schema" file: if you want to understand what a B2B zone is or what a swing point looks like in memory, this is the file to read.

## Layer
Data

## Key Classes & Functions

| Name | Type | Description |
|------|------|-------------|
| `RawBreakoutInfo` | Struct | A single breakout event: which swing was broken, at what price/time, in which direction, and what the impulse start price was |
| `SwingPointInfo` | Struct | A single swing high or low: price, time, bar close, type (HIGH/LOW), whether it has been broken, and cache metadata |
| `B2BZoneInfo` | Struct | The main zone object: L1/L2 prices, direction, TF, creation time, age, touch tracking (T1/T2/T3), trade lifecycle data, confluence flags, and persistence metadata |
| `B2BZoneList` | Struct | Dynamic array wrapper — one instance per timeframe, holds an array of `B2BZoneInfo` |
| `TimeFrameDataCache` | Struct | Per-TF snapshot of the `MqlRates[]` array and its bar count |

## Field Highlights — B2BZoneInfo

| Field | Description |
|-------|-------------|
| `zone_id` | Deterministic FNV-1a hash of L1/L2/TF/direction/time — used as stable unique key |
| `L1_price` / `L2_price` | Entry level and invalidation level |
| `L1_touched`, `fifty_touched`, `L2_touched` | Touch tracking flags for T1, mid-zone, and T3 |
| `was_traded` | True once a trade has been placed from this zone |
| `entry_price`, `sl_price`, `tp_price` | Filled when zone is traded |
| `max_adverse_excursion`, `max_favorable_excursion` | MAE/MFE tracking during live trade |
| `is_multi_parent` | True if this zone is nested inside multiple HTF parent zones |
| `is_confluence_zone` | True if another zone overlaps this one |
| `is_invalidated` | True when price has closed beyond L2 |
| `rr_planned` | Risk/reward ratio at entry |

## Inputs / Outputs
- **Inputs:** None — pure data definitions
- **Outputs:** Struct types available to all modules that include this file

## Dependencies
- `Defines.mqh`

## Python Equivalent
`sigma_core/sigma_core/b2b/models/structures.py` — contains `B2BZoneInfo`, `SwingPointInfo`, `TradeSignal` as Python dataclasses. Field names are closely mirrored. `RawBreakoutInfo` maps to `Breakout` dataclass in `sigma_core/b2b/detectors/breakouts.py`.

## Notes
- `B2BZoneInfo` is the most frequently read/written struct in the system — nearly every module touches it
- `zone_id` is deterministic, meaning the same zone detected on a backtest will have the same ID as in live trading (enables data reconciliation between CSV logs and database)
- `B2BZoneList` exists because MQL5 does not support dynamic arrays of structs inside other structs — the wrapper provides a clean interface
