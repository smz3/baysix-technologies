# SIGMA Quant 2.0: Universal Audit Report (V3)
**Date:** 2026-01-19 09:56
**Thesis:** Time-Invariant Physics & Temporal Integrity Verification.

**Note:** Filtered to Valid Sessions Only (Removed NaN Garbage Data).


### 1. Touch Efficiency (Win Depth)
| depth_class   | Win Rate | Expectancy | Velocity (Pips/Min) | Count |
| ---           | ---      | ---        | ---                 | ---   |
| Deep (T3)     | 35.3%    | 26.50R     | 0.05                | 232   |
| Mid (T2)      | 48.3%    | 11.81R     | 0.06                | 205   |
| Shallow (T1)  | 42.1%    | 9.80R      | 10.53               | 668   |



### 2. Structural Integrity (Fractal vs Orphan)
| has_htf_alignment   | Win Rate | Expectancy | Velocity (Pips/Min) | Count |
| ---                 | ---      | ---        | ---                 | ---   |
| False               | 36.8%    | 6.31R      | 0.80                | 565   |
| True                | 47.0%    | 21.39R     | 0.30                | 540   |



### 3. Market Regime (Trend Alignment)
| trend_alignment   | Win Rate | Expectancy | Velocity (Pips/Min) | Count |
| ---               | ---      | ---        | ---                 | ---   |
| Counter Trend     | 5.3%     | 61.09R     | 0.05                | 19    |
| Neutral           | 30.9%    | 5.57R      | 0.79                | 421   |
| With Trend        | 49.8%    | 17.46R     | 0.42                | 665   |



### 4. Context Matrix (Session x Direction)
| session_at_touch      | direction | Win Rate | Expectancy | Velocity (Pips/Min) | Count |
| ---                   | ---       | ---      | ---        | ---                 | ---   |
| ASIAN                 | BUY       | 31.0%    | 29.69R     | 0.09                | 116   |
| ASIAN                 | SELL      | 42.3%    | 11.34R     | 0.40                | 111   |
| LONDON                | BUY       | 32.0%    | 20.04R     | 0.36                | 100   |
| LONDON                | SELL      | 39.6%    | 7.69R      | 0.25                | 96    |
| NY                    | BUY       | 47.9%    | 13.62R     | 1.48                | 190   |
| NY                    | SELL      | 44.7%    | 7.91R      | 2.54                | 170   |
| OFF_HOURS             | BUY       | 34.8%    | 11.09R     | 7.25                | 23    |
| OFF_HOURS             | SELL      | 45.2%    | 7.89R      | 7.41                | 31    |
| OVERLAP               | BUY       | 42.0%    | 14.24R     | 0.46                | 131   |
| OVERLAP               | SELL      | 47.4%    | 10.01R     | 0.68                | 137   |



### 5. Deployment Matrix (Session x Age)
| session_at_touch      | age_bucket     | Win Rate | Expectancy | Velocity (Pips/Min) | Count |
| ---                   | ---            | ---      | ---        | ---                 | ---   |
| ASIAN                 | Legend (>1w)   | 43.8%    | 31.62R     | 82.86               | 48    |
| ASIAN                 | Prime (4-24h)  | 26.4%    | 17.41R     | 0.12                | 72    |
| ASIAN                 | Swing (1-7d)   | 40.9%    | 16.56R     | 0.09                | 66    |
| ASIAN                 | Toxic (<4h)    | 39.0%    | 20.45R     | 0.17                | 41    |
| LONDON                | Legend (>1w)   | 44.1%    | 25.41R     | 5.44                | 34    |
| LONDON                | Prime (4-24h)  | 41.3%    | 14.25R     | 0.27                | 63    |
| LONDON                | Swing (1-7d)   | 23.3%    | 8.08R      | 0.80                | 43    |
| LONDON                | Toxic (<4h)    | 33.9%    | 11.29R     | 0.21                | 56    |
| NY                    | Legend (>1w)   | 56.0%    | 14.81R     | 429.65              | 91    |
| NY                    | Prime (4-24h)  | 41.5%    | 9.57R      | 0.29                | 118   |
| NY                    | Swing (1-7d)   | 45.0%    | 10.38R     | 1.49                | 80    |
| NY                    | Toxic (<4h)    | 43.7%    | 8.81R      | 0.49                | 71    |
| OFF_HOURS             | Legend (>1w)   | 57.1%    | 18.04R     | 472.65              | 14    |
| OFF_HOURS             | Prime (4-24h)  | 31.2%    | 4.59R      | 2.19                | 16    |
| OFF_HOURS             | Swing (1-7d)   | 43.8%    | 8.26R      | 32.30               | 16    |
| OFF_HOURS             | Toxic (<4h)    | 25.0%    | 5.17R      | 0.70                | 8     |
| OVERLAP               | Legend (>1w)   | 62.2%    | 20.10R     | 6.70                | 45    |
| OVERLAP               | Prime (4-24h)  | 41.0%    | 8.34R      | 0.49                | 100   |
| OVERLAP               | Swing (1-7d)   | 40.3%    | 6.34R      | 0.68                | 67    |
| OVERLAP               | Toxic (<4h)    | 42.9%    | 19.20R     | 0.30                | 56    |



### 6. Timeframe Performance
| tf         | Win Rate | Expectancy | Velocity (Pips/Min) | Count |
| ---        | ---      | ---        | ---                 | ---   |
| PERIOD_D1  | 27.0%    | 8.26R      | 0.25                | 126   |
| PERIOD_H1  | 47.5%    | 19.88R     | 0.58                | 501   |
| PERIOD_H4  | 41.0%    | 8.58R      | 0.53                | 454   |
| PERIOD_MN1 | 20.0%    | 3.05R      | 0.03                | 5     |
| PERIOD_W1  | 15.8%    | 10.84R     | 0.06                | 19    |



### 7. Fractal Source (TF x Trend Alignment)
| tf         | trend_alignment   | Win Rate | Expectancy | Velocity (Pips/Min) | Count |
| ---        | ---               | ---      | ---        | ---                 | ---   |
| PERIOD_D1  | Neutral           | 27.0%    | 8.26R      | 0.25                | 126   |
| PERIOD_H1  | Counter Trend     | 9.1%     | 87.61R     | 0.05                | 11    |
| PERIOD_H1  | Neutral           | 35.3%    | 4.25R      | 2.04                | 85    |
| PERIOD_H1  | With Trend        | 51.1%    | 21.31R     | 0.44                | 405   |
| PERIOD_H4  | Counter Trend     | 0.0%     | 24.62R     | 0.04                | 8     |
| PERIOD_H4  | Neutral           | 33.3%    | 3.88R      | 1.12                | 186   |
| PERIOD_H4  | With Trend        | 47.7%    | 11.45R     | 0.35                | 260   |
| PERIOD_MN1 | Neutral           | 20.0%    | 3.05R      | 0.03                | 5     |
| PERIOD_W1  | Neutral           | 15.8%    | 10.84R     | 0.06                | 19    |



### 8. Sequence Efficiency (Fresh vs Retest)
| sequence_index | Win Rate | Expectancy | Velocity (Pips/Min) | Count |
| ---            | ---      | ---        | ---                 | ---   |
| 0              | 41.8%    | 13.68R     | 0.51                | 1105  |

