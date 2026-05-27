# B2BZoneManager.mqh

## Purpose
Static utility class for zone storage operations — CRUD, deduplication, cleanup, and consolidation. All methods are static (no instance state), making it a pure function library that operates on zone arrays passed in by the caller. `CB2BDetector` delegates all zone management operations here.

## Layer
Detection

## Key Classes & Functions

| Name | Type | Description |
|------|------|-------------|
| `CB2BZoneManager` | Class | All-static zone operations library |
| `GenerateZoneId(L1, L2, tf, dir, time)` | Static | FNV-1a hash of zone geometry → 53-bit safe integer ID |
| `FindZoneIndexById(zones[], zone_id)` | Static | O(n) scan, returns index or -1 |
| `FindZoneById(zones[], zone_id, out_zone)` | Static | O(n) scan, returns zone by reference |
| `RemoveInvalidatedZones(zones[])` | Static | Delete zones with `is_invalidated = true` |
| `RemoveDeadZones(zones[], max_age)` | Static | Delete zones older than `max_age` bars |
| `PruneInvalidatedZones(zones[], buffers[])` | Static | Batch prune across TF buffers |
| `ConsolidateOverlappingZones(zones[])` | Static | Merge zones whose L1-L2 ranges overlap by more than threshold |
| `GetZone(zones[], index)` | Static | Safe array access with bounds check |
| `GetAllZones(zones[], out[])` | Static | Copy zone array |

## Inputs / Outputs
- **`GenerateZoneId`**: Takes doubles + int + enum + datetime → returns long (zone ID)
- **`ConsolidateOverlappingZones`**: Modifies zone array in-place, removing duplicates and merging overlaps
- **`RemoveInvalidatedZones`**: Modifies zone array in-place, shrinks count

## Dependencies
- `Structures.mqh`
- `CircularBuffer.mqh`

## Python Equivalent
`sigma_core/sigma_core/b2b/detectors/zone_manager.py` — `ZoneManager` class with equivalent methods: `generate_zone_id()`, `remove_invalidated()`, `consolidate_overlapping()`. Python version uses a dict keyed by zone_id for O(1) lookups instead of O(n) array scans.

## Notes
- **All-static design**: Methods are static because they operate on external state (arrays passed by reference). This enables reuse without needing to pass a manager instance around — any module that includes this file can call these directly.
- `GenerateZoneId` using FNV-1a hash ensures the same zone gets the same ID regardless of when/where it is detected — critical for cross-session deduplication in `MergeLoadedZones`
- `ConsolidateOverlappingZones` is called after every detection pass to prevent the zone count from growing unboundedly when the detector finds slightly different versions of the same zone across bars
