# Signal & Execution Layer Architecture
*Sigma Trading System | Syafiq M. Zin | May 2026*

---

## What the Signal Layer Is

The Signal Layer is where the system makes a decision: take the trade, or don't. It sits at the bottom of the stack — after the Context Engine has scored the environment and the Regime Engine has classified the market state. It answers one question: **given the current regime, is there a specific, sized, positioned trade to take right now?**

It does NOT do research. It does NOT assess whether the environment is bullish. That's already done upstream. The Signal Layer consumes outputs, checks conditions, and either fires a fully-specified trade or stays flat.

---

## Six First Principles of Signal & Execution

**1. Signal conditionality — regime gates signal, not the other way around.**
A breakout signal in a ranging regime is not a weak signal. It is a false signal. The regime is not a filter to apply with some weight. It is a hard gate. No regime confirmation = no trade.

**2. Entry is the least important variable.**
What determines outcome: stop placement, target placement, position size, and whether the regime was correct. Entry within ±0.5 ATR of ideal is irrelevant.

**3. Every signal must be falsifiable.**
A signal must have a specific, pre-defined condition that would cause you to exit or reverse. If you cannot write down in advance exactly what would prove the trade wrong, you don't have a trade.

**4. Simplicity is a feature, not a limitation.**
Complex signals degrade in live trading. Every additional condition is a parameter to overfit, a data dependency to fail, a latency to add.

**5. Edge is upstream.**
The signal layer has no edge of its own. The edge lives in the regime detection and context scoring. The signal layer harvests that edge by choosing the right moment to enter.

**6. Output must be five specific numbers.**
Entry price, stop price, target price, position size, and expiry time. If you cannot produce all five, you don't have a signal — you have an opinion.

---

## Three Strategies — Sigma Alpha Engine

### Strategy 1: Sigma Gold Breakout (SAMTC + Regime)
**Type:** Trend-following breakout
**When active:** RE1 = TRENDING BULL or TRENDING BEAR only
**Core logic:** SAMTC multi-timeframe consensus + key level breakout + volume confirmation
**Regime dependency:** Full dependency. GEX positive → no trades regardless of signal.
**Instruments:** XAUUSD (Just Market B Book), GC Futures (Darwinex)

### Strategy 2: Gold-Silver Ratio Mean Reversion
**Type:** Stat arb / mean reversion
**When active:** RE1 = RANGING. Runs when Gold Breakout is paused.
**Core logic:** Gold/Silver ratio z-score. Enter when ratio > +2.0σ or < -2.0σ.

```python
spread = np.log(gold_price) - hedge_ratio * np.log(silver_price)
spread_zscore = (spread - spread.rolling(252).mean()) / spread.rolling(252).std()

if spread_zscore > 2.0:
    signal = "SHORT_GOLD_LONG_SILVER"
elif spread_zscore < -2.0:
    signal = "LONG_GOLD_SHORT_SILVER"
elif abs(spread_zscore) < 0.5:
    signal = "EXIT"
```

### Strategy 3: Cross-Sectional Commodity Momentum
**Type:** Momentum / relative value
**When active:** Always-on. Runs independently of gold regime.
**Core logic:** Rank commodity universe (gold, silver, oil, copper, natgas) by 1M and 3M momentum. Long top quintile, short bottom quintile. Monthly rebalance.

---

## Signal Layer Architecture — L4 (Tier C Target)

```python
def generate_signal(regime_probs, cp_prob, context_score, price_data, vol_regime):
    # Hard gates first
    if max(regime_probs) < 0.65:          # Regime conviction gate
        return None
    if cp_prob > 0.70:                     # Transition gate
        return None

    bull_prob, bear_prob, range_prob = regime_probs
    if bull_prob >= 0.65:
        direction = "LONG"
    elif bear_prob >= 0.65:
        direction = "SHORT"
    else:
        return None

    if not check_samtc_multiTF(price_data):
        return None

    if calculate_breakout_strength(price_data) < 1.5:
        return None

    atr = calculate_atr(price_data, period=14)
    entry = price_data['close'].iloc[-1]

    atr_stop_multiplier = {
        "HIGH_EXPANDING": 2.0,
        "HIGH_STABLE": 1.75,
        "LOW_STABLE": 1.5,
        "LOW_COMPRESSING": 1.25
    }[vol_regime]

    stop   = entry - atr * atr_stop_multiplier if direction == "LONG" else entry + atr * atr_stop_multiplier
    target = entry + atr * atr_stop_multiplier * 2.0 if direction == "LONG" else entry - atr * atr_stop_multiplier * 2.0

    conviction      = float(max(regime_probs))
    trans_scalar    = 1.0 - (cp_prob * 0.5)
    vol_scalar      = {"HIGH_EXPANDING": 0.50, "HIGH_STABLE": 0.75,
                       "LOW_STABLE": 1.00, "LOW_COMPRESSING": 1.00}[vol_regime]

    position_risk = BASE_RISK * conviction * trans_scalar * vol_scalar
    size = position_risk * get_account_equity() / abs(entry - stop)

    return {
        "direction": direction, "entry": entry, "stop": stop,
        "target": target, "size": size,
        "position_risk_pct": position_risk, "conviction": conviction,
        "expiry": pd.Timestamp.now() + pd.Timedelta(days=5)
    }
```

Signal accuracy at L4: ~72–78% (regime-conditional). IC on entries: 0.08–0.12.

---

## Execution First Principles

**Hard limits in code:**
```python
MAX_RISK_PER_TRADE       = 0.01   # 1% max
MAX_DAILY_LOSS           = 0.02   # 2% daily loss limit
MAX_PORTFOLIO_DRAWDOWN   = 0.04   # 4% total — full stop
MAX_CORRELATION          = 0.60   # Two concurrent positions max correlation

def pre_execution_check(signal, portfolio_state):
    if signal['position_risk_pct'] > MAX_RISK_PER_TRADE:
        signal['size'] *= MAX_RISK_PER_TRADE / signal['position_risk_pct']
    if portfolio_state['daily_pnl'] < -MAX_DAILY_LOSS:
        return None
    if portfolio_state['drawdown'] < -MAX_PORTFOLIO_DRAWDOWN:
        return None
    return signal
```

**BOCPD circuit breaker:**
```python
if cp_prob > 0.85:
    close_all_positions()
    set_system_state("PAUSED")
    alert("BOCPD circuit breaker triggered — manual review required")
```

---

## Full System Integration

```
Data Layer (FRED, CFTC COT, Polygon, yfinance)
    ↓
Context Engine (CE1-CE4)
    ↓ Context Score (-1 to +1)
    ↓
Regime Engine
    ├── RE1 Trend HMM + BOCPD → P(bull)/P(bear)/P(range) + cp_prob
    ├── RE2 Vol HMM           → vol_regime + stop scalar
    ├── RE3 Correlation       → signal trust weights
    └── RE4 Liquidity         → execution gate
    ↓
Signal Layer
    ├── Check: RE1 conviction ≥ 0.65
    ├── Check: cp_prob < 0.70
    ├── Check: SAMTC multi-TF confirmed
    ├── Check: breakout_strength ≥ 1.5
    └── Output: {entry, stop, target, size, expiry}
    ↓
Pre-Execution Checks
    ↓
Execution
    ├── XAUUSD → MT5 API (Just Market B Book)
    └── GC Futures / GLD / SLV → Darwinex REST API
    ↓
Trade Log → TimescaleDB
```

---

## Build Path

| Phase | Timeline | Work |
|-------|----------|------|
| Validate SAMTC baseline | Weeks 1–2 | Run on XAUUSD historical, measure raw hit rate |
| Add L2 regime gate | Weeks 3–4 | GEX binary filter + real yields gate |
| L3 composite score | Month 2 | Signal scoring, vol-adjusted sizing, paper trade |
| L4 full integration | Month 3 | HMM regime outputs → signal generation → conviction-weighted sizing |
| Live execution | Month 4 | MT5 API + Darwinex REST connected, BOCPD circuit breaker live |
| L5 alpha decay monitoring | Ongoing | Rolling IC per component, auto-disable degrading signals |
