# B2B 5-Pointer Detection Specification (FINAL)

> **Status:** ✅ Official Documentation - V5.1 Implementation Complete

---

## SELL B2B Zone - 5-Pointer Rules

### Visual Structure
```
Price
  ^
  │                    P1 (HIGH) ════════════ L2 (origin)
  │                   /│\
  │                  / │ \
  │                 /  │  \      P3 (Lower High) ← Required for context
  │                /   │   \      /\
  │               /    │    \    /  \
  │              /     │     \  /    \
  │    /\       /      │      \/      \
  │   /  \     /       │      P2       \
  │  /    \   /        │     (LOW)      \
  │ /      \ /         │    ════════════ L1 (entry)
  │/        ●          │                  \
  │        P5          │                   \
  │    (first LOW      │                    \
  │    below P2)       │                     ● P4 (breaks P5)
  └────────────────────┴────────────────────────────────> Time
```

### Point Definitions

| Point | Type | Role | Selection Rule |
|-------|------|------|----------------|
| **P1** | Swing HIGH | **L2** (Origin/Extreme) | Highest point before reversal |
| **P2** | Swing LOW | **L1** (Entry Level) | First LOW after P1 |
| **P3** | Swing HIGH | Structure Context | First HIGH after P2, must be LOWER than P1 |
| **P4** | Breakout Bar | Confirmation | Bar that closes below P5 (can also break P2 same bar) |
| **P5** | Swing LOW | 2nd Barrier | **First LOW below P2's price** (older than P1) |

### Detection Logic
```
1. Find P1 (swing HIGH)
2. Find P2 (swing LOW after P1)
3. Find P3 (swing HIGH after P2, lower than P1) ← REQUIRED
4. Find P5 (first swing LOW with price < P2.price, exists BEFORE P1)
5. Wait for P4 (bar closes below P5.price)
   - P4 can break P2 and P5 on same bar
6. Zone confirmed when P4 breaks P5
```

---

## BUY B2B Zone - 5-Pointer Rules (Mirror)

### Visual Structure
```
Price
  ^
  │                     ● P4 (breaks P5)
  │                    /
  │                   /
  │    (first HIGH   /
  │    above P2)    /        
  │        ●       /         
  │        P5     /          
  │\        \    /           
  │ \      / \  /            
  │  \    /   \/      P2     
  │   \  /     \     (HIGH)  
  │    \/       \   ════════════ L1 (entry)
  │    /\        \      /\
  │   /  \        \    /  \
  │  /    \        \  /    P3 (Higher Low) ← Required for context
  │ /      \        \/
  │/        \       P1 (LOW) ════════════ L2 (origin)
  └────────────────────────────────────────────────> Time
```

### Point Definitions (Mirror)

| Point | Type | Role | Selection Rule |
|-------|------|------|----------------|
| **P1** | Swing LOW | **L2** (Origin/Extreme) | Lowest point before reversal |
| **P2** | Swing HIGH | **L1** (Entry Level) | First HIGH after P1 |
| **P3** | Swing LOW | Structure Context | First LOW after P2, must be HIGHER than P1 |
| **P4** | Breakout Bar | Confirmation | Bar that closes above P5 |
| **P5** | Swing HIGH | 2nd Barrier | **First HIGH above P2's price** (older than P1) |

---

## L2 Selection (Edge Case)

When P1 and P3 both qualify as L2:
- For **SELL zones**: L2 = the **HIGHER** price between P1 and P3
- For **BUY zones**: L2 = the **LOWER** price between P1 and P3

L2 is always the **more extreme** swing point.

---

## Zone Invalidation Rules

| Zone Type | Invalidation Condition |
|-----------|------------------------|
| **SELL B2B** | Price closes **ABOVE** L2 level |
| **BUY B2B** | Price closes **BELOW** L2 level |

**IMPORTANT:** Invalidation uses **CLOSE price**, not wick/shadow.

---

## Key Rules Summary

| Rule | SELL B2B | BUY B2B |
|------|----------|---------|
| P1 (L2) | Swing HIGH | Swing LOW |
| P2 (L1) | Swing LOW after P1 | Swing HIGH after P1 |
| P3 | Lower HIGH (< P1) | Higher LOW (> P1) |
| P5 | First LOW below P2 price | First HIGH above P2 price |
| P4 breaks | Below P5 | Above P5 |
| P5 timing | Older than P1 | Older than P1 |
| Invalidation | Close > L2 | Close < L2 |

---

## Implementation Notes

### CircularBuffer Ordering (CRITICAL)

The detection algorithm depends on specific buffer ordering:

```
CCircularBuffer<SwingPointInfo>:
  - Index 0 = OLDEST swing point
  - High index = NEWEST swing point
  - Iteration from 0 → Count() processes oldest to newest chronologically
```

**Detection iterates from oldest to newest** to ensure zones are created in temporal order.

### P5 Selection Clarification

When searching for P5 (the older barrier), the algorithm finds the **most recent qualifying swing that is still older than P1**:

```
Search direction: From P1 backwards in time
Returns: FIRST match encountered (i.e., the barrier closest to P1)
NOT: The absolute oldest barrier in history
```

This means if multiple barriers qualify (all below P2 price for SELL, all above P2 price for BUY), the one **closest in time to P1** is selected.

### P5 Swing Reuse & Context Logic (New V5.1.1)

> [!DATE]
> Updated 2025-12-26: Context-Aware Detection Logic

To solve the "Structure Context" problem (where stale patterns were detected blindly), the detection now uses a **2-Pass Candidate Selection Strategy**:

1. **Pass 1: Find Candidates** - Scan specifically for *ALL* valid 5-point patterns.
2. **Pass 2: Select Winners** - Group candidates by their P5 barrier.
3. **Selection Rule:** If multiple patterns share the same P5, the **Freshest Pattern** (highest P1 index / most recent time) is selected.
4. **Exclusivity:** Once a zone is created, P1, P2, P3, AND **P5** are marked as used.

**Result:**
- One zone per P5 structure.
- Always the most recent/relevant pattern formation.
- No "stale" duplicate zones.

### L2 Selection: P1 vs P3 (Deterministic)

Both P1 and P3 are swing points that could qualify as the L2 (invalidation) level. To prevent random/inconsistent selection, the algorithm **always chooses the more extreme price**:

| Zone Type | L2 Selection Rule | Reason |
|-----------|-------------------|--------|
| **SELL B2B** | `L2 = MAX(P1.price, P3.price)` | Higher = more extreme for shorts. (P3 can > P1) |
| **BUY B2B** | `L2 = MIN(P1.price, P3.price)` | Lower = more extreme for longs. (P3 can < P1) |

```mql5
// Code implementation (B2BDetector.mqh Lines 366-379)
if(direction == DIRECTION_BEARISH)
  {
   if(P1.price >= P3.price)
     { L2_price = P1.price; L2_time = P1.time; }
   else
     { L2_price = P3.price; L2_time = P3.time; }
  }
else  // BULLISH
  {
   if(P1.price <= P3.price)
     { L2_price = P1.price; L2_time = P1.time; }
   else
     { L2_price = P3.price; L2_time = P3.time; }
  }
```

> [!NOTE]
> This guarantees L2 is always the widest possible zone boundary, providing maximum invalidation protection.

---

My Understanding of the Problem
You're saying: "If there are multiple valid 5-point patterns, we shouldn't just blindly create zones for all of them."

The question is: what should the "winner" be?

Option 1: Latest/Freshest Pattern

Only create zone for the most recent valid P1 → P2 → P3 → P4 sequence
Older patterns are ignored (structure is "stale")
Option 2: One Zone Per P5

If multiple patterns share the same P5, only keep ONE
Winner could be: earliest, latest, or widest zone

## Version History

- V5.1.1 - Added implementation notes (CircularBuffer, P5 selection)
- V5.0 - Initial B2B detection (4-pointer, deprecated)

---

## Structure Integrity (New V5.1.2)

> [!DATE]
> Updated 2025-12-26: Strict Freshness Validation

To ensure the **P3 (Context)** is directly relevant to the **P4 (Breakout)**, a strict "No Interruption" rule is enforced.

| Rule | Description |
|------|-------------|
| **No Interruption** | **NO new swing points** (High or Low) are allowed to form between P3 and P4. |
| **Logic** | If a new swing forms after P3 but before the breakout, the P3 context is considered "interrupted" or "stale". |
| **Implementation** | The algorithm scans *all* swing points. If any swing `S` exists such that `P3.Time < S.Time < P4.Time`, the pattern is **REJECTED**. |

**Why this matters:**
This prevents the system from connecting an old P3 to a much later P4 across a period of consolidation or structure formation. It forces the B2B pattern to be the **Immediate Predecessor** of the breakout.
