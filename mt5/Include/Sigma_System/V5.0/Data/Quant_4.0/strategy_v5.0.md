# Strategy V5.0: The Conscious Hierarchy & Storyline Memory

## Change Log (Engineering & Implementation)

### 2026.02.08 16:10 | V5.2 Implementation Fixes
- **FIX: Vacuum-Blind Outposts**: Orchestrator now scans for `Forward Outposts` even when in a "Vacuum" (Magnet ID 0). This ensures a structural floor is always available for trap authorization.
- **FIX: Signal Data Pipeline**: Corrected `TradeSignalInfo` population in `TradeSignalGenerator.mqh` to pass actual `zone_tf` and `signal_time`. Removed `PERIOD_CURRENT` defaults.
- **FIX: Flow Persistence**: Resolved bug where `origin_touch_time` was not persisting across ticks, causing false "Stale" Rejections.
- **LOG: Born vs Gun Diagnostics**: Implemented binary timing logs (`TrapBorn` vs `HTF-Gun`) and price-nesting logs (`Trap L1` vs `Flow L1`) to verify "Reactive Freshness" and "Spatial Integrity" on every block.
- **LOG: Muted Terminal Noise**: Commmented out `[SPATIAL_REJECT]` per-tick spam after confirming nesting logic is operational.
- **FIX: GENERIC COMMENTS**: Updated Orchestrator to sign `TradeSignalInfo` with Authorizing Origin ID. Comments now show `ParentTF#OriginID` (e.g., `D1#2862`) instead of `D1#0000`.
- **FEAT: Multi-Trap Execution**: Enabled T1 (Entry), T2 (50%), and T3 (L2) signal generation in `TradeSignalGenerator`.
- **FIX: Outpost Attribution**: Trade comments now display `#Origin>#Outpost` (e.g., `#2862>#1894`) when authorized by a nested structure.

---

## Philosophy
The market is a battlefield where specific timeframes hold specific authority.
- **MN1 (The Tide)**: The invincible momentum. It bulldozes minor obstacles but respects major structural walls.
- **W1 (The Wave)**: The structural swing. It rides the tide but respects local resistance.
- **D1 (The Path)**: The execution route. It must be clear of immediate roadblocks.

This strategy combines **"Storyline Memory"** (Persisting the Narrative deep into zones) with **"Conscious Hierarchy"** (Intelligent Roadblock Awareness).

---

## 1. The Generals (Flow Logic)

### A. Storyline Memory (Deep Siege Persistence)
Once an Origin/Magnet pair is established, it is **LOCKED**.
- **The Siege**: Touching T1 (Entry) or T2 (50%) of the Magnet does **NOT** reset the story. The narrative continues deep into the zone.
- **Completion (Reset Trigger)**: The Story only ends when:
    1.  **VICTORY (Magnet T3 Touched)**: The Target (L2) is reached. The zone is fully exhausted.
    2.  **DEFEAT (Origin L2 Broken)**: The Origin is invalidated.

### B. Outpost Succession (The March)
When **VICTORY** is achieved (Magnet T3 Touched):
- **Action**: We do NOT reset to vacuum immediately.
- **Succession**: We promote the **Latest Forward Outpost** (a new zone formed in the same direction during the move) to be the **New Origin**.
- **Result**: The Trend Continues seamlessly from the new base.
- *Exception*: If no valid Outpost exists, we reset to Vacuum.

### C. Conscious Hierarchy (Roadblock Awareness)
Before authorizing a trade, the "General" checks the path ahead.
- **MN1 Flow**: Checks **W1 & MN1** Roadblocks. (Ignores D1 = Bulldoze Mode).
- **W1 Flow**: Checks **MN1, W1, & D1** Roadblocks.
- **D1 Flow**: Checks **MN1, W1, & D1** Roadblocks.

> **Roadblock Definition**: Any valid opposing zone immediately *ahead* of price.

---

## 2. The Snipers (Trap Logic)

### A. Scenario 2: Reactive Freshness
We do not trade "stale" structure. We wait for confirmation.
- **Rule**: A Trap is **ONLY VALID** if it is created **AFTER** the Narrative Zone (Origin/Magnet/Outpost) was **TOUCHED**.
- **Logic**: `Trap.CreatedTime > NarrativeZone.L1_TouchTime`
- **Why**: This prevents "catching falling knives" on old levels. We enter on the *reaction* to the HTF level.

### B. Spatial Integrity
- **Rule**: The Trap must be physically `InsideOrTouching` the Active Narrative Zone.
- **Rejection**: Loose traps that are just "aligned" but floating in space are **REJECTED**.

### C. Multi-Trap Execution (V5.2 Fluid)
We deploy a "ladder" of traps. The system now supports **Fluid Stacking** (multiple timeframes firing simultaneously) and **Tier Toggles**.
-   **Control**: Use `InpEnableEntry_T1/T2/T3` to enable/disable specific tiers.
-   **Risk**: Use `InpAllocation_T1/T2/T3` to set specific risk % for each tier.
-   **Fluidity**: If H4, H1, and M30 are all valid, the system will fire **ALL** of them (Stacking), instead of stopping at the first one.

- **T1 (Standard Entry)**: Probes the Front Door (L1).
- **T2 (The Value Play)**: Enters at 50% retracement.
- **T3 (Front-Run Invalidation)**: Snipes the L2 (Back Door).

---

## 5. Exit Protocol (The Payoff)

### A. Stop Loss (Protection)
- **Logic**: Placed behind the **Trap Zone's L2** (Invalidation Point) with a **Safety Buffer**.
- **Buy SL**: `Trap.L2 - InpSLBufferPoints`
- **Sell SL**: `Trap.L2 + InpSLBufferPoints`

### B. Take Profit (The Target)
- **Philosophy**: We trade the "Vacuum" between structures.
- **Rule**: TP is placed at the **Front Door (L1)** of the **Target Magnet** for the specific Flow Timeframe.
- **MN1 Flow**: TP = MN1 Magnet L1.
- **W1 Flow**: TP = W1 Magnet L1.
- **D1 Flow**: TP = D1 Magnet L1.
- *Note*: We do not target T2/T3 of the Magnet initially. We let the **Trailing Stop** handle the "Siege" phase if price blasts through L1.

---

## 6. Execution Matrix

| Flow      | Authority | Roadblocks Checked | Trap Requirement                     | TP Target       |
| :---      | :---      | :---               | :---                                 | :---            |
| **MN1**   | High      | W1, MN1            | Fresh H4/H1/M30 inside W1/MN1 Origin | **MN1 Magnet L1** |
| **W1**    | Medium    | D1, W1, MN1        | Fresh H4/H1/M30 inside W1 Origin     | **W1 Magnet L1**  |
| **D1**    | Low       | D1, W1, MN1        | Fresh H4/H1/M30 inside D1 Origin     | **D1 Magnet L1**  |

---

## 7. State Management Summary
1.  **Init**: Find Origin A -> Magnet B. **LOCK STATE.**
2.  **New Zone (Same Dir)**: Classify as **Forward Outpost**. (Does not reset Origin).
3.  **New Zone (Opp Dir)**: Classify as **Roadblock**. (Check Hierarchy to see if we stop or bulldozer).
4.  **Magnet T3 Hit**: **VICTORY**. Promote Latest Outpost to Origin A'. Find new Magnet B'.
5.  **Origin L2 Hit**: **DEFEAT**. Reset to Vacuum.
