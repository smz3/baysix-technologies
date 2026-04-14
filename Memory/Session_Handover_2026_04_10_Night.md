# Session Handover — April 10, 2026 (Night — Kronos BTC Backtest + B2B Direction Pivot)

## What Was Accomplished This Session

### 1. Kronos + Freqtrade BTC/USDT Integration — Built End-to-End

Full deployment stack for Kronos foundation model on BTC/USDT:

| File | Status |
|------|--------|
| `workspace/freqtrade-kronos/strategies/KronosStrategy.py` | Built — Freqtrade IStrategy wrapper around Kronos |
| `workspace/freqtrade-kronos/kronos_backtest.py` | Built — standalone backtester, no exchange dependency |
| `workspace/freqtrade-kronos/config.json` | Built — Bybit dry_run=true, $1000 wallet |
| `workspace/freqtrade-kronos/download_data.py` | Built — yfinance → Freqtrade JSON format |
| `workspace/freqtrade-kronos/README.md` | Built — quickstart guide |

### 2. First Backtest Results (3 samples, 1.5% trailing, Long-only)

```
Capital:       $1000 → $963.62  (-3.64%)
Total Trades:  55
Win Rate:      23.6%
Profit Factor: 0.33
Sharpe:        -5.30
Max Drawdown:  -3.96%
Exit reasons:  trailing_stop=45, stoploss=5, signal_exit=5
```

**Root cause analysis:**
- Trailing stop (1.5%) too tight for BTC hourly noise (~0.5-1.5% normal)
- Long-only in a downtrend: Kronos correctly predicted 2.4× more shorts (540) than longs (228), but we weren't shorting
- BTC range during period: $62,957–$97,585 (Jan–Apr 2026 was declining)

**Key insight:** Kronos IS detecting the downtrend (more short signals). The trade management was the problem, not the model.

### 3. Improved Backtest — Running in Background

Fixed version: 10 MC samples, 2.5% trailing stop, longs + shorts enabled.
- Task ID: `bgxs6x208`
- Started ~22:00, takes ~55 min total
- **Low priority** — user has pivoted away from Freqtrade

---

## Strategic Direction Pivot

**Old direction:** Kronos + Freqtrade for BTC/USDT forecasting
**New direction:** Train Kronos to detect B2B supply/demand zones from raw OHLCV

### Why the Pivot
- Kronos is a financial LLM — should be doing structural pattern recognition, not just price forecasting
- B2B zones are currently detected by rule-based MQL5 code (B2BDetector.mqh)
- Training Kronos on B2B patterns → ML-powered zone detector that can:
  - Detect zones earlier (before the rule-based fires)
  - Score zone quality/freshness without hand-coded thresholds
  - Generalize to any instrument, any exchange (not just MT5/XAUUSD)

---

## What's Needed for Next Session

### Data
- **BTC historical OHLCV**: Binance public data at `https://data.binance.vision/data/spot/monthly/klines/BTCUSDT/{interval}/`
- Start with: H1, H4, D1 (manageable size, rich in B2B patterns)
- All 9 TFs eventually: 1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w, 1M

### Build Queue (workspace/kronos-b2b/)
1. `data/download_btc.py` — Binance kline downloader
2. `data/swing_detector.py` — Python port of SwingPointDetector.mqh
3. `data/b2b_detector.py` — Python port of B2BDetector.mqh (5-pointer pattern)
4. `data/build_dataset.py` — labeled (512-bar window, B2B zone) dataset
5. `embeddings/extract.py` — Kronos tokenizer → feature vectors
6. `train.py` — MLP classifier on Kronos embeddings
7. `validate.py` — ML vs rule-based comparison

### Key Reference
- B2B detection logic: `workspace/sigma-mt5/Include/Sigma_System/V5.0/Detection/B2BDetector.mqh` lines 540-900
- SELL pattern scan: L588 | BUY pattern scan: L675
- Kronos model: `workspace/kronos/model.py`

---

## What Is NOT Done (Deprioritized)

- Freqtrade paper trading setup (built but not run)
- Improved backtest result analysis (still running)
- Validation tab for Backtest Lab (from previous session — still pending)
- Cloud Run deployment for sigma-research (still blocked)

---

## Running Processes

| Task | Status | Notes |
|------|--------|-------|
| Kronos improved backtest (bgxs6x208) | Running | 10 samples, longs+shorts, 2.5% trailing. Low priority. |

---

## Priority for Next Session

1. Build `workspace/kronos-b2b/` scaffold
2. Download BTC H1/H4/D1 from Binance (data.binance.vision)
3. Port MQL5 swing + B2B detection to Python
4. Verify Python detector reproduces MT5 zones on sample XAUUSD data
5. Build labeled training dataset
6. Train Kronos-based zone classifier
