# Session Handover — May 18, 2026 (Afternoon — B2B Python Port Phase A)

## Strategic Context

Syafiq pivoted off the MQL5 `InpSimpleMode` plan after deeper code review revealed:

1. **The "pioneer" flag in the master doc is misdescribed.** `B2BConfluence.IsPioneerZone()` only flags entry-TF zones (M1/M5) sitting within 1% of 10-year ATH/ATL with no HTF parent. A "raw H1 pioneer zone" is structurally impossible in the current code.

2. **The current EA cannot fire H1 trades via the Russian Doll path.** `TradeSignalGenerator.ProcessRussianDollStrategy()` hard-codes `eval_tfs[] = {M15, M5, M1}`. H1/H4/M30 zones are only parents/officers — never triggers. The only path that fires H1/M30 entries is `ProcessIntradayStrategy()`, gated off by `InpEnableIntraday = false`.

3. **The 3-gate filter is severely restrictive.** Gate 1 alone has 7 mutually exclusive trade types, each requiring a valid Origin→Outpost→Magnet chain on MN1/W1/D1. In a 1-year backtest warm-up these rarely establish cleanly. Gate 1 does ~90% of the rejection; Gate 3 nesting is nearly decorative.

**Decision:** Stop iterating MQL5 blind. Test the raw B2B signal in Python on the 10-year H1 CSV, separated from the gates. Then rewrite MQL5 around whatever conditioners actually add IC.

## Data Asset

H1 OHLCV CSV from Dukascopy XAUUSD (10 years):
- Path: `workspace/baysix-engine/quant-data-manager/dukas-copy/2026.5.18XAUUSD(2)-H1-No Session.csv`
- Also at: `workspace/baysix-engine/brokers/high-leverage-broker/2026.5.18XAUUSD(2)-H1-No Session.csv`
- 59,125 H1 bars, 2016-05-18 → 2026-05-17
- Columns: `Date,Time,Open,High,Low,Close,Volume`
- Date format `YYYYMMDD`, time `HH:MM:SS`, prices to 3 decimals
- "No Session" = all-hours (no session filter applied)

## Plan: Python B2B Validation, Split Into Two Phases

### Phase A (THIS SESSION) — Detector Parity

Goal: faithful Python equivalent of MQL5 zone detection chain. NO edge measurement yet.

**Folder:** `workspace/baysix-engine/sigma-are/strategies/b2b-gold/h1_test/`
- Sits next to `B2B_STRATEGY_MASTER.md`
- Isolated from SAMTC code under `sigma-are/core/`

**Files to write:**
```
h1_test/
├── README.md
├── requirements.txt              (pandas, numpy, pyarrow, matplotlib)
├── data/
│   └── xauusd_h1.parquet        (built from CSV by ingest.py)
├── src/
│   ├── __init__.py
│   ├── ingest.py                (CSV → parquet, UTC time index)
│   ├── swing_detector.py        (port of SwingPointDetector.mqh)
│   ├── breakout_detector.py     (port of RawBreakoutDetector.mqh)
│   ├── b2b_detector.py          (port of B2BDetector.DetectB2B_5Pointer)
│   └── run_phase_a.py           (runner: ingest → detect → counts + sample plots)
└── reports/
```

**Deliverable:** zone count summary on full H1 history + 3 visual zone plots eyeball-checked against B2B mental model.

### Phase B (NEXT SESSION) — Edge Measurement

1. Port `B2BZoneStatus.mqh` (T0/T1/T2/T3 touch tracking, close-beyond-L2 invalidation)
2. For every L1 touch, compute forward returns at 1h / 4h / 24h
3. Compute hit rate to TP=2R before invalidation
4. Stratify by: aligned-with-D1, fresh-vs-stale, monthly range position
5. Verdict: does raw B2B have edge → rewrite MQL5 simpler, or kill the hypothesis

## Critical Porting Caveats (Documented for Phase B)

1. **Swing detector uses CLOSE prices, not highs/lows.** `IsSwingHigh()` checks middle bar close > all neighbor closes (strict). Port as-is for production parity. If signal has no edge, this could be a knob to flip in a v2 experiment.

2. **5-pointer pattern (SELL example):**
   - P5 = swing LOW BEFORE P1, with price < P2.price (the OLDER deeper barrier)
   - P1 = swing HIGH (after P5)
   - P2 = swing LOW (after P1) ← becomes zone L1 (entry on retest)
   - P3 = swing HIGH (after P2)
   - P4 = first bar after P3 with close < P5.price (breakout confirmation)
   - Zone: L1 = P2.price, L2 = max(P1.price, P3.price) (invalidation)
   - Mirror for BUY (swap HIGH/LOW, < / >, min/max)

3. **Freshness validation:** Pattern is rejected if any new swing forms between P3 and P4 (strict "uninterrupted" rule). Also rejected if any bar between P3 and P4 closes beyond L2 (gap invalidation).

4. **Same-P5 dedup:** When multiple candidates share P5, keep the one with the NEWEST P1 (highest p1_idx).

5. **In MQL5 CCircularBuffer `swings.Get()`, higher index = NEWER in time.** (The code header comment says the opposite — it's wrong; the iteration logic confirms higher = newer.)

## Architecture Findings (Reference)

- `TradeSignalGenerator.OnTick()` evaluates only M15/M5/M1 zones (`eval_tfs[]` hardcoded line 190)
- `StrategyOrchestrator.IsTradeAllowed()` runs 3 gates: Direction (FlowState), Location (Context), Structure (Tier 2 nesting + freshness)
- `IntradayOrchestrator` is the only path that fires H1/M30 entries (gated off)
- Frozen modules: `SwingPointDetector.mqh` (do not modify per file header)
- Master doc location: `workspace/baysix-engine/sigma-are/strategies/b2b-gold/B2B_STRATEGY_MASTER.md`

## State at Handover Write

- This handover written BEFORE Phase A code is committed (insurance against context max-out)
- Folder not yet created
- No Python files written yet
- Next action after this handover: TodoWrite shows Phase A tasks; agent will create folder structure and begin writing `ingest.py`, `swing_detector.py`, `breakout_detector.py`, `b2b_detector.py`, `run_phase_a.py` in that order
- Then execute the runner to validate zone counts and plot samples

## If Context Maxes Out Mid-Phase A

Continue from wherever the last file got committed. The port order is intentional (swing → breakout → 5-pointer → runner) because each depends on the previous. The MQL5 source files to consult are:
- `workspace/baysix-engine/sigma-mt5/Include/Sigma_System/V5.0/Detection/SwingPointDetector.mqh`
- `workspace/baysix-engine/sigma-mt5/Include/Sigma_System/V5.0/Detection/RawBreakoutDetector.mqh`
- `workspace/baysix-engine/sigma-mt5/Include/Sigma_System/V5.0/Detection/B2BDetector.mqh` (DetectB2B_5Pointer + CreateZoneFrom5Pointer)

All porting decisions are documented in the "Critical Porting Caveats" section above. Do not re-derive — just port.

## Priority for Next Session (Phase B)

ONLY IF Phase A is complete and zone counts look sane (rule of thumb: H1 should produce roughly 50-200 zones per year, mixed BUY/SELL). If Phase A produces zero or absurdly many zones, debug the port before Phase B.

## Blockers

None. Data is available, MQL5 source has been fully read, plan is locked.
