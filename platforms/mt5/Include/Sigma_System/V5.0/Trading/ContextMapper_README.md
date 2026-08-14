# ContextMapper.mqh (V5.9) - The 9-TF Stacked Radar

## 1. Core Purpose
The `ContextMapper` is a completely isolated Structural Topography Engine. Its sole purpose is to mathematically map the historical boundaries of the market across 9 specific timeframes, entirely decoupled from visual charting logic.

It provides the `StrategyOrchestrator` with a lossless "Topographical Map" of exactly where institutional liquidity walls (Back-to-Back Origins) are situated within fixed Unix epochs (Month, Week, Day).

## 2. The Stacked Radar Architecture
Unlike previous iterations that blindly scanned a single timeframe, the ContextMapper now uses a **100% loss-less Stacked TF Topography** using the `FindTopographicalBoundary` algorithm.

When mapping a high or low for a given window, it evaluates the strongest physics across **each permitted timeframe** within that window, preserving critical Macro Vacuums while providing local speed bumps.

### The Temporal Scans
*   **Monthly Scanner (Level 1):** Scans D1, H4, H1, M30 within the Current and Previous Month Unix window.
*   **Weekly Scanner (Level 2):** Scans H4, H1, M30 within the Current and Previous Week Unix window.
*   **Intraday Scanner (Level 3):** Scans H1, M30 within the Current and Previous Day Unix window.

### Example Stacked Matrix Log (Expert Advisor Output)
```text
=========================================================================================
>>>                      SAMTC CONTEXT MAPPER (STACKED RADAR)                         <<<
=========================================================================================
[MONTH] PREV H: D1-VACUUM | H4-#2015 (2050.00) | H1-#3011 (2050.00) | M30-#4201 (2051.00)
[MONTH] CUR  H: D1-VACUUM | H4-VACUUM | H1-#6547 (5227.82) | M30-#6547 (5227.82)
[MONTH] PREV L: D1-#8502 (4980.50) | H4-#8505 (4980.50) | H1-#8510 (4980.00) | M30-VACUUM
...
```
*Interpretation:* In the "Current Month High" row, D1 and H4 are `VACUUM`. This truth is preserved. The executing AI now strictly knows there is no Macro resistance ceiling holding the monthly trend down, despite local H1/M30 turbulence.

## 3. Key Components

### 3.1 `SessionBoundary` (The Armor Matrix)
This struct houses the topographically mapped IDs and Prices for D1, H4, H1, and M30 for *every single temporal period*. It holds 8 total elements per time slot (High ID/Price + Low ID/Price x 4 TFs).

### 3.2 `FindTopographicalBoundary` (The Master Scanner)
Loops through every single active `B2BZoneInfo` globally.
1.  **Temporal Filter:** Is `zone_created_time` strictly $>=$ the start of the defined Unix window, and $<$ the end?
2.  **Topographical Filter:** Is this zone's specific TF allowed to be mapped for this time period? (e.g., Weekly map ignores D1).
3.  **Physics Check:** If the zone is Bearish, is its `L1_price` higher than the highest known `L1_price` *for that specific timeframe*? If yes, it becomes the new High ID for that TF slot.

### 3.3 Unix Time Math (`GetPrevWeekStart`, etc.)
The system relies on integer math (`time - (time % 86400)`) and structural time offsets to calculate exact midnights of Prior Days, Prior Weeks, and Prior Months entirely independently of MT5's Broker Server Time shifts, ensuring seamless cross-platform logic.

## 4. Phase 2 (WIP): The Regime Intelligence
The Map currently exists only to collect and structure data. 
In Phase 2, `EvaluateContext` will calculate Strategic Regimes based on distance offsets between Current Price and the Stacked Matrix.

*   `REGIME_TREND`: Sky is clear across the Matrix.
*   `REGIME_FADE`: Price is physically compressed into a massive HTF mapped wall. 
*   `REGIME_CLUSTER`: Tiers are interwoven tightly.

This Regime will be polled by `StrategyOrchestrator::IsTradeAllowed` to dictate whether to trigger a Liberated Flow (trend) or a Reverse Domino (anti-trend target).
