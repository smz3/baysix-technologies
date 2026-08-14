# Strategy V5.7: Free Flow Traps (FFT) Optimizations

**Version:** 5.7
**Date:** 2026-02-11
**Module:** StrategyOrchestrator

---

## 1. Executive Summary
This update addresses critical bottlenecks in the "Free Flow" logic where the system would become paralyzed by stale Higher Timeframe (MN1) structures or freeze when a Magnet zone was broken but not yet invalidated by a candle close.

**Key Optimizations:**
1.  **Freshness Handover**: Lower timeframes (D1/W1) can now override MN1 authority if they present a **newer** trend in the **same direction**.
2.  **Bulldozer Mode**: The system now recognizes that a "Pierced" wall (L2 Touched) is no longer a valid roadblock for entry, allowing momentum to continue without waiting for the slow invalidation cycle (Monthly Candle Close).

---

## 2. Problem Analysis

### A. The "MN1 Stuck" Problem
**Symptom:** The strategy would latch onto an old MN1 trend and refuse to trade fresh D1/W1 setups even if they were aligned.
**Root Cause:** The `IsTradeAllowed` logic used a strict hierarchy: `if (MN1.Valid) { Trade MN1; } else if (W1.Valid)...`.
**Impact:** A 4-year-old MN1 trend would block a fresh D1 breakout from executing its own logic, forcing the D1 trade to conform to stagnant MN1 parameters (or failing to fire triggers).

### B. The "Phantom Roadblock" Problem
**Symptom:** When a strong trend broke through a Monthly Magnet (Price touched L2), trading would stop completely until the end of the month.
**Root Cause:**
1.  **B2B Invalidation Rule:** A zone is only invalidated when a candle *closes* beyond L2.
2.  **Location Filter:** `IsInsideOpposingZone` checked ALL valid zones. Since the broken magnet was still "Valid" (waiting for close), it was flagged as a "Roadblock", preventing any further trades in that direction.
**Impact:** We missed the most explosive part of the move (the breakout) because the system was waiting for administrative paperwork (candle close) to file the zone as dead.

---

## 3. V5.7 Logic Solutions

### 3.1. Handover Logic (Freshness Protocol)
We introduce a competitive selection for the "Dominant Flow". We do not blindly follow the highest timeframe. We follow the **Freshness of the Move**.

**Rule:**
If multiple timeframes (MN1, W1, D1) have valid flows:
1.  **Alignment Check:** Do they share the SAME Direction?
    -   *No:* Higher Timeframe (Tide) retains Veto power. Safety First.
    -   *Yes:* Proceed to Freshness check.
2.  **Freshness Check:** Compare the `Origin_Touch_Time` (or `Zone_Created_Time`) of the active flows.
    -   If D1 is **Newer** than MN1 -> **D1 takes the Wheel**.
    -   If MN1 is **Newer** (e.g., fresh reversal) -> MN1 retains control.

**Result:** The system stays with the "Current Leg" of the market, regardless of timeframe ranking.

### 3.2. Bulldozer Mode (Roadblock Clearance)
We separate "Chart Validity" from "Navigational Obstacles".

**Rule:**
Inside `IsInsideOpposingZone`:
-   Iterate through all Opposing Zones.
-   **Check:** `if (zone.L2_touched == true)`
    -   **Action:** **IGNORE**. This zone is compromised. It is not a wall; it is rubble.
-   **Result:** The Location Filter returns `0` (Safe), allowing the trade to "Bulldoze" through the broken zone.

**Safety Note:** 
This does **NOT** delete the zone from the chart. It remains visible until the candle closes, respecting the user's strict B2B definition. We simply stop respecting it as a threat.

---

## 4. Implementation Details

### Code Changes in `StrategyOrchestrator.mqh`

#### `IsTradeAllowed`
```cpp
// ... inside flow validation ...
bool d1_is_fresh = (m_d1.is_valid && m_d1.origin_touch_time > m_mn1.origin_touch_time);

if (d1_is_fresh && m_d1.origin_dir == m_mn1.origin_dir)
{
    // D1 HANDOVER
    Authorize(m_d1);
}
else
{
    // STANDARD HIERARCHY
    Authorise(m_mn1);
}
```

#### `IsInsideOpposingZone`
```cpp
// ... inside loop ...
if (zones[i].L2_touched) continue; // IGNORE PIERCED ZONES (BULLDOZER)
```

---

## 5. Conclusion
These changes convert the strategy from a static, hierarchy-bound system into a dynamic, momentum-aware engine. It respects major structures until they are broken, at which point it ruthlessly capitalizes on the breakout.

---

## 6. V5.7.1 Discovery Mode (ATH/ATL Fix)

### Problem
When the market breaks into All-Time Highs (ATH) or All-Time Lows (ATL), there are **NO Magnet Zones** above or below.
-   **Old Logic:** `Target Price` depends on a Magnet. If no magnet, `Target = 0`. Safety check `if (Target == 0) return false;` blocked the trade.
-   **Impact:** The system perfectly identified the breakout but refused to fire because it didn't know "where to stop".

### Solution: "Let It Rip"
-   **Condition:** If `Target Price == 0` (Blue Sky).
-   **Action:** 
    1.  Allow the Trade.
    2.  Set `Target Price = 0` (No Fixed TP).
    3.  Rely on **Trailing Stop (Exit Manager)** to capture the trend.
    4.  Log: `(Discovery)` tag added to the trade comment.

---

## 7. Version Comparison (Before vs. After)

### A. Handover Logic (IsTradeAllowed)

**BEFORE (Static Hierarchy):**
```cpp
// Strictly checks MN1 first
if (m_mn1.is_valid && ValidateTrap(m_mn1)) {
    Use(MN1); 
}
else if (m_w1.is_valid...) // Only runs if MN1 is invalid
```

**AFTER (Dynamic Freshness):**
```cpp
// Check Freshness
bool d1_fresh_override = false;
if (m_d1.is_valid && m_d1.origin_touch_time > m_mn1.origin_touch_time) 
    d1_fresh_override = true;

// If Fresh Override is Active + Directions Align
if (d1_fresh_override && m_d1.origin_dir == m_mn1.origin_dir) {
    Use(D1); // Handover to Fresh D1
    reason = "D1 Flow (Handover)";
}
else if (m_mn1.is_valid...) {
    Use(MN1); // Fallback to Tide
}
```

### B. Bulldozer Mode (IsInsideOpposingZone)

**BEFORE (Phantom Roadblock):**
```cpp
// Checks all zones. Even broken ones are "Valid" until candle close.
if (zone.type == OPPOSITE) return zone_id; // BLOCKED
```

**AFTER (Pierced = Safe):**
```cpp
// If the wall is pierced, we drive through it.
if (zone.L2_touched) continue; // IGNORE
if (zone.type == OPPOSITE) return zone_id; // BLOCKED only if solid
```

### C. Discovery Mode (ATH Fix)

**BEFORE (Safety Block):**
```cpp
if (target_price == 0) target_price = m_w1.details_magnet_L2;
// ...
if (out_tp == 0 || out_sl == 0) return false; // REJECT
```

**AFTER (Let It Rip):**
```cpp
if (target_price == 0) reason += " (Discovery)";
// ...
// if (out_tp == 0) return false; // REMOVED
if (out_sl == 0) return false;    // Safety: SL Still Required
```
