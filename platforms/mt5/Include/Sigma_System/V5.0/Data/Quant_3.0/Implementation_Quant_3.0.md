# Implementation Plan: Pure Physics Unification (Quant 3.0)

## Objective
Unify the system into a single, cohesive **Pure Physics** permission hierarchy. 

We are moving to an **Absolute Physics Gate**: 
1. **Space is Authorization**: If `Space_Ratio >= InpVacuumThreshold`, the trade is authorized. Consensus (votes) are logged for data analysis but are **NOT** part of the permission bridge.
2. **Scorched Earth**: The legacy `InpReversalMargin` is removed. We no longer negotiate with "consensus"—we only listen to the vacuum.

## Technical Requirements

### 1. Variable A: Consensus Aggregator
- **Task**: Modify `CalculateConsensus` to provide a numeric "Net Delta" of the 9 timeframes.
- **Logic**: 
  - `Match (Var 1)`: If all 9 TFs are aligned.
  - `Conflict (Var 2/3)`: If LTF aligns but HTF disagrees.

### 2. Variable B: The Proximity Sensor (The Vacuum)
- **Task**: Update `IsTradeAllowed` to calculate the spatial relationship between price and the "Highway Walls."
- **Roadblock Selection Logic**:
  - If `signal_tf` is M1 or M5 -> Target H1 or H4 opposing zones.
  - If `signal_tf` is M15 or M30 -> Target D1 or W1 opposing zones.
- **The Stride (ATR)**: Fetch the ATR for the `signal_tf`.
- **Space Ratio Logic**:
  - `Authorized V2`: If `Distance > 3x ATR`.
  - `Blocked Knife`: If `Distance < 1.5x ATR`.
  - `ATH/ATL Exception`: If `Roadblock == 0`, set `Space_Ratio = 999.0` (Infinite Vacuum).

### 3. Variable C: The Pivot Upgrade (The L2 Breach)
- **Task**: Implement a state tracker for active Variation 2 trades.
- **Upgrade Trigger**: If price closes beyond the `L2_price` of the identified Roadmap Roadblock.
- **Result**: Remove the roadblocked TP and allow for full Trend Expansion (Variation 3).

### 4. Variable D: The Consensus Filter (Stabilizer)
- **Task**: Implement a numeric gate to prevent back-to-back flipping in range markets.
- **Logic**: 
    - `InpNetDeltaThreshold`: Minimum sum of 9-TF votes required to authorize a trade.
    - If `InpNetDeltaThreshold = 4`:
        - Reject BUY if `Net Delta < 4`.
        - Reject SELL if `Net Delta > -4`.
    - This ensures that "Vacuum" trades (Var 2) still require a minimum fractal tilt before firing.


## Proposed Code Changes

### `StrategyOrchestrator.mqh`
1.  **`FindNearestRoadblock`**: Add a `min_tf` parameter to ensure it ignores "bumps in the road" (LTF zones) and targets HTF roadblocks.
2.  **`IsTradeAllowed`**: 
    - Insert the Space Ratio calculation before granting permission.
    - Implement the logic to allow trades against the D1 Wind if `Space_Ratio >= 3.0`.
    - Set the `out_tp` to the Roadblock price for Variation 2 trades.

### `OrderManager.mqh`
1.  **`QuantTradeExport`**: Add `roadblock_tf`, `vacuum_pts`, and `space_ratio` to the export struct.
2.  **`LogTrade`**: Ensure these metrics are written to the CSV for verification.

## Verification Workflow
The audit CSV must verify the following sample logic:
`Signal: M5 BUY | Roadblock: H4 BEAR | Space_Ratio: 8.5 | Status: AUTHORIZED (Variation 2)`

---
## Connected Parameters (The Control Knobs)

### 1. InpVacuumThreshold (The Absolute Gate)
- **Role**: The single "Yes/No" sensor for spatial physics.
- **Logic**: Any trade (With-Wind or Contrary) must have `Space_Ratio >= InpKnifeThreshold`. Contrary trades must have `>= InpVacuumThreshold`.

---
**Status**: Pure Physics Unification Complete. ERA Inputs Purged.
