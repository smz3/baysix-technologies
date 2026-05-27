# SIGMA V5.0 Changelog

All notable changes to the V5.0 codebase are documented in this file.

---

## [5.0.3] - 2025-12-20

### Fixed
- **Live B2B Detection Alignment** - Live detection was producing different zones than historical detection due to:
  1. Different swing detection methods (inline V3.2 vs SwingDetector class)
  2. Swing filtering (only active vs all swings)
  3. Missing post-detection calls

### Changed
- `ProcessNewBar()` in `Sigma_V5.0.mq5`:
  - Now uses `g_SwingDetector.CheckForSwingHigh/Low()` for swing detection (matching historical)
  - Passes ALL swings to breakout detector (not just active ones)
  - Added `SetConfluenceFlags()` call after live B2B detection
  - Added `ValidateAllZonesAgainstHistory()` call to prevent invalid zones on sniper TF

---

## [5.0.2] - 2025-12-20

### Fixed
- **B2B Cluster Edge Case Fix** - In clustered breakout scenarios (multiple nearby swing highs/lows), B2B pair selection was incorrectly choosing older, more extreme swings instead of the most recent valid pair. Changed `FindAllB2BPairs()` from selecting by "best price" (extreme) to "nearest in time" (temporal proximity). This ensures consistent L1/L2 selection in cluster scenarios.

- **L2 Selection Logic Update** - L2 now uses proper connected swing logic: 
  - **Option B:** Find swing **closest in time to L1** (connected/adjacent), NOT most extreme in window
  - **Option A:** Use `impulse_start_price` (swing that started the impulse)
  - Pick whichever of A or B is **more extreme**
  - Validates L2 is on correct side of L1 (BUY: swing LOW below L1, SELL: swing HIGH above L1)

### Changed
- `FindAllB2BPairs()` in `B2BDetector.mqh` now uses `breakout_bar_time` comparison instead of `broken_swing_price` for selecting the optimal 1st breakout candidate.
- `FindL2Price()` now accepts `impulse_start_price` and `L1_price` parameters to implement the new L2 selection logic.

---

## [5.0.1] - 2025-12-19

### Fixed
- **Multi-Breakout Visualization Bug** - When a single bar broke multiple swings, only one breakout was being visualized. Root cause: object name collisions in `ObjectCreate`. Solution: added static counter to `DrawRawBreakout()` in `Visualizer.mqh` to ensure unique object names.

### Changed
- Object naming scheme now uses counter prefix: `_1_<breakout_time>_<swing_time>` instead of just `_<breakout_time>_<swing_time>`

---

## [5.0.0] - 2025-12 (Initial V5.0 Release)

### Major Architecture Changes (V3.2 → V5.0)

#### Removed
- **Sequence Detection System** - Entire `SequenceDetector.mqh`, `SequenceBarrierManager.mqh`, and related code
- **CF/FOB/PBO Architecture** - Complex child/parent breakout relationships
- **"Best Candidate" Logic** - Legacy code that picked lowest (BUY) / highest (SELL) swing instead of all breakouts
- **SequenceInfo Structure** - Replaced with simpler B2B-focused structures
- **Barrier Point Detection** - `BarrierPointDetector.mqh` complexity removed

#### Added
- **B2B Zone Detection** - New `B2BDetector.mqh` focused on Break-of-Two-Barriers pattern
- **Clean Circular Buffers** - Simplified swing/breakout storage with `CCircularBuffer<T>`
- **TF-Specific Visualization** - Objects only drawn for matching chart timeframe
- **Rescan Functionality** - Press 'R' to clear and rescan all historical signals

#### Changed
- **RawBreakoutDetector** - Now outputs ALL breakouts (removed "best wins" filter)
- **SwingPointInfo** - Simplified structure with essential fields only
- **File Organization** - Clean folder structure under `Include/V5.0/`
  - `Common/` - Defines, Utils
  - `Configuration/` - TradingParameters
  - `Data/` - Structures, CircularBuffer
  - `Detection/` - RawBreakoutDetector, B2BDetector
  - `Visualization/` - Visualizer
  - `System/` - TimeFrameManager
  - `Trading/` - RiskManager, TrailingStopManager

### Technical Improvements
- Removed ~70% of legacy code complexity
- Faster historical detection (no sequence building overhead)
- Cleaner separation of concerns between detection and visualization
- Proper `has_been_broken` flag management for swings

---

## Debug Logging Reference

The following debug code exists (commented out) for future troubleshooting:

| Location | Tag | Purpose |
|----------|-----|---------|
| `Sigma_V5.0.mq5` | `[DETECTION-SUMMARY]` | Log swing/breakout counts per TF |
| `Sigma_V5.0.mq5` | `[OBJECT-COUNT]` | Count chart objects created per TF |
| `Visualizer.mqh` | `[DRAW-FAIL]` | Log ObjectCreate failures |

To enable: search for "(uncomment for debugging)" in the relevant files.

---

## File Reference

### V5.0 Core Files
- `Experts/Sigma_V5.0.mq5` - Main EA
- `Include/V5.0/Common/Defines.mqh` - Constants and enums
- `Include/V5.0/Common/Utils.mqh` - Utility functions
- `Include/V5.0/Data/Structures.mqh` - Data structures
- `Include/V5.0/Data/CircularBuffer.mqh` - Generic circular buffer
- `Include/V5.0/Detection/RawBreakoutDetector.mqh` - Breakout detection
- `Include/V5.0/Detection/B2BDetector.mqh` - B2B zone detection
- `Include/V5.0/Visualization/Visualizer.mqh` - Chart object drawing
- `Include/V5.0/Configuration/TradingParameters.mqh` - Input parameters
