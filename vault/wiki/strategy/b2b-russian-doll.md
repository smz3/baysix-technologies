---
type: wiki
domain: strategy
status: stable
tags:
  - b2b
  - confluence
  - nesting
related:
  - "[[b2b-overview]]"
  - "[[b2b-timeframe-hierarchy]]"
  - "[[b2b-invalidation]]"
  - "[[b2b-touch-depth]]"
source_files:
  - "workspace/sigma-mt5/Documentation/B2B_STRATEGY_DECISIONS.md"
last_updated: 2026-04-14
maintained_by: ai
ai_summary: "Russian Doll: child zone L1 AND L2 must both physically sit inside parent L1-L2. Control zones use H4→H1→M30→M15 fallback. Multiple control zones in same direction = stacked confirmation. Cascade invalidation: parent dies, all children die."
---

# B2B Russian Doll (Nested Zone Confluence)

## Concept

The "Russian Doll" describes the nesting of B2B zones across timeframe layers. A Narrative zone is the outer shell. A Control zone sits physically inside it. A Sniper zone sits inside the Control. Each added layer increases trade conviction — the zones reinforce each other structurally.

```
┌── Narrative (D1 SELL): L1=1950 ─────────────────── L2=1980 ──┐
│                                                                 │
│   ┌── Control (H4 SELL): L1=1955 ─────── L2=1965 ──┐          │
│   │                                                  │          │
│   │   ┌── Sniper (M5 SELL): L1=1956 ─ L2=1960 ─┐   │          │
│   │   │                                          │   │          │
│   │   │   ← Optimal entry zone                   │   │          │
│   │   └──────────────────────────────────────────┘   │          │
│   └──────────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

**Why it works:** Each zone in the doll represents a different institutional timeframe agreeing on the same directional thesis. More agreement = stronger structural imbalance = higher probability zone.

---

## The Nesting Rule

> [!DECISION]
> **Control zone's L1 AND L2 must BOTH fall between parent's L1 and L2.**
>
> ```
> Parent (D1):    L1 ─────────────────────────────── L2
>                      │                         │
> Control (H4):        └─── L1 ───── L2 ─────────┘   ✓ VALID
>
> Control (H4):   L1 ──────────── L2                  ✗ INVALID (L1 outside parent)
> ```
>
> Both boundaries must be inside. A partial overlap is not valid nesting.

---

## Control Zone Fallback Hierarchy

> [!DECISION]
> When looking for a Control zone, use this priority order:
>
> **H4 → H1 → M30 → M15**
>
> If no H4 B2B exists inside the Narrative zone, look for H1. If no H1, look for M30. If no M30, look for M15.

This fallback ensures that even in low-volatility environments (where H4 rarely forms a clean B2B), execution can still proceed via M30 or M15 confirmation.

---

## Multiple Control Zones — Stacked Confirmation

> [!DECISION]
> If BOTH H4 AND M30 have B2B zones in the same direction inside the Narrative zone, use both.
>
> **Multiple aligned control zones = stacked confirmation = higher conviction trade.**

```
D1 SELL narrative zone
  ├── H4 SELL zone (L1/L2 inside D1)   ← Control layer #1
  ├── M30 SELL zone (L1/L2 inside D1)  ← Control layer #2 (bonus)
  └── M5 SELL zone (inside H4)         ← Sniper entry
```

Two control zones pointing the same direction means two different institutional timeframes have left supply at the same level. The probability is higher than a single control zone.

---

## Child Zone Visibility Rules

| Layer | Historical Detection | Live Detection |
|-------|---------------------|----------------|
| **Narrative** (MN1/W1/D1) | Always detect and show | Always detect and show |
| **Control** (H4/H1/M30/M15) | Detect independently, validate vs Narrative | Detect independently, validate when parent forms |
| **Sniper** (M5/M1) | Only show inside Narrative or Control parent | Only show inside Narrative or Control parent |

**Visualization note:** Control zones use the same color whether or not their Narrative parent is currently active. This reduces display complexity.

---

## Entry Sequence (Full Russian Doll)

```
Step 1: Narrative zone (D1/W1/MN1) exists — price approaches L1  →  WAIT

Step 2: Price touches Narrative L1  →  WAIT for Control

Step 3: Find Control zone (H4 → H1 → M30 → M15 fallback)
        Control zone L1 AND L2 must sit inside Narrative L1/L2
        Direction must match Narrative

Step 4: Sniper B2B (M5 or M1) forms inside Control zone, same direction

Step 5: Execute at Sniper L1, 50%, or L2
```

> [!DECISION]
> Entry is always via Sniper (M5 or M1) confirmation. No exceptions.
> Do NOT take opposite-direction Sniper B2B even if it forms at Narrative L2.

---

## Opposite-Direction Zones at Parent L2

**Scenario:** D1 SELL zone exists. At the D1 L2 level, an H4 BUY zone forms (opposite direction).

> [!DECISION]
> Show both zones. Let the market decide. No "trap" labels.
>
> If H4 creates a BUY at D1 L2, that is valid B2B data — execute the BUY signal from that zone.
>
> The system follows what B2B forms, not what we expect it to form.

---

## Cascade Invalidation

> [!DECISION]
> When a **parent zone invalidates**, all child zones within it **auto-invalidate simultaneously**.
>
> Rationale: The parent zone provided the structural context. If the parent thesis fails (price closed beyond L2), child zones lose their anchor — they cannot stand on their own.

```
Example:
D1 SELL zone: L1=1950, L2=1980

  ├── H4 SELL zone (child): L1=1955, L2=1965
  └── M5 SELL zone (child): L1=1956, L2=1960

IF: D1 candle closes at 1985 (above D1 L2=1980)
THEN:
  → D1 zone: INVALIDATED
  → H4 zone: INVALIDATED (cascade)
  → M5 zone: INVALIDATED (cascade)
```

> [!CAUTION]
> Cascade invalidation is **decided but not yet implemented in V5.0**. See [[b2b-open-questions]] OQ-002.

---

## MQL5 Implementation

- Nesting validation: `CB2BConfluence::IsNarrativeTF()`, `IsControlTF()`, `IsEntryTF()`
- Child visibility: `InpShowB2BNarrativeZones`, `InpShowB2BControlZones`, `InpShowB2BSniperZones` in `TradingParameters.mqh`
- Cross-layer deduplication **disabled**: Narrative and Control zones at the same price level are BOTH kept (Dec 18, 2025)

---

## Related Pages

- [[b2b-timeframe-hierarchy]] — Layer rules and roles (Narrative/Control/Sniper)
- [[b2b-invalidation]] — Cascade rules and implementation status
- [[b2b-overview]] — Zone boundaries (L1/L2/50%)
- [[b2b-touch-depth]] — How touch depth tracks inside nested zones
