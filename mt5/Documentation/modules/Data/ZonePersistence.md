# ZonePersistence.mqh

## Purpose
Saves and loads the full B2B zone state to a binary file so zones survive MT5 chart switches, EA restarts, and broker disconnections. Without this, all detected zones would be lost whenever the EA reloads — requiring a full re-scan of historical data. This module makes the zone database durable across sessions.

## Layer
Data

## Key Classes & Functions

| Name | Type | Description |
|------|------|-------------|
| `CZonePersistence` | Class | Manages read/write of zone arrays to MT5's `Files/` directory |
| `Initialize(symbol)` | Method | Set file path based on symbol name |
| `SaveZones(zones[], count)` | Method | Serialize zone array to binary file |
| `LoadZones(zones[], count)` | Method | Deserialize binary file into zone array |
| `SaveZonesFromBuffers(buffers[])` | Method | Save from per-TF `B2BZoneList` buffer array |
| `LoadZonesToBuffers(buffers[])` | Method | Load into per-TF buffer array |
| `MergeLoadedZones(loaded[], existing[])` | Method | Merge loaded zones with current in-memory zones (deduplicates by zone_id) |
| `FileExists()` | Method | Check if persistence file exists |
| `DeleteFile()` | Method | Remove persistence file (used on full reset) |

## Inputs / Outputs
- **`SaveZones`**: Takes zone array + count, writes binary file. Returns bool success.
- **`LoadZones`**: Reads binary file, populates zone array. Returns count loaded.
- **`MergeLoadedZones`**: Deduplicates using `zone_id` hash — loaded zones that already exist in memory are skipped.

## Dependencies
- `Structures.mqh`
- `Defines.mqh`

## Python Equivalent
No direct equivalent in sigma-crypto — Python backtests start from scratch each run. In a live Python trading context, zone state would be persisted to Supabase or a local SQLite database. This MQL5 module is specific to the MT5 session-persistence requirement.

## Notes
- **Binary format version:** v11 — includes `g_next_display_number` (zone label counter) in the header. Older format files are rejected to prevent struct mismatch corruption.
- File path: `MQL5/Files/Sigma_Zones_{symbol}.bin` in MT5's sandboxed file system
- `MergeLoadedZones` is critical after EA restart — it prevents duplicate zones when the detector re-discovers zones that were already tracked before the restart
- On timeframe chart change (e.g., switching from H1 to H4 view), MT5 reloads the EA, triggering a load from this file
