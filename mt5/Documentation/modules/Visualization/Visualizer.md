# Visualizer.mqh

## Purpose
Renders all chart objects — B2B zones (as rectangles), swing points (as arrows or dots), and breakout markers — onto the MT5 chart. Manages TF-specific visibility so only the objects relevant to the current chart TF are shown. Handles label updates without full zone redraws (V5.0.1 "zero-twitch" optimization) and prunes stale visual objects when zones are removed from memory.

## Layer
Visualization

## Key Classes & Functions

| Name | Type | Description |
|------|------|-------------|
| `CVisualizer` | Class | MT5 chart object manager |
| `DrawSwingPoint(swing, tf)` | Method | Draw single swing as arrow/dot on chart |
| `DeleteSwingPoint(swing_id, tf)` | Method | Remove swing visual |
| `ClearSwingPoints(tf)` | Method | Remove all swing visuals for a TF |
| `RedrawAllSwingPoints(swings[], tf)` | Method | Redraw from scratch for a TF |
| `DrawRawBreakout(breakout, tf)` | Method | Draw breakout event marker |
| `ClearRawBreakouts(tf)` | Method | Remove all breakout markers for a TF |
| `DrawB2BZone(zone)` | Method | Draw zone as a price rectangle with label |
| `ClearB2BZone(zone_id)` | Method | Remove specific zone rectangle + label |
| `ClearAllB2BZones()` | Method | Nuclear clear: remove all zone visuals |
| `DrawAllB2BZones(zones[])` | Method | Batch draw from zone array |
| `UpdateB2BZoneLabel(zone)` | Method | Update zone label text only — no redraw of rectangle |
| `UpdateAllZoneLabels(zones[])` | Method | Batch label update (efficient) |
| `PruneMissingZones(zones[])` | Method | Remove chart objects for zones that no longer exist in memory |
| `SyncB2BZones(zones[], origin_id, target_id)` | Method | Full sync: draw new, remove deleted, highlight origin/target |
| `ClearAllVisuals()` | Method | Remove all EA chart objects (nuclear option) |
| `ShouldShowForCurrentTF(zone_tf)` | Private | Returns true if zone's TF matches current chart TF |

## Inputs / Outputs
- **`DrawB2BZone`**: Takes `B2BZoneInfo` → creates MT5 rectangle + text objects with unique names
- **`SyncB2BZones`**: Takes full zone array + origin/target zone IDs → reconciles chart state with memory state
- **`PruneMissingZones`**: Iterates all chart objects with EA prefix, checks if corresponding zone still exists in array, deletes orphans

## Dependencies
- `Defines.mqh`, `Structures.mqh`, `Utils.mqh`, `TradingParameters.mqh`

## Python Equivalent
`core/visualization/plotly_visualizer.py` — `PlotlyVisualizer` class. Renders B2B zones as `plotly` shapes on an interactive HTML chart. No TF-specific visibility needed in Python (static chart per TF). Label update optimization does not apply (plotly recreates figures on each call).

## Notes
- **TF visibility**: MT5 shows all chart objects from all EAs at once. The Visualizer tags each object with the TF it belongs to and filters via `ShouldShowForCurrentTF()` on each draw/sync cycle. This prevents H4 zones from cluttering an M15 chart.
- **Zero-twitch pruning (V18)**: `PruneMissingZones` removed the "clear all and redraw" pattern that caused visual flickering on every bar. Now only deletes objects for zones that are actually gone.
- **Origin/target highlighting**: `SyncB2BZones` accepts `origin_id` and `target_id` to highlight the current flow state's active zones in a distinct color
- Object names follow the pattern: `SIGMA_{zone_id}_{type}` (rectangle, label, etc.) — enables reliable lookup and deletion
