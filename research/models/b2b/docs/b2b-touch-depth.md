---
type: wiki
domain: strategy
status: stable
tags:
  - b2b
  - tracking
  - zones
related:
  - "[[b2b-overview]]"
  - "[[b2b-zone-lifecycle]]"
  - "[[b2b-invalidation]]"
source_files:
  - "workspace/sigma-mt5/Documentation/B2B_DETECTION_SYSTEM.md"
  - "workspace/sigma-mt5/Documentation/B2B_STRATEGY_DECISIONS.md"
last_updated: 2026-04-14
maintained_by: ai
ai_summary: "B2B zones track touch depth T0→T1→T2→T3. T0 = fresh zone, T1 = first touch at L1, T2 = penetration to 50% midpoint, T3 = deep touch to L2 (wick only — close beyond L2 = invalidation). Touch count is cumulative and informs position sizing."
---

# B2B Touch Depth (T0 / T1 / T2 / T3)

## Overview

Each B2B zone tracks how deeply price has tested it. This "touch depth" system provides intelligence about zone strength — a zone that has been touched deeply multiple times is structurally weakening.

---

## Touch Depth Levels

| Level | Name | Definition |
|-------|------|------------|
| **T0** | Fresh | Zone created, price has not yet reached L1. Untouched. |
| **T1** | First Touch | Price crosses L1 for the first time (zone goes ACTIVE). |
| **T2** | Mid-Zone | Price penetrates to the 50% midpoint between L1 and L2. |
| **T3** | Deep Test | Price wicks to L2 but closes inside the zone. Zone is still valid. |

```
SELL zone (price approaches from below):

   L2 ────────────────────────────────── ← T3 reached (wick to L2, zone survives)
   50% ─────────────────────────────────  ← T2 reached (mid-zone penetration)
   L1 ────────────────────────────────── ← T1 (first touch, zone goes ACTIVE)
         ↑ Price approaches from below
```

---

## T3 vs. Invalidation — Critical Distinction

> [!CAUTION]
> **T3 is NOT invalidation.**
>
> - If price **wicks** to L2 but **closes inside** the zone → T3. Zone remains VALID.
> - If price **closes beyond** L2 → Zone is INVALIDATED.
>
> A T3 wick to L2 is intelligence: the zone is being deeply tested and may be weakening. It is NOT a kill signal.

See [[b2b-invalidation]] for full invalidation rules.

---

## Exit-First Rule

> [!DECISION]
> After zone formation, price must **exit** the zone completely before any touch counts as T1.
>
> - SELL zones: price must go **below** the zone first, then return up to L1 to trigger T1
> - BUY zones: price must go **above** the zone first, then return down to L1 to trigger T1
>
> Rationale: Prevents counting zone formation candles as a touch (false T1).

---

## Touch Count Persistence

> [!DECISION]
> Touch count is **cumulative across all visits**. It does not reset when price leaves the zone.
>
> If price enters a zone (T1), leaves, and returns 3 weeks later — the zone is still ACTIVE and will advance from T1 to T2 on the next deeper penetration.
>
> Rationale: Institutional positioning doesn't reset when price exits temporarily. Each test weakens the zone structurally.

---

## Position Sizing Intelligence

Touch depth informs trade conviction:
- **T1 zones:** Standard size — first touch is the strongest signal
- **T2/T3 zones:** Reduced size — zone is weakening; institutional orders may be partially filled
- **Multiple T3 touches:** Highest caution — zone is likely to fail on next approach

---

## MQL5 Implementation

- Touch depth tracked in `CB2BZoneStatus::UpdateZoneStatus()` — increments T0→T1→T2→T3 on each bar
- Touch state persisted via `ZonePersistence.mqh` — survives EA restarts
- Historical validation: `ValidateZonesInBuffer()` replays bars to restore correct touch depth after downtime

## Related Pages

- [[b2b-zone-lifecycle]] — Full state machine (DETECTED → ACTIVE → INVALIDATED)
- [[b2b-invalidation]] — When T3 becomes invalidation (close beyond L2)
- [[b2b-overview]] — B2B zone structure (L1, L2, 50%)
