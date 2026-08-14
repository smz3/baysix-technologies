# b2b-mt5 Module Documentation Index

Complete reference for all 25 `.mqh` include files in the Sigma V5.0 EA.

---

## Architecture Overview

> **[Sigma_V5.0.mq5](Sigma_V5.0.md)** — Entry point. Owns all global state, wires all modules, handles MT5 event lifecycle.

```
Sigma_V5.0.mq5  (entry point)
│
├── CONFIGURATION
│   └── TradingParameters.mqh          ← All input parameters (root dependency)
│
├── COMMON  (shared utilities)
│   ├── Defines.mqh                    ← Constants + enums
│   ├── Structures.mqh                 ← Core data types (B2BZoneInfo, SwingPointInfo)
│   ├── Utils.mqh                      ← Bar lookup + font helpers
│   ├── CircularBuffer.mqh             ← Generic fixed-size ring buffer
│   ├── UniversalSymbolManager.mqh     ← Symbol-agnostic pip/lot handling
│   └── PerformanceUtils.mqh           ← Swing cache + batch processor
│
├── DATA
│   ├── QuantTypes.mqh                 ← Supabase export struct
│   ├── ZonePersistence.mqh            ← Binary file save/load for zones
│   ├── DataExporter.mqh               ← JSON export for dashboards
│   └── QuantLogger.mqh                ← CSV logging pipeline to Supabase
│
├── DETECTION  (B2B pipeline)
│   ├── SwingPointDetector.mqh         ← DNA layer: swing highs/lows  [STABLE]
│   ├── RawBreakoutDetector.mqh        ← Breakout events + L2 discovery
│   ├── B2BDetector.mqh                ← 5-Pointer zone formation engine
│   ├── B2BZoneManager.mqh             ← Zone CRUD + consolidation
│   ├── B2BZoneStatus.mqh              ← Real-time touch tracking + invalidation
│   ├── B2BConfluence.mqh              ← TF hierarchy + Russian Doll nesting
│   └── B2BTradeTracker.mqh            ← Trade lifecycle on zone objects
│
├── SYSTEM
│   └── TimeFrameManager.mqh           ← 9-TF pair registry + new bar detection
│
├── ANALYSIS
│   └── MetricCalculator.mqh           ← God Data: fractal depth scoring
│
├── TRADING  (execution)
│   ├── TradeSignalGenerator.mqh       ← Signal orchestration hub (OnTick entry)
│   ├── StrategyOrchestrator.mqh       ← Russian Doll 3-gate engine + FlowState
│   ├── ContextMapper.mqh              ← Gate 2: session boundary + spatial map
│   ├── IntradayOrchestrator.mqh       ← Intraday 3-gate engine (T1 phase + bridge)
│   ├── RiskManager.mqh                ← Position sizing + account safety gates
│   ├── OrderManager.mqh               ← Broker execution (Sniper Protocol)
│   └── TrailingStopManager.mqh        ← Break-even + trailing stop
│
├── VISUALIZATION
│   └── Visualizer.mqh                 ← Chart objects: zones, swings, breakouts
│
├── COMMUNICATION
│   └── TelegramBot.mqh                ← Notification stub (not yet implemented)
│
└── UI
    └── FeedbackPanel.mqh              ← In-chart B2B Command Centre dashboard
```

---

## Module Reference Table

| Module | Layer | File | Python Equivalent | Status |
|--------|-------|------|-------------------|--------|
| [Sigma_V5.0](Sigma_V5.0.md) | **Entry Point** | `Experts/Sigma_System/Sigma_V5.0.mq5` | `simulation/engine/vectorized_backtester.py` | Active |
|--------|-------|------|-------------------|--------|
| [TradingParameters](Configuration/TradingParameters.md) | Configuration | `Configuration/TradingParameters.mqh` | `DetectionConfig` dataclass | Stable |
| [Defines](Common/Defines.md) | Common | `Common/Defines.mqh` | `models/structures.py` enums | Stable |
| [Utils](Common/Utils.md) | Common | `Common/Utils.mqh` | pandas `.loc[]` / `.searchsorted()` | Stable |
| [CircularBuffer](Common/CircularBuffer.md) | Common | `Common/CircularBuffer.mqh` | `collections.deque(maxlen=N)` | Stable |
| [UniversalSymbolManager](Common/UniversalSymbolManager.md) | Common | `Common/UniversalSymbolManager.mqh` | `core/risk/sizing.py` (partial) | Stable |
| [PerformanceUtils](Common/PerformanceUtils.md) | Common | `Common/PerformanceUtils.mqh` | N/A (vectorized in Python) | Stable |
| [Structures](Data/Structures.md) | Data | `Data/Structures.mqh` | `sigma_core/b2b/models/structures.py` | Stable |
| [QuantTypes](Data/QuantTypes.md) | Data | `Data/QuantTypes.mqh` | Supabase `trades` table schema | Stable |
| [ZonePersistence](Data/ZonePersistence.md) | Data | `Data/ZonePersistence.mqh` | N/A (Supabase in Python) | Stable |
| [DataExporter](Data/DataExporter.md) | Data | `Data/DataExporter.mqh` | `scripts/supabase_push.py` | Stable |
| [QuantLogger](Data/QuantLogger.md) | Data | `Data/QuantLogger.mqh` | `scripts/supabase_push.py` | V6.0 |
| [SwingPointDetector](Detection/SwingPointDetector.md) | Detection | `Detection/SwingPointDetector.mqh` | `sigma_core/b2b/detectors/swing_points.py` | **FROZEN** |
| [RawBreakoutDetector](Detection/RawBreakoutDetector.md) | Detection | `Detection/RawBreakoutDetector.mqh` | `sigma_core/b2b/detectors/breakouts.py` | Stable |
| [B2BDetector](Detection/B2BDetector.md) | Detection | `Detection/B2BDetector.mqh` | `sigma_core/b2b/detectors/b2b_engine.py` | Active |
| [B2BZoneManager](Detection/B2BZoneManager.md) | Detection | `Detection/B2BZoneManager.mqh` | `sigma_core/b2b/detectors/zone_manager.py` | Stable |
| [B2BZoneStatus](Detection/B2BZoneStatus.md) | Detection | `Detection/B2BZoneStatus.mqh` | `sigma_core/b2b/detectors/zone_status.py` | V6.0 |
| [B2BConfluence](Detection/B2BConfluence.md) | Detection | `Detection/B2BConfluence.mqh` | `sigma_core/b2b/detectors/confluence.py` | Stable |
| [B2BTradeTracker](Detection/B2BTradeTracker.md) | Detection | `Detection/B2BTradeTracker.mqh` | `core/execution/trade_manager.py` (partial) | Stable |
| [TimeFrameManager](System/TimeFrameManager.md) | System | `System/TimeFrameManager.mqh` | `core/system/timeframe_mgr.py` | Stable |
| [MetricCalculator](Analysis/MetricCalculator.md) | Analysis | `Analysis/MetricCalculator.mqh` | `simulation/engine/` (inline) | V11.3 |
| [RiskManager](Trading/RiskManager.md) | Trading | `Trading/RiskManager.mqh` | `core/risk/sizing.py` | Stable |
| [OrderManager](Trading/OrderManager.md) | Trading | `Trading/OrderManager.mqh` | `core/execution/trade_manager.py` | V5.0 |
| [TrailingStopManager](Trading/TrailingStopManager.md) | Trading | `Trading/TrailingStopManager.mqh` | N/A | V7.0 |
| [TradeSignalGenerator](Trading/TradeSignalGenerator.md) | Trading | `Trading/TradeSignalGenerator.mqh` | `core/strategy/scanner.py` | Stable |
| [StrategyOrchestrator](Trading/StrategyOrchestrator.md) | Trading | `Trading/StrategyOrchestrator.mqh` | `core/strategy/orchestrator.py` | V6.2 |
| [ContextMapper](Trading/ContextMapper.md) | Trading | `Trading/ContextMapper.mqh` | `core/strategy/engines/fracture_engine.py` (partial) | V6.2 |
| [IntradayOrchestrator](Trading/IntradayOrchestrator.md) | Trading | `Trading/IntradayOrchestrator.mqh` | `core/strategy/engines/efficiency_governor.py` (partial) | V6.3 |
| [Visualizer](Visualization/Visualizer.md) | Visualization | `Visualization/Visualizer.mqh` | `core/visualization/plotly_visualizer.py` | V5.0 |
| [TelegramBot](Communication/TelegramBot.md) | Communication | `Communication/TelegramBot.mqh` | N/A | Stub |
| [FeedbackPanel](UI/FeedbackPanel.md) | UI | `UI/FeedbackPanel.mqh` | sigma-quant web dashboard | V5.0 |

---

## Detection Pipeline (Data Flow)

```
OnNewBar(tf)
  → SwingPointDetector.DetectLiveSwing()      [raw swings]
  → RawBreakoutDetector.Detect()              [raw breakouts]
  → B2BDetector.DetectB2B_5Pointer()         [new zones]
  → B2BConfluence.SetConfluenceFlags()        [nesting flags]
  → B2BZoneStatus.UpdateZoneStatus()          [touch + age]
  → MetricCalculator.CalculateFractalDepth()  [God Data scores]

OnTick()
  → TradeSignalGenerator.OnTick()
      → ContextMapper.EvaluateContext()
      → StrategyOrchestrator.IsTradeAllowed() OR IntradayOrchestrator.IsTradeAllowed()
      → RiskManager.CalculateRiskBasedLot()
      → OrderManager.ExecuteSignal()
      → QuantLogger.LogTrade()
      → TrailingStopManager.UpdateAllPositions()
```

---

## Known Active Issues

| Module | Issue | Reference |
|--------|-------|-----------|
| TelegramBot | All methods are no-ops | Intentional stub — not yet implemented |

---

## Python Source of Truth Mapping

The Python implementation (`sigma_core` + `sigma_crypto`) is the canonical reference for detection logic. MQL5 is the execution adapter. When logic diverges:
- Detection rules: defer to Python (`sigma_core`)
- MT5-specific concerns (lot sizing, order types, broker API): no Python equivalent
- Strategy orchestration: Python and MQL5 are co-authoritative — changes must be applied to both
