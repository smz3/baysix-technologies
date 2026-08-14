# SIGMA V5.0 Option A: Independent TF Trading with Direction Filter

## Overview

Each timeframe trades its own B2B zones independently, but with an optional direction filter to ensure alignment with higher timeframes.

```
Core Philosophy: "Trade with the flow, not against it"
- Higher TF = Direction bias
- Lower TF = Entry precision
- Each zone trades its own levels, but only if aligned
```

---

## Design Choices

### Design 1: Hierarchical Direction Filter (Simple)

**Concept**: Higher TFs set direction, lower TFs must agree to trade.

```
Direction Chain (Top-Down):

D1/W1 → Sets NARRATIVE BIAS (BUY or SELL)
    ↓
H4/H1 → Confirms or overrides with CONTROL BIAS
    ↓
M15/M30 → Confirms ENTRY DIRECTION
    ↓
M5/M1 → EXECUTES with precision
```

| Trade TF | Requires Agreement From |
|----------|------------------------|
| M1 | M5 + M15 same direction |
| M5 | M15 + H1 same direction |
| M15 | H1 + H4 same direction |
| H1 | H4 + D1 same direction |
| H4 | D1 same direction |
| D1+ | No requirement (top of chain) |

**Pros**: Simple, clear logic
**Cons**: Strict, may miss valid trades

---

### Design 2: Weighted Confluence Score (Nuanced)

**Concept**: Assign scores based on alignment, trade if score meets threshold.

```
Score Calculation:
+3 : D1/W1 zone in same direction
+2 : H4/H1 zone in same direction  
+1 : M15/M30 zone in same direction
-2 : Any higher TF zone in OPPOSITE direction

Trade if: Total Score >= Threshold (configurable)
```

**Examples**:
| Scenario | Score | Action |
|----------|-------|--------|
| M5 BUY, H1 BUY, D1 BUY | +2+3 = 5 | ✅ TRADE |
| M5 BUY, H1 BUY, D1 neutral | +2+0 = 2 | ✅ TRADE |
| M5 BUY, H1 BUY, D1 SELL | +2-2 = 0 | ❌ NO TRADE |
| M5 BUY, no higher zones | 0 | Depends on threshold |

**Pros**: Nuanced, configurable
**Cons**: More complex, needs tuning

---

### Design 3: Risk Scaling by TF Agreement

**Concept**: Position size varies based on confluence strength.

```
Risk Multiplier:
Strong alignment (D1+H4+H1 agree): 2.0x normal risk
Medium alignment (H4+H1 agree):    1.0x normal risk  
Weak alignment (only 1 agrees):    0.5x normal risk
No alignment:                      NO TRADE or 0.25x
```

**Pros**: Aggressive when confident, conservative when not
**Cons**: More complex position sizing

---

### Design 4: Entry/Exit Optimization

**Entry**: Own zone L1 → 50% → L2 (scale-in)

**SL**: Own zone L2 + buffer (TF-appropriate)
- M1/M5: 30-50 points buffer
- M15/H1: 100-200 points buffer
- H4/D1: 300-500 points buffer

**TP Options**:
| Trade TF | TP Option A (Own) | TP Option B (Higher TF) |
|----------|-------------------|-------------------------|
| M1/M5 | M1/M5 zone L1 | M15 zone opposite edge |
| M15/M30 | M15/M30 zone L1 | H1 zone opposite edge |
| H1/H4 | H1/H4 zone L1 | D1 zone opposite edge |
| D1+ | D1 zone L1 | Own zone L1 |

---

## Recommended Hybrid Design

```
┌─────────────────────────────────────────────────┐
│ STEP 1: Check Direction Bias                    │
│ - Is there a D1/H4 zone? What direction?        │
│ - Bias = BULLISH, BEARISH, or NEUTRAL           │
├─────────────────────────────────────────────────┤
│ STEP 2: Filter by Alignment                     │
│ - If Bias exists, only trade same-direction     │
│ - If NEUTRAL, all zones can trade               │
├─────────────────────────────────────────────────┤
│ STEP 3: Trade Each Zone Independently           │
│ - Entry: Own zone L1/50%/L2                     │
│ - SL: Own zone L2 + buffer (TF-scaled)          │
│ - TP: Next higher TF zone edge OR own L1        │
├─────────────────────────────────────────────────┤
│ STEP 4: Risk Adjustment (Optional)              │
│ - More TFs aligned = higher position size       │
│ - Fewer aligned = smaller position size         │
└─────────────────────────────────────────────────┘
```

---

## Proposed Parameters

```cpp
//+------------------------------------------------------------------+
//| DIRECTION FILTER                                                  |
//+------------------------------------------------------------------+
input int InpDirectionFilterLevel = 1;  
// 0 = None (trade any direction)
// 1 = Match H4/D1 bias (if exists)
// 2 = Match all higher TFs (strict)

input int InpDirectionBiasTF = PERIOD_H4;  
// Which TF sets the direction bias

//+------------------------------------------------------------------+
//| RISK SCALING                                                      |
//+------------------------------------------------------------------+
input bool InpScaleRiskByConfluence = true;
input double InpWeakAlignmentRisk = 0.5;    // 50% of normal
input double InpNormalAlignmentRisk = 1.0;  // 100% of normal
input double InpStrongAlignmentRisk = 1.5;  // 150% of normal

//+------------------------------------------------------------------+
//| TP MODE                                                           |
//+------------------------------------------------------------------+
input int InpTPMode = 1;
// 0 = Own zone L1 (conservative)
// 1 = Next higher TF zone edge (extended)
// 2 = Fixed Risk:Reward ratio

input double InpFixedRR = 2.0;  // Used if InpTPMode = 2

//+------------------------------------------------------------------+
//| SL BUFFER (TF-Scaled)                                             |
//+------------------------------------------------------------------+
input double InpSLBufferM1M5 = 50.0;     // Buffer for M1/M5 (points)
input double InpSLBufferM15H1 = 150.0;   // Buffer for M15/H1 (points)
input double InpSLBufferH4D1 = 300.0;    // Buffer for H4/D1 (points)
```

---

## Flow Diagram

```
┌─────────────┐
│ Zone Formed │
│ (Any TF)    │
└──────┬──────┘
       ↓
┌──────────────────────┐
│ Direction Filter?    │
│ Check H4/D1 bias     │
└──────┬───────────────┘
       ↓
   ┌───┴───┐
   │ Match?│
   └───┬───┘
       ↓
  YES ─┼─ NO → Skip Zone
       ↓
┌──────────────────────┐
│ Wait for Zone Touch  │
│ L1 / 50% / L2        │
└──────┬───────────────┘
       ↓
┌──────────────────────┐
│ Calculate Position   │
│ Apply Risk Scaling   │
└──────┬───────────────┘
       ↓
┌──────────────────────┐
│ EXECUTE TRADE        │
│ SL: Own L2 + buffer  │
│ TP: Based on mode    │
└──────────────────────┘
```

---

## Comparison: Current vs Option A

| Aspect | Current System | Option A |
|--------|---------------|----------|
| Who can trade | M1/M5 only | ALL timeframes |
| Parent requirement | Must have parent | Optional filter |
| Direction filter | Parent touch + timing | Simple HTF bias check |
| SL | Entry zone L2 | Own zone L2 |
| TP | Parent zone L1 | Own zone L1 (or higher TF) |
| Complexity | High | Low-Medium |
| Debug difficulty | Hard | Easy |

---

## Implementation Priority

1. ✅ Remove IsEntryTimeframe restriction (allow all TFs to trade)
2. ✅ Remove parent touch requirement  
3. ✅ Add simple direction bias check (optional)
4. ✅ TP uses own zone L1 by default
5. ⬜ Add risk scaling (enhancement)
6. ⬜ Add higher TF TP option (enhancement)
