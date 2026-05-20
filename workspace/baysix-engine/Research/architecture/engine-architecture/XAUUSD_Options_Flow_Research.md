# XAUUSD — Options Flow & Derivatives Research
*Sigma Trading System | Syafiq M. Zin | May 2026*

---

## What Actually Moves XAUUSD — Priority Order

| Priority | Driver | Mechanism | Data Source |
|----------|--------|-----------|-------------|
| 1 | Real Yields (10Y TIPS) | Gold = f(↓real yields). 70–80% of long-run variance. | FRED `DFII10` |
| 2 | DXY | Gold priced in USD. Strong dollar = global demand falls. Corr: −0.7 to −0.85. | FRED `DTWEXBGS` |
| 3 | COT Managed Money | Sentiment extremes = contrarian signal. | CFTC (free, weekly) |
| 4 | GLD ETF Holdings | Institutional allocation proxy. | SPDR CSV (free, daily, 2004+) |
| 5 | Fed Policy / FOMC | Mechanism: FOMC → rate expectations → real yields → gold. | CME FedWatch |
| 6 | Geopolitical Risk | Episodic safe haven. Sharp but mean-reverting. | Not backtest-able cleanly |
| 7 | Central Bank Buying | Structural floor. China, India, Poland buying post-2022. | WGC quarterly |

**Single best signal to build first:** FRED `DFII10` 3-month change z-score.

---

## The Six Options Flow Signals

### 1. GEX (Net Gamma Exposure) — most important for regime identification

**Positive GEX** = dealers net LONG gamma → **Mean-reverting, rangy. Breakouts fail.**
**Negative GEX** = dealers net SHORT gamma → **Trending, explosive. Breakouts run.**

**For SAMTC:** GEX is the filter on top of breakout signals.
- Positive GEX → skip breakout signals, they'll fail.
- Negative GEX → take breakout signals, conditions support follow-through.

### 2. IV Skew (25-delta risk reversal)
- Positive (calls bid over puts) = institutional upside demand. Bullish signal.
- Negative (puts bid) = downside protection. Bearish or hedging.

### 3. Vanna Flow
- VIX spikes → GLD IV rises → Vanna forces dealer spot buying → gold overshoots.
- VIX normalises → IV falls → Vanna unwind → gold gives back 30–50% over 2–5 days.

### 4. COMEX OI
| OI Change | Price Change | Signal |
|-----------|-------------|--------|
| Rising | Rising | New longs. Strong conviction trend. |
| Rising | Falling | New shorts. Strong conviction downtrend. |
| Falling | Rising | Short covering. Weak rally. |
| Falling | Falling | Long liquidation. Potential bottom. |

### 5. 0DTE (Zero Days to Expiration)
GLD expires weekly (Fridays). Expiration day only — price gravitates toward max pain.

### 6. Options Flow (real-time tape)
Large GLD call sweeps → dealers must buy spot to delta-hedge → gold moves up.
**Best for live trading only. Not backtest-able from EOD snapshots.**

---

## Power Ranking

**Standalone:** GEX > IV Skew > Vanna Flow > COMEX OI > Options Flow > 0DTE

**Best Combinations:**
- GEX + IV Skew — regime + direction. Core combo.
- GEX + Vanna — timing combo. Risk-off gold rallies.
- COMEX OI + GEX — conviction filter. Multi-day trend setups.

---

## Data Sources

### Free — Build Now
| Data | Source | History |
|------|---------|---------|
| Real Yields (10Y TIPS) | FRED `DFII10` | 2003+ |
| Breakeven Inflation | FRED `T10YIE` | 2003+ |
| DXY | FRED `DTWEXBGS` | 1973+ |
| COT Managed Money | CFTC direct download | 1986+ |
| GLD ETF Holdings | SPDR CSV | 2004+ |
| CBOE GVZ (Gold VIX) | Yahoo Finance `^GVZ` | 2008+ |

### Paid — Build Next
| Service | Cost | What You Get |
|---------|------|-------------|
| Polygon.io | ~$79/month | Full GLD options chain. Build GEX, call wall, put wall, max pain. |
| OptionsDX | ~$40/month | Historical chains. Better for deep backtesting. |

---

## Strategy Architecture

```
Layer 0 — SAMTC Signal          Direction (price action, multi-TF)
Layer 1 — GEX Regime            Whether to take the trade
Layer 2 — IV Skew + Term Struct  Conviction level
Layer 3 — Vanna Timing          Post-event fade setups
Layer 4 — COMEX OI              Conviction filter on multi-day directional trades
```

---

## Execution Context

| Broker | Use Case |
|--------|----------|
| Just Market B Book | XAUUSD spot execution |
| Darwinex | GLD ETF, COMEX futures (GC), GDX/GDXJ miners, TLT (rates proxy) |
