# Market Flow GPS System

> **Version**: V8.1  
> **Created**: 2026-01-07  
> **Module**: `Include/V5.0/MarketFlow/`

---

## Overview

The Market Flow GPS System replaces the static "closest zone = origin" logic with a **state-machine** that tracks the Zone-to-Zone journey dynamically.

### Core Concept

```
Zone A (Origin)       →→→→→→→→→→→→       Zone B (Target)
       🚩                                      🏁
       │            THE MARKET FLOW            │
       │            (The "Journey")            │
       └──────────────────────────────────────┘
```

- **Zone A (Origin)**: The zone that was **tested and held** (price touched and rejected)
- **Zone B (Target)**: The **nearest opposing fresh zone** in the flow direction
- **Flow Direction**: Zone A's direction (BUY zone = BULLISH flow, SELL zone = BEARISH flow)

---

## GPS States

| State | Description | Trading Action |
|-------|-------------|----------------|
| **FLOW_NONE** | No valid flow established | No trading |
| **FLOW_PENDING** 🆕 | Zone L1 touched, awaiting held | Wait for confirmation |
| **FLOW_ON_ROUTE** ✅ | Price moving A → B (confirmed) | Trade aligned LTF zones |
| **FLOW_REVERSE** | Price retracing toward A | Wait / prepare for retest |
| **FLOW_ARRIVED** | Price reached Zone B | Close / TP hit |
| **FLOW_DETOUR** ⚠️ | Zone A invalidated | Flow broken, recalculate |
| **FLOW_FLIPPED** 🔄 | Zone B held, direction flips | Find new target |

### State Transition Diagram

```
                    L1 TOUCHED (Early Trigger)
                             │
                             ▼
                        ┌─────────┐
                        │ PENDING │─────────────────┐
                        └────┬────┘                 │
                             │                      │
                     Zone held             Zone A broken
                     (price away)          (L2 violated)
                             │                      │
                             ▼                      ▼
     ┌──────────────────── ON_ROUTE ◄────┐       DETOUR
     │                          │         │         │
     │ Zone A broken            │         │         │
     ▼                          ▼         │         │
  DETOUR                   ┌─────────┐    │         │
     │                     │ ARRIVED │────┘         │
     │                     └────┬────┘              │
     │                          │                   │
     │                     Zone B held              │
     │                          │                   │
     │                          ▼                   │
     │                     FLIPPED ─────────────────┘
     │                          │
     └──────────────────────────┴─────────────────────
                                │
                           (Find new A-B pair)
```

---

## "Tested and Held" Definition

A zone is confirmed as **Zone A (Origin)** when:

1. ✅ Price **touched L1** or deeper
2. ✅ Zone is **NOT invalidated** (L2 not broken)
3. ✅ Price **moved away** by threshold distance

### Threshold Calculation

```cpp
double threshold = MathMax(
    zone.GetZoneSize() * 0.5,   // 50% of zone size
    atr_value * 0.3             // 30% of ATR(14)
);
```

Uses the **LARGER** of two values to ensure meaningful confirmation.

---

## Multi-Timeframe GPS

The system supports multiple timeframe GPS instances via input parameters:

```cpp
input bool InpEnableGPS_H4 = true;   // Active for testing
input bool InpEnableGPS_D1 = false;  // Placeholder
input bool InpEnableGPS_H1 = false;  // Placeholder
```

LTF journeys are validated to be **within** HTF journeys for confluence.

---

## Zone Chain Tracking (ML Export)

### Trading Logic: A→B Only

Simple current-pair tracking for trading decisions:

```cpp
ulong zone_a_id;  // Current origin
ulong zone_b_id;  // Current target
```

### ML Export: Full Chain History

Rich data for machine learning:

```cpp
struct FlowLeg
{
    ulong from_zone;                      // Origin zone ID
    ulong to_zone;                        // Target zone ID
    ENUM_SIGNAL_DIRECTION direction;      // Flow direction
    datetime start_time;                  // When leg started
    datetime end_time;                    // When leg ended
    double distance_traveled;             // Points traveled
    bool completed;                       // Did price reach target?
};

FlowLeg m_flow_history[];  // Full chain for ML analysis
```

---

## File Structure

```
MQL5/Include/V5.0/MarketFlow/
├── MarketFlowTypes.mqh    ← Enums & struct definitions
├── MarketFlowState.mqh    ← State machine transitions
├── MarketFlowGPS.mqh      ← Main GPS controller
└── MarketFlowLogger.mqh   ← Debug logging (optional)
```

---

## Integration Points

### TradeSignalGenerator.mqh

```cpp
// In ResolveBestZone():
if(InpRequireH4Flow && (zone.timeframe == PERIOD_M30 || zone.timeframe == PERIOD_M15))
{
    if(!m_flow_gps.IsOnRoute())
        continue;  // Not in tradeable flow state
    
    if(zone.direction != m_flow_gps.GetFlowDirection())
        continue;  // Zone against flow direction
}
```

### FractalDominoLogger.mqh (Future)

Export `h4_flow_direction`, `zone_a_id`, `zone_b_id` for ML training.

---

## See Also

- [B2B_MarketFlow_V8.md](file:///c:/Users/User/Desktop/SIGMA%20System%20Anti%20Gravity/MQL5/Include/V5.0/Docs/B2B_MarketFlow_V8.md) - Core V8 concepts
- [V6_AnchorLogic.md](file:///c:/Users/User/Desktop/SIGMA%20System%20Anti%20Gravity/MQL5/Include/V5.0/Docs/V6_AnchorLogic.md) - Previous anchor approach
