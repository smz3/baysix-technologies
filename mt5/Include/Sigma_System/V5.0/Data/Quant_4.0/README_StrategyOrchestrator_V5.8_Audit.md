# Technical Audit: StrategyOrchestrator.mqh (V5.8)

This document provides a block-by-block breakdown of the current structural logic as of V5.8.

---

## 1. Foundation: Data Structures (L17 - L97)

### `struct FlowState` (L18 - L64)
This is the "Membrane" of a market narrative. It stores the identity and status of structural zones for a specific timeframe (MN1, W1, or D1).
- **Origin/Magnet/Outpost IDs**: Core pointers to the B2B zones defining the current trend leg.
- **Touch Tracking**: `magnet_fifty_touched` (T2) and `magnet_L2_touched` (T3) track price proximity to the target wall.
- **Safety Flags**: `anchor_is_traded` (V5.7 Trigger) and `is_magnet_extreme` (V5.8 Discovery Filter) ensure structural health.
- **Siege Mode**: `is_siege_active` flags when price is attempting to break through an opposing magnet.

### `struct TrapState` (L67 - L97)
*Note: This is partially deprecated in favor of Multi-Trap, but still used for legacy single-trap compatibility.*
- Stores temporary signal-specific data (price, SL, TP) and whether it was authorized.

---

## 2. The Orchestration Entry (L116 - L163)

### `void Orchestrate()` (L137 - L141)
The primary entry point. Every tick, it triggers the state update.
- Calls `UpdateFlowState` to process all timeframes.

### `void UpdateFlowState()` (L143 - L163)
The "Heartbeat" of the engine.
- Loops through MN1, W1, and D1 in order.
- Generates the **Heartbeat Log** (L154 - L162) which allows the user to see the structural "Storyline" (Tide, Wind, Path) in the terminal.

---

## 3. The Core Narrative Engine: `UpdateTimeframeFlow()` (L165 - L350)

This is the most critical logic block. It manages the evolution of the narrative from Origin to Magnet.

### Persistence & Defeat (L167 - L183)
- If a timeframe is already valid, it verifies the **Origin Still Exists**.
- **Defeat Check**: If price breaks the back of the Origin (L2), the narrative is destroyed (`state.Reset()`).

### Successor Logic (Magnet Touch) (L185 - L214)
- When price touches the Magnet L2 (T3):
    - It searches for a **Successor Outpost** using `GetLatestOutpost`.
    - If found, the Outpost becomes the **New Origin**. The cycle resets for a new trend leg.
    - **V5.8 ATH Protection** (L204): If at ATH/ATL and no successor exists, the origin is *not* reset. This maintains the "Discovery" state.

### Outpost & Siege Tracking (L221 - L273)
- Continuously identifies the latest same-direction zone as the `outpost_id`.
- **V5.7 Safety Trigger**: Sets `anchor_is_traded` if the Outpost L1 has been hit. Free Flow depends on this.
- **Siege Trigger**: If an outpost touch is **Fresher** than the magnet touch, it means price "bounced" off the wall and hit support. Siege Mode turns **ON**.

### Vacuum / Origin Search (L276 - L349)
- If no narrative exists (Clean Slate), it searches for the newest untouched zone to act as the **Origin**.
- **Discovery Preference** (L287): In ATH/ATL, the search ignores any zone that opposes the MN1 Tide to prevent "Hijacker" trends.
- **Magnet Discovery**: Once an Origin is found, it looks for the **closest opposing zone** as the Magnet.

---

## 4. Linear Selection: `GetLatestOutpost()` (L351 - L397)

### Strict Linear Logic (V5.6.4)
- Prevents "Zombie Trends." It finds the absolute newest candidate zone in the trend direction.
- **The Gate**: If the NEWEST zone is broken by price, the trend is dead. It returns 0 to force a reset rather than falling back to an older, stale zone.

---

## 5. Defensive Scouting: `IsInsideOpposingZone()` (L400 - L444)

### Location Filter (V5.4) & Bulldozer Mode (L431)
- Scans higher timeframe zones to see if current price is "Inside enemy lines."
- **Bulldozer Mode**: If Siege is active, it IGNORES the roadblock that triggered the siege, allowing the engine to "punch through" the wall.

---

## 6. The Validation Gauntlet: `ValidateTrap()` (L454 - L529)

Determines if a candidate "Sniper" (Trap) is authorized by its Parent.

### Freshness Guard (V5.6.5) (L458 - L473)
- **Relative Baseline**: Uses Origin touch time (Strict) or Outpost touch time (Free Flow).
- The trap **MUST** be created after this baseline. This stops the "Falling Knife/Stale Trap" issue.

### Global Shield (L478 - L493)
- If a Higher Timeframe (MN1/W1) Magnet is being hit (T2/T3) and Siege is OFF, the "Shield is UP." No D1 continuation trades are allowed. You must wait for the Magnet Flip.

### Liberation Check (L499 - L528)
- **Level 1 (Strict)**: If no Outpost/Trigger, the trap **MUST** be spatially nested inside the Origin L1-L2.
- **Level 2 (Free Flow)**: Once an Outpost is "Traded", the trap is "Liberated" and can fire anywhere in the vacuum.

---

## 7. The Decision Engine: `IsTradeAllowed()` (L532 - 789)

### The Hierarchy Loop
1. **Global Siege Guard** (L545): Blocks any trade opposing an active MN1/W1/D1 Siege.
2. **Handover Logic (V5.7)** (L556-571): D1 or W1 can "Take Authority" if they are fresher than the higher timeframe, provided they align in direction.

### Authority Tiers
- **MN1 Flow** (L573): Top priority. Ignores everything. Target = MN1 L2.
- **W1/D1 Flow**: Checked in sequence. Includes **Roadblock Filters** to ensure price isn't inside an opposing HTF zone.
- **Magnet Fades** (L657 - L723): Specialized gates for trading *against* the trend when a Magnet T2/T3 is hit (MN1 Pullback, W1 Fade, D1 ATH Fade).

---

## Summary of the Structural "Handshake"
In V5.8, a trade only fires when:
1. The **State Engine** identifies a clear Origin-Target path.
2. The **Location Filter** confirms the path is not blocked.
3. The **Validation Gauntlet** confirms the timing (Freshness) and location (Nesting/Liberation).
