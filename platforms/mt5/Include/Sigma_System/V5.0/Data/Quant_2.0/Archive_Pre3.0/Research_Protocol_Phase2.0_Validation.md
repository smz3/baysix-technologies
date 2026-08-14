# Research Protocol: Phase 2 Validation (The Falsification Suite)

**Date:** 2026-01-19
**Author:** SIGMA Quant (Physicist Profile)
**Objective:** Rigorously attempt to **falsify** the findings of Universal Audit V3 to prove their resilience.

---

## 1. The "Too Good To Be True" Flag
The Audit V3 shows **Expectancy values of 21R+** and **Win Rates > 60%** for specific buckets. In Physics and Quant finance, "Anomalous Efficiency" usually implies one of three things:
1.  **The Holy Grail:** We found a fundamental flaw in the market (Unlikely, but possible).
2.  **Lookahead Bias:** The code "knew" the future (Common).
3.  **Overfitting:** We drew the bullseye around the arrow (Common).

We must assume cases #2 or #3 until proven otherwise.

---

## 2. Defensive Definitions

### A. Lookahead Bias (The Time Machine)
*   **Definition:** Using data at time `T` that only became available at `T+1`.
*   **Risk Area:** The `ZigZag` or `Fractal` logic often "repaints" – a bottom is only confirmed *after* price moves up. If we enter *at* the bottom in the backtest but *after* the move in live, our backtest is fake.
*   **Validation Test:** "The Hard-Right-Edge Test".
    *   Run visualization mode.
    *   Pause at the *exact* moment a Zone is created.
    *   Does it exist *before* the price touches it? or does it pop into existence *because* price touched it?

### B. Selection Bias (The Cherry Pick)
*   **Definition:** "Filtered to Valid Sessions Only (Removed NaN Garbage Data)".
*   **Risk:** Did we remove "Garbage Data" because it was mathematically invalid (e.g., Division by Zero) or because it was *losing money*?
*   **Validation Test:** "The Dumpster Dive".
    *   Run the audit with **NO FILTERS**. Show me the ugly.
    *   If the "Garbage" is just random noise (0R expectancy), the filters are valid.
    *   If the "Garbage" is highly negative (-10R), our filters are just hiding losses.

### C. Overfitting (The Curve Fit)
*   **Definition:** "Legend (>1w)" vs "Prime (4-24h)". Why 24h? why not 20h?
*   **Risk:** Tuning variables `(Session == NY) AND (Age > 1 Week)` to capture a specific cluster of past wins.
*   **Validation Test:** "Parameter Shaking".
    *   Shift the Age bucket boundaries by +/- 20%. (e.g., test > 5 days instead of 1 week).
    *   Shift the Age bucket boundaries by +/- 20%. (e.g., test > 5 days instead of 1 week).
    *   If the edge collapses, it was noise.
    *   If the edge degrades smoothly (Linear Sensitivity), it is robust physics.

### D. The "Universal Time" Constraint (CRITICAL)
*   **Definition:** "Age" is defined as **ABSOLUTE TIME (Minutes)** since creation.
*   **Threshold:** `Age < 480 Minutes` (8 Hours) = **TOXIC**.
    *   *Context:* This value is derived from the "8 Bar Rule" on H1 (8 * 60m = 480m).
*   **Scope:** This audit applies **ONLY** to `H1, H4, D1, W1, MN1`.
    *   *Note:* Code must enforce `TimeCurrent - CreationTime > MinMinutes`.
    *   *Note:* `M1/M5` are excluded from the main audit but used for "Naive" stress testing.

---

## 3. The Test Suite (Action Plan)

### Test 1: Code Integrity Audit (Static Analysis)
*   **Goal:** Ensure no `iShift` or future-bar access.
*   **Action:** Grep codebase for `iHigh(..., i)` where `i` could be negative relative to current loop, or access to `Rates[total - x]`.

### Test 2: The "Out-of-Sample" Lockbox (Temporal)
*   **Goal:** Verify time invariance.
*   **Action:**
    *   **In-Sample (Training):** Jan 1, 2022 -> Dec 31, 2024.
    *   **Out-of-Sample (Exam):** Jan 1, 2025 -> Present (2026).
    *   *Constraint:* We are NOT allowed to change settings for the 2025-2026 run. Not even once.

### Test 3: Cross-Asset Universalism (Spatial)
*   **Goal:** Physics applies everywhere.
*   **Action:**
    *   Take the exact settings from `US30` (or primary asset).
    *   Apply them blindly to `NAS100` or `XAUUSD`.
    *   **Hypothesis:** The *Win Rate* might drop slightly due to volatility differences, but the **Expectancy (R-Multiple)** must remain positive. If it flips negative, the theory is local (overfitted), not universal.

### Test 4: The "Blind Monkey" Benchmark
*   **Goal:** Prove skill over luck.
*   **Action:**
    *   Randomize entry directions at the *same* zones.
    *   If our "With Trend" filter (50% WR, 17R) is real, the "Random Direction" should show significantly worse metrics (e.g., 30% WR, -2R).

---

## 4. Next Steps for USER
1.  **Confirm Dates:** What date range was used for the "Universal Audit V3"?
2.  **Confirm Logic:** Are the "Age Buckets" hardcoded based on this chart, or were they derived from first principles (Phase 0)?
3.  **Execute:** Shall we proceed with **Test 1 (Code Integrity)** or **Test 2 (Out-of-Sample)** first?
