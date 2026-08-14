# RawBreakoutDetector.mqh

## Purpose
Detects when price closes beyond an existing swing point, creating a "raw breakout" event. This is the second step in the B2B pipeline: SwingPointDetector finds the swings; RawBreakoutDetector finds the moment one of those swings gets broken. It also identifies the "impulse swing" — the opposing swing that started the move toward the break — which becomes L2 in the zone.

## Layer
Detection

## Key Classes & Functions

| Name | Type | Description |
|------|------|-------------|
| `CRawBreakoutDetector` | Class | Stateless breakout detector, operates on a bar-by-bar basis |
| `Detect(bar_to_check, rates[], swings[], breakouts[])` | Method | Main detection: scans all unbroken swings, checks if the given bar's close broke any of them. Populates `found_breakouts[]`. |
| `FindImpulseSwingPrice(swings[], broken_swing, breakout_bar)` | Private | Finds the first swing of opposite type after the broken swing but before the breakout bar — this becomes the L2 impulse anchor |

## Inputs / Outputs
- **`Detect`**:
  - Input: bar index to check, rates array, current swing array
  - Output: appends `RawBreakoutInfo` structs to `found_breakouts[]`
  - Returns: count of breakouts found on this bar
- **`FindImpulseSwingPrice`**: Returns the impulse swing price (double), or 0.0 if not found

## Key Concepts

| Concept | Description |
|---------|-------------|
| L1 | The broken swing point price — becomes the inner boundary of the B2B zone |
| L2 | The impulse swing after L1 (opposite type) — becomes the outer boundary of the zone |
| Forming bar shield | The detector will NOT fire on bar index 0 (the bar currently forming) — prevents phantom breakouts |
| L2 sharing (V5.0.5) | If multiple swings are broken on the same bar, they share the same L2 swing — optimization to avoid duplicate zone creation |

## Dependencies
- `Structures.mqh`
- `Defines.mqh`
- `Utils.mqh`

## Python Equivalent
`sigma_core/sigma_core/b2b/detectors/breakouts.py` — `detect_breakouts(df, swings, config)`. Logic is equivalent: scan confirmed swings, check if close price crossed the swing level, find the impulse anchor. In Python, this is vectorized rather than bar-by-bar.

## Notes
- "Doctrinal shield" is the internal name for the forming-bar prevention — it is considered a core rule of the B2B methodology, not just a bug fix
- The distinction between L1 (broken swing) and L2 (impulse swing that starts the move to L1) is fundamental to the 5-pointer pattern — if L2 is wrong, the entire zone geometry is wrong
- `breakout_age_in_bars` is set here at detection time and used later by `B2BDetector` to filter stale breakouts
