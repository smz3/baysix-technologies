# SIGMA Phase 1: The Probability Engine
## "The Mathematical Combination"

**Date:** January 18, 2026
**Status:** DRAFT (Renamed from Phase 2)
**Based on:** Verified Findings of Phase 0.5, 0.75, and 1.0

---

## 1. The Unified Theory (The "Stack")

We allow three distinct layers of statistical edge to stack upon each other. We do not "mix" them; we "layer" them.

| Layer                 | Source     | Edge Type                    | Metric         | Role                                     |
| :---                  | :---       | :---                         | :---           | :---                                     |
| **1. The Filter**     | Phase 0.75 | **Fractal Resonance**        | Win Rate: 67%  | **SELECTION.** (Don't trade Orphans).    |
| **2. The Shield**     | Phase 0.75 | **Hard Structure (T1/T2)**   | Win Rate: 100% | **VELOCITY.** (Catching the Rocket).     |
| **3. The Trigger**    | Phase 0.5  | **Deep Value (T3)**          | Win Rate: 70%  | **VALUE.** (Buying Cheap).               |
| **4. The Validation** | Phase 0.5  | **Time Decay (>16 Bars)**    | Win Rate: 82%  | **CONFIRMATION.** (Survival = Strength). |

### The "Anti-Overfitting" Check
*   **Fractal:** Binary State (Parent Exists). No curve fitting.
*   **Shield (T1):** The "Surface" of the zone. Physical constant.
*   **T3 (Deep Value):** Physical limit of the zone (L2). No curve fitting.
*   **Time (>16 Bars):** Validated across multiple regimes (2020 vs 2023).

---

## 2. The Protocols (Exploitable Combinations)

We derived three specific "Probability Protocols" from this combinations.

### Protocol A: "The Shield" (Aggressive Impulse)
*Logic: Exploiting the Phase 0.75 finding that "Hard Shields" (T1/T2 touches) on Fractal Zones have a 100% Win Rate and 30R-40R payoff.*

*   **Zone Selection:** Must be **Fractal** (H1 Zone with H4/D1 Parent).
*   **Trigger:** **Touch at T1 (L1 Price).**
*   **Entry Method:** **Market Execution** (Immediate).
*   **Why it works:** Captures the "Rockets" (4% occurrence, massive EV).
*   **Risk:** Accepts drawdown to T3 (96% probability).

### Protocol B: "The Deep Trap" (Limit Orders)
*Logic: Exploiting the Phase 0.5 finding that T3 touches have the highest 2R Win Rate (70%) among non-instant winners.*

*   **Zone Selection:** Must be **Fractal**.
*   **Entry Method:** **Limit Order at T3 (L2 Entry).**
*   **Target:** Zone B (Calculated).
*   **Why it works:** Captures the "Grind" trades at max value.

### Protocol C: "The Survivor" (Market Execution)
*Logic: Exploiting the Phase 0.5 finding that zones surviving 16+ bars after first touch have 82% Win Rate.*

*   **Condition:** Fractal Zone touched + active for > 16 Bars.
*   **Entry Method:** **Market Execution** on breakout.
*   **Why it works:** Survivorship Bias. Zone has proven it cannot be killed.

---

## 3. The Probability Math (Target Selection)

We replace "guessing" Zone B with **calculated probability**.

### The "Median Horizon" Thesis
*   **Fact:** H1 Fractal Zones have a **Median R of ~5 R** (Phase 0.75 Data).
*   **Deduction:** There is a > 50% statistical probability that any Fractal Launch will travel 5R.
*   **Implication:** Any opposing structure < 5R away is statically insignificant (likely to be bulldozed).

### The Formula: Probability of Arrival ($P_{arrive}$)
For any candidate Target Zone ($Z_b$) at distance ($D$) from Entry ($Z_a$):

$$ P(Arrive) = \frac{\text{Count}(Fractals_{MFE} \ge D)}{\text{Total Fractals}} $$

*   Example: Target at 3R -> $P(Arrive) \approx 60\%$ (High Confidence)
*   Example: Target at 20R -> $P(Arrive) \approx 20\%$ (Low Confidence)

### The "5R Rule" (Target Filter)
> **Refined Logic:** `FindNearestOpposingZone` must IGNORE any zone where `Distance < 5 * ZoneA_Risk`.
> **Goal:** Trust the rocket to clear the immediate noise. Set the target at the *first significant gravitational body* beyond the escape velocity horizon.

---

## 4. Verification: Thesis & Hypothesis

To fact-check this before coding, we define the scientific claims.

### The "Gravity Well" Hypothesis
**Claim:** "Fractal Zones generate sufficient Kinetic Energy (Mean 17R, Median 5R) to nullify minor opposing structures within a 5R radius."
**Null Hypothesis:** "Opposing zones within 5R are just as likely to reverse price as those beyond 5R."
**Test:** Compare the "Bulldoze Rate" of opposing zones < 5R vs > 5R.
**Prediction:** Opposing zones < 5R will have a >50% failure rate (they get smashed).

### The "Shield" Hypothesis
**Claim:** "Fractal Zones touched only at T1/T2 (never T3) act as 'Hard Shields' and result in Outlier R-Multiples (>20R)."
**Test:** Segment flows by Max Depth (T1 vs T3).
**Prediction:** T1-Only flows will show significantly higher Mean MFE than T3 flows.

### The "Time Decay" Hypothesis
**Claim:** "Fractal Zones that survive the initial 'Session Shock' (16 Bars) have a >80% probability of reaching 2R."
**Test:** Filter flows by `Duration > 16 Bars`. 
**Prediction:** Win Rate will jump from ~67% (All) to >80% (Survivors).

---

## 5. Implementation Plan (Phase 1 Finalization)

### Step 1: The Probability Engine
We need to calculate and display these possibilities in real-time.
*   `CalculateArrivalProb(target_dist)` -> Returns % chance based on historical CSV data.
*   `IsShieldCandidate()` -> Returns true if currently at T1 with high velocity.

### Step 2: Protocol Selection (Hybrid Mode)
The bot should not choose *one* protocol. It should execute a **Hybrid Portfolio**:
*   **Unit 1 (Shield):** 0.3% Risk @ T1. (Hoping for the 100x).
*   **Unit 2 (Trap):** 0.7% Risk @ T3 Limit. (Banking on the 70% win rate).
*   **Unit 3 (Survivor):** Scale-in if 16 bars pass.

**Verdict:** This blueprint moves from "Setup Trading" to "Probability Engineering."
