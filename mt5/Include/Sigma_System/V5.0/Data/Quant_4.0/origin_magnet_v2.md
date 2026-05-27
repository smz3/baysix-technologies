# Fractal Flow V2.0: Origin-Magnet Fixed Role Model

> **Document Version:** V2.0  
> **Date:** 2026-02-07  
> **Status:** Strategy Locked

---

## Core Philosophy

**The Origin-Magnet model replaces the Flip-based model.**

| Old Model (V1.x)            | New Model (V2.0)                                |
|-----------------------------|-------------------------------                  |
| Anchor/Magnet swap on touch | Origin/Magnet stay FIXED                        |
| Roles change constantly     | Roles only change on new structure formation    |
| Confusing state management  | Clear, persistent state                         |

---

## Key Definitions

### Origin Anchor
> **The zone where price most recently BOUNCED FROM at that timeframe.**

- It's the genesis of the current move
- It represents the "Point A" of the current leg
- Trades from Origin = **WITH TREND**

### Magnet
> **The first opposing zone ahead of price (the target).**

- It's where price is heading
- It represents the "Point B" of the current leg
- Trades from Magnet = **COUNTER TREND**

---

## The Fractal Cascade

Each timeframe maintains its own Origin-Magnet pair, nested within higher timeframes:

```
MN1: Origin @ 1500 (BUY)  ─────────────►  Magnet @ 1700 (SELL)
     │                                          │
     │   W1: Origin @ 1520 (BUY)  ─────►  Magnet @ 1650 (SELL)
     │        │                                 │
     │        │   D1: Origin @ 1530 ──► Magnet @ 1620
     │        │        │                        │
     │        │        │   H4/H1/M30: Traps     │
     │        │        │                        │
     │        └────────┴─────────────────────── ┘
     │
     └── MN1 sets the NARRATIVE for all nested timeframes
```

---

## Trade Classification

| Price Location | Trade Direction  | Classification    | Target         |
|----------------|------------------|-------------------|----------------|
| Near Origin    | Anchor direction | **WITH TREND**    | Magnet         |
| Near Magnet    | Magnet direction | **COUNTER TREND** | Origin Anchor  |

---

## Roadblock System

Each timeframe's zones act as roadblocks for trades:

- **With-Trend trade:** Magnet is the target, intermediate magnets are TPs
- **Counter-Trend trade:** Origin Anchor is the target, intermediate anchors are TPs

```
Example: Price at D1 Magnet area (1620)

Counter-Trend SELL:
├── Entry: D1 Magnet trap
├── SL: Trap L2 + buffer (execution TF structure, unchanged)
├── TP1: W1 intermediate level
└── TP2: D1 Origin @ 1530 (roadblock)

With-Trend BUY (wait until):
├── Price returns to D1 Origin area
├── Fresh trap forms inside D1 Origin
├── Entry: D1 Origin trap toward Magnet
├── SL: Trap L2 + buffer (execution TF structure, unchanged)
└── TP: D1 Magnet @ 1620
```

---

## When Roles Change

**Origin and Magnet only change when:**

1. **New structure forms** - A new zone is created that becomes the new Origin
2. **Zone is invalidated** - Price breaks through L2 (zone broken)
3. **Full retracement complete** - Price travels from Origin → Magnet → back to Origin → new Magnet

**Roles do NOT change when:**
- Price simply touches a zone
- Price bounces slightly
- Time passes

---

## Alignment Matrix

| MN1 Origin | W1 Origin | D1 Origin | Trade Signal | Classification      | Confidence  |
|------------|-----------|-----------|--------------|---------------------|-------------|
| BUY        | BUY       | BUY trap  | BUY          | With-Trend (All aligned) | **HIGH** |
| BUY        | BUY       | SELL trap | SELL         | Counter D1 (D1 Magnet) | MEDIUM    |
| BUY        | SELL      | SELL trap | SELL         | Counter W1 (W1 Magnet) | MEDIUM    |
| BUY        | SELL      | BUY trap  | BUY          | Avoid (Mixed signals)  | LOW       |
| SELL       | SELL      | SELL trap | SELL         | With-Trend (All aligned) | **HIGH** |
| SELL       | SELL      | BUY trap  | BUY          | Counter D1 (D1 Magnet) | MEDIUM    |
| SELL       | BUY       | BUY trap  | BUY          | Counter W1 (W1 Magnet) | MEDIUM    |
| SELL       | BUY       | SELL trap | SELL         | Avoid (Mixed signals)  | LOW       |

> **Note:** Origin columns show the **Origin Anchor direction** for that TF. Trade from Origin = With-Trend. Trade from Magnet = Counter-Trend.

---

## Implementation Requirements

### Data Structure Changes

```cpp
struct FlowState {
   ulong origin_id;           // The Origin Anchor zone ID
   ulong magnet_id;           // The Magnet zone ID
   ENUM_SIGNAL_DIRECTION origin_dir;  // Origin direction (trade WITH trend)
   ENUM_SIGNAL_DIRECTION magnet_dir;  // Magnet direction (trade COUNTER)
   datetime origin_touch_time;        // When Origin was last touched
   bool is_valid;
};
```

### Trade Authorization Logic

```cpp
// Check if trade is With-Trend or Counter-Trend
bool is_with_trend = (trap.direction == origin_dir);
bool is_counter_trend = (trap.direction == magnet_dir);

// Set TP based on trade type
if(is_with_trend)
   tp = magnet_zone.L1_price;  // Target is Magnet
else
   tp = origin_zone.L1_price;  // Target is Origin (roadblock)
```

---

## Summary

1. **Origin = Point A** (where the move started)
2. **Magnet = Point B** (where the move is heading)
3. **Roles are FIXED** (no more flip confusion)
4. **With-Trend = Origin direction** (higher probability)
5. **Counter-Trend = Magnet direction** (lower probability, tighter TP)
6. **Roadblocks = Intermediate zones as TPs**
