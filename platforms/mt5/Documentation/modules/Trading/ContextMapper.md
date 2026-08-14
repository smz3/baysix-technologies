# ContextMapper.mqh

## Purpose
Gate 2 of the execution engine — the Structural Narrative Layer. Maps the current price into a spatial context by identifying session boundaries (the highest and lowest zones for each TF in the current period). Answers questions like: "Is price close to an HTF barrier?", "Is the path to the target blocked by an opposing zone?", "Is price breaking out of the current range or returning to the mean?" Used by `StrategyOrchestrator` and `IntradayOrchestrator`.

## Layer
Trading

## Key Classes & Functions

| Name | Type | Description |
|------|------|-------------|
| `SessionBoundary` | Struct | Tracks zone IDs at the top and bottom of the session range for MN1, W1, D1, H4, H1, M30 |
| `CContextMapper` | Class | Session boundary tracker and spatial query engine |
| `EvaluateContext(price, time, zones[])` | Method | **Core**: Scan all zones, update `SessionBoundary` for current and previous session periods. Maps current price into context. |
| `GetTargetCoordinate(tf, direction)` | Method | Returns price of the nearest zone in the given direction (where price is heading) |
| `GetDistanceToWall(tf, direction, price)` | Method | Distance in pips/points to the nearest opposing HTF zone |
| `IsPathBlocked(tf, direction, price, target)` | Method | Returns true if an opposing zone sits between current price and target |
| `GetEpochPosition(tf, direction)` | Method | Direction-specific epoch: where in the session range is price currently? |
| `IsBreakout(tf, price)` | Method | True if price has left the established session range |
| `GetIntradayPosition(tf, price)` | Method | Returns intraday range position as percentage (0% = session low, 100% = session high) |

## Session Boundary Mapping

For each TF, `EvaluateContext` finds:
- **Top boundary**: Highest active zone (resistance)
- **Bottom boundary**: Lowest active zone (support)
- **Previous top/bottom**: Prior session's boundaries (for breakout detection)

## Inputs / Outputs
- **`EvaluateContext`**: Takes price/time + all zones → updates internal `SessionBoundary` map. No return value.
- **`IsPathBlocked`**: Takes TF, direction, current price, target price → returns bool
- **`GetIntradayPosition`**: Returns double (0.0–1.0 ratio)

## Dependencies
- `Structures.mqh`

## Python Equivalent
`core/strategy/orchestrator.py` (inline) and partially in `core/strategy/engines/fracture_engine.py`. The `EpochPosition` concept is implemented in `FractureEngine.get_latest_outpost()`. Python version does not have a dedicated `ContextMapper` class — session boundary logic is folded into the orchestrator. The `GetIntradayPosition` logic appears in `IntradayOrchestrator` in Python.

## Notes
- "Epoch position" is the strategy's term for where price sits in the historical context of zone activity — not calendar-based epochs
- `IsPathBlocked` is the critical Gate 2 check: even if a zone is valid and the flow state approves, a trade is blocked if an opposing zone creates a barrier before the target
- Context is re-evaluated every new bar or when `ZONE_CHANGE_STRUCTURAL` is set — not every tick
- `SessionBoundary` tracks both current and previous session boundaries to detect continuation vs reversal setups across session transitions
