---
type: wiki
domain: systems
status: stable
tags:
  - mt5
  - architecture
  - mql5
related:
  - "[[sigma-engine-map]]"
  - "[[mt5-detection-pipeline]]"
  - "[[mt5-execution-pipeline]]"
  - "[[mt5-data-pipeline]]"
source_files:
  - "workspace/sigma-mt5/Documentation/modules/INDEX.md"
  - "workspace/sigma-mt5/Experts/Sigma_System/Sigma_V5.0.mq5"
last_updated: 2026-04-14
maintained_by: ai
ai_summary: "sigma-mt5 V5.0 is a 26-module MQL5 EA across 10 layers: Configuration, Common, Data, Detection, System, Analysis, Trading, Visualization, Communication, and UI. Full docs exist in workspace/sigma-mt5/Documentation/modules/."
---

# MT5 EA Architecture

> **Single source of truth for module docs:** `workspace/sigma-mt5/Documentation/modules/`
> This page is an index — it links to those files, not a duplicate.

---

## Entry Point

**File:** `workspace/sigma-mt5/Experts/Sigma_System/Sigma_V5.0.mq5`  
**Doc:** [Sigma_V5.0.md](../../../workspace/sigma-mt5/Documentation/modules/Sigma_V5.0.md)

The main EA file. Declares 14 global module instances, handles 5 MT5 events (`OnInit`, `OnDeinit`, `OnTick`, `OnTimer`, `OnChartEvent`). Uses hybrid lazy-loading init: all TF managers and zone detectors initialize on first `OnTick` after chart is ready, not in `OnInit`.

---

## Module Map (26 Files)

### Configuration Layer

| Module | Role | Doc |
|--------|------|-----|
| `TradingParameters.mqh` | All EA input parameters. Root dependency — everything imports this. | [TradingParameters.md](../../../workspace/sigma-mt5/Documentation/modules/Configuration/TradingParameters.md) |

### Common Layer

| Module | Role | Doc |
|--------|------|-----|
| `Defines.mqh` | Global constants and enums (`ZONE_STATUS_*`, `SIGNAL_TYPE_*`, etc.) | [Defines.md](../../../workspace/sigma-mt5/Documentation/modules/Common/Defines.md) |
| `Utils.mqh` | Utility functions (time, price math, string helpers) | [Utils.md](../../../workspace/sigma-mt5/Documentation/modules/Common/Utils.md) |
| `CircularBuffer.mqh` | Fixed-size ring buffer for OHLCV history | [CircularBuffer.md](../../../workspace/sigma-mt5/Documentation/modules/Common/CircularBuffer.md) |
| `UniversalSymbolManager.mqh` | Multi-symbol data normalizer (pip size, digits, spread) | [UniversalSymbolManager.md](../../../workspace/sigma-mt5/Documentation/modules/Common/UniversalSymbolManager.md) |
| `PerformanceUtils.mqh` | Timing utilities for EA performance profiling | [PerformanceUtils.md](../../../workspace/sigma-mt5/Documentation/modules/Common/PerformanceUtils.md) |

### Data Layer

| Module | Role | Doc |
|--------|------|-----|
| `Structures.mqh` | All shared data structures (`SB2BZone`, `STradeContext`, `SMetrics`) | [Structures.md](../../../workspace/sigma-mt5/Documentation/modules/Data/Structures.md) |
| `QuantTypes.mqh` | Enum types for logging and quant data export | [QuantTypes.md](../../../workspace/sigma-mt5/Documentation/modules/Data/QuantTypes.md) |
| `ZonePersistence.mqh` | Binary serialization: save/load zones across EA restarts | [ZonePersistence.md](../../../workspace/sigma-mt5/Documentation/modules/Data/ZonePersistence.md) |
| `DataExporter.mqh` | CSV export of zone events for Supabase pipeline | [DataExporter.md](../../../workspace/sigma-mt5/Documentation/modules/Data/DataExporter.md) |
| `QuantLogger.mqh` | Structured JSON logging for all zone lifecycle events | [QuantLogger.md](../../../workspace/sigma-mt5/Documentation/modules/Data/QuantLogger.md) |

### Detection Layer

| Module | Role | Doc |
|--------|------|-----|
| `SwingPointDetector.mqh` | Detects swing highs/lows — foundation of all B2B detection. **FROZEN/STABLE.** | [SwingPointDetector.md](../../../workspace/sigma-mt5/Documentation/modules/Detection/SwingPointDetector.md) |
| `RawBreakoutDetector.mqh` | Identifies when price breaks a prior swing point | [RawBreakoutDetector.md](../../../workspace/sigma-mt5/Documentation/modules/Detection/RawBreakoutDetector.md) |
| `B2BDetector.mqh` | Chains two breakouts into a valid B2B zone (5-pointer) | [B2BDetector.md](../../../workspace/sigma-mt5/Documentation/modules/Detection/B2BDetector.md) |
| `B2BZoneManager.mqh` | Stores zones, handles deduplication, persistence, and zone registry | [B2BZoneManager.md](../../../workspace/sigma-mt5/Documentation/modules/Detection/B2BZoneManager.md) |
| `B2BZoneStatus.mqh` | Tracks zone lifecycle state (DETECTED → ACTIVE → INVALIDATED) | [B2BZoneStatus.md](../../../workspace/sigma-mt5/Documentation/modules/Detection/B2BZoneStatus.md) |
| `B2BConfluence.mqh` | Scores TF confluence (Narrative/Control/Sniper layer validation) | [B2BConfluence.md](../../../workspace/sigma-mt5/Documentation/modules/Detection/B2BConfluence.md) |
| `B2BTradeTracker.mqh` | Links trade events to the B2B zone that triggered them | [B2BTradeTracker.md](../../../workspace/sigma-mt5/Documentation/modules/Detection/B2BTradeTracker.md) |

### System Layer

| Module | Role | Doc |
|--------|------|-----|
| `TimeFrameManager.mqh` | Multi-TF bar tracking — fires events when a new bar opens on any TF | [TimeFrameManager.md](../../../workspace/sigma-mt5/Documentation/modules/System/TimeFrameManager.md) |

### Analysis Layer

| Module | Role | Doc |
|--------|------|-----|
| `MetricCalculator.mqh` | Zone quality scoring: hit rate, R-multiple, recency weighting | [MetricCalculator.md](../../../workspace/sigma-mt5/Documentation/modules/Analysis/MetricCalculator.md) |

### Trading Layer

| Module | Role | Doc |
|--------|------|-----|
| `RiskManager.mqh` | Position sizing, drawdown limits, exposure controls | [RiskManager.md](../../../workspace/sigma-mt5/Documentation/modules/Trading/RiskManager.md) |
| `OrderManager.mqh` | Order placement, modification, and closure | [OrderManager.md](../../../workspace/sigma-mt5/Documentation/modules/Trading/OrderManager.md) |
| `TrailingStopManager.mqh` | ATR-based trailing stop logic | [TrailingStopManager.md](../../../workspace/sigma-mt5/Documentation/modules/Trading/TrailingStopManager.md) |
| `TradeSignalGenerator.mqh` | 3-gate signal generation: Narrative + Control + Sniper alignment required | [TradeSignalGenerator.md](../../../workspace/sigma-mt5/Documentation/modules/Trading/TradeSignalGenerator.md) |
| `StrategyOrchestrator.mqh` | Top-level strategy coordinator — routes signals and manages session state | [StrategyOrchestrator.md](../../../workspace/sigma-mt5/Documentation/modules/Trading/StrategyOrchestrator.md) |
| `ContextMapper.mqh` | Maps market context (session, volatility, spread) to strategy adjustments | [ContextMapper.md](../../../workspace/sigma-mt5/Documentation/modules/Trading/ContextMapper.md) |
| `IntradayOrchestrator.mqh` | Intraday session rules and time-of-day filters | [IntradayOrchestrator.md](../../../workspace/sigma-mt5/Documentation/modules/Trading/IntradayOrchestrator.md) |

### Visualization / Communication / UI Layers

| Module | Role | Doc |
|--------|------|-----|
| `Visualizer.mqh` | Draws zone rectangles, labels, and touch markers on MT5 chart | [Visualizer.md](../../../workspace/sigma-mt5/Documentation/modules/Visualization/Visualizer.md) |
| `TelegramBot.mqh` | Sends zone alerts and trade notifications to Telegram | [TelegramBot.md](../../../workspace/sigma-mt5/Documentation/modules/Communication/TelegramBot.md) |
| `FeedbackPanel.mqh` | On-chart dashboard panel (P&L, active zones, session state) | [FeedbackPanel.md](../../../workspace/sigma-mt5/Documentation/modules/UI/FeedbackPanel.md) |

---

## Dependency Tree (Simplified)

```
Sigma_V5.0.mq5
├── TradingParameters.mqh          (root)
├── Defines.mqh + Utils.mqh        (constants + helpers)
├── Structures.mqh + QuantTypes.mqh (data models)
├── CircularBuffer.mqh             (OHLCV storage)
├── UniversalSymbolManager.mqh     (multi-symbol support)
├── TimeFrameManager.mqh           (multi-TF bar events)
│
├── [Detection pipeline]
│   SwingPointDetector → RawBreakoutDetector → B2BDetector
│   → B2BZoneManager → B2BZoneStatus → B2BConfluence → B2BTradeTracker
│
├── [Trading pipeline]
│   TradeSignalGenerator → StrategyOrchestrator → IntradayOrchestrator
│   → RiskManager → OrderManager → TrailingStopManager
│
├── [Context & Analysis]
│   ContextMapper → MetricCalculator
│
├── [Data export]
│   ZonePersistence + DataExporter + QuantLogger
│
└── [UI]
    Visualizer + TelegramBot + FeedbackPanel + PerformanceUtils
```

---

## Detection Pipeline

```
New bar event (TimeFrameManager)
    │
    ▼
SwingPointDetector → detects swing highs/lows for that TF
    │
    ▼
RawBreakoutDetector → checks if price broke a prior swing
    │
    ▼
B2BDetector → chains 2 breakouts into 5-pointer zone (L1, L2, 50%)
    │
    ▼
B2BZoneManager → stores zone, checks redundancy (50pt / 50% overlap / 30d)
    │
    ▼
B2BConfluence → validates TF layer (Narrative / Control / Sniper)
    │
    ▼
B2BZoneStatus → monitors zone lifecycle each bar (DETECTED→ACTIVE→INVALIDATED)
```

See [[mt5-detection-pipeline]] for the full data flow with field-level detail.

---

## Execution Pipeline

```
B2BZoneStatus fires ZONE_CHANGE_STRUCTURAL
    │
    ▼
TradeSignalGenerator → 3-gate check (Narrative + Control + Sniper aligned?)
    │
    ▼
ContextMapper → session / spread / volatility OK?
    │
    ▼
IntradayOrchestrator → intraday time filter OK?
    │
    ▼
RiskManager → position size, drawdown headroom OK?
    │
    ▼
OrderManager → place order (market or limit)
    │
    ▼
TrailingStopManager → manage stop on each tick
```

See [[mt5-execution-pipeline]] for full flow.

---

## Known Issues / Notes

- `FeedbackPanel.mqh` is included twice in `Sigma_V5.0.mq5` (lines 51 and 63) — safe due to include guards but should be cleaned up
- Cascade invalidation (parent zone invalidates → child zones auto-invalidate) is decided but not fully implemented in V5.0 — see [[b2b-open-questions]]
- The B2B cluster detection edge case has 3 proposed fixes (A/B/C) in `workspace/sigma-mt5/Documentation/B2B_CLUSTER_FIX_PLAN.md` — awaiting decision

---

## Related Pages

- [[sigma-engine-map]] — How MT5 relates to sigma_core and sigma-crypto
- [[mt5-detection-pipeline]] — Detection data flow (stub)
- [[mt5-execution-pipeline]] — Execution data flow (stub)
- [[mt5-data-pipeline]] — QuantLogger → CSV → Supabase (stub)
- [[b2b-open-questions]] — Cluster fix, cascade gap
