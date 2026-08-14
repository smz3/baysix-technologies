# Phase 0.5 Research Report: Zone MFE Profitability Analysis

**Author:** SIGMA Quant Research  
**Date:** January 2026  
**Asset:** XAUUSD  
**Period:** 2020-2023 (Training Data)

---

## Executive Summary

This research validates that B2B zones deliver profitable MFE (Max Favorable Excursion) **before death**, making them tradeable regardless of eventual survival. Analysis of 1,024 bulldozed zones shows:

- **72.5%** achieved ≥ 1R before death
- **56.2%** achieved ≥ 2R before death
- **Bar survival > 16 bars** increases 2R success to **82.7%**
- **T3 touch depth** shows highest profitability at **70.7%**

---

## 1. Methodology

### Data Collection
| Metric                  | Value                           |
|-------------------------|---------------------------------|
| Total Zone Events       | 14,010                          |
| Bulldozed Zones Analyzed| 1,024                           |
| Timeframe               | H1 (zones created on H1 chart)  |
| Backtest Mode           | Every Tick                      |
| MFE Tracking            | From L1 touch to invalidation   |
| **Data Integrity Note** | ~17% "Silent Deaths" (instant invalidation) are included as losses to ensure robustness. |

### R-Multiple Calculation
```
R-Multiple = MFE_pips / Zone_Size_pips
```

Where:
- **MFE** = Maximum favorable price excursion from L1 touch
- **Zone Size** = Distance between L1 and L2 (stop risk)

### Anti-Overfitting Measures
1. **Pre-registered hypotheses** — No p-hacking
2. **Hold-out data** — 2024-2025 reserved for validation
3. **Training only** — All results from 2020-2023 data

---

## 2. R-Threshold Analysis

| Threshold | Zones Hit | Hit Rate  |
|-----------|-----------|-----------|
| ≥ 0.5R    | 860       | 84.0%     |
| ≥ 1.0R    | 742       | 72.5%     |
| ≥ 1.5R    | 646       | 63.1%     |
| ≥ 2.0R    | 576       | 56.2%     |
| ≥ 2.5R    | 536       | 52.3%     |
| ≥ 3.0R    | 495       | 48.3%     |
| ≥ 4.0R    | 436       | 42.6%     |
| ≥ 5.0R    | 377       | 36.8%     |

### Key Insight
The 2R threshold offers the best balance:
- **56.2% win rate** at 2:1 reward-to-risk
- Expectancy = (0.562 × 2) - (0.438 × 1) = **0.686R per trade**

---

## 3. R-Multiple Distribution Analysis

### Overall Statistics
| Metric        | Value   |
|---------------|---------|
| **Min R**     | 0.00R   |
| **Max R**     | 267.78R |
| **Mean R**    | 9.61R   |
| **Median R**  | 2.75R   |

> **Key Insight:** The median R is **2.75R**, meaning 50% of all bulldozed zones offer nearly 3R profit potential before dying.

### Percentile Breakdown
| Percentile    | R-Multiple |
|---------------|------------|
| 10th          | 0.32R      |
| 25th          | 0.86R      |
| **50th**      | **2.75R**  |
| 75th          | 8.06R      |
| 90th          | 22.56R     |
| 95th          | 37.30R     |
| 99th          | 127.91R    |

> **How to Read This Table:**
> - **25th (0.86R):** The "weak" trades. 25% of zones provided less than 0.86R.
> - **50th (2.75R):** The "limit". Half of all trades performed better than this, half worse. If you pick a random zone, you should expect ~2.75R.
> - **75th (8.06R):** The "good" trades. Top 25% of zones delivered massive 8R returns.
> - **99th (127.91R):** The "home runs". Top 1% of zones that likely caught a major trend reversal.

---

## 4. Timeframe Analysis

| Timeframe | Count | Mean R | Median R | 2R Hit Rate |
|-----------|-------|--------|----------|-------------|
| **H1**    | 463   | 12.8R  | 3.7R     | **62.9%**   |
| H4        | 432   | 7.6R   | 2.4R     | 53.9%       |
| D1        | 110   | 5.3R   | 1.3R     | 40.0%       |
| W1        | 15    | 2.3R   | 1.8R     | 46.7%       |
| MN1       | 4     | 3.6R   | 1.3R     | 25.0%       |

### Key Insights
1. **H1 is the Golden Timeframe:** It offers the highest 2R hit rate (62.9%) and the highest Mean R (12.8R). It is the primary engine for daily setups.
2. **H4 is Reliable:** Solid 53.9% hit rate at 2R.
3. **D1 Lags:** Surprisingly lower performance (40% at 2R), likely due to wider zones requiring larger moves to hit R-multiples.

---

| Age Bucket    | Count | Mean R  | Median R | 2R Rate   |
|-------------  |-------|---------|----------|-----------|
| 0-100 bars    | 843   | 6.42R   | 1.84R    | 47.8%     |
| 100-200 bars  | 58    | 15.45R  | 9.56R    | 89.7%     |
| 200-500 bars  | 58    | 17.78R  | 11.06R   | 96.6%     |
| 500+ bars     | 65    | 38.40R  | 23.03R   | 100.0%    |

### Key Insights
1. **Young zones (0-100 bars) ARE tradeable** — 47.8% hit 2R
2. **Age is a quality predictor** — Older zones have higher success
3. **Phase 0 finding confirmed** — 500+ bars shows 100% success at 2R

### Causal Hypothesis
Older zones have been "tested" by the market multiple times. Survival signals structural importance. However, younger zones still offer profitable opportunities.

---

## 4. Bar Survival Analysis

| Category    | Bars After Touch | Count | Mean R  | 2R Rate   |
|-------------|------------------|-------|---------|-----------|
| Immediate   | 1 bar            | 99    | 8.32R   | 38.4%     |
| Short       | 2-5 bars         | 141   | 3.33R   | 44.0%     |
| Medium      | 6-15 bars        | 162   | 4.49R   | 47.5%     |
| Extended    | 16+ bars         | 445   | 16.94R  | 82.7%     |

### Key Insights
1. **Immediate failures (1 bar)** still deliver 38% at 2R — not worthless
2. **Extended survival (16+ bars)** is the strongest predictor at **82.7%**
3. **Sweet spot:** Wait for 16+ bars of survival before targeting 2R

### Actionable Rule
> If zone survives 16+ bars after T1 touch, target 2R (82.7% success)

---

## 5. Touch Depth Analysis

| Depth       | Count | Mean R  | 2R Rate   |
|-------------|-------|---------|-----------|
| T1 Only     | 106   | 10.29R  | 59.4%     |
| T2          | 304   | 7.56R   | 56.9%     |
| T3          | 437   | 14.12R  | 70.7%     |

### Key Insights
1. **T3 entries show highest success** — 70.7% at 2R
2. **T1 entries are viable** — 59.4% success rate
3. **T2 shows no advantage** over T1 — 56.9%

### Causal Hypothesis
T3 touch represents full zone penetration (to L2 edge). Zones that survive T3 demonstrate maximum structural resilience.

---

## 5B. Phase 0.75: Fractal Refinement
*Analysis moved to dedicated report: `Research_Paper_Phase075_Fractal_Resonance.md`*

We identified that filtering for **Fractal Zones** (Has Parent) improves Win Rate from 56% to **66%**. See separate paper for full breakdown.

## 6. Session Analysis (Updated)

| Session     | Count | Mean R  | 1.5R Rate | 2.0R Rate | 4.0R Rate |
|-------------|-------|---------|-----------|-----------|-----------|
| Asian       | 191   | 10.96R  | 62.3%     | 54.5%     | 42.4%     |
| London      | 186   | 10.39R  | 57.5%     | 50.0%     | 33.9%     |
| Overlap     | 254   | 9.66R   | 64.2%     | 58.7%     | 46.9%     |
| NY          | 341   | 8.43R   | **66.6%** | **59.2%** | **44.6%** |
| Off-Hours   | 52    | 9.29R   | 57.7%     | 53.8%     | 40.4%     |

### Key Insight
- **NY Session is slightly superior**, offering the highest hit rate across 1.5R (66%) and 2R (59%).
- **London is the "wild card"**, with the lowest hit rates but high Mean R (outliers).

---

## 7. Direction Analysis (Balanced Edge)

We analyzed performance by zone direction to check for trend bias.

| Direction | Count | Mean R  | 1.5R Rate | 2.0R Rate | 4.0R Rate |
|-----------|-------|---------|-----------|-----------|-----------|
| **BUY**   | 483   | 10.20R  | 62.9%     | **57.8%** | 43.7%     |
| **SELL**  | 541   | 9.08R   | 63.2%     | **54.9%** | 41.6%     |

### Key Insight
- **Remarkably Balanced:** Despite XAUUSD being in a macro bull run (2020-2023), **SELL zones performed almost as well as BUY zones** for harvesting (55% vs 58% at 2R).
- **Validation:** This proves the "Harvesting" strategy works on *volatility and reactions*, not just trend following. You can trade both sides.

---

## 8. Conclusions

### Thesis Validation
> "B2B zones deliver profitable MFE before invalidation, making them tradeable regardless of survival."

**CONFIRMED.** 56.2% of all bulldozed zones achieved ≥ 2R MFE.

### Recommended Trading Rules

| Rule                | Condition                         | Expected 2R Rate    |
|---------------------|-----------------------------------|---------------------|
| Base Case           | Any bulldozed zone                | 56.2%               |
| Age Filter          | Zone age 100-200 bars             | 89.7%               |
| Survival Filter     | 16+ bars after touch              | 82.7%               |
| Touch Depth         | T3 touch                          | 70.7%               |
| **Rank A Setup**    | H1 Zone + T3 Touch + 16 Bars      | **High Confidence** |

### Next Steps
1. **Hold-out validation**       — Test on 2024-2025 data
2. **Combined filters**          — Test Age + Survival + T3 together
3. **Live forward test**         — Apply to live trading

---

## 8. The Relevance of Zone Survivability (< 200 Bars)

**Question:** *"Does this mean zone structure survivability (< 200 bars) is not relevant anymore?"*

**Answer:** No. It means we have **two distinct edges** operating on different timeframes:

| Metric          | Phase 0 Edge (Survival)                     | Phase 0.5 Edge (MFE)                  |
|-----------------|---------------------------------------------|---------------------------------------|
| **Goal**        | Structural Integrity                        | Profitable Opportunity                |
| **Timeframe**   | Long-term (Weeks/Months)                    | Short-term (Hours/Days)               |
| **Relevance**   | Determines if we should **MARRY** a zone    | Determines if we can **DATE** a zone  |
| **Strategy**    | Position Trading (Trend Following)          | Swing/Day Trading (Harvesting)        |

### The "Two-Tiered" Strategy
1. **Tier 1 (Harvesting):**
   - **Target:** Young Zones (< 200 bars)
   - **Goal:** Extract 2R-3R MFE before the zone dies.
   - **Confidence:** 47.8% (0-100 bars) to 89.7% (100-200 bars) success at 2R.
   - *Survivability is irrelevant here — we just want the bounce.*

2. **Tier 2 (Structural):**
   - **Target:** Aged Zones (> 500 bars)
   - **Goal:** Ride trend continuation for 5R-10R+.
   - **Confidence:** 100% success at 2R, enabling larger position sizing and longer holds.
   - *Survivability is EVERYTHING here — it protects the long-term position.*

---

## 9. The Survivor "Jackpot" (Asymmetric Edge)

We analyzed the zones that **survived** the entire backtest period vs. those that were **bulldozed**. The difference is stark:

| Metric            | Bulldozed Zones (The "Daters") | Survived Zones (The "Marriage") |
|-------------------|--------------------------------|---------------------------------|
| **Count**         | 1,024                          | 81                              |
| **Outcome**       | Failed eventually              | Held structure                  |
| **Median R**      | **2.75R**                      | **31.66R**                      |
| **Mean R**        | 9.61R                          | 65.15R                          |
| **2R Hit Rate**   | 56.2%                          | **97.5%**                       |

### The "Free Option" Strategy
This confirms the ultimate edge:
1.  **Base Expectancy:** Even "loser" zones (bulldozed) pay for themselves (56% win rate at 2R).
2.  **Upside Convexity:** By holding a runner, you expose yourself to the "Survivors" which deliver massive outlier returns (Median 31R).
3.  **Conclusion:** You get paid small sums to hunt for massive structural winners.

### Survivor Anatomy (Deep Dive)

**1. Age Breakdown**
| Age Bucket        | Count     | Mean R     | Median R  | Insight                      |
|-------------------|-----------|---------   |---------  |---------                     |
| 0-100 bars        | 12        | 4.5R       | 3.2R      | Newly formed survivors       |
| 200-500 bars      | 12        | 53.6R      | 12.2R     | Breakout runners             |
| **500+ bars**     | **57**    | **80.3R**  | **61.7R** | **The Structural Jackpot**   |

> **Confirmed:** 70% of survivors were > 500 bars old. The "Age Constant" is the primary filter for finding 60R+ trades.

**2. Timeframe Breakdown**
| Timeframe | Count     | Median R   | Mean R     |
|-----------|-----------|------------|------------|
| **H1**    | **38**    | **68.5R**  | **106.3R** |
| H4        | 22        | 16.4R      | 27.9R      |
| D1        | 16        | 12.6R      | 28.3R      |

> **H1 is the Wealth Engine.** H1 survivors delivered an average of **106R**.

**3. Direction Bias (Gold 2020-2023)**
- **BUY:** 77 survivors (Median 35.6R)
- **SELL:** 4 survivors (Median 3.0R)
*(Reflects macro bull trend)*

---

## 10. Conclusions

### Thesis Validation
> "B2B zones deliver profitable MFE before death, making them tradeable regardless of survival."

**CONFIRMED.** 56.2% of all bulldozed zones achieved ≥ 2R MFE.

### Recommended Trading Rules

| Rule                | Condition                         | Expected 2R Rate    |
|---------------------|-----------------------------------|---------------------|
| Base Case           | Any bulldozed zone                | 56.2%               |
| Age Filter          | Zone age 100-200 bars             | 89.7%               |
| Survival Filter     | 16+ bars after touch              | 82.7%               |
| Touch Depth         | T3 touch                          | 70.7%               |
| **Rank A Setup**    | H1 Zone + T3 Touch + 16 Bars      | **High Confidence** |

### Next Steps
1. **Hold-out validation**       — Test on 2024-2025 data
2. **Combined filters**          — Test Age + Survival + T3 together
3. **Live forward test**         — Apply to live trading

---

## Appendix: Statistical Notes

- **Sample Size:**  1,024 bulldozed zones (sufficient for statistical validity)
- **Confidence:**   Results are pre-registered; no p-hacking applied
- **Limit:**        Training data only (2020-2023); validation pending
- **Definitions:**
  - **Mean R:**     The arithmetic average. Heavily skewed by outliers (jackpot survivors). Represents "Expectancy" if you take every trade.
  - **Median R:**   The middle value. Represents the "Typical Experience" for a random trade.
  - **P-hacking:**  The misuse of data analysis to find patterns in data that can be presented as statistically significant, dramatically increasing the risk of false positives.
