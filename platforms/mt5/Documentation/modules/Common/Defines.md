# Defines.mqh

## Purpose
Global constants and enumerations shared across every module. Acts as the "vocabulary" of the system — defines what timeframes exist, how many zones are allowed per TF, what directions and session types are recognised, and what bitmask flags mean. Without this file, every module would need to duplicate these definitions or use magic numbers.

## Layer
Common

## Key Classes & Functions

| Name | Type | Description |
|------|------|-------------|
| `TOTAL_TIMEFRAMES` | Constant | `9` — M1, M5, M15, M30, H1, H4, D1, W1, MN1 |
| `MAX_B2B_ZONES_PER_TF` | Constant | `600` — max zones stored per timeframe |
| `MAX_HISTORICAL_SWINGS` | Constant | `1000` — max swing points in memory |
| `ZONE_CHANGE_STRUCTURAL` | Bitmask | Bit 0 — zone geometry changed |
| `ZONE_CHANGE_METRIC` | Bitmask | Bit 1 — zone metrics updated (touch count, age) |
| `ENUM_SIGNAL_DIRECTION` | Enum | `NONE`, `BULLISH`, `BEARISH` |
| `ENUM_SWING_TYPE` | Enum | `NONE`, `HIGH`, `LOW` |
| `ENUM_TRADING_SESSION` | Enum | `DEAD_ZONE`, `ASIA`, `LONDON`, `NY`, `OVERLAP` |
| `ENUM_TP_DEPTH` | Enum | `T1`, `T2`, `T3` — entry tier within a zone |
| `ENUM_VECTOR_ANCHOR` | Enum | `OFF`, `H1`, `H1_H4`, `H4` — HTF anchor mode |

## Inputs / Outputs
- **Inputs:** None
- **Outputs:** Compile-time constants and enum types available globally

## Dependencies
None — this is the lowest-level file in the include chain.

## Python Equivalent
`sigma_core/sigma_core/b2b/models/structures.py` — contains `SignalDirection`, `SwingType` enums and `DetectionConfig` dataclass. Session enums are handled in `core/system/timeframe_mgr.py`.

## Notes
- Change `MAX_B2B_ZONES_PER_TF` carefully — it affects memory allocation for every timeframe simultaneously
- Bitmask flags (`ZONE_CHANGE_*`) are used as return values from `CB2BZoneStatus::UpdateZoneStatus()` to signal what changed without returning multiple values
