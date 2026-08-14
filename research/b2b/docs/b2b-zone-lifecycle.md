---
type: wiki
domain: strategy
status: stable
tags:
  - b2b
  - zones
  - zone-detection
related:
  - "[[b2b-overview]]"
  - "[[b2b-touch-depth]]"
  - "[[b2b-invalidation]]"
  - "[[b2b-russian-doll]]"
source_files:
  - "workspace/sigma-mt5/Documentation/B2B_DETECTION_SYSTEM.md"
  - "workspace/sigma-mt5/Documentation/B2B_STRATEGY_DECISIONS.md"
last_updated: 2026-04-14
maintained_by: ai
ai_summary: "B2B zones move through three states: DETECTED (zone exists, price hasn't reached it), ACTIVE (price crosses L1 for the first time), INVALIDATED (one close beyond L2 on the zone's own timeframe). Zones never expire due to age alone."
---

# B2B Zone Lifecycle

## States

```
 DETECTED ──────► ACTIVE ──────► INVALIDATED
   (zone             (L1           (L2 close
  created)         crossed)        beyond)
```

| State | Definition | How to Enter |
|-------|------------|--------------|
| **DETECTED** | Zone exists, price has not yet reached L1 | Automatic at zone creation |
| **ACTIVE** | Price has crossed L1 for the first time | Price enters zone boundary (crosses L1) |
| **INVALIDATED** | Zone is dead — structural thesis failed | One candle close beyond L2 on zone's own TF |

---

## DETECTED State

Zone is created from historical swing + breakout detection. At creation:
- Touch count = **T0** (fresh, untouched)
- Zone is visible on chart
- Trade is NOT triggered yet — waiting for price to return

> [!DECISION]
> **Zone aging does not trigger state change.** Old zones are 100% valid regardless of age.
> Rationale: B2B indicates accumulation → rally → trapping traders → returns to zone. The return can happen months or years later.

---

## ACTIVE State

Price enters the zone by crossing L1 for the first time. Touch count advances to **T1**.

### Exit-First Rule

> [!DECISION]
> After zone formation, price must first **EXIT** the zone completely before any touch counts as T1.
>
> - SELL zones: Price must go **below** the zone first, then return UP to L1 to trigger T1
> - BUY zones: Price must go **above** the zone first, then return DOWN to L1 to trigger T1
>
> Rationale: Prevents counting the zone formation candles as a touch (which would falsely inflate T1 signals).

---

## INVALIDATED State

A zone is invalidated when **one candle closes beyond L2** on the zone's own timeframe.

| Zone Direction | Invalidation Trigger |
|----------------|---------------------|
| SELL | One candle close **above** L2 |
| BUY | One candle close **below** L2 |

Specific rules per TF:

| Timeframe | Invalidation Candle |
|-----------|---------------------|
| MN1, W1 | 1 monthly/weekly close beyond L2 |
| D1 | 1 daily close beyond L2 |
| H4, H1 | 1 H4/H1 close beyond L2 |
| M30, M15 | 1 M30/M15 close beyond L2 |
| M5, M1 | 1 M5/M1 close beyond L2 (fast invalidation) |

> [!CAUTION]
> **T3 ≠ Invalidation.** A wick to L2 (without a close beyond) sets T3 but does NOT invalidate the zone. The zone remains valid.

---

## Zone Persistence and Re-entry

> [!DECISION]
> Touch count is **cumulative across all visits**. Zone remains ACTIVE until INVALIDATED.
>
> Scenario: Price enters zone (T1), leaves, comes back 3 weeks later.
> Result: Zone is still ACTIVE, touch count continues from T1 (advances to T2 on deeper penetration).
>
> Rationale: Institutional positioning doesn't reset when price leaves temporarily. Each test weakens the zone structurally — that intelligence must not be lost.

---

## Historical Validation

When zones are loaded from persistence (EA restart, TF chart change), `ValidateZonesInBuffer()` replays all historical bars to:
1. Confirm zones were not already invalidated while EA was offline
2. Restore correct touch count (T0/T1/T2/T3) from historical price action
3. Mark stale zones as INVALIDATED before display

This prevents ghost zones from appearing on chart that were already consumed by price.

---

## Zone ID and Persistence

Each zone gets a **deterministic FNV-1a hash** as its ID, computed from L1/L2/TF/direction/time. This means:
- The same zone detected in backtest has the same ID as in live trading
- Zones persist across EA restarts via binary file (`ZonePersistence.mqh`)
- `MergeLoadedZones()` uses the ID to prevent duplicates after reload

---

## Related Pages

- [[b2b-overview]] — What B2B zones are and how they form
- [[b2b-touch-depth]] — T0/T1/T2/T3 depth tracking system
- [[b2b-invalidation]] — Full invalidation rules including cascade
- [[b2b-russian-doll]] — Child zone visibility rules within parent zones
