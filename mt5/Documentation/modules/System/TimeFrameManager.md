# TimeFrameManager.mqh

## Purpose
Manages the 9-timeframe pair system and handles new bar detection. The EA needs to know when a new bar has opened on each TF to trigger zone detection and status updates. This module tracks the last-seen bar time per TF and exposes "new bar" events. It also defines which TFs are paired (primary ↔ secondary), enabling the strategy to look up companion timeframes for confluence checks.

## Layer
System

## Key Classes & Functions

| Name | Type | Description |
|------|------|-------------|
| `S_TimeFramePair` | Struct | Pairs two ENUM_TIMEFRAMES: a primary and its secondary companion |
| `CTimeFrameManager` | Class | TF pair registry and new bar detector |
| `IsNewBar(tf)` | Method | Returns true if a new bar has formed on the given TF since last call. Updates internal last-bar-time if so. |
| `GetTimeFramePair(index)` | Method | Returns `S_TimeFramePair` for pair at given index |
| `TotalPairs()` | Method | Returns total number of TF pairs defined (8) |
| `GetSecondaryTimeFrame(primary_tf)` | Method | Given a primary TF, returns its paired secondary TF |
| `GetPrimaryTimeFrame(secondary_tf)` | Method | Reverse lookup: given secondary, returns primary |
| `IsPrimaryTimeFrame(tf)` | Method | True if TF is designated as primary in any pair |
| `TimeFrameToIndex(tf)` | Method | Convert ENUM_TIMEFRAMES to 0-8 array index |

## TF Pairs (8 pairs, 9 unique TFs)

| Index | Primary | Secondary | Purpose |
|-------|---------|-----------|---------|
| 0 | MN1 | W1 | Monthly narrative + Weekly filter |
| 1 | W1 | D1 | Weekly narrative + Daily filter |
| 2 | D1 | H4 | Daily narrative + H4 control |
| 3 | H4 | H1 | Control + Entry anchor |
| 4 | H1 | M30 | Entry anchor + M30 precision |
| 5 | M30 | M15 | M30 + M15 precision |
| 6 | M15 | M5 | M15 + M5 precision |
| 7 | M5 | M1 | M5 + M1 scalp |

## Inputs / Outputs
- **`IsNewBar(tf)`**: No input beyond TF identifier; internally queries `iTime()` via MT5 API. Returns bool.
- **`TimeFrameToIndex`**: ENUM_TIMEFRAMES → int (0–8)

## Dependencies
- `Defines.mqh`

## Python Equivalent
`sigma_core/sigma_core/b2b/...` → `core/system/timeframe_mgr.py` — `TimeframeManager` class. Python version tracks state across a dictionary of TF → last_processed_time. New bar detection is implicit in the vectorized backtester (it iterates bar-by-bar), and explicit in a live trading adapter.

## Notes
- `IsNewBar` must be called once per TF per `OnTick()` iteration — calling it multiple times on the same tick for the same TF will return false on the second call (state is updated on first call)
- `TOTAL_TIMEFRAMES = 9` (from `Defines.mqh`) but only 8 pairs — M1 only appears as a secondary, never as a primary
- The pair system encodes the strategy's confluence philosophy: every entry TF has a companion that provides context
