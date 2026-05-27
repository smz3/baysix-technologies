# SIGMA System: The 3 Levels of Trap Selection

This documentation defines the hierarchical progression of H4, H1, and M30 execution traps as implemented in the `StrategyOrchestrator.mqh`.

---

## 1. Level 1: Strict Mode Traps (Nesting)
**Strict Mode** is the initial safety gate used when a new Narrative (Origin/Magnet pair) is first established.

### Criteria:
- **Condition**: No Forward Outpost exists, or the Outpost exists but has not been touched yet (`anchor_is_traded == false`).
- **Nesting**: The execution trap **MUST** be physically nested inside the HTF Origin zone.
- **Freshness**: Trap must be created **after** the Origin's first touch.

### Logic:
- This is the "Refuse to Lose" defense. The system will only accept entries that are anchored directly to the major structural floor.

---

## 2. Level 2: Free Flow Traps (FFT)
**Free Flow Mode** is activated once the market establishes momentum and confirms a "March" toward the target.

### Criteria:
- **Condition**: A Forward Outpost exists AND has been touched (`anchor_is_traded == true`).
- **Liberation**: Spatial nesting in the Origin is **no longer required**.
- **The Vacuum**: Traps can fire anywhere in the "Vacuum" between the Outpost and the Magnet.
- **Freshness**: Trap must be newer than the **Outpost touch time**.

### Logic:
- This enables trend-following. The system "Liberates" the snipers to chase the target once the structural breakout is confirmed.

---

## 3. Level 3: Discovery Mode Free Flow Traps
**Discovery Mode** is the specialized state for All-Time Highs (ATH) or All-Time Lows (ATL) where no historical roadblocks exist.

### Criteria:
- **Condition**: Level 2 FFT logic is active + **Magnet ID is 0** (Blue Sky territory).
- **Logic**: 
    - The D1/W1 Origin is strictly "Locked" to prevent structural hijacks.
    - FFTs fire continuously on the reaction to every new Outpost created during the breakout.
- **Target**: TP is set to 0 (No fixed target).
- **Exit**: Exclusively managed by the **Trailing Stop** to maximize run-room.

---

## Summary Comparison

| Level | Mode          | Requirement              | Targeting              | Goal                |
| :---  | :---           | :---                     | :---                   | :---                |
| **1** | **Strict**    | Nested in Origin         | Magnet L1/L2           | Defensive Entry     |
| **2** | **Free Flow** | Post-Outpost Touch       | Magnet L1/L2           | Momentum Chase      |
| **3** | **Discovery** | Post-Outpost + No Magnet | Trailing Stop (TP=0)   | Blue Sky Extraction |
