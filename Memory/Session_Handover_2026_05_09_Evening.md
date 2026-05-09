# Session Handover — May 9, 2026 (Evening — LEAN CLI locked as sole backtesting engine)

## What Was Accomplished This Session

### 1. Full Strategy & Backtest Engine Architecture Discussion
Spent the full session debating backtesting engine options from first principles. Covered:
- Current state: custom Python `VectorizedBacktester` (sigma-crypto/) + partial LEAN CLI setup (sigma-lean/)
- Evaluated: LEAN CLI, Nautilus Trader, VectorBT, Backtrader, Lumibot, custom Python
- Key discovery: custom Python engine is NOT peer-reviewed, has no test suite, cannot be defended institutionally
- Key discovery: LEAN CLI enforces correct bar timing, fill simulation, slippage/commission by design

### 2. LEAN CLI Confirmed as ONLY Backtesting Framework
**Decision: LEAN CLI is the sole engine. Custom Python VectorizedBacktester is archived.**

Rationale:
- Peer-reviewed, open source (Apache 2.0), maintained by QuantConnect (company, not solo dev)
- Enforces no look-ahead bias structurally — signal on bar close, fill on next bar open
- Supports tick data, multi-timeframe Consolidators, slippage/commission models out of the box
- Multi-asset native: US equities, ETF, COMEX futures, crypto
- Generates HTML backtest report automatically (equity curve, drawdown, monthly heatmap, trade log)
- Free forever for local backtesting. Docker required (already installed and working).
- sigma-lean/ already 30% set up: lean.json configured, B2BZoneStrategy with sigma_core wired, one BTCUSDT H1 run completed (2026-04-15)

### 3. Institutional-Grade Validation Gate Defined
Every strategy must pass before live demo deployment:
- Max Drawdown < 10%
- Sharpe Ratio > 2.0 (note: may need to revisit threshold for crypto — 1.0+ more realistic there)
- IS and OOS both pass independently (two separate `lean backtest` runs with different date ranges)
- 3x Monte Carlo all pass:
  1. Trade Shuffle (random reorder, N=10,000 paths)
  2. Parametric (fit return distribution, simulate N=10,000 equity paths)
  3. Block Bootstrap (resample actual returns in blocks, CI on Sharpe/DD)
- Existing `sigma-crypto/scripts/monte_carlo_validation.py` can be reused — just feed LEAN's trade log output

### 4. Live Demo Platform Stack Confirmed
| Platform | Markets | Purpose |
|----------|---------|---------|
| IBKR Paper Account | ETF (SPY, QQQ, GLD, TLT, EEM) + GC Futures | Primary institutional showcase |
| MT5 Demo (Just Markets) | XAUUSD + FCPO | Already set up, continue using |
| Binance Testnet | Crypto / SAMTC | Crypto demo |
Broker for live capital: TBD after strategy validation passes gate.

### 5. Strategy Roadmap Defined
Target markets: Global ETFs, GC (COMEX Gold Futures), FCPO (Bursa Malaysia), Crypto
Target strategies (from SSRN/arXiv research papers):
1. VWAP — intraday, SPY/QQQ (Kissell & Glantz 2003)
2. Mean Reversion — daily swing, ETF pairs SPY/IWM, GLD/SLV (Avellaneda & Lee 2010)
3. Trend Following — weekly swing, ETF/GC/FCPO (Moskowitz, Ooi & Pedersen 2012 — AQR)
4. Orderflow Proxy — intraday, CVD from OHLCV (no L2 data available) (Chordia et al 2002)

SAMTC V7.0 "Alpha Composite" planned after all 4 strategies validated.

### 6. Plan File Updated
Full detailed build plan written to:
`C:\Users\User\.claude\plans\ok-buddy-lets-refresh-floofy-teacup.md`

---

## What Is NOT Done / Still Open

- **SAMTC port into LEAN** — not started. sigma-lean/B2BZoneStrategy/ has B2B detection (sigma_core wired) but FlowState machine, Storyline Latches, Siege Detection, Gate A/B/C are not ported. This is Step 1 of the build order.
- **Cross-validation** — need to re-run SAMTC in LEAN on same period (IS 2020-2022, OOS 2023-2025) to verify custom engine's Sharpe 1.16 was real, not a bug.
- **VWAP, MR, TF, Orderflow strategies** — not started. Steps 2-5 of build order.
- **FCPO data sourcing** — no data access yet. Try Yahoo Finance `FCPO.KL` first (free EOD).
- **IBKR Paper Account** — not set up. Syafiq needs to register (free, instant paper trading).
- **Live demo equity curve panel** — sigma-quant app has no live performance UI yet. Future task.
- **Workspace cleanup** — root directory has 10+ loose `micro-*.png` and `micro-*.md` debug artifacts from MICRO terminal session. Needs cleanup before new dev work.

---

## Running Processes

None

---

## Priority for Next Session

1. **Workspace cleanup first** — delete loose files from sigma-brain root:
   - Safe to delete: `micro-*.png`, `micro-*.md`, `pip_output.txt`, `outputs/`
   - Do NOT touch: `workspace/`, `Memory/`, `.claude/`, `vault/`, `Braindump/`
   - Git status shows all these as untracked (`??`) — safe to remove

2. **Begin SAMTC port into LEAN** — starting point is `workspace/sigma-lean/B2BZoneStrategy/backtests/2026-04-15_09-58-29/code/main.py`
   - sigma_core B2B detection already imported and working in that file
   - Need to add: FlowState class, Storyline Latches, Siege Detection, Gate A/B/C logic
   - Reference implementation: `workspace/sigma-crypto/core/strategy/orchestrator.py` (Gate logic) and `workspace/sigma-crypto/core/strategy/engines/state_manager.py` (FlowState)

3. **Run cross-validation backtest** — once SAMTC ported:
   - `lean backtest "B2BZoneStrategy"` for IS period (2020-2022)
   - `lean backtest "B2BZoneStrategy"` for OOS period (2023-2025)
   - Compare Sharpe vs custom engine result of 1.16
   - Run 3x Monte Carlo on LEAN output via `sigma-crypto/scripts/monte_carlo_validation.py`

---

## Key Decisions Made

- **LEAN CLI only**: Custom Python VectorizedBacktester archived. LEAN is the single source of truth for all future backtests across all asset classes and strategies.
- **Institutional validation gate**: Sharpe > 2.0, DD < 10%, 3x Monte Carlo — no strategy goes to live demo without passing all three.
- **IBKR Paper as primary showcase**: Most institutional credibility for job applications. MT5 Demo stays for XAUUSD/FCPO.
- **No Nautilus Trader**: Dropped — no L2 order book data available, so its main advantage is irrelevant.
- **No VectorBT**: Dropped — SAMTC's stateful multi-TF machine doesn't fit vectorized paradigm.
- **Monte Carlo on LEAN output**: Reuse existing `sigma-crypto/scripts/monte_carlo_validation.py` — feed it LEAN's trade log CSV instead of custom engine output.
- **Orderflow = volume proxy**: No L2 data → CVD approximation from OHLCV bars. True orderflow deferred until L2 data access is resolved.

---

## Blockers

- **IBKR Paper Account**: Syafiq needs to register at interactivebrokers.com (free, no minimum for paper). Blocks live demo wiring (Step 8).
- **FCPO data**: No data source confirmed yet. Yahoo Finance `FCPO.KL` to be tested first. Blocks Trend Following strategy on FCPO.
- **SAMTC Sharpe gate**: Current OOS result is Sharpe 1.16 — below the 2.0 gate. Either the gate threshold needs adjusting for crypto (likely) or SAMTC needs parameter work. Decision needed after cross-validation in LEAN.
