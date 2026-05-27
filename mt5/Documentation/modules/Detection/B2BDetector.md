# B2BDetector.mqh

## Purpose
The core 5-Pointer B2B zone detection engine. Takes the output of `RawBreakoutDetector` (breakout events) and the swing history, then pairs them according to the 5-pointer pattern to produce validated B2B zones. Also acts as the central zone repository — other modules query it for the current set of active zones per TF.

## Layer
Detection

## Key Classes & Functions

| Name | Type | Description |
|------|------|-------------|
| `CB2BDetector` | Class | Zone detection + zone storage coordinator |
| `Initialize()` / `Reset()` | Methods | Setup and state reset |
| `DetectB2B_5Pointer(swings[], breakouts[], tf, config)` | Method | **Core algorithm**: scans swing+breakout pairs, validates 5-pointer geometry, returns new `B2BZoneInfo[]` array |
| `ClearAllZones()` | Method | Wipe all stored zones |
| `GetZone(index)` | Method | Read zone by index |
| `GetAllZones(zones[])` | Method | Copy full zone array |
| `GetZoneById(zone_id)` | Method | O(n) lookup by deterministic hash |
| `GetZoneIndexById(zone_id)` | Method | Returns index, or -1 if not found |
| `RecordTradeOpen(zone_id, ...)` | Method | Delegate to `CB2BTradeTracker` |
| `RecordTradeClose(zone_id, ...)` | Method | Delegate to `CB2BTradeTracker` |
| `UpdateTradeExcursions(zone_id, low, high)` | Method | Delegate to `CB2BTradeTracker` |
| `SetZoneTraded(zone_id, level)` | Method | Mark zone as traded at T1/T2/T3 level |
| `SetConfluenceFlags(zones[])` | Method | Delegate to `CB2BConfluence` |
| `SetMultiParentFlags(zones[])` | Method | Delegate to `CB2BConfluence` |
| `SaveZonesToFile()` / `LoadZonesFromFile()` | Methods | Delegate to `CZonePersistence` |

## The 5-Pointer Pattern

A valid B2B zone requires these 5 structural points in sequence:
1. **Point 1** — Original swing high (bearish) or swing low (bullish)
2. **Point 2** — Breakout of Point 1 (the L1 break)
3. **Point 3** — The impulse swing after Point 1 that started the move to Point 2 (L2)
4. **Point 4** — Pullback into the L1–L2 zone
5. **Point 5** — Continuation in the breakout direction

If all 5 points are structurally sound, a zone is created between L1 and L2.

## Inputs / Outputs
- **`DetectB2B_5Pointer`**: 
  - Input: swing array, breakout array, timeframe, detection config
  - Output: array of new `B2BZoneInfo` structs (zones not yet in memory)
- **`GetZoneById`**: Input zone_id hash → Output `B2BZoneInfo` (by reference)

## Dependencies
- `Structures.mqh`, `Defines.mqh`, `CircularBuffer.mqh`, `TradingParameters.mqh`
- `B2BZoneStatus.mqh`, `B2BZoneManager.mqh`, `B2BConfluence.mqh`
- `B2BTradeTracker.mqh`, `MetricCalculator.mqh`

## Python Equivalent
`sigma_core/sigma_core/b2b/detectors/b2b_engine.py` — `detect_b2b_zones(df, swings, tf, config)`. Implements the same 3-pass validation: (1) scan candidates, (2) filter interrupted zones, (3) select winners. The MQL5 version delegates sub-responsibilities to static helper classes; the Python version is more monolithic.

## Notes
- `DetectB2B_5Pointer` supports incremental detection via `start_index` parameter — only scans swings added since last run, avoiding full re-scan every bar
- The class acts as both detector and repository: this dual role makes it easy to query zones, but means it holds mutable state (unlike the Python version's stateless design)
- L1 selection rule (locked Dec 18 2025): BUY zones prefer HIGHER L1 (tighter zone, better R:R); SELL zones prefer LOWER L1. "More extreme" swing requirement removed — only temporal ordering (earlier in time) is enforced.
