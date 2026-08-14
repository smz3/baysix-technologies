# Phase Delta: Velocity & Temporal Structure
**Date:** 2026-01-25
**Status:** PROPOSED

## 1. The Thesis (The Why)
**Temporal Anchor & Auction Memory:**
Price movement is a function of time. Markets operate in auction cycles defined by time constants (Weeks, Months, Years). The boundaries of these auctions—The High and Low of the previous Year, Month, or Week—represent **Hard Statistical Limits** (Where the auction failed).
We reject the subjective "Body-to-Wick" morphology. Instead, we define **Structure** as the interaction between a B2B Zone and a **Temporal Partition**.
*   **Hypothesis:** A B2B Zone forming at a Temporal Boundary (e.g., Previous Week's Low) inherits the "Memory" of that major auction. A B2B Zone forming in the middle of a time period is "Floating" (Random Walk).

## 2. The Hypothesis (The Test)
**$H_1$ (Temporal Node):**
If we categorize trade signals into **Bin A (Floating)** and **Bin B (Anchored)**, then Bin B will exhibit a statistically significant increase in **Expectancy ($E$)** and **Profit Factor ($PF$)** with a **Z-Score $> 2.0$**.

**$H_2$ (Trajectory Accuracy):**
We hypothesize that **Path Trajectory Accuracy** (attaining the opposing Temporal Boundary) will be $> 65\%$ when a trade is initiated from an Anchored Node. The "Target" is the opposing limit of that timeframe (e.g., Low $\to$ High).

## 3. The Manifold (Sigma Auction Market Theory)
The "Brain" of Phase Delta. It shifts the logic from "Pattern Recognition" to "Time-Space Constraints".

### A. Sigma Auction Market Theory (Sigma AMT)
Traditional AMT uses Volume Profiles (fuzzy). We use **Temporal Extremes** (precise).
*   **The Auction:** A time-bound search for fair value.
*   **The Boundary:** The High/Low of a completed Time Unit (Year, Month, Week, Day). These are "Hard Statistical Limits" where the previous auction failed to find agreement.
*   **The Signal:** A B2B Zone forming **AT** a Boundary implies a "Test of Structure."

### B. The Geometry: "Temporal Partitions"
We define structure using the Period Separators (Time Dividers) which represent the true Auction Boundaries:
*   **The Alpha Layer (Yearly):** Previous Year High/Low (PYH/PYL). (12 Monthly Candles).
*   **The Beta Layer (Monthly):** Previous Month High/Low (PMH/PML). (D1 Separators).
*   **The Gamma Layer (Weekly):** Previous Week High/Low (PWH/PWL). (H4 Separators).
*   **The Delta Layer (Daily):** Previous Day High/Low (PDH/PDL). (H1/M15 Separators).

### C. Node Classification
*   **Anchored Node:** A B2B Zone (any TF) that interacts with an Alpha, Beta, Gamma, or Delta boundary. This is a "Decision Point."
*   **Floating Node:** A B2B Zone that forms inside the range (Between High and Low) without touching the boundaries. This is "Internal Noise."

## 4. Statistical Verification Loop
We don't trust the theory; we trust the Z-Score.
*   **Bin A (Floating):** Trades in zones inside the temporal range.
*   **Bin B (Anchored):** Trades in zones touching the PYH/L, PMH/L, PWH/L, or PDH/L.
*   **Success Metric:** We require a **Z-Score > 2.0** (95% confidence) to prove the Anchored trades have superior expectancy.

## 5. Implementation Plan (Detailed)
This phase introduces a new Core Module and modifies the Logging system.

### Step 1: Create `CManifold` Module
*   **File:** `Include/V5.0/Core/CManifold.mqh`
*   **Responsibility:** 
    *   Calculate and Cache the `SManifold` struct.
    *   **Alpha (Annual):** Prev Year High/Low.
    *   **Beta (Monthly):** Prev Month High/Low.
    *   **Gamma (Weekly):** Prev Week High/Low.
    *   **Delta (Daily):** Prev Day High/Low.

### Step 1.5: Visual Validation (The Oscilloscope)
*   **Requirement:** The EA must draw the Manifold on the chart to verify the calculations match the visible Period Separators.
*   **Visual Hierarchy (All Dashed 1px):**
    *   **Alpha (Annual):** `clrGold`
    *   **Beta (Monthly):** `clrSilver`
    *   **Gamma (Weekly):** `clrMagenta`
    *   **Delta (Daily):** `clrDodgerBlue`
*   **Control:** Toggle via input `InpDrawManifold`.

### Step 2: Integrate with `TradeSignalGenerator` (The Intersection Test)
*   **Logic:** A Zone is a range `[Low, High]`. A Manifold Line is a value `P`.
*   **Condition:** `IsAnchored` if `P >= (ZoneLow - Tolerance)` AND `P <= (ZoneHigh + Tolerance)`.
*   **Modification:** In the `ScanForPhrases` or equivalent loop where a zone is created.
*   **Action:** Call `manifod.CheckStructure(zone)`.
*   **Tagging:** Add a new field to `SZone` or the Signal output: `ENUM_STRUCTURE_TYPE structure_tag`.

### Step 3: Update `CSVLogger` & `TradeManager`
*   **CSV Column:** Add `structure_tag` (String or Int) to `QUANT_TRADES.csv`.
*   **Data Harvest:** Run a backtest (Physics Mode) to populate this new column for all historical trades.

### Step 4: Python Analysis (Jupyter)
*   **Binning:** Split the dataset into `Anchored` vs `Floating`.
*   **Validation:** Calculate $E$, $PF$, and Win Rate for both bins. Verify $Z > 2.0$.

## 6. Expected Outcome
*   **Precision**: Eliminating "mid-range" chop by filtering out Floating zones.
*   **Clarity**: Moving from subjective "shapes" to objective "time" allows for rigid statistical proof.
*   **Statistical Arbitrage**: Harvesting the flow from Weekly Low to Weekly High.

## 7. Amendment 2: Elastic Reconvergence (The Fractal Return)
**Date:** 2026-01-26
**Scientific Name:** **Elastic Reconvergence** (Mean Reversion to Structural Origin).

### The Fractal Trigger Logic
We introduce a rigorous "Return to Base" protocol based on fractal invalidation.

#### Protocol A: The Macro Loop (W1 -> D1)
1.  **Origin:** W1 B2B **BUY** (The Launchpad).
2.  **Extension:** Price rallies away from the Origin.
3.  **Trigger:** **FIRST** D1 B2B **SELL** (The Breakdown).
4.  **Target:** The Top of the W1 B2B Buy Zone.
5.  **Probability Booster:** This trade is valid IF AND ONLY IF the W1 Origin was **ANCHORED** (verified by Manifold Memory).

#### Protocol B: The Meso Loop (D1 -> H4)
1.  **Origin:** D1 B2B **BUY**.
2.  **Trigger:** **FIRST** H4 B2B **SELL**.
3.  **Target:** The Top of the D1 B2B Buy Zone.

### Manifold Memory Integration
We cannot rely on "Floating" B2B zones as Origins. They are weak attractors.
*   **The Filter:** "Return to Base" is ONLY activated if the **Origin Zone** has a `Manifold Score > 0`.
*   **Physics:** A W1 Origin at a Yearly Low has massive gravity (Deep Gravity Well). A W1 Origin in the middle of nowhere has weak gravity.
*   **Implementation:** `CManifold` must store a `CList` of historical extremities ("Ghost Manifolds") to valid ancient Origins.
