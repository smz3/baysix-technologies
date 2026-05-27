# B2BConfluence.mqh

## Purpose
Defines and enforces the multi-timeframe zone hierarchy. Determines which timeframes are "narrative" (MN1/W1/D1), which are "control" (H4), and which are "entry" (H1 and below). Detects when an entry-TF zone is nested inside a HTF parent zone ("Russian Doll"), marks zones that have multiple HTF parents, and identifies pioneer zones (the first zone at a price level never seen before).

## Layer
Detection

## Key Classes & Functions

| Name | Type | Description |
|------|------|-------------|
| `CB2BConfluence` | Class | All-static TF hierarchy and confluence analyzer |
| `GetTFRank(tf)` | Static | Returns hierarchy rank: 0 = MN1 (highest), 8 = M1 (lowest) |
| `IsNarrativeTF(tf)` | Static | Returns true for MN1, W1, D1 |
| `IsControlTF(tf)` | Static | Returns true for H4 only |
| `IsEntryTF(tf)` | Static | Returns true for H1, M30, M15, M5, M1 |
| `SetConfluenceFlags(zones[], all_tf_zones[])` | Static | For each zone, find all parent zones (HTF zones it sits inside) and set `parent_zone_id`, `parent_tf` |
| `SetMultiParentFlags(zones[])` | Static | Mark zones that have 2+ HTF parents (`is_multi_parent = true`) — the "Russian Doll" flag |
| `IsPioneerZone(zone, all_zones[])` | Static | True if no existing zone at any TF covers the same price level |
| `SetPioneerFlags(zones[], all_tf_zones[])` | Static | Batch-mark pioneer zones |
| `FilterEntryZonesByNesting(zones[], mode)` | Static | Filter entry TF zones by nesting mode (nested only, non-nested only, or all) |
| `IsParentZoneTouched(zone, parent_zones[])` | Static | Check if the zone's HTF parent has been touched (T1 level) |

## TF Hierarchy

```
MN1  ─── Narrative (macro context, long-term bias)
W1   ─── Narrative
D1   ─── Narrative
H4   ─── Control (institutional context)
H1   ─── Entry
M30  ─── Entry
M15  ─── Entry
M5   ─── Entry
M1   ─── Entry
```

## Inputs / Outputs
- **`SetConfluenceFlags`**: Modifies zone array in-place — sets `parent_zone_id`, `parent_tf`, `is_nested`
- **`FilterEntryZonesByNesting`**: Returns filtered subset of zones array
- **`IsParentZoneTouched`**: Returns bool — used by signal generator to gate entries

## Dependencies
- `Structures.mqh`
- `TradingParameters.mqh`

## Python Equivalent
`sigma_core/sigma_core/b2b/detectors/confluence.py` — `detect_confluence(zones_by_tf, config)`. Same hierarchy concept. Python version is also all-static (module-level functions). The `is_multi_parent` flag corresponds to the "Russian Doll" concept in sigma-crypto's orchestrator.

## Notes
- "Russian Doll" is the strategy's name for nested zone confluence: an H1 zone inside an H4 zone inside a D1 zone = maximum confluence score
- `FilterEntryZonesByNesting` is used by `TradeSignalGenerator` to restrict entries to only nested zones when the `NESTED_ONLY` mode is active in `TradingParameters`
- Pioneer zones are directionally significant because they represent fresh untested price levels — no prior zone exists to act as support/resistance
