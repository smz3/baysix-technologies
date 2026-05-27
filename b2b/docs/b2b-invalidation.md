---
type: wiki
domain: strategy
status: stable
tags:
  - b2b
  - risk
  - zone-detection
related:
  - "[[b2b-zone-lifecycle]]"
  - "[[b2b-overview]]"
  - "[[b2b-timeframe-hierarchy]]"
  - "[[b2b-open-questions]]"
source_files:
  - "workspace/sigma-mt5/Documentation/B2B_DETECTION_SYSTEM.md"
  - "workspace/sigma-mt5/Documentation/B2B_STRATEGY_DECISIONS.md"
last_updated: 2026-04-14
maintained_by: ai
ai_summary: "A B2B zone is invalidated by one candle close beyond L2 on the zone's own timeframe. When a parent zone invalidates, all child zones within it cascade-invalidate automatically. Wicking to L2 (T3) does NOT invalidate."
---

# B2B Zone Invalidation

## Core Rule

> [!DECISION]
> **1 candle close beyond L2 = Zone invalidated.**
>
> - SELL zone: 1 close **above** L2 → INVALIDATED
> - BUY zone: 1 close **below** L2 → INVALIDATED
>
> No need for 2 consecutive closes. One is sufficient.

The candle must be on **the zone's own timeframe** — an M1 close does not invalidate a D1 zone.

---

## Per-Timeframe Invalidation

| Timeframe | Invalidating Candle |
|-----------|---------------------|
| MN1 | 1 monthly close beyond L2 |
| W1 | 1 weekly close beyond L2 |
| D1 | 1 daily close beyond L2 |
| H4 | 1 H4 close beyond L2 |
| H1 | 1 H1 close beyond L2 |
| M30 | 1 M30 close beyond L2 |
| M15 | 1 M15 close beyond L2 |
| M5 | 1 M5 close beyond L2 (fast) |
| M1 | 1 M1 close beyond L2 (fast) |

Sniper (M5/M1) zones invalidate quickly by design — they are short-duration execution zones.
Narrative (D1/W1/MN1) zones require a full candle close on that TF — monthly invalidation requires patience.

---

## Wick vs. Close — Critical Distinction

> [!CAUTION]
> **T3 ≠ Invalidation.**
>
> - If price **wicks** to L2 but **closes inside** the zone → Touch depth advances to T3. Zone stays VALID.
> - If price **closes beyond** L2 → Zone is INVALIDATED.
>
> A T3 wick to L2 is intelligence (deep zone test, zone is weakening). It is NOT a kill signal.

---

## Cascade Invalidation

> [!DECISION]
> When a **parent zone invalidates**, ALL child zones within it auto-invalidate simultaneously.
>
> Rationale: The parent zone defined the structural context. If the parent thesis is dead (price closed beyond its L2), the child zones within it lose their anchor — they cannot stand alone.

### Cascade Example

```
D1 SELL zone exists (Narrative) — L1 at 1950.00, L2 at 1980.00

  ┌── D1 zone: L1=1950 ──── L2=1980 ──────────────────────┐
  │                                                         │
  │   H4 SELL zone: L1=1955 ── L2=1965 (Control)          │
  │   M5 SELL zone: L1=1953 ── L2=1958 (Sniper)           │
  │                                                         │
  └─────────────────────────────────────────────────────────┘

IF: D1 candle closes at 1985 (above D1 L2=1980)
THEN:
  → D1 zone: INVALIDATED
  → H4 zone (child of D1): INVALIDATED automatically
  → M5 zone (child of D1): INVALIDATED automatically
```

> [!CAUTION]
> Cascade invalidation is a **planned decision** but not fully implemented in V5.0 yet.
> See [[b2b-open-questions]] for implementation status and options.

---

## Opposite-Direction Zones at Invalidation Level

**Scenario:** D1 SELL zone exists. At D1's L2, an H4 BUY zone forms.

> [!DECISION]
> Show both zones. Let the market decide. No trap labels.
> The system follows what B2B forms — if H4 creates a BUY at D1 L2, execute the BUY signal from that zone.

---

## Post-Invalidation Behavior

> [!DECISION]
> Use **pre-detected zones (Option B)** — all zones are detected at `OnInit` across all TFs.
> Invalidation simply removes the consumed zone from the display.
> The next available zone was already visible before invalidation happened.
> No special re-scan is triggered.

---

## Historical Validation

At startup (EA init or restart), `ValidateZonesInBuffer()` replays all historical bars for loaded zones to:
1. Check if any loaded zone was invalidated while EA was offline
2. Mark those zones as INVALIDATED before displaying on chart

This ensures no "ghost zones" appear that were already consumed by price during downtime.

---

## MQL5 Implementation

- Core logic: `CB2BZoneStatus::UpdateZoneStatus()` — checks every active zone per TF on each new bar
- Returns bitmask: `ZONE_CHANGE_STRUCTURAL` if a zone was invalidated, `ZONE_CHANGE_METRIC` if only age/metrics updated
- Historical validation: `CB2BZoneStatus::ValidateZonesInBuffer()`
- See [[mt5-ea-architecture]] → `Detection/B2BZoneStatus.md`

## Related Pages

- [[b2b-zone-lifecycle]] — Full zone state machine (DETECTED → ACTIVE → INVALIDATED)
- [[b2b-touch-depth]] — T3 touch vs. invalidation — the critical distinction
- [[b2b-open-questions]] — Cascade implementation status, cluster fix
