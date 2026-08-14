# Post-Mortem: Gamma 1.2 "The Opposing Wall" Failure

**Status:** FAILED (System Degradation)
**Comparison:** Gamma 1.1 (SQN 3.21) -> Gamma 1.2 (SQN 2.29)

## 1. Executive Summary
The attempt to fix the "Gamma Paradox" (High Win Rate / Low R:R) by targeting the **Opposing Zone** was a mathematical failure. While the theory of "Targeting the Ceiling/Floor" works for Swing trading, it failed for our M15 Momentum/Reversion engine.

## 2. Statistical Breakdown
| Metric                     | Gamma 1.1 (Entry Target) | Gamma 1.2 (Opposing Target) | Change   |
| -------------------------- | ------------------------ | --------------------------- | -------- |
| **Total Net PnL**          | $323.67                  | $193.47                     | **-40%** |
| **SQN**                    | 3.21 (Excellent)         | 2.29 (Good/Average)         | **-28%** |
| **Gamma Win Rate**         | 85.45%                   | 52.36%                      | **-33%** |
| **Profit Factor**          | 1.17                     | 1.11                        | **-5%**  |
| **Max Consecutive Losses** | 26                       | 26                          | No Change|

## 3. Why It Failed: "Physics of the Bounce"
*   **The Trap:** By aiming for an H4/Daily opposing zone, we forced the trade to stay open too long.
*   **The Reversion Reality:** A reversion (Gamma) trade is a reaction to an over-extension. The price "bounces" but doesn't necessarily "reverse trend". 
*   **The Result:** Trades that were in profit in Gamma 1.1 (using the tighter exit) were held in Gamma 1.2 until they retraced and hit the full stop loss. This turned our 85% Win Rate engine into a 52% coin-toss.

## 4. Immediate Rationale for Reversion
The data proves that **Gamma 1.1 (the "Catch and Release" model) is the stable base.** Even with a low R:R, the high win rate (85%) and high SQN (3.2) make it a professional-grade system. 

We will not chase 2.0 R:R by expanding targets again. Any improvement to R:R must come from **SL Tightening** or **Volatility-Based Trailing**, not from extending Take Profit into "Hope Territory".

## 5. Status of Fix
1.  **REVERTED:** Dynamic TP for Gamma trades has been removed.
2.  **RETAINED:** `InpTargetMinAge = 20` (Safety Gate).
3.  **RETAINED:** M5 Speed Optimization.

**Verdict:** System restored to Gamma 1.1 Stability. Requesting re-compilation and verification.
