# SwingPointDetector.mqh

## Purpose
Identifies swing highs and swing lows from bar data using a sliding window comparison. This is the "DNA layer" of the strategy — every downstream component (breakout detection, zone formation, flow state) depends on the quality of these swing points. Marked **STABLE — DO NOT MODIFY** because changing detection logic here ripples through the entire pipeline.

## Layer
Detection

## Key Classes & Functions

| Name | Type | Description |
|------|------|-------------|
| `CSwingPointDetector` | Class | Stateless swing detection engine |
| `DetectLiveSwing(rates[], bar_index, swings[])` | Method | Detect a swing at a specific bar using a rates window |
| `CheckForSwingHigh(rates[], bar_index)` | Method | Test if a bar is a historical swing high |
| `CheckForSwingLow(rates[], bar_index)` | Method | Test if a bar is a historical swing low |
| `ValidateSwingPoint(swing, rates[])` | Method | Retroactively validate that an existing swing still holds |
| `CleanupInvalidatedSwings(swings[])` | Method | Remove swings that have since been broken by price |
| `IsSwingHigh(rates[], bar_index, window)` | Private | Window-based extrema test: bar's high > all surrounding bars' highs |
| `IsSwingLow(rates[], bar_index, window)` | Private | Window-based extrema test: bar's low < all surrounding bars' lows |

## Inputs / Outputs
- **`DetectLiveSwing`**: Takes rates array + bar index → appends confirmed `SwingPointInfo` to output array
- **`ValidateSwingPoint`**: Takes existing swing → returns bool (still valid or broken)
- **`CleanupInvalidatedSwings`**: Modifies swing array in-place, removing broken swings

## Dependencies
- `Structures.mqh`
- `Utils.mqh`

## Python Equivalent
`sigma_core/sigma_core/b2b/detectors/swing_points.py` — `detect_swings(df, config)` function. Uses close-based 3-bar comparison (vectorized via pandas). The MQL5 version uses a configurable window (default 3) on bar highs/lows; the Python version uses close prices only — a documented philosophical difference.

## Notes
- **STABLE — DO NOT MODIFY**: This file has a freeze tag. Detection logic changes must be discussed and validated against backtest before touching.
- Window size (default 3) is configurable via `TradingParameters.mqh`. Wider windows = fewer, more significant swings.
- `DetectLiveSwing` has a "forming bar shield" — it will not confirm a swing on the currently-forming bar (bar index 0) to prevent false signals that disappear when the bar closes.
- Swing imprint fields (`swing_imprint_top`, `swing_imprint_bottom`) store the full high/low of the swing bar, used later by zone status to compute the 50% level.
