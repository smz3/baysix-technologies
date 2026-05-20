# Data Layer Architecture
*Sigma Trading System | Syafiq M. Zin | May 2026*

---

## What a Data Engine Is

Every layer above it — Context Engine, Regime Engine, Signal Layer — assumes it receives clean, valid, correctly-timed data. The Data Engine is the one making that assumption true. It answers one question: **is the data available, valid, correctly timestamped, and in a usable form right now?**

---

## Six First Principles

**1. Bad data is worse than no data.**
A gap in your data is visible — your system can detect it and fall back. Bad data is invisible.

**2. Garbage in, garbage out — but the garbage looks clean.**
The outputs of a system fed bad data are not obviously wrong. They're subtly wrong in ways that only show up in live trading.

**3. Every data source has a latency and a revision risk. Know both.**
FRED publishes DFII10 daily — but it revises. COT data reflects Tuesday positions, releases Friday. If you load "today's FRED data" in a backtest, you may be loading a value that didn't exist yet on that historical date. That's lookahead bias.

**4. Stationarity transformation happens once, at the data layer output.**
Define the canonical transformed form once. Every consumer downstream uses that.

**5. Data has a freshness constraint, not just a value.**
The data layer must track when each data point was last updated and surface a freshness flag alongside the value.

**6. Backtests must be reproducible. That requires point-in-time storage.**
FRED revises historical series. Without point-in-time (as-of) storage, your backtest has lookahead bias baked into the database itself.

---

## Point-in-Time Correct Storage

```python
# Naive (wrong) — stores only current value
CREATE TABLE real_yields (
    date        DATE PRIMARY KEY,
    value       FLOAT
);

# Point-in-time correct (right)
CREATE TABLE real_yields (
    date            DATE,
    value           FLOAT,
    as_of_date      TIMESTAMPTZ,
    is_revised      BOOLEAN,
    PRIMARY KEY (date, as_of_date)
);

# Backtest query: what did real yields look like on 2024-03-01 as of that date?
SELECT value FROM real_yields
WHERE date = '2024-03-01'
  AND as_of_date <= '2024-03-01'
ORDER BY as_of_date DESC
LIMIT 1;
```

| Source | Revision Risk | Priority |
|--------|--------------|----------|
| FRED DFII10 | High — FRED revises series | Critical |
| CFTC COT | Low — rarely revised | Medium |
| GLD ETF holdings | None | Low |
| Polygon options EOD | None (snapshot) | Low |

---

## Four Data Pipelines

### DP1 — Macro & Fundamental
Sources: FRED DFII10 (real yields), FRED DTWEXBGS (DXY), FRED T10YIE (breakevens), CFTC COT, SPDR GLD ETF holdings
Update: Daily (FRED), Weekly (COT)

### DP2 — Market Data
Sources: yfinance (GLD, GC, SLV, TLT, SPX, GDX, DXY)
Update: Daily EOD + intraday 1H/4H

### DP3 — Derived Data
Contents: GEX (Polygon), IV skew, realised vol (10/20/60-day), rolling correlations, z-scores, Hurst exponent, COMEX OI change
Update: Daily EOD — recomputed from DP1 + DP2

### DP4 — Alternative Data (L5 / Future)
Contents: NLP gold news sentiment, central bank speech analysis, satellite mine output, physical gold flow
Status: Build at L5. Not needed for Tier C demo.

---

## Full Data Layer Stack

```
External Sources
    ├── FRED API          → real_yields, DXY, breakevens
    ├── CFTC Direct       → COT CSV (weekly)
    ├── SPDR              → GLD holdings CSV (daily)
    ├── yfinance          → OHLCV: GLD, GC, SLV, TLT, SPX, GDX
    └── Polygon.io        → GLD options chain (daily, ~$79/mo)
    ↓
ETL Layer (Python + APScheduler)
    ├── Fetch → Validate → Transform → Store
    └── Point-in-time as_of_date stamped on every record
    ↓
TimescaleDB
    ├── macro_data        (FRED, COT, GLD holdings)
    ├── market_data       (OHLCV, all instruments)
    ├── derived_data      (GEX, vol, correlations, z-scores, Hurst)
    └── pipeline_runs     (audit log)
    ↓
Data Access Layer
    ├── get_data_as_of()             → point-in-time safe queries
    ├── get_latest_with_freshness()  → live trading + staleness flags
    └── get_backtest_snapshot()      → full dataset for a date range
    ↓
Context Engine (clean, validated, timestamped inputs)
```

---

## Build Path

| Phase | Timeline | Work |
|-------|----------|------|
| L2 → L3 | Weeks 1–2 | TimescaleDB setup. Migrate CSV fetches to automated ETL. |
| L3 stabilisation | Weeks 3–4 | Quality checks passing daily. Backtest pulling from DB. |
| L3 → L4 | Month 2 | Add as_of_date. Point-in-time queries. Staleness flags to Context Engine. |
| L4 → L5 | Month 6+ | Kafka streaming. Alternative data. Vendor redundancy. |

**First thing to build:** Replace manual CSV downloads with a proper DP1 ETL job writing to TimescaleDB.
