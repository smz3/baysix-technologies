---
type: wiki
domain: strategy
status: stable
tags:
  - b2b
  - timeframes
  - architecture
related:
  - "[[b2b-overview]]"
  - "[[b2b-russian-doll]]"
  - "[[b2b-zone-lifecycle]]"
source_files:
  - "workspace/sigma-mt5/Documentation/B2B_STRATEGY_DECISIONS.md"
last_updated: 2026-04-14
maintained_by: ai
ai_summary: "B2B zones are classified into three layers: Narrative (MN1/W1/D1) for direction and bias, Control (H4/H1/M30/M15) for zone refinement, and Sniper (M5/M1) for execution. Each layer has distinct rules for visibility, invalidation, and child zone requirements."
---

# B2B Timeframe Hierarchy

## The Three Layers

```
┌─────────────────────────────────────────────────────────┐
│  NARRATIVE  ─── MN1 / W1 / D1                           │
│  "Where are institutions going?"                         │
│  Sets direction and bias. Always visible.                │
├─────────────────────────────────────────────────────────┤
│  CONTROL  ─── H4 / H1 / M30 / M15                       │
│  "How big is the opportunity?"                           │
│  Refines zone. Must be inside Narrative zone.            │
├─────────────────────────────────────────────────────────┤
│  SNIPER  ─── M5 / M1                                     │
│  "Where exactly do we enter?"                            │
│  Execution only. Must confirm Narrative direction.       │
└─────────────────────────────────────────────────────────┘
```

| Layer | Timeframes | Role |
|-------|------------|------|
| **NARRATIVE** | MN1, W1, D1 | Direction & Bias |
| **CONTROL** | H4, H1, M30, M15 | Zone Refinement |
| **SNIPER** | M5, M1 | Execution |

> [!DECISION]
> M15 and M30 are **CONTROL layer**, not Sniper. Sniper = M5 and M1 only.

---

## Narrative Layer (MN1 / W1 / D1)

**Purpose:** Establish where institutions are positioned and where price is going.

**Rules:**
- Always detected and visible — no parent alignment required
- Set the top-level directional bias
- Zones survive without any parent because they ARE the parent
- Trade direction of all child zones must align with Narrative direction

**Invalidation:** 1 close beyond L2 on that specific TF (monthly, weekly, or daily candle)

---

## Control Layer (H4 / H1 / M30 / M15)

**Purpose:** Refine the opportunity — find the exact zone structure within the Narrative zone.

**Rules:**
- Control zone's L1 **and** L2 must both fall between the Narrative zone's L1 and L2
  ```
  Narrative (D1): L1 ────────────────────────────── L2
                       │                        │
  Control (H4):        └── L1 ──────── L2 ──────┘  ✓ VALID
  ```
- Detect independently, then validate against Narrative when parent forms
- Same color whether Narrative parent is active or not (reduces complexity)
- **Fallback hierarchy:** H4 → H1 → M30 → M15 (if no H4 exists, look for H1, etc.)
- **Multiple control zones** in same direction = stacked confirmation = higher conviction

**Invalidation:** 1 close beyond L2 on the Control zone's TF

---

## Sniper Layer (M5 / M1)

**Purpose:** Execution confirmation — the final signal to enter a trade.

**Rules:**
- Only show Sniper zones **inside parent (Narrative or Control) zones**
- Must be in the **same direction** as Narrative — no counter-direction entries even at L2
- Whichever Sniper TF (M5 or M1) forms B2B first → Execute

**Invalidation:** 1 close beyond L2 on M5 or M1 (fast invalidation by design)

---

## Entry Sequence (Full Flow)

```
Step 1: Narrative zone (D1/W1/MN1) exists and price approaches L1
Step 2: Price touches Narrative L1  →  WAIT
Step 3: Control zone (H4 → H1 → M30 → M15) forms INSIDE Narrative in same direction
Step 4: Sniper B2B (M5 or M1) forms in same direction
Step 5: Enter trade at Sniper L1, 50%, or L2
```

> [!DECISION]
> **Only execute when Sniper B2B matches Narrative direction.**
> Do NOT take opposite direction Sniper B2B even if it forms at Narrative L2.

---

## Child Zone Visibility Rules

| Layer | Historical Detection | Live Detection |
|-------|---------------------|----------------|
| Sniper (M5/M1) | Only show inside Narrative/Control parent | Only show inside Narrative/Control parent |
| Control (H4/H1) | Detect independently, validate vs Narrative | Detect independently, validate when parent forms |
| Narrative (D1/W1/MN1) | Always detect and show | Always detect and show |

---

## Cascade Invalidation

> [!DECISION]
> When a **parent zone invalidates**, all child zones within it **auto-invalidate**.
>
> Rationale: If the parent thesis is dead, the children are worthless — they were only valid because of the parent structure.

See [[b2b-invalidation]] for full cascade rules.

---

## Layer Protection (Cross-Layer Deduplication Disabled)

> [!DECISION]
> Zones from **different layers** do NOT deduplicate each other.
> Only zones **within the same layer** are compared for redundancy.
>
> Example: A D1 (Narrative) zone and H4 (Control) zone at the same price level are BOTH kept.
> Implemented: Dec 18, 2025.

---

## MQL5 Implementation

- Layer detection: `CB2BConfluence::IsNarrativeTF()`, `IsControlTF()`, `IsEntryTF()`
- Layer visibility: `InpShowB2BNarrativeZones`, `InpShowB2BControlZones`, `InpShowB2BSniperZones` in `TradingParameters.mqh`
- See [[mt5-ea-architecture]] → `Detection/B2BConfluence.md` for implementation details

## Related Pages

- [[b2b-overview]] — B2B zone formation basics
- [[b2b-russian-doll]] — Nesting rules and confluence scoring
- [[b2b-invalidation]] — Invalidation and cascade rules per TF
