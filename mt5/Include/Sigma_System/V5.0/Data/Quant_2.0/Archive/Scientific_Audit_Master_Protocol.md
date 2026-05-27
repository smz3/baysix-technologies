# Scientific Audit Master Protocol (Quant 2.0 Field Theory)

**Version:** 3.0 (Unified Physics Engine)
**Status:** PROPOSED
**Purpose:** Defines the rigorous scientific standards for the Quant 2.0 "B2B Field Theory" strategy. This document serves as the "Source of Truth" for validation.

---

## 🔬 Core Philosophy: The Structural Field
Market price action is not random; it functions as a **Structural Field** that evolves through a quantifiable lifecycle.
*   **Memory:** The market has finite memory.
*   **LIFO (Last In, First Out):** Stable trends respect the most recent structure.
*   **FIFO (First In, First Out):** Unstable trends collapse to the origin.

---

## 🟢 Phase 1: Field & Lifecycle (The Map)
**Scientific Question:** Does the market respect "Recent Structure" (LIFO) more during specific phases of a trend?

### The Hypothesis ($H_{lifecycle}$)
The stability of the LIFO Field follows an inverted-U curve relative to the **Sequence Index ($N_{seq}$)**:
1.  **Probe ($N=1$):** High Variance. Field is forming. Low LIFO reliability.
2.  **Flow ($N=2,3$):** **The Sweet Spot.** Maximum LIFO stability.
3.  **Decay ($N \ge 4$):** Degrading stability. High probability of FIFO reset.

### Validation Metrics
*   **Sequence Index Tagging:** Every trade must be tagged with its $N_{seq}$ in the current trend.
*   **LIFO Rate:** % of Pullbacks that hold the *Most Recent* Zone vs crashing to Origin.
*   **Target:** LIFO Rate > 60% for $N \in \{2,3\}$.

---

## 🔵 Phase 2: Resolution (Zone Refinement)
**Scientific Question:** Can we increase Reward:Risk without sacrificing Win Rate by refining Macro Zones?

### The Hypothesis ($H_{refinement}$)
"True" structure is strictly defined. Large H1 Zones (>25 pips) are often vague containers. The "True Field" is defined by the **M15/M30 structure** nested *inside* the H1 Zone.

### Validation Metrics
*   **Refinement Factor:** Width(H1) / Width(Refined).
*   **Sharpness Gauge:** Compare Risk:Reward of Raw H1 vs Refined M15.
*   **Containment:** % of touches that respect the Refined Zone boundaries.

---

## 🟣 Phase 3: Interaction (Fractal Resonance)
**Scientific Question:** Does waiting for a Micro-Structure ($Z_{micro}$) inside the Macro-Zone reduce Drawdown?

### The Hypothesis ($H_{resonance}$)
Entry into the Field is best confirmed by **Fractal Resonance**—a confirmed M1/M5 B2B Zone forming *inside* the Refined Macro Field.

### Validation Metrics
*   **MAE Delta:** MAE(Blind Entry) - MAE(Fractal Entry).
*   **Lag Cost:** Does the improved Win Rate/MAE offset the worse Entry Price?

---

## 🟡 Phase 4: Vacuum Validation (Vector Vacuum)
**Scientific Question:** Is there enough "room to run" before the next structural obstacle?

### The Hypothesis ($H_{vacuum}$)
Entries with a **Compressed Vector** (Reward:Risk < 2.0) have negative expectancy, regardless of zone quality. Buying into a ceiling invalidates the Field.

### Validation Metrics
*   **Vacuum Distance ($V_{vac}$):** Pips from Entry (A) to Obstacle (B).
*   **GPS Score:** $V_{vac} / \text{Risk}_{pips}$.
*   **Filter Efficacy:** Compare Expectancy of $GPS \ge 2.0$ vs $GPS < 2.0$.

---

## 🔄 The Quant Loop
1.  **Tag:** Process history to apply $N_{seq}$ and $T_{type}$ tags.
2.  **Map:** Visualize the Lifecycle Curve (Win Rate vs $N_{seq}$).
3.  **Refine:** Optimize Zone Coordinates.
4.  **Vacuum:** Filter out "No-Go" vectors ($GPS < 2.0$).
5.  **Execute:** Trade the "Flow" ($N=2,3$) with Max Risk, "Probe" ($N=1$) with Min Risk.
