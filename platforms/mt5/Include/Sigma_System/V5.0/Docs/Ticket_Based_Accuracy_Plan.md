# Implementation Plan: Ticket-Based Trade Reconciliation (Source of Truth)

## 1. Objective
Replace the current fragile "Comment Parsing" and "Manual P&L Calculation" logic with a **Ticket-Based Matching System**. 
Instead of trying to reconstruct trade outcomes, we will link our rich Strategy Data (Cascade, Zones, Voting) directly to MT5's official History using the unique **Order/Position Ticket**.

This ensures our JSON export matches the MT5 Strategy Tester report 100% of the time.

## 2. Core Concept
1.  **Entry (Real-time)**: When we open a trade, we capture its `Ticket` ID and store it in memory alongside our Strategy Data.
2.  **Exit (Post-Test)**: At the end of the session (`OnDeinit` / `OnTester`), we ask MT5: *"What was the final result for Ticket #12345?"*
3.  **Result**: We combine the authoritative MT5 result with our custom Strategy Data.

## 3. Required Changes

### A. Data Structure Updates (`FractalDominoLogger.mqh`)
*   **Modify `FractalDominoTrade` Struct**:
    *   Add `ulong ticket;` field.
    *   (Optional) Remove `trade_id` dependence for matching (keep it only for UI display purposes).

### B. Simplify Order Manager (`OrderManager.mqh`)
*   **Capture Ticket**: In `OpenBuyOrder` / `OpenSellOrder`, ensure the returned `ticket` is passed to the Logger.
*   **Logging**: Call `g_FDLogger.RecordTradeEntry(..., ticket)` immediately after successful order placement.

### C. Major Logic Shift (`FractalDominoLogger.mqh`)
*   **Method: `ReconcileHistory()`**:
    *   **New function** to be called at the end of the session.
    *   Iterates through all recorded `m_trades`.
    *   Uses `HistorySelectByPosition(ticket)` to pull the complete deal history for that specific ticket.
    *   **Calculates**:
        *   `Realized P&L` (Sum of all deals for this ticket: partial closes, swaps, commissions).
        *   `Exit Time` & `Exit Price` (from the final deal).
        *   `Exit Reason` (SL/TP checks based on deal comments/prices).
    *   **Updates** the `m_trades` entry with this authoritative data.

### D. Cleanup (`Sigma_V5.0.mq5`)
*   **DELETE**: `ScanHistoricalDealsForExits` (The complex "Pass 1 / Pass 2" parser).
*   **MODIFY**: `OnDeinit` or `OnTester` to simple call `g_FDLogger.ReconcileHistory()`.

## 4. Benefits
1.  **100% Accuracy**: P&L is derived from the broker/tester ledger, not a manual math calculation.
2.  **Swaps & Commissions**: Automatically included (our manual calculation couldn't easily account for these).
3.  **Partials**: If we scale out, MT5 history tracks it. Ticket matching handles it naturally.
4.  **Robustness**: Changes to comment formats (like "B2B_...") will never break the data pipeline again.

## 5. Execution Steps
1.  **Backup**: Ensure current code is backed up (we have the previous version).
2.  **Refactor Logger**: Update struct and add `ReconcileHistory`.
3.  **Refactor OrderManager**: Pass tickets to Logger.
4.  **Integration**: Update Main EA to use new flow.
5.  **Verify**: Run backtest and compare JSON Result vs MT5 HTML Report.
