# Session Handover — May 18, 2026 (Morning #2 — MT5 Symlink Fix + Simplicity Strategy Pivot)

## What Was Accomplished This Session

### 1. Strategic Reframe: Simplicity First
Locked in a new principle for the B2B strategy build:
> Master simplicity first — clear entry, clear exit, high PnL, smooth equity curve, low drawdown — with the LEAST complexity possible. Add complexity only after the core signal proves edge.

This reframe changes the build order. IC engine, DuckDB, Context Engine, Regime Engine are all deferred. The question is: **does a raw B2B pioneer zone on H1 have edge on XAUUSD?**

### 2. Full MT5 Codebase Read
Read and understood all key files:
- `Sigma_V5.0.mq5` — orchestrator/framework, 1880 lines
- `TradeSignalGenerator.mqh` — entry logic, Russian Doll + Intraday
- `StrategyOrchestrator.mqh` — 3-gate authorization (Gate1: Direction, Gate2: Location, Gate3: Structure)
- `TradingParameters.mqh` — all input parameters

**Key findings from code read:**
- Only M5 zones fire trades (Russian Doll eval loop only processes M15/M5/M1, H4/H1/M30 Execute flags are wired to nothing)
- `InpEnableIntraday = false` — H1/M30 intraday path never runs
- Exit is trailing stop (450pt start, 250pt step), NOT fixed TP — `InpUseFixedTarget = false`
- Entry is 3-touch allocation: T1=20%/L1, T2=40%/50%, T3=40%/L2
- SL buffer = 350 points beyond L2 (not exactly at L2)
- The 3-gate Orchestrator is extremely restrictive — Gate1 alone kills most trades

### 3. MT5 Fresh Install + Symlink Fix
**Problem:** Old symlinks pointed to `C:\Users\User\Desktop\sigma-mt5\` (removed folder).

**Fix:**
- Uninstalled MT5, deleted old AppData terminal folder
- Reinstalled fresh MT5 under JustMarkets
- Terminal hash: `E7DB6AF1FE93F292652A5D3B98342601` (same — tied to broker server)
- Created new junctions via PowerShell:
  ```
  MQL5\Experts\Sigma_System → sigma-brain\workspace\baysix-engine\sigma-mt5\Experts\Sigma_System
  MQL5\Include\Sigma_System  → sigma-brain\workspace\baysix-engine\sigma-mt5\Include\Sigma_System
  ```
- EA compiled successfully: **0 errors, 0 warnings**, 7286ms, cpu='AVX2 + FMA3'

### 4. Problem Confirmed: No Trades Firing
Ran strategy tester. Zero trades. The 3-gate Orchestrator requires all of:
- MN1/W1/D1 FlowState established with freshness conditions met
- Price not at monthly range extremes
- M5 trigger spatially nested inside fresh H4/H1/M30 zone

All 3 must pass simultaneously. In practice Gate1 kills everything — the HTF narrative rarely establishes cleanly in backtest warm-up.

### 5. Solution Designed: InpSimpleMode Switch
Designed a clean, non-breaking solution:
- **One EA, one set of include files** — no duplication, no confusion
- Add `input bool InpSimpleMode = true` to `TradingParameters.mqh`
- In `TradeSignalGenerator.mqh`: when `InpSimpleMode = true`, bypass Orchestrator entirely
- Simple mode logic: H1 zones only + `zone.is_pioneer == true` + enter at L1 + fixed 2:1 RR (SL=L2, TP=L1+2×zone_range)
- When `InpSimpleMode = false`: full Russian Doll runs unchanged

**This has NOT been written yet.** Design only, no code changes made.

---

## What Is NOT Done / Still Open

- `InpSimpleMode` switch — designed but not coded yet
- Strategy tester run on simple mode — blocked until code is written
- Cleanup of `TradingParameters.mqh` — bloated with unused/legacy parameters
- The `.ex5` compiled binary — needs recompile after any code change
- IC measurement pipeline (`ic_engine.py`) — still fully stubbed, deferred
- Gold H1 OHLCV data — still not in `data/raw/`

---

## Running Processes

None

---

## Priority for Next Session

1. **Write `InpSimpleMode` switch** — two file changes only:
   - `TradingParameters.mqh`: add `input bool InpSimpleMode = true;`
   - `TradeSignalGenerator.mqh`: wrap Orchestrator calls + replace `IsTradeAllowed()` with pioneer check + fixed 2:1 RR in H1 zones only
   - Compile in MT5 (F7), confirm 0 errors

2. **Run strategy tester on simple mode** — XAUUSD, H1 or M5 chart, 1+ year history, fixed lot or 1% risk. Read the equity curve + report tab. Does it produce trades? Is the curve smooth?

3. **Discuss code cleanup** — `TradingParameters.mqh` is bloated. Consider stripping unused parameters. Also discuss whether the `.ex5` strategy approach is the right long-term path vs rebuilding clean.

---

## Key Decisions Made

- **Simplicity first**: prove edge on the simplest possible B2B system before re-adding complexity
- **InpSimpleMode over separate EA**: one codebase, behavior controlled by a toggle — avoids include file confusion
- **H1 as test timeframe**: H1 zones are the structural level manual trading is based on; M5 is noise without backing structure
- **Fixed 2:1 RR**: replaces dynamic Orchestrator TP for the simple mode test
- **MT5 Strategy Tester as the test vehicle**: real tick data, real spreads, native reporting + QuantLogger CSV export fires automatically at end

---

## Architecture Context (Do Not Re-Explain)

```
sigma-brain/
└── workspace/baysix-engine/sigma-mt5/
    ├── Experts/Sigma_System/
    │   └── Sigma_V5.0.mq5          ← main EA (compiled, 0 errors)
    └── Include/Sigma_System/V5.0/
        ├── Configuration/
        │   └── TradingParameters.mqh   ← ADD InpSimpleMode HERE
        └── Trading/
            └── TradeSignalGenerator.mqh ← MODIFY ProcessRussianDollStrategy HERE
```

MT5 MQL5 folder junctions:
```
...\MQL5\Experts\Sigma_System  →  sigma-mt5\Experts\Sigma_System  ✓
...\MQL5\Include\Sigma_System  →  sigma-mt5\Include\Sigma_System  ✓
```

QuantLogger CSV auto-exports to `SIGMA_Quant\Trades\` on backtest end — God Data fields captured per trade (pioneer flag, fractal_depth, touch_count, MAE, MFE, etc.)

---

## Blockers

- None — MT5 is compiled and operational, junctions are clean, design is ready to implement
