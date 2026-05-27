# Trap Refinement: Strict Nesting Protocol

## Overview
This document outlines the optimization of the "Fractal Maturity" logic to mitigate "floating trades" that occur outside of identified HTF structural boundaries.

## Rationale
Current observation shows that traps are being authorized as "Mature" simply by being born after the HTF Anchor touch, even if they appear far away from the Anchor's physical level (in the "vacuum" toward the Magnet). 

The goal is to enforce a **Strict Nesting Rule**: A trap is only valid if it represents a reaction *at* or *inside* the structural source.

## Logic Definition: Phase 1 (Strict Nesting)

### Physical Constraint
A Control Trap is only candidate for Authorization if its primary barrier (L1) resides within the vertical boundaries of the active HTF Anchor (W1 or MN1).

**Mathematical Bounds:**
- **Bullish Anchor (Demand):** `Anchor.L2_price <= Trap.L1_price <= Anchor.L1_price`
- **Bearish Anchor (Supply):** `Anchor.L1_price <= Trap.L1_price <= Anchor.L2_price`

### Categorization
- **Strictly Anchored:** Trap L1 is inside the HTF box.
- **Floating (Rejected):** Trap L1 is outside the HTF box (typically front-running or late momentum).

## Implementation Strategy
1. **Modify `LocateControlTrap`**:
   - During the matures scan, perform a price-range check against the `active_anchor`.
   - Update rejection logs to distinguish between `LEGACY` and `OUT_OF_BOUNDS`.

2. **Verification**:
   - Cross-reference terminal logs with chart visuals to ensure traps in the vacuum are marked as `[REJECTED: OUT OF BOUNDS]`.
   - Ensure the `#XXXX` ID corresponds to the visual zone being rejected.
