# StrategyOrchestrator.mqh

## Purpose
The 3-Gate Execution Engine for the Russian Doll strategy. Maintains a persistent `FlowState` for each timeframe — tracking which zone is the origin, outpost, magnet, and roadblock — and uses these to decide whether a trade is allowed at the current price. All three gates must pass before a signal reaches `OrderManager`.

## Layer
Trading

## Key Classes & Functions

| Name | Type | Description |
|------|------|-------------|
| `FlowState` | Struct | Per-TF directional state machine: tracks origin_id, magnet_id, outpost_id, roadblock_id, their prices, L2 levels, siege state, touch times, traded flags, and the magnet extremum flag |
| `ENUM_TRADE_TYPE` | Enum | `CONTINUATION`, `FADE`, `BREAKOUT`, `NONE` |
| `CStrategyOrchestrator` | Class | 3-gate authorization engine |
| `SetContextMapper(mapper)` | Method | Wire in ContextMapper for Gate 2 spatial checks |
| `Orchestrate(price, time, zones[], tf)` | Method | Advance FlowState for the given TF based on current price and zones |
| `IsTradeAllowed(signal, zones[])` | Method | **Core**: Run all 3 gates. Returns bool. |

## The 3 Gates

| Gate | Name | What It Checks |
|------|------|----------------|
| Gate 1 | DIRECTION | FlowState: is there a valid origin → outpost → magnet chain in the right direction? |
| Gate 2 | LOCATION | ContextMapper: is price in the right spatial position relative to session boundaries? |
| Gate 3 | STRUCTURE | Is the target zone nested inside a higher-TF zone (Tier 2 nesting check)? |

## FlowState Lifecycle

```
Origin → Outpost → Magnet (target zone)
  ↑ price breaks L1    ↑ price breaks next swing    ↑ zone of interest
```
A trade is allowed only when the magnet zone is touched and Gates 1+2+3 all pass.

## Inputs / Outputs
- **`Orchestrate`**: Takes current price/time + zones array + TF → updates `FlowState` array in-place
- **`IsTradeAllowed`**: Takes `TradeSignal` + zones array → returns bool (and may update FlowState traded flags)

## Internal State
- `FlowState m_flow_states[TOTAL_TIMEFRAMES]` — one per TF, persists across ticks
- Pointer to `CContextMapper` for Gate 2

## Dependencies
- `Structures.mqh`, `B2BDetector.mqh`, `B2BZoneManager.mqh`
- `B2BConfluence.mqh`, `B2BTradeTracker.mqh`
- `QuantLogger.mqh`, `TradingParameters.mqh`, `ContextMapper.mqh`

## Python Equivalent
`core/strategy/orchestrator.py` — `StrategyOrchestrator` class. The `FlowState` struct maps to Python's `FlowState` dataclass in `models/structures.py`. Gates 1/2/3 are implemented as `_validate_trap()`, `FractureEngine.is_inside_opposing_zone()`, and `EfficiencyGovernor.is_tier_allowed()` respectively.

## Notes
- **Version 6.2** — this module has gone through the most iterations of any trading layer file
- FlowState persists across ticks/bars (it lives on the class instance) — this is the "memory" of the strategy
- "Siege state" in `FlowState` tracks whether the magnet zone is currently being approached or retreated from
- The `magnet_extremum_flag` is set when price has fully penetrated the magnet zone — signals the zone has been "consumed" and the flow should reset to find a new origin
