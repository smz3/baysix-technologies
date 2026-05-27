# V6 Anchor Logic - Design Document

## Overview

This document defines the simplified "Anchor L2" trading logic for V6, replacing the current V5 zone-based approach with a hierarchical, key-level focused system.

---

## Core Hierarchy

```
ANCHOR       → H4 / H1 / M30 (or M15 at ATH/ATL)
CONFIRMATION → REMOVED (Direct overlap check)
SETUP        → M5 within Anchor L2 (L2 +/- buffer)
EXECUTION    → Best M5 or M1 zone (Closest to Anchor L2)
```

---

## Current V5 vs V6 Comparison

| Aspect         | Current V5                | V6 Anchor Logic |
|--------------- |---------------------------|-----------------|
| Zone Selection | ALL M5 zones              | Only M5 at HTF L2 |
| Key Level      | Not defined               | HTF L2 where LTF clusters |
| Parent Check   | M15 overlap only          | M5/M1 overlaps Anchor L2 directly |
| Entry Trigger  | T1, T2, or T3             | T3 only (L2 touch) |
| Execution TF   | M5                        | Best Positioned M5 or M1 |
| Direction      | Static filter             | Dynamic anchor-based |

---

## V6 Logic Flow

```
┌─────────────────────────────────────────────────────────────┐
│  1. Find ANCHOR:                                            │
│     └── Normal: Nearest untouched H4/H1/M30 zone            │
│     └── ATH/ATL: M15 becomes the anchor                     │
│                                                             │
│  2. EXECUTION CANDIDATES OVERLAP:                           │
│     └── Find all M5/M1 zones overlapping Anchor L2          │
│                                                             │
│  3. SELECT BEST CANDIDATE:                                  │
│     └── Determine "Best Positioned" zone                    │
│         (Closest to Anchor L2 / best R:R start point)       │
│                                                             │
│  4. EXECUTION LAYER:                                        │
│     └── Is this the BEST zone?                              │
│         ├── YES → Valid for Trade + Visualized              │
│         └── NO  → Ignored (Dimmed/Hidden)                   │
│                                                             │
│  5. Wait for L2 touch (T3) on execution zone                │
│  6. Execute trade                                           │
└─────────────────────────────────────────────────────────────┘

*Better positioned:
  - SELL: M1 L2 is HIGHER than M5 L2 (better entry)
  - BUY: M1 L2 is LOWER than M5 L2 (better entry)
```

---

## Anchor Selection Priority

When multiple anchor zones exist (H4, H1, M30) and don't overlap:

```
Priority: NEAREST UNTOUCHED zone to current price

Rationale: Price fills nearest liquidity void first (physics: potential → kinetic)

Selection Logic:
1. Calculate distance from current price to each untouched HTF L2
2. Select CLOSEST one as anchor
3. If tie → Higher TF wins (H4 > H1 > M30)
```

### Example:
```
Current Price: 1.0500

H4 SELL L2 @ 1.0700 (200 pips away)
H1 SELL L2 @ 1.0580 (80 pips away)  ← ANCHOR (closest)
M30 BUY L2 @ 1.0450 (50 pips away)  ← Skip (opposite direction)
```

---

## Take Profit Logic (Equilibrium Fill)

**Concept:** Price is attracted to unfilled zones. TP when anchor zone is "filled."

```
ENTRY:  M1/M5 L2 touch (at key level cluster)
TP1:    Anchor T2/50% (partial 50% close) - Equilibrium midpoint
TP2:    Opposing Anchor L1 (Anchor to Anchor)
        FALLBACK: Current Anchor L1 (Zone Fill) if no opposing anchor
```

### Physics Analogy:
| Trading | Physics |
|---------|---------|
| Untouched zone | Potential energy (stored) |
| Price reaching zone | Kinetic energy (released) |
| TP at Anchor L2 | Equilibrium restored |

### Visual:
```
Price
  ▲
  │  ════════ ANCHOR H1 L1 ════════
  │      
  │           [TP2: Anchor L2] ← 100% exit (potential filled)
  │           [TP1: Anchor 50%] ← 50% exit (equilibrium)
  │
  │  ════════ ANCHOR H1 L2 ════════  ← KEY LEVEL
  │      ├── M15/M5/M1 cluster
  │      └── ENTRY @ M1 L2
  │
  ▼ Current Price
```

---

## Implementation Plan

### Phase 1: New Functions

| File | Function | Purpose |
|------|----------|---------|
| `AnchorLogic.mqh` | `FindAnchorZone()` | Find nearest untouched H4/H1/M30 |
| `AnchorLogic.mqh` | `IsAtKeyLevel()` | Check if M15 is at anchor L2 |
| `AnchorLogic.mqh` | `GetExecutionZone()` | Return best M1 or M5 zone |
| `AnchorLogic.mqh` | `IsBetterEntry()` | Compare M1 vs M5 L2 position |

### Phase 2: Modify Existing

| File | Change |
|------|--------|
| `TradeSignalGenerator.mqh` | Replace `EvaluateZone()` with anchor-based logic |
| `TradingParameters.mqh` | Add toggle: `InpUseAnchorLogic` |
| `Structures.mqh` | Add `anchor_zone_id` field to track anchor |

### Phase 3: Data Collection

| Metric | Purpose |
|--------|---------|
| `anchor_tf` | Which TF was anchor (H4/H1/M30/M15) |
| `execution_tf` | Which TF executed (M1/M5) |
| `at_key_level` | Was M15 at anchor L2? |
| `m1_vs_m5_entry` | Which gave better R:R |

---

## Files to Create/Modify

### [NEW] AnchorLogic.mqh
```
c:\Users\User\Desktop\SIGMA System Anti Gravity\MQL5\Include\V5.0\Detection\AnchorLogic.mqh
```

### [MODIFY] TradeSignalGenerator.mqh
- Add anchor-based evaluation
- Keep V5 logic as fallback with toggle

### [MODIFY] TradingParameters.mqh
- Add V6 anchor logic parameters

### [MODIFY] Structures.mqh
- Add anchor tracking fields

---

## Next Steps

1. [ ] Create `AnchorLogic.mqh` with core functions
2. [ ] Add toggle parameter `InpUseAnchorLogic`
3. [ ] Integrate into `EvaluateZone()`
4. [ ] Add data collection fields
5. [ ] Backtest to compare V5 vs V6 performance

ADDITIONAL LOGIC TO FULLY IMPLEMENT v6. 

1. Lets only visualize Anchored timeframes that have existing LTF clusters. 
2. This way we can confirm that the anchor zone is valid.  

Simplified Anchor Overlap Rule - Implementation Plan
Goal
Unify visualization and trade execution with a single, simple rule: M5/M1 zone is valid for trading if its L1-L2 range touches any valid Anchor zone's L2 level.

Current Problem
Two separate validation paths (Viz vs Trade)
Race conditions between state updates and visualization
Complex M15 bridge requirement causing false negatives
New Rule (Simplified)
VALID ANCHORED EXECUTION:
  └── M5/M1 zone is tradeable if:
      1. Overlaps a valid Anchor L2
      2. Is the BEST POSITIONED zone for that Anchor (Single Best Rule)
L2 inside range?
Yes
No
Is Best?
Yes
No
M5/M1 Zone
Anchor H4/H1/M30
CANDIDATE
ORPHAN
VALID (Trade)
IGNORED (Dim)
Proposed Changes
[NEW] 
AnchorLogic.mqh
 - IsAnchoredExecution()
New single function for both Viz and Trade:

bool IsAnchoredExecution(const B2BZoneInfo &exec_zone, 
                         const B2BZoneInfo &all_zones[], int zone_count)
{
   // 1. Is it a candidate? (Overlaps Anchor)
   if(!OverlapsAnchor(exec_zone, ...)) return false;

   // 2. Is it the BEST candidate?
   // Find the specific anchor this zone overlaps
   // Ask anchor: "GetExecutionZone()". If result == exec_zone, return true.
   return true/false;
}
[MODIFY] 
TradeSignalGenerator.mqh
 - EvaluateZoneV6()
Replace current anchor validation with:

// Before triggering trade, verify anchored execution
if(!m_anchor_logic.IsAnchoredExecution(execution_zone, all_zones, zone_count))
   continue;  // Skip - not anchored
[MODIFY] 
AnchorLogic.mqh
 - IsPartOfValidCluster()
Simplify to use same check:

bool IsPartOfValidCluster(const B2BZoneInfo &zone, ...)
{
   // If it's an Anchor TF, check if it has any execution zone overlapping
   if(zone.timeframe >= PERIOD_M15) // H4/H1/M30/M15
   {
      // Check if any M5/M1 overlaps this anchor
      for(int i = 0; i < zone_count; i++)
      {
         if(all_zones[i].timeframe == PERIOD_M5 || all_zones[i].timeframe == PERIOD_M1)
         {
            if(IsAnchoredExecution(all_zones[i], all_zones, zone_count))
               return true;
         }
      }
      return false;
   }
   
   // If it's M5/M1, use direct check
   return IsAnchoredExecution(zone, all_zones, zone_count);
}
Race Condition Safeguard
To prevent "valid but invisible" scenarios, add a pre-trade visualization sync:

// In EvaluateZoneV6, before generating signal:
if(InpOnlyShowValidAnchors && !IsPartOfValidCluster(execution_zone, all_zones, count, tol))
{
   // Zone should be visible but isn't - skip to prevent invisible trade
   return signal;  // Empty signal
}
Verification Plan
Compile - No errors
Backtest with InpOnlyShowValidAnchors = true
Check: Every trade should have a visible execution zone
Log: Add [AC CHECK] log on trade to confirm anchor overlap
User Review Required
IMPORTANT

This removes the M15 "bridge" requirement. Any M5/M1 zone that overlaps a valid Anchor L2 AND is the best positioned candidate will be tradeable.

Is this the behavior you want? YES.
```