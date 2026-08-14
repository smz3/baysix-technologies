# IntradayOrchestrator.mqh

## Purpose
An alternative execution engine specifically for intraday setups (Option B, V6.3). Where `StrategyOrchestrator` uses multi-TF Russian Doll flow states, `IntradayOrchestrator` focuses on the intraday session context — classifying the T1 phase of the narrative and the T2 "bridge" class between TFs. Trades are only authorised when the T1 phase, range position, and reward/risk all align.

## Layer
Trading

## Key Classes & Functions

| Name | Type | Description |
|------|------|-------------|
| `ENUM_T1_PHASE` | Enum | `CONQUEST` (trending), `SIEGE` (testing key level), `EXHAUSTION` (overextended), `VACUUM` (no clear direction), `INVALID` |
| `ENUM_BRIDGE_CLASS` | Enum | `FULL_ALIGN` (T1+T2 same direction), `PARTIAL` (mixed signals), `COUNTER` (T2 opposes T1), `NONE` |
| `CIntradayOrchestrator` | Class | Intraday 3-gate authorization engine |
| `Initialize(context_mapper, strategy_orchestrator)` | Method | Wire in Gate 2 and Gate 1 dependencies |
| `UpdateState(price, time)` | Method | Update internal price/time tracking each tick |
| `IsTradeAllowed(signal, zones[])` | Method | **Core**: Run all 3 intraday gates. Returns bool. |
| `DetermineT1Phase(tf_flow_states[])` | Private | Classify current phase from HTF FlowStates |
| `ClassifyBridge(t1_tf, t2_tf, flow_states[])` | Private | Compare T1 and T2 zone directions to classify bridge |
| `GetEntryThreshold(phase, bridge)` | Private | Phase+bridge-dependent price threshold for entry confirmation |
| `IsWithinSession(time)` | Private | UTC hour check against configured intraday trading window |
| `Gate1_NarrativePosture()` | Private | T1 phase must be CONQUEST or SIEGE; not EXHAUSTION/VACUUM |
| `Gate2_RangePosition(signal)` | Private | ContextMapper intraday position check |
| `Gate3_RewardCheck(signal, zones[])` | Private | Distance to nearest wall (reward) must exceed SL distance by minimum factor |

## The 3 Intraday Gates

| Gate | Name | Condition |
|------|------|-----------|
| Gate 1 | NARRATIVE POSTURE | T1 phase ∈ {CONQUEST, SIEGE} AND bridge ∈ {FULL_ALIGN, PARTIAL} |
| Gate 2 | RANGE POSITION | Price is within entry threshold based on intraday range position |
| Gate 3 | REWARD CHECK | Wall distance (reward) ≥ minimum factor × SL distance |

## Inputs / Outputs
- **`IsTradeAllowed`**: Takes `TradeSignal` + zones array → returns bool
- **`UpdateState`**: Takes price + time → updates internal state, no return

## Dependencies
- `Structures.mqh`, `TradingParameters.mqh`
- `ContextMapper.mqh`, `StrategyOrchestrator.mqh`

## Python Equivalent
`core/strategy/orchestrator.py` — the `StrategyOrchestrator._validate_trap()` method contains some intraday phase logic. A more complete parallel is `core/strategy/engines/efficiency_governor.py` — `EfficiencyGovernor.is_tier_allowed()` (Gate 1) and `is_spatially_efficient()` (Gate 3 analog). Python version does not separate Russian Doll and Intraday into distinct orchestrators.

## Notes
- T1 = the primary narrative TF (typically H4/D1); T2 = the entry TF (typically H1/M30)
- **CONQUEST** phase = price is moving strongly in one direction with no opposing zones in range — highest conviction, widest entry threshold
- **SIEGE** phase = price is testing a key zone repeatedly — medium conviction, tighter threshold
- **EXHAUSTION** phase = price has gone too far without a pullback — Gate 1 blocks trades in this phase
- The UTC session window (`IsWithinSession`) defaults to London+NY overlap but is configurable in `TradingParameters.mqh`
