# **Research Directives: Metrics & Visualizations**

This document maps the Scientific Phases to specific Database Queries and Frontend Visualizations.

## **Phase 1: The Lifecycle & Risk Curve**

**Hypothesis:** The trend is most stable at Sequence \#2 and \#3 ("The Flow"). Sequence \#1 is risky ("Probe").

* **Metric:** Win Rate & Expectancy per sequence\_index.  
* **Webapp Visualization: The Lifecycle Curve**  
  * **Type:** Bar Chart \+ Line Overlay.  
  * **X-Axis:** Sequence Index (1, 2, 3, 4, 5+).  
  * **Bar:** Win Rate %.  
  * **Line:** Avg. Risk:Reward Ratio.  
  * **Success Criteria:** If Bars 2 & 3 are \> 55%, the "Flow" hypothesis is valid.

## **Phase 2: Field Memory (LIFO vs. FIFO)**

**Hypothesis:** In stable fields, price stops at the recent zone ($Z\_{-1}$). In unstable fields, it crashes to origin ($Z\_{start}$).

* **Metric:** landing\_type (Categorical: 'LIFO\_RESPECT' vs 'FIFO\_RESET').  
* **Webapp Visualization: The Memory Heatmap**  
  * **Type:** 2D Matrix / Heatmap.  
  * **X-Axis:** Sequence Index ($N\_{seq}$).  
  * **Y-Axis:** Landing Outcome (Recent vs. Origin).  
  * **Color Intensity:** Frequency/Count.  
  * **Success Criteria:** Green hotspots in the "Recent" row for $N=2,3$. Red hotspots in "Origin" row for $N=1$.

## **Phase 3: Fractal Resonance (Entry Timing)**

**Hypothesis:** Waiting for an M5 Fractal ($Z\_{micro}$) reduces drawdown compared to Blind Limit Orders.

* **Metric:** Compare MAE\_Blind vs. MAE\_Fractal.  
* **Webapp Visualization: The Fractal Delta Plot**  
  * **Type:** Scatter Plot.  
  * **X-Axis:** Time Lag (Minutes between H1 touch and M5 confirmation).  
  * **Y-Axis:** Trade Outcome (P/L).  
  * **Insight:** "Does waiting \> 30 mins kill the trade?"

## **Phase 4: Zone Refinement (M15 Optimization)**

**Hypothesis:** Refining H1 zones to internal M15 structures improves RR without destroying Win Rate.

* **Metric:** RR\_Improvement\_Factor (Original Width / Refined Width).  
* **Webapp Visualization: The Sharpness Gauge**  
  * **Type:** Box Plot.  
  * **Compare:** Group A (Raw H1 Zone) vs Group B (Refined M15 Zone).  
  * **Metric:** Net Profitability per Trade.

## **Summary of Database Tags Needed**

To power these visuals, the Python Engine must tag every trade with:

1. sequence\_index (int)  
2. lifecycle\_phase (string: 'PROBE', 'FLOW', 'DECAY')  
3. landing\_outcome (string)  
4. is\_refined (boolean)  
5. has\_fractal\_confirm (boolean)