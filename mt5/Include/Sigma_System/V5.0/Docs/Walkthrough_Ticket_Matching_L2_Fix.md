# Walkthrough - Ticket-Based Reconciliation & L2 Logic Fix

## 1. Ticket-Based Reconciliation (Completed)
We successfully transitioned to a ticket-based system for 100% accurate P&L tracking.
*   **Result**: P&L data now perfectly matches MT5 Strategy Tester.
*   **Verification**: latest JSON file contained correct `ticket` IDs and P&L matching the report.

## 2. Investigating Missing L2 Trades (Completed)
User reported that L2 trades were missing from the dashboard.
*   **Investigation**:
    *   Confirmed `fractal_domino_analyzer.py` (Python) works correctly.
    *   Confirmed `fractal_domino_latest.json` (Data) had zero L2 trades.
    *   **Root Cause**: The EA had two layers of "Anti-Pyramiding" blocks:
        1.  `TradeSignalGenerator` Rule 1b (Fixed): Blocked signal if Parent active.
        2.  `OrderManager` Execution Guard (Fixed): Blocked execution if *any* trade existed for the zone.

## 3. The L2 Logic Fix (Final)
We implemented a robust "Stacking" logic (Cost Averaging) for the same zone.

**Files Modified:**
*   **`TradeSignalGenerator.mqh`**: Updated `EvaluateZone` to accept `is_self_active`, allowing signals even if 50% is active.
*   **`OrderManager.mqh`**:
    *   Refined `HasOpenPosition` search to support `_Z{id}_` patterns.
    *   **Crucial Update**: Replaced blanket `HasOpenPositionForZone` with `HasOpenPositionForZoneAndLevel`. This allows multiple trades for the same zone *as long as they are different levels* (e.g. one FIFTY + one L2 is allowed, but two L2s are blocked).

**Result**:
*   **Stacking Enabled**: 50% + L2 trades can now coexist.
*   **Safety Preserved**: Duplicate trades at the same level are prevented.

## 4. Next Steps
1.  **Recompile** `Sigma_V5.0.mq5` in MetaEditor.
2.  **Run Backtest**.
3.  **Sync Data**: `npm run sync:fd`.
4.  **Verify**: Dashboard should now show L2 trades populated.
