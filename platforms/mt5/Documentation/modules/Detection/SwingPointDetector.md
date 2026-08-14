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
| `IsSwingHigh(rates[], bar_index, window)` | Private | Window-based extrema test: bar's **close** strictly > all surrounding bars' **closes** |
| `IsSwingLow(rates[], bar_index, window)` | Private | Window-based extrema test: bar's **close** strictly < all surrounding bars' **closes** |

## Inputs / Outputs
- **`DetectLiveSwing`**: Takes rates array + bar index → appends confirmed `SwingPointInfo` to output array
- **`ValidateSwingPoint`**: Takes existing swing → returns bool (still valid or broken)
- **`CleanupInvalidatedSwings`**: Modifies swing array in-place, removing broken swings

## Dependencies
- `Structures.mqh`
- `Utils.mqh`

## Python Equivalent
`sigma_core/sigma_core/b2b/detectors/swing_points.py` — `detect_swings(df, config)` function. Uses close-based comparison (vectorized via pandas). **Both** implementations detect on **close** prices — verified against source ([SwingPointDetector.mqh](../../../Include/Sigma_System/V5.0/Detection/SwingPointDetector.mqh) lines 224–261: `candidate_close` vs `neighbor_close`). The configurable window (default 3) sets how many neighbouring bars the candidate close must exceed. (Earlier revisions of this doc claimed the MQL5 used bar highs/lows — that was wrong; `.high`/`.low` are read **only** for the wick-imprint fields below, never for detection.)

## Notes
- **STABLE — DO NOT MODIFY**: This file has a freeze tag. Detection logic changes must be discussed and validated against backtest before touching.
- Window size (default 3) is configurable via `TradingParameters.mqh`. Wider windows = fewer, more significant swings.
- `DetectLiveSwing` has a "forming bar shield" — it will not confirm a swing on the currently-forming bar (bar index 0) to prevent false signals that disappear when the bar closes.
- Swing imprint fields (`swing_imprint_top`, `swing_imprint_bottom`) store the full high/low of the swing bar, used later by zone status to compute the 50% level.
