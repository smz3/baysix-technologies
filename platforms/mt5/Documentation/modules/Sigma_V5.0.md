# Sigma_V5.0.mq5

## Purpose
The main Expert Advisor entry point. This file is the "shell" — it owns no strategy logic itself, but wires together every subsystem, manages the MQL5 event lifecycle (`OnInit`, `OnTick`, `OnTimer`, `OnDeinit`, `OnTester`), and holds all global state (manager instances, data buffers, zone arrays). Everything else is delegated to the `.mqh` include modules.

**Version:** V5.0 — "Clean Slate, B2B Only". All sequence logic and GPS engine code removed. Focus: B2B zone detection + Russian Doll confluence trading.

## Layer
Entry Point (Experts/)

**File path:** `Experts/Sigma_System/Sigma_V5.0.mq5`

---

## Global Instances

| Variable | Type | Purpose |
|----------|------|---------|
| `g_TimeFrameManager` | `CTimeFrameManager` | New bar detection across 9 TFs |
| `g_SwingDetector` | `CSwingPointDetector` | Swing high/low detection |
| `g_BreakoutDetector` | `CRawBreakoutDetector` | Breakout event detection |
| `g_B2BDetector` | `CB2BDetector` | 5-pointer zone formation + zone repository |
| `g_Visualizer` | `CVisualizer` | Chart object rendering |
| `g_SymbolManager` | `CUniversalSymbolManager` | Symbol-agnostic pip/lot resolution |
| `g_TelegramBot` | `CTelegramBot` | Notification stub |
| `g_FeedbackPanel` | `CFeedbackPanel` | In-chart dashboard |
| `g_RiskManager` | `CRiskManager` | Position sizing + account safety |
| `g_TrailingManager` | `CTrailingStopManager` | Break-even + trailing stop |
| `g_SignalGenerator` | `CTradeSignalGenerator` | Signal orchestration |
| `g_OrderManager` | `COrderManager` | Broker execution |
| `g_DataExporter` | `CDataExporter` | JSON export (disabled in live) |
| `g_QuantLogger` | `CQuantLogger` | CSV logging → Supabase pipeline |

## Global Data Arrays

| Variable | Type | Purpose |
|----------|------|---------|
| `g_swings[TOTAL_TIMEFRAMES]` | `CCircularBuffer<SwingPointInfo>` | Unified swing buffer per TF (HIGH + LOW, chronological) |
| `g_breakouts[TOTAL_TIMEFRAMES]` | `CCircularBuffer<RawBreakoutInfo>` | Raw breakout events per TF |
| `g_b2b_zones[TOTAL_TIMEFRAMES]` | `B2BZoneList` | Dynamic zone array per TF |
| `g_b2b_zone_count[TOTAL_TIMEFRAMES]` | `int[]` | Zone counts per TF |
| `g_rate_cache[TOTAL_TIMEFRAMES]` | `TimeFrameDataCache` | Per-TF OHLCV snapshot |
| `g_tf_enabled[TOTAL_TIMEFRAMES]` | `bool[]` | Which TFs are active (set by execution profile) |

## Key Global State Variables

| Variable | Purpose |
|----------|---------|
| `g_is_initialized` | Prevents double initialization — set to true after first-tick init in Strategy Tester |
| `g_next_display_number` | Sequential zone label counter (persisted in binary save file) |
| `g_switch_blocked_direction` | V5.3 switch logic: direction currently blocked from trading |
| `g_warmup_start_time` | V7 warmup period — detection runs but trading is suppressed until warmup elapsed |
| `g_active_parent_ids[]` | Cached parent zone IDs with open trades (rebuilt only on position change, not every tick) |

---

## Event Handlers

### `OnInit()`
1. Sets `g_tf_enabled[]` based on execution profile (`PROFILE_INTRADAY_M15` vs `PROFILE_FULL_MANUAL`)
2. Initializes all circular buffers (`g_swings`, `g_breakouts`) and clears zone arrays
3. **Live/Demo mode**: initializes all components immediately, then calls `DetectHistoricalSignals()` and sets `g_is_initialized = true`
4. **Strategy Tester**: defers everything to `OnTick` first-tick (avoids race condition with HTF data not yet loaded)

### `OnTick()`
- If not initialized: runs deferred init (forces HTF data sync in tester, then runs `DetectHistoricalSignals()`)
- Per-TF loop: checks `IsNewBar()` → runs swing detection → breakout detection → zone detection → zone status update
- Calls `g_SignalGenerator.OnTick()` with current price, zones, and change bitmask
- Calls `g_TrailingManager.UpdateAllPositions()` every tick
- Updates `g_FeedbackPanel` on new bars

### `OnTimer()`
- Live only (not in tester)
- Collects all zones across TFs and calls `g_DataExporter.ExportActiveZones()` (currently disabled/commented)
- Frequency: set via `EventSetTimer()` in `OnInit` (live mode)

### `OnDeinit(reason)`
- Live: saves zone state to persistence file via `g_B2BDetector.SaveZonesFromBuffers()`
- Tester: calls `g_QuantLogger.ReconcileHistory()` and exports timestamped CSV
- Logs final zone states (survived vs bulldozed) via `g_QuantLogger.LogZoneSurvived()` / `LogZoneBulldozed()`
- Clears all chart visuals and destroys panel

### `OnTester()`
- Called after backtest completes
- Syncs zone buffers back into detector
- Runs reconciliation + exports TESTER-tagged CSV
- Returns 0.0 (custom optimization metric not yet wired)

---

## Initialization Strategy: Hybrid Lazy Loading

The EA uses two different init paths to solve a known MT5 race condition:

| Mode | When Components Init | Reason |
|------|---------------------|--------|
| Live/Demo | `OnInit()` immediately | Prevents blank chart lag on attach |
| Strategy Tester | First `OnTick()` | HTF rates not available at `OnInit()` time in tester — deferring prevents empty detection |

### `DetectHistoricalSignals()`
Called after initialization. Runs a full historical scan on all enabled TFs to detect all existing swings, breakouts, and zones from historical data. This is the "cold start" detection pass — after this, `OnTick` only processes new bars.

### `EnsureHistoryLoaded(symbol, period, bars)`
Tester-only helper. Forces MT5 to synchronize and download HTF data before detection runs. Without this, MN1/W1/D1 data may not be available on the first tick.

---

## Include Order (Important)

MQL5 requires includes in dependency order:
```
1. TradingParameters.mqh     ← inputs (must be first)
2. Defines.mqh               ← constants
3. Utils.mqh, CircularBuffer.mqh, UniversalSymbolManager.mqh, PerformanceUtils.mqh
4. Structures.mqh            ← core data types
5. ZonePersistence.mqh
6. TimeFrameManager.mqh
7. Detection modules         ← SwingPointDetector → RawBreakoutDetector → B2BDetector → etc.
8. Visualization/Communication/UI
9. Trading modules           ← RiskManager → TrailingStopManager → TradeSignalGenerator → OrderManager
10. DataExporter, QuantLogger
11. MetricCalculator
```

`FeedbackPanel.mqh` appears twice in the include list (lines 51 and 63) — this is a duplicate include that MQL5 handles via include guards. Safe but should be cleaned up.

---

## Dependencies
All 25 `.mqh` modules — this file is the only consumer of all includes.

## Python Equivalent
`simulation/engine/vectorized_backtester.py` — `VectorizedBacktester` class. The `run()` method is the Python equivalent of `OnTick()`: iterates bar-by-bar, calls detection → signal → execution in sequence. `OnInit` maps to `__init__` + `load_data()`. There is no Python equivalent of `OnDeinit`/`OnTester` — the backtester generates a summary report via `ReportEngine.print_report()` at the end of `run()`.

## Notes
- **V5.3 Switch Logic**: `g_switch_blocked_direction` implements "Fractal Domino" — when H1 direction changes, trading in the old direction is blocked until a new signal confirms. The `CheckSwitchEvent()` forward declaration manages this.
- **V5.2 Optimization**: `g_active_parent_ids[]` cache is rebuilt only when `GetOpenPositionCount()` changes — avoids the expensive "scan all zones for open trades" operation on every tick
- **Commented-out code**: Several legacy systems are preserved as commented blocks (GPS Engine, ZoneLogger, dynamic TP) — these are research archives, not dead code to remove
- **`QuantTypes.mqh` and `StrategyOrchestrator.mqh`** are notably absent from the include list — they are pulled in transitively by `B2BDetector.mqh` and `TradeSignalGenerator.mqh` respectively
