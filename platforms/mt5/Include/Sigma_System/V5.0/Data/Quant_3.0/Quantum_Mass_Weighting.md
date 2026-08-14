# SIGMA Quant 3.0: Quantum Mass Weighting Protocol

## Overview
The **Quantum Mass Weighting** protocol replaces the legacy 1:1 voting system (where every timeframe had an equal vote) with a **Mass-Weighted Consensus**. This ensures that the Expert Advisor (EA) responds to structural liquidity rather than fractal noise.

---

## 1. The Weighting Hierarchy (N1 - N4)
Each layer of the SIGMA Russian Doll is assigned a "Mass" value based on its structural significance.

| Layer | Component | Weight | Logic |
| :--- | :--- | :--- | :--- |
| **N1** | MN1 (The Master) | **10.0** | The absolute structural floor. |
| | W1 (The Tide) | **6.0** | The dominant weekly flow. |
| **N2** | D1 (The Wind) | **4.0** | Daily momentum vector. |
| **N3** | H4 (The Trap) | **3.0** | Major intraday authorization level. |
| | H1 (The Trap) | **2.0** | Intermediate authorization. |
| | M30 (The Trap) | **1.0** | Minor authorization. |
| **N4** | M15 / M5 | **1.0** | Execution noise (Trigger). |
| | M1 | **0.0** | Pure volatility (Ignored). |

---

## 2. Calculation Logic
The **Net Delta** is now a measurement of **Total Weighted Mass** rather than a simple count of timeframes.

$$Net\ Delta = \sum (Weights_{Bullish}) - \sum (Weights_{Bearish})$$

### Threshold Interaction (Example: Delta 5)
With the implementation of weighting, the `InpNetDeltaThreshold = 5` becomes a strict hierarchy filter:

*   **MN1 Dominance**: If the Monthly chart aligns (+10), the trade is **immediately authorized**. The master context rules.
*   **Collaborative Context**: If MN1 is flat, authorization now requires **W1 (6)** OR a strong cluster like **D1 (4) + H1 (2)**.
*   **Noise Rejection**: M15 and M30 signals (+1 each) can no longer authorize a trade alone. They require at least a Daily or H4 "Anchor" to reach the threshold of 5.

---

## 3. The "Context" Bridge
This protocol acts as a mathematical bridge between **Human Perception** and **Mechanical Execution**:

1.  **Mass Over Quantity**: Humans naturally ignore "choppy" M15 zones if they are fighting a Weekly wall. Quantum Mass codes this "ignoring" behavior.
2.  **Anti-Flipping**: Because the HTF weights are high (5.0), the Net Delta threshold is stable. Minor M5 pullbacks won't flip the consensus, preventing the EA from "chopping" itself out of a trend.
3.  **Low Win-Rate / High Expectancy**: By only authorizing trades where the "Mass" is aligned, we eliminate the low-probability entries that usually drag the win-rate below 30% in high-noise environments (like Gold).

---

## Implementation Reference
- **Source**: `StrategyOrchestrator.mqh`
- **Function**: `CalculateConsensus()`
- **Patch Status**: HARDENED (V17.3)
