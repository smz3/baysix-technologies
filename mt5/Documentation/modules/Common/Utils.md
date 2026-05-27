# Utils.mqh

## Purpose
Miscellaneous utility functions used across multiple modules. Currently houses two key helpers: a font-name converter and a high-performance bar index lookup. Keeps one-off helpers out of detection and trading modules so those stay focused on their core logic.

## Layer
Common

## Key Classes & Functions

| Name | Type | Description |
|------|------|-------------|
| `FontEnumToString(font)` | Function | Converts font enum value to the string name MT5 chart objects expect |
| `FindBarIndexByTime(rates[], time)` | Function | Binary search through a rates array to find the bar at a given timestamp. Handles MQL5's descending sort (newest bar at index 0). |

## Inputs / Outputs
- **`FindBarIndexByTime`**: Takes a `MqlRates[]` array and a `datetime` target. Returns the integer bar index, or `-1` if not found.
- **`FontEnumToString`**: Takes a font enum, returns `string`.

## Dependencies
- `Defines.mqh`
- `Structures.mqh`

## Python Equivalent
No direct equivalent file. In sigma-crypto, bar lookups are done via pandas `.loc[]` or `.searchsorted()` on the DataFrame index. Font handling does not apply (Python uses matplotlib/plotly).

## Notes
- `FindBarIndexByTime` is performance-critical — it is called repeatedly during zone status updates across 9 timeframes. The binary search keeps this O(log n) instead of O(n).
- MQL5 rates arrays are sorted descending (index 0 = most recent bar), which is the opposite of most Python DataFrames. The binary search accounts for this.
