---
type: wiki
domain: strategy
status: stable
tags:
  - b2b
  - core
  - zone-detection
related:
  - "[[b2b-zone-lifecycle]]"
  - "[[b2b-timeframe-hierarchy]]"
  - "[[b2b-touch-depth]]"
  - "[[b2b-invalidation]]"
  - "[[sigma-engine-map]]"
source_files:
  - "workspace/sigma-mt5/Documentation/B2B_DETECTION_SYSTEM.md"
  - "workspace/sigma-mt5/Documentation/B2B_STRATEGY_DECISIONS.md"
last_updated: 2026-04-14
maintained_by: ai
ai_summary: "B2B (Break of Two Barriers) zones form when two consecutive breakouts in the same direction identify institutional accumulation levels. L1 is the entry level, L2 is the invalidation level, and the 50% midpoint is the zone centre."
---

# B2B Zone Strategy — Overview

## What Is a B2B Zone?

A **Break of Two Barriers (B2B)** zone is a price region that forms when two consecutive breakouts occur in the same direction, where the second breakout reaches a more extreme swing point than the first. The zone represents an area of institutional positioning — price tends to return to these levels because trapped traders created a structural imbalance there.

### Zone Boundaries

| Level | Name | Definition |
|-------|------|------------|
| **L1** | Entry Level | The swing price broken by the 1st breakout. Price re-entering this level is the trade trigger. |
| **L2** | Invalidation Level | The most extreme swing within the pattern window. One close beyond L2 = zone dead. |
| **50% Line** | Zone Centre | Midpoint between L1 and L2. Used for mid-zone entry and touch depth tracking. |

```
BUY B2B (price going up, zone below current price):

   L1 ────●──────────────────────────────  ← 1st breakout level (higher high)
           │
  50% ─────┼──────────────────────────────  ← Midpoint
           │
   L2 ────●──────────────────────────────  ← Impulse swing (lowest low in window)
           │
           └─ Zone anchored at L2 swing time
```

```
SELL B2B (price going down, zone above current price):

   L2 ────●──────────────────────────────  ← Impulse swing (highest high in window)
           │
  50% ─────┼──────────────────────────────  ← Midpoint
           │
   L1 ────●──────────────────────────────  ← 1st breakout level (lower low)
           │
           └─ Zone anchored at L2 swing time
```

---

## The 5-Pointer Pattern

A valid B2B zone requires five structural points in sequence:

1. **Point 1** — Original swing (a significant high or low)
2. **Point 2** — Price breaks Point 1 (this becomes L1, the 1st barrier broken)
3. **Point 3** — The impulse swing after Point 1 that drove price to break it (this becomes L2, the 2nd barrier)
4. **Point 4** — Pullback into the L1–L2 zone
5. **Point 5** — Continuation in the breakout direction

If all 5 points are present and structurally sound, a zone is created.

---

## Detection Rules

### Direction Match

Both breakouts must be in the same direction — both bullish (breaking highs) or both bearish (breaking lows).

### L1 Selection (CORRECTED Dec 18, 2025)

When multiple valid 1st breakout candidates exist for the same 2nd breakout:

> [!DECISION]
> **BUY zones:** Prefer the **HIGHEST L1** (tighter zone = better risk/reward)
> **SELL zones:** Prefer the **LOWEST L1** (tighter zone = better risk/reward)
>
> This was inverted before Dec 18, 2025. The old logic (BUY = lowest, SELL = highest) was wrong.

### L2 Selection

| Direction | L2 = |
|-----------|------|
| BUY | LOWEST swing LOW within the pattern window |
| SELL | HIGHEST swing HIGH within the pattern window |

L2 can appear before or after L1 in time — position flexibility is intentional.

### Redundancy Checks (same direction only)

Duplicate zones are pruned when:
- L2 prices are within **50 points** of each other, OR
- Zone boundaries **overlap >50%**, AND
- Zones are within **30 days** of each other

When redundant, keep the zone with the tighter L1 (highest for BUY, lowest for SELL).

> [!DECISION]
> **Cross-layer protection (Dec 18, 2025):** Zones from different TF layers (Narrative/Control/Sniper) do NOT deduplicate each other. Only same-layer zones are compared.

---

## Multi-Pair Detection

The system detects up to **5 B2B pairs per direction** (max 10 zones per TF: 5 SELL + 5 BUY). This provides visibility into multiple historical patterns, not just the most recent.

---

## Entry Sequence

The full entry flow from Narrative to execution:

```
1. Narrative zone (D1/W1/MN1) exists in a direction
2. Price approaches and touches the Narrative zone's L1  → WAIT
3. Control zone (H4/H1/M30/M15) forms inside Narrative in same direction
4. Sniper confirmation (M5/M1 B2B) forms in same direction
5. Execute trade at Sniper zone L1/50%/L2
```

> [!DECISION]
> Entry is ALWAYS via M5 or M1 B2B sniper confirmation. No exceptions.
> Do NOT take opposite direction sniper B2B even if it forms at parent L2.

---

## Why B2B Zones Work

Institutional accumulation requires multiple attempts. Each time price breaks a swing, it leaves trapped traders behind. When price returns to the zone, those trapped participants cover positions, creating the bounce or reversal. The two-barrier requirement filters out weaker signals — a single breakout is common noise; two consecutive breakouts in the same direction indicate deliberate, directional institutional flow.

---

## Related Pages

- [[b2b-zone-lifecycle]] — Full DETECTED → ACTIVE → INVALIDATED state machine
- [[b2b-timeframe-hierarchy]] — Which TFs are Narrative, Control, Sniper
- [[b2b-touch-depth]] — T0/T1/T2/T3 touch tracking within zones
- [[b2b-invalidation]] — All invalidation rules including cascade
- [[b2b-open-questions]] — Known edge cases and pending decisions
- [[sigma-engine-map]] — How this detection is implemented in Python and MQL5

## Source References

- `workspace/sigma-mt5/Documentation/B2B_DETECTION_SYSTEM.md` — primary detection spec
- `workspace/sigma-mt5/Documentation/B2B_STRATEGY_DECISIONS.md` — all agreed decisions
