# B2BZoneStatus.mqh

## Purpose
Real-time zone state machine. On every new bar, this module checks each active zone to see whether price has touched or crossed its key levels (L1, 50% midpoint, L2), updates the touch flags, increments zone age, and marks zones as invalidated when price closes beyond L2. Returns a bitmask so callers know exactly what changed without having to diff the zone array themselves.

## Layer
Detection

## Key Classes & Functions

| Name | Type | Description |
|------|------|-------------|
| `CB2BZoneStatus` | Class | All-static zone state updater |
| `UpdateZoneStatus(zones[], tf, rates[])` | Static | **Core method**: Update all zones for one TF on the current bar. Tracks L1/50%/L2 touches, increments age, marks invalidations. Returns bitmask. |
| `UpdateZoneStatusInBuffer(buffer, tf, rates[])` | Static | Same as above but operates on a `B2BZoneList` buffer |
| `ValidateZonesInBuffer(buffer, tf, rates[])` | Static | Historical batch validation — scan all historical bars to validate loaded zones |
| `ValidateZoneAgainstHistory(zone, rates[])` | Static | Single zone historical validation |

## Return Bitmask

| Bit | Constant | Meaning |
|-----|----------|---------|
| 0 | `ZONE_CHANGE_STRUCTURAL` | Zone was invalidated or a new touch level was reached |
| 1 | `ZONE_CHANGE_METRIC` | Zone age or metric updated but geometry unchanged |

## Touch Level Logic

| Zone Direction | L1 (Entry side) | L2 (Invalidation side) |
|----------------|-----------------|------------------------|
| BEARISH | `Min(L1_price, L2_price)` | `Max(L1_price, L2_price)` |
| BULLISH | `Max(L1_price, L2_price)` | `Min(L1_price, L2_price)` |

**Self-trigger prevention**: A zone created on bar N will not register a touch on bar N itself (prevents false T1 flag from the creation bar).

## Inputs / Outputs
- **`UpdateZoneStatus`**:
  - Input: zone array, timeframe, rates array for this TF
  - Output (in-place): updates `L1_touched`, `fifty_touched`, `L2_touched`, `is_invalidated`, `zone_age_bars` on each zone
  - Return: bitmask int (0 = no change, 1 = structural, 2 = metric, 3 = both)

## Dependencies
- `Structures.mqh`
- `CircularBuffer.mqh`
- `QuantLogger.mqh` (to log zone touch/survival/bulldoze events)
- `Defines.mqh`

## Python Equivalent
`sigma_core/sigma_core/b2b/detectors/zone_status.py` — `update_active_zones(low, high, close, time, zones)`. Equivalent touch tracking and invalidation logic. Python version is vectorized across all bars at once; MQL5 version runs bar-by-bar in the EA's `OnNewBar()` handler.

## Notes
- **Version 6.0** integrated Phase 0 Zone Logging — every touch/survival/invalidation event is now logged to `QuantLogger` directly from this module
- The 50% level (midpoint between L1 and L2) is tracked as a separate touch because it represents the "zone midpoint retest" — a useful signal for T2 entry timing
- `ValidateZonesInBuffer` is called after loading zones from `ZonePersistence` — it replays history to ensure loaded zones are still valid (price may have invalidated them while the EA was offline)
