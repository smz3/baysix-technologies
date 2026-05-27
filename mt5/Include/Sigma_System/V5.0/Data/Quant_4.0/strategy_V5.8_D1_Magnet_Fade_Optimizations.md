# SIGMA System V5.8: D1 Magnet Fade Optimizations

## Goal
To solve the "Structural Hijack" problem at ATH/ATL (Discovery Mode) where D1 prematurely flips its trend direction. This upgrade implements a dedicated D1 Magnet Fade Reversal that triggers **only** when higher timeframes are in Discovery Mode.

## Core Change: Origin Protection
At ATH, the system will now "Lock" the D1 Origin. A new counter-zone (e.g., a Bearish B2B at the peak) will no longer be allowed to hijack the `origin_id`. Instead, it will be classified as a **Magnet**.

### Logical Transition:
- **BEFORE (V5.7.1):** New Sell at ATH $\rightarrow$ D1 flips to Bearish Origin $\rightarrow$ Authorizes "Flow" trades (Shorts the first pullback).
- **AFTER (V5.8):** New Sell at ATH $\rightarrow$ D1 remains Bullish Origin $\rightarrow$ Sell zone becomes **Magnet** $\rightarrow$ Authorizes **Magnet Fade** (Reversal toward Buy Origin).

## D1 Magnet Fade (ATH Specific)
This logic mirrors the existing MN1 Magnet Fade but is restricted to Discovery scenarios to prevent interference with macro-scheduled fades.

### Entry Criteria:
1. **Discovery Mode:** `MN1 Magnet == 0` (No higher timeframe targets).
2. **Structural Supremacy:** The D1 Magnet must be the absolute price extreme in the current buffer.
3. **Core Interaction:** Price must be inside the T2/T3 (Core) of the D1 Magnet.
4. **Touch confirmation:** `magnet_fifty_touched` or `magnet_L2_touched` must be true.
5. **Directional Conflict:** `Signal Direction != D1 Origin Direction`.

### Execution Logic:
- **Reason:** `D1 Magnet Fade (ATH Reversal)`
- **Target Price:** Back wall (L2) of the D1 Origin (The base of the breakout).
- **Anchor:** The D1 Magnet ID.

## Impact
This upgrade ensures the system respects the macro-trend during breakouts while providing a mathematically sound way to "Fade the Top" using the exact same safety gates proven on the MN1 timeframe.

## Technical Fix Log (V5.8 Upgrades)

### 1. Successor Protection (The "Persistence" Fix)
*   **Vulnerability:** At ATH, if price touched a Magnet but no Outpost (Successor) existed, the system would call `state.Reset()`, killing the Origin and the narrative.
*   **Fix:** Added a specific gate in `UpdateTimeframeFlow`. If in MN1 Discovery, the system now retains the Origin even if no successor is found.
*   **Code Change:**
```diff
- else { state.Reset(); return; }
+ else { 
+    if(m_mn1.magnet_id == 0 && (tf == PERIOD_D1 || tf == PERIOD_W1)) {
+       state.magnet_id = 0; state.is_siege_active = false;
+    } else state.Reset(); 
+    return; 
+ }
```

### 2. Origin Search Hijack (Structural Preference)
*   **Vulnerability:** The fresh search loop had a recency bias. At ATH, a new counter-trend Sell zone would be newer than the historical Buy Origin, causing the loop to pick the Sell as the New Origin.
*   **Fix:** Introduced "Macro Direction Preference." During Discovery Mode, the search loop is forbidden from picking an origin that opposes the MN1 Tide.
*   **Code Change:**
```diff
  for(int i=0; i<zone_count; i++) {
+    if(m_mn1.magnet_id == 0 && (tf == PERIOD_D1 || tf == PERIOD_W1) && zones[i].direction != m_mn1.origin_dir) continue;
     // ... recency logic continues ...
  }
```

### 3. Structural Supremacy (Highest Magnet)
*   **Vulnerability:** D1 could authorize fades on "intermediate" counter-zones that weren't the actual top.
*   **Fix:** Added `is_magnet_extreme` property. The system now scans all D1 zones and only authorizes a Magnet Fade if the target magnet is the absolute price extreme in its direction.
