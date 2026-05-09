# Session Handover — April 15, 2026 (Morning — LEAN CLI integration planning complete, Phase 2A ready to execute)

## What Was Accomplished This Session

### 1. LEAN CLI Integration — Full Plan Written and Approved

A complete Phase 2 architecture plan was discussed, researched, and approved by Syafiq for adopting QuantConnect's LEAN CLI as the unified backtesting + live execution framework.

**Plan file:** `C:\Users\User\.claude\plans\snoopy-orbiting-breeze.md`

**Key research done this session:**
- Explored sigma-crypto's current data pipeline: BTCUSDT OHLCV parquet files in `workspace/sigma-crypto/data/raw/`, fetched via CCXT (Binance/Bitget/OKX), backtested via `VectorizedBacktester` (`simulation/engine/vectorized_backtester.py`), entry point `scripts/run_backtest.py`
- Verified LEAN Docker image Python version **directly from the Dockerfile** (`DockerfileLeanFoundation` on GitHub master): **Python 3.11.11** (Miniconda3-py311, `LABEL strict_python_version=3.11.11`)
- Confirmed this is a **hard blocker** — sigma_core .pyd files are compiled for Python 3.13 (cpython-313-win_amd64), which is ABI-incompatible with LEAN's 3.11 runtime

**Decisions locked in:**
| Decision | Choice |
|----------|--------|
| QuantConnect account | ✅ Syafiq has one |
| Docker Desktop | ✅ Already installed |
| Python version fix | **Option A — Recompile sigma_core for Python 3.11** |
| Data pipeline | **Convert existing parquet** (write `parquet_to_lean.py`) |

**Why Option A (not Option C venv shortcut):** LEAN forces Docker for live trading (Binance, IB). Building on `--python-venv` creates technical debt that must be unwound before Phase 2E. Recompiling sigma_core for 3.11 is ~30 min one-time cost.

---

### 2. LEAN Phase Plan — 5 Phases Defined

| Phase | Goal | Sessions |
|-------|------|----------|
| **2A** | sigma_core Cython rebuild (3.11) + LEAN install + stub strategy running in Docker | 1 |
| **2B** | Data pipeline: `parquet_to_lean.py` converts BTCUSDT parquet → LEAN zip format | 1–2 |
| **2C** | Strategy wrapper: SAMTC wrapped as `QCAlgorithm`, sigma_core imported inside LEAN | 1–2 |
| **2D** | Cross-validation: Test 13A re-run in LEAN vs VectorizedBacktester (±15% Sharpe tolerance) | 1 |
| **2E** | Live Binance via LEAN (replaces sigma-crypto execution) — sigma-mt5 stays for XAUUSD | Future |

**Key architecture boundary confirmed:** LEAN does NOT replace sigma-mt5. XAUUSD lives on MT5 until a ZMQ/REST bridge is built (separate Phase 3). LEAN handles crypto (Binance) and eventually IB (equities/futures).

---

## What Is NOT Done / Still Open

- **Phase 2A not yet started** — plan approved this session, implementation not begun. Next session executes Phase 2A.
- **OQ-002 — Cascade invalidation** — decided but not implemented in sigma-mt5 V5.0. Target: `CB2BZoneStatus::UpdateZoneStatus()` in `workspace/sigma-mt5/Include/Sigma_System/V5.0/Detection/B2BZoneStatus.mqh`. Low priority vs LEAN work.
- **OQ-003 — SAMTC slippage test (HYP-001)** — Test 13A uses clean fills. Slippage sweep not run. Script: `workspace/sigma-crypto/scripts/run_phase_4_simulation.py`. Blocks Test 13A CIO approval.
- **sigma-research Cloud Run deployment** — still blocked on org policy issue. See `DEPLOYMENT_HANDOVER.md`. Not touched this session.
- **Vault Phase 3 stubs** — `sigma-crypto-architecture`, `mt5-detection-pipeline`, `hypothesis-board`, `agent-roster`, `kronos-integration` pages still have no content.

---

## Running Processes

None

---

## Priority for Next Session

1. **Execute Phase 2A** — LEAN CLI setup + sigma_core Python 3.11 recompile:
   - Install Python 3.11 alongside existing 3.13 (Python Launcher: `py -3.11`)
   - Recompile: `cd workspace/sigma_core && py -3.11 setup.py build_ext --inplace`
   - `pip install lean` → `lean login` → `lean init workspace/sigma-lean/`
   - Create stub `QCAlgorithm` strategy and run `lean backtest "SAMTCStrategy"` to confirm Docker works
   - Check `workspace/sigma_core/setup.py` exists and is correct for Cython build

2. **Execute Phase 2B** — write `workspace/sigma-lean/scripts/parquet_to_lean.py`:
   - Read `workspace/sigma-crypto/data/raw/BTCUSDT_1h.parquet` (and D1, W1)
   - Convert to LEAN zip format: `data/crypto/binance/hour/btcusdt/YYYYMMDD_quote.zip`
   - LEAN resolution: Hourly (H1) + Daily (D1). LEAN auto-aggregates H4 from H1.

3. **OQ-003 slippage test** (if time permits after Phase 2A/2B) — run `scripts/run_phase_4_simulation.py` with 0bp/5bp/10bp/20bp sweep. This unblocks Test 13A CIO approval.

---

## Key Decisions Made

- **LEAN CLI adopted as Phase 2 framework**: Replaces `VectorizedBacktester` for backtesting; will replace ccxt for Binance live execution in Phase 2E. sigma-mt5 stays live for XAUUSD throughout.
- **sigma_core recompile to Python 3.11**: Not optional — LEAN Docker is locked to 3.11.11. Option B (custom Docker image with 3.13) rejected as too complex. Option C (local venv) rejected as a dead end for live trading.
- **Data strategy = convert existing parquet**: Keeps consistency with existing Test 13A data. Fresh LEAN download would break cross-validation (Phase 2D).
- **No QuantConnect Cloud**: All LEAN work runs local-only (`lean backtest --local`). Cloud mode would require data upload and risk leaking strategy.
- **LEAN for Binance + IB; MT5 stays for XAUUSD**: No MT5 broker adapter in LEAN. MT5 stays live until ZMQ/REST bridge is built in a future Phase 3.

---

## Blockers

- **Python 3.11 not yet installed** — needed before sigma_core Cython rebuild. Install from python.org alongside 3.13 using Python Launcher. First step of Phase 2A.
- **sigma_core setup.py unknown state** — need to verify `workspace/sigma_core/setup.py` exists and is configured for Cython before running the rebuild. Read it at session start.
- **Test 13A CIO approval**: Blocked on OQ-003 slippage test (not yet run).
- **sigma-research Cloud Run**: Still blocked on org policy issue (unchanged).
