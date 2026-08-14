# Fracture Flow V3.0: Zone-to-Zone Strategy

> **Document Version:** V3.0  
> **Date:** 2026-02-07  
> **Status:** User Approved / Implementation Ready

---

## 1. Core Philosophy: Zone-to-Zone

We trade the **Flow** between two fixed points:
1.  **Origin (Point A)**: The start of the move (where price bounced from).
2.  **Magnet (Point B)**: The destination (where price is heading).

The strategy is purely **Zone-to-Zone**. We do not guess midway. We enter at the edges (Traps) and exit at the opposing zone (Magnet/Origin).

---

## 2. Fractal Hierarchy (The Narrative)

The market narrative is dictated by a strict hierarchy of **Structure Timeframes (Generals)**:

| Timeframe | Role                  | Function                                              |
| :---      | :---                  | :---                                                  |
| **MN1**   | **Long-Term Bias**    | The "Arena". Sets the overall season (Bull/Bear).     |
| **W1**    | **Mid-Term Bias**     | The "Structure". Often nested within MN1.             |
| **D1**    | **Short-Term Bias**   | The "Path". The primary day-to-day directional guide. |

*   **Rule**: Higher timeframes dominate. An MN1 Origin holds more weight than a D1 limit.
*   **Alignment**: The ideal trade aligns MN1, W1, and D1.

---

## 3. Trap Zones (The Execution)

We execute trades on **Trap Timeframes (Snipers)**:
*   **H4**, **H1**, **M30**

### Authorization Rules
A Trap is **VALID** only if:
1.  **Freshness**: The Trap formed *after* price entered the Narrative Zone (Origin/Magnet). Old traps are ignored.
2.  **Location**: The Trap is inside or touching the Narrative Zone.
3.  **Alignment**: The Trap direction matches the intended trade direction (WT or CT).

### Trigger Logic
We execute on specific touch events within the Trap:
*   **T1 (Level 1)**: First touch of the entry structure. (Aggressive)
*   **T2 (50%)**: Touch of the zone's equilibrium. (Balanced)
*   **T3 (Level 2)**: Deep touch near invalidation. (High R:R)

---

## 4. Trade Classification & Targets

We classify trades based on the **Flow Direction**:

### A. With-Trend (WT) - The Expansion
> **Trading FROM Origin TO Magnet.**

*   **Context**: Price bounced from Origin (Demand) and is moving towards Magnet (Supply).
*   **Action**: BUY (if Bullish Origin).
*   **Target**: **Magnet Zone** (Point B).
    *   *Logic*: "Go with the flow to the destination."

### B. Counter-Trend (CT) - The Pullback
> **Trading FROM Magnet BACK TO Origin.**

*   **Context**: Price hit Magnet (Supply) and rejected.
*   **Action**: SELL (if Bullish Narrative / Bearish Pullback).
*   **Target**: **Origin Zone** (Point A).
    *   *Logic*: "Fade the move at the destination to catch the retracement."

---

## 5. State Management (Fixed Roles)

*   **Origin**: Remains fixed until price breaks it (Invalidation) or a new structure forms *beyond* it.
*   **Magnet**: Remains fixed until price breaks it (Invalidation/Bulldoze) or a new structure forms *in front* of it.
*   **No Flip-Flop**: Roles do NOT change on simple touches. A zone is either an Origin or a Magnet based on price position.

---

## 6. Implementation Notes

*   **Data Source**: Use `B2BConfluence` and `B2BZoneInfo` from the Detection system. Do not re-calculate overlaps manually.
*   **State Machine**:
    *   `FlowState` struct tracks the current Origin/Magnet for MN1, W1, D1.
    *   `TrapState` struct tracks the active H4/H1/M30 signal.
