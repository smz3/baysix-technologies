# PerformanceUtils.mqh

## Purpose
Provides caching structures to avoid redundant computation on hot paths. The swing point cache gives O(1) lookups for recently accessed swings instead of O(n) array scans. The batch processor groups breakout checks so they are not repeated every tick unnecessarily.

## Layer
Common

## Key Classes & Functions

| Name | Type | Description |
|------|------|-------------|
| `SwingStateCache` | Struct | Caches up to 100 most recent swing lookups. Maps swing price/time to array index for O(1) re-access. Tracks dirty flag for cache invalidation. |
| `BatchProcessor` | Struct | Batches breakout detection calls. Tracks last processed bar index per TF to avoid re-scanning bars that have already been checked. |

## Inputs / Outputs
- **`SwingStateCache`**: Updated by swing detectors; read by zone detectors and status updaters
- **`BatchProcessor`**: Read/written by `RawBreakoutDetector` — prevents duplicate processing of the same bar across multiple ticks

## Dependencies
None — pure performance utility structures, no project logic dependencies.

## Python Equivalent
No direct equivalent in sigma-crypto. Python's backtester is vectorized (processes the entire bar history in one pass via pandas), so tick-level caching is not needed. In a live Python trading setup (e.g., LEAN), similar caching would be required.

## Notes
- `SwingStateCache` capacity is hardcoded at 100 entries — sufficient for 9 TFs × ~10 relevant swings each
- Cache invalidation (`dirty` flag) is triggered by `SwingPointDetector` when a new swing is confirmed or an old one is broken
- These are plain structs, not classes — they hold data only, with no methods. Callers manage their lifecycle.
