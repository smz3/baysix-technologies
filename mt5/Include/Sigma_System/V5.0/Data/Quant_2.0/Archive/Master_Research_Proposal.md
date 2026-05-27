# **Quantitative Research Proposal: Structural Memory, Field Dynamics & Trend Lifecycle**

Date: January 14, 2026  
Researcher Role: Lead Quant  
Subject: Algorithmic Validation of "B2B" (Breakout-to-Breakout) Zones

## **1\. Abstract**

This study formalizes the "B2B" trading strategy by synthesizing **Field Theory** (Physics of Market Memory) with **Trend Lifecycle Dynamics** (Temporal Evolution). We challenge the random walk hypothesis by proposing that price action is governed by specific memory structures (LIFO vs. FIFO) that evolve through distinct phases of stability (Probe, Flow, Decay). This logic is **Scale Invariant**, applying recursively from MN1 down to M1. This research aims to mathematically validate the "Sweet Spot" for risk allocation and the optimal entry mechanism via Fractal Resonance.

## **2\. The Unified Thesis**

**Market price action functions as a 'Structural Field' that evolves through a quantifiable lifecycle.**

1. **The Mechanism (Field Theory):** The market possesses finite memory. In stable trends, it respects the most recent structure (**LIFO** \- *Last In, First Out*). In unstable trends, it collapses to the origin (**FIFO** \- *First In, First Out*).  
2. **The Evolution (Lifecycle):** The stability of this LIFO Field is not constant. It follows an inverted-U curve:  
   * **Phase 1 \- The Probe (**$N=1$**):** High variance as the new field is established. (Requires "Probe" Risk).  
   * **Phase 2 \- The Flow (**$N=2..3$**):** Maximum LIFO stability. The "Sweet Spot" for trend continuation. (Requires "Max" Risk).  
   * **Phase 3 \- The Decay (**$N\>4$**):** Stability degrades as the field stretches. High probability of FIFO reset.  
3. **The Resolution (Zone Refinement):** H1 Zones are often too broad. We postulate that the "True Field" is defined by the M15/M30 structure nested *inside* the H1 Zone.  
4. **The Spark (Fractal Resonance):** Entry into the Field is best confirmed not by blind limit orders, but by **Fractal Resonance** ($Z\_{micro}$) forming inside $Z\_{macro}$.

## **3\. Definitions & Standardization**

| Symbol | Concept | Definition |
| :---- | :---- | :---- |
| $N\_{seq}$ | **Sequence Index** | The count of the B2B Zone in the current trend (1st, 2nd, 3rd...). |
| $Z\_{macro}$ | **Macro Field** | The H1/H4 B2B Zone acting as the primary container. |
| $Z\_{refined}$ | **Refined Field** | The M15/M30 Zone found *inside* the Macro Field to reduce risk. |
| $Z\_{micro}$ | **Fractal Spark** | A confirmed M1/M5 B2B Zone forming *inside* $Z\_{macro}$. |
| $T\_{type}$ | **Memory Type** | **LIFO** (Respects Recent Zone) vs. **FIFO** (Crashes to Origin). |

## **4\. The Hypothesis Matrix**

### **4.1 Primary Hypothesis: Field Memory ($H\_1$)**

*Conditional on a sequence of* $N\_{seq} \\ge 2$*, there is a statistically significant (\>60%) probability that price will respect the most recent zone (*$Z\_{-1}$*), validating the **Pullback** strategy over the **Reversal** strategy.*

### **4.2 Secondary Hypothesis: Lifecycle Stability ($H\_2$)**

*The Win Rate of B2B Zones is correlated to* $N\_{seq}$*. We hypothesize lower stability at* $N=1$ *(Probe), peak stability at* $N=2,3$ *(Flow), and declining stability at* $N \\ge 4$ *(Decay).*

### **4.3 Tertiary Hypothesis: Zone Refinement ($H\_3$)**

*Large H1 Zones (\>25 pips) yield a lower Risk:Reward ratio. By refining coordinates to the "Origin" M15 Zone nested inside the H1 Zone, we can maintain the same Win Rate while increasing the Reward/Risk ratio by \>1.5x.*

### 4.4 Quaternary Hypothesis: Fractal Resonance ($H_4$)

*Entries taken only after a Micro-Structure ($Z_{micro}$) forms inside a Macro-Zone yield a significantly higher Sharpe Ratio due to reduced Drawdown (MAE) compared to blind limit orders.*

### 4.5 Quinary Hypothesis: Global Gravity ($H_{bias}$)

*The Win Rate of execution layers (H1/H4) is significantly correlated to the Field State of Global Layers (D1/W1). We hypothesize that H1 "Sweet Spots" ($N=2,3$) fail more frequently when opposing a W1 "Flow" ($N=2,3$).*

## **5\. Validation Hierarchy (The Execution Plan)**

### **Phase 1: Validate the Field & Lifecycle (The Map)**

**Objective:** Map the LIFO/FIFO probability relative to the Sequence Number.

* **The Experiment:** Query all trades grouped by Sequence\_Index.  
* **The Question:** "Does the LIFO (Pullback) probability peak at Sequence \#2 and \#3?"  
* **Strategic Outcome:** If proven, this dictates our **Dynamic Risk Scaling** (0.5% on Probe, 2.0% on Flow).

### **Phase 2: Validate the Resolution (Refinement)**

**Objective:** Confirm that shrinking H1 zones to M15 doesn't cause us to miss trades.

* **The Experiment:** Compare outcome of "Raw H1" vs "Refined M15" coordinates.  
* **The Question:** "Does price touch the M15 core, or just skim the H1 edge?"

### **Phase 3: Validate the Interaction (Fractal)**

**Objective:** Confirm the entry timing.

* **The Experiment:** Compare "Blind Entry" vs "Fractal Entry" MAE.

## **6\. Required Visualizations (Webapp)**

1. **The Lifecycle Curve:**  
   * **X-Axis:** Sequence Index ($N=1$ to $N=5$).  
   * **Y-Axis:** Win Rate (Bar) & LIFO Probability (Line).  
   * *Insight:* Visualizes the "Sweet Spot" of the trend.  
2. **The Sharpness Gauge (Box Plot):**  
   * **Compare:** H1 Risk:Reward vs. M15 Refined Risk:Reward.  
   * *Insight:* Proves the value of "Refining."  
3. **The Memory Heatmap:**  
   * **X-Axis:** Sequence Count.  
   * **Y-Axis:** Landing Zone (Recent vs Origin).  
   * *Insight:* Visualizes the strength of the Field.

## **7\. Implementation Checklist**

* \[ \] **Python (Field Engine):** Implement calculate\_sequence\_index() (Tag $N\_{seq}$ and $T\_{type}$).  
* \[ \] **Python (Refiner Engine):** Implement refine\_h1\_with\_m15() (Scan M15 inside H1).  
* \[ \] **Python (Fractal Engine):** Connect H1 Zones to M5 Data to detect has\_micro\_confirmation.  
* \[ \] **Supabase:** Run SQL to find the Win Rate per Sequence and LIFO probability.  
* \[ \] **Webapp:** Plot the Lifecycle Curve.