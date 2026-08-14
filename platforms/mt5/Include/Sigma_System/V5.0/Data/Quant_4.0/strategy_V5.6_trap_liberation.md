# STRATEGY V5.6 - TRAP LIBERATION & RUNWAY CONTROL

## **The Core Problem: Nested vs. Continuation**
In V5.4, we enforced **Strict Spatial Nesting**. Every trap had to be "better" or "equal" to the Origin price.
*   **Good**: Ensuring precision for high-probability reversals.
*   **Bad**: Blocking strong continuation moves (Higher Lows / Lower Highs) that naturally occur *after* the trend is established.

## **The Solution: "Prove It, Then Release It"**
We split the logic into two phases based on the **Outpost**.

### Phase 1: The Nest (Strict Mode)
*   **Condition**: `FlowState::outpost_id == 0` (No successful reaction yet).
*   **Rule**: Trap MUST be spatially nested (Inside Origin candle).
*   **Purpose**: Catch the initial reversal with sniper precision.

### Phase 2: The Liberation (Free Roam)
*   **Condition**: `FlowState::outpost_id > 0` (Outpost established).
*   **Rule**: Trap is **LIBERATED**. Spatial check is skipped.
*   **Constraint**: The trap must simply be **Fresh** (Time > Origin Touch).
*   **Purpose**: Allow continuation trades to "Ride the Wave".

---

## **V5.6.1 - RUNWAY CONTROL LOGIC**
The "Free Roam" logic introduced a risk: Traps firing blindly into overhead resistance (Magnets). To fix this, we introduce **Runway Awareness**.

### The Control Logic
If a Trap is **Liberated** (Not Nested), we apply a **Proximity Guard** before firing.

#### 1. The Runway Check
*   **Calculate**: Distance from Entry Price to the next Active Magnet (MN1/W1/D1).
*   **Rule**: If `Distance < Minimum_Runway` (e.g., 0.5 * ATR or fixed points), the trade is **BLOCKED**.
*   **Reason**: "Insufficient Runway for Momentum Trade". We don't buy into a brick wall.

#### 2. The Siege Override (Bulldozer)
*   **Condition**: If `Siege Mode` is active on the Magnet being approached.
*   **Action**: The Runway Check is **IGNORED**.
*   **Reason**: The trend has already proven its intent to break the wall. We allow the trade to "Ladder Up" through the resistance.

### Summary Hierarchy
| Trap Type | State | Constraint | Action |
| :--- | :--- | :--- | :--- |
| **Reversal** | No Outpost | Strict Nesting | Must be better price than Origin. |
| **Continuation** | Outpost Exists | Free Roam | **Runway Check Required**. |
| **Bulldozer** | Siege Active | Free Roam | **Runway Check IGNORED**. |

---

## **V5.6.2 - SIMPLIFIED IMPLEMENTATION (FINAL)**
**Date**: 2026-02-09
**Status**: Implemented

We replaced the complex "Runway Calculation" with a **Logic-Based** approach that leverages the existing `FlowState` flags.

### The "Anti-Fade" Logic (Falling Knife Protection)
Instead of calculating distance, we check if the **Magnet is Active (Fading)**.

#### The Rule:
*   **IF** `Outpost > 0` (Free Flow is Active)...
*   **AND** `Magnet_50%_Touched` OR `Magnet_L2_Touched` (We are in the Fade Window)...
*   **AND** `Siege_Mode` is **FALSE** (The Wall is Holding)...
*   **THEN**: **BLOCK FREE TRAPS**.

#### The Result:
*   **Clear Path**: If Magnet hasn't been touched yet -> **Free Flow Allowed**.
*   **Hitting the Wall**: If Magnet is touched (Fade Window) -> **Free Flow Blocked**.
*   **Breaking the Wall**: If Siege Mode activates -> **Free Flow Allowed (Bulldozer)**.

### Updated Hierarchy
1.  **Strict Mode** (No Outpost): Trap must be **Spacial Nested**.
2.  **Free Mode** (Outpost Exists): Trap can be **Continuation** (Freshness Only).
    *   *Constraint*: Blocked if Magnet is Fading & Siege is OFF.
3.  **Siege Mode** (Outpost Reset > Magnet): **ALL RESTRICTIONS REDUCED** (Bulldozer).

---

## **V5.6.3 - GLOBAL FADE AWARENESS (THE FIX)**
**Date**: 2026-02-09
**Status**: Pending Implementation

The V5.6.2 logic was still catching "Falling Knives" because it was **Too Local**.
*   **The Flaw**: A W1 Free Trap only checked the W1 Magnet. It ignored the MN1 Magnet (The Tide Wall).
*   **The Result**: Price hits the MN1 Wall and reverses hard. W1 sees "Clear Coast" locally and buys into the crash.

### The Solution: "Respect Your Elders"
We are introducing a **Global Fade Check** into `ValidateTrap`.

#### The New Rule:
Before firing a **Free Trap** on *any* timeframe (D1 or W1)...
We must scan **ALL HIGHER TIMEFRAMES** for Active Fades (Shields Up).

1.  **Check MN1 (The Tide)**:
    *   Is MN1 Magnet Fading? (`50%` or `L2` Touched + `Siege` OFF)
    *   **Yes?** -> **BLOCK ALL TRADES** (Even W1/D1 Free Flow).
    *   *Reason*: "Do not fight the Tide Reversal."

2.  **Check W1 (The Wave)**:
    *   Is W1 Magnet Fading?
    *   **Yes?** -> **BLOCK D1 TRADES**.
    *   *Reason*: "Do not fight the Wave Reversal."

3.  **Check Local (The Path)**:
    *   Is Local Magnet Fading?
    *   **Yes?** -> **BLOCK LOCAL TRADES**.

### Summary
If **ANY** Superior Timeframe has its "Shield Up" (Magnet Fade Active), **ALL** Inferior Timeframe Free Traps are grounded.
You cannot "Free Flow" into a Brick Wall.

---

## **V5.6.5 - FRESHNESS BASELINE FIX (The Falling Knife)**
**Date**: 2026-02-09
**Status**: Implemented

The "Free Roam" logic had a fatal flaw: It used `Outpost Creation Time` as the freshness baseline.
*   **The Bug**: This authorized "Stale Traps" (Stairs) formed during the trend ascent. When price crashed (Magnet Fade), the EA bought into these old stairs, catching the falling knife.
*   **The Fix**: We now use `Outpost TOUCH Time` as the baseline.
*   **Result**: 
    1.  Traps must be **REACTIONS** to the Outpost Touch (Bounces).
    2.  Old stairs from the previous leg are **Ignored**.
    3.  Result: Falling Knives are blocked. Bounces are bought.
