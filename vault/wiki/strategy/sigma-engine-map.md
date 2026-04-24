---
type: wiki
domain: strategy
status: stable
tags:
  - core
  - ip
  - architecture
related:
  - "[[b2b-overview]]"
  - "[[samtc-overview]]"
  - "[[mt5-ea-architecture]]"
  - "[[sigma-crypto-architecture]]"
source_files:
  - "workspace/sigma_core/sigma_core/__init__.py"
  - "workspace/sigma-crypto/core/detectors/b2b_engine.py"
  - "workspace/sigma-mt5/Documentation/modules/INDEX.md"
last_updated: 2026-04-14
maintained_by: ai
ai_summary: "sigma_core (.pyd) is the sealed detection engine shared by sigma-crypto (Python backtesting). sigma-mt5 (MQL5) is a parallel live-trading implementation. Target: Python as single source of truth with MT5 as a dumb execution adapter."
---

# Sigma Engine Map

> This page defines the architecture boundary between the three execution environments and the IP protection boundary. Read this before making any cross-system changes.

---

## The Three Systems

| System | Language | Purpose | Status |
|--------|----------|---------|--------|
| **sigma_core** | Python → Cython (.pyd) | Sealed detection engine — shared library | ✅ Compiled April 1, 2026 |
| **sigma-crypto** | Python | SAMTC backtesting + research | ✅ Active (Test 13A OOS) |
| **sigma-mt5** | MQL5 | Live trading on MetaTrader 5 | ✅ Active (V5.0) |

---

## Current Architecture

```
sigma-crypto (Python)
    ├── core/detectors/     ← Python source (imports sigma_core when available)
    └── imports ──────────► sigma_core (.pyd) ← sealed Cython binary
                                 │
                                 └──► vectorized_backtester.py
                                           │
                                           └──► Backtesting (13A OOS etc.)

sigma-mt5 (MQL5) ──────────────────────────────────────────────────────────────
    └── Sigma_V5.0.mq5  ← self-contained, no Python dependency
         └── 25 .mqh modules (parallel implementation of same B2B logic)
              └──► Live Trading on MetaTrader 5 (Just Markets)
```

**Key insight:** sigma_core and sigma-mt5 implement the **same B2B detection logic** in two different languages. There is no runtime bridge between them — changes must be replicated manually.

---

## Target Architecture (Phase 2)

```
sigma-crypto (Python)   ← Single source of truth for ALL detection logic
     ├──► sigma_core (.pyd)          ← Backtesting (sealed, already working)
     ├──► MT5 Bridge (ZMQ/REST)      ← MT5 becomes a dumb execution adapter
     ├──► ccxt adapter               ← Crypto exchange execution
     └──► ib_insync adapter          ← Futures / Equities (Interactive Brokers)
```

**Why Python as source of truth:**
1. sigma_core proves Python → compiled binary works for performance-critical paths
2. Python → C#/Rust/C++ transpilation is far cleaner than MQL5 → Python
3. LEAN CLI integration (Phase 2) requires Python strategy code natively

**Current blocker:** The MT5 bridge (ZMQ or FastAPI adapter) is Phase 2 work. sigma-mt5 remains the live trading implementation until the bridge is validated.

---

## sigma_core — The Detection Engine

**Location:** `workspace/sigma_core/`  
**Status:** ✅ Sealed — source is present but NEVER passed to LLM context.

### Compiled Modules (6 .pyd files)

| Module | Python Source | Compiled .pyd | Role |
|--------|--------------|---------------|------|
| `b2b_engine` | `sigma_core/b2b/detectors/b2b_engine.py` | `b2b_engine.cp313-win_amd64.pyd` | Core B2B zone detection orchestrator |
| `breakouts` | `sigma_core/b2b/detectors/breakouts.py` | `breakouts.cp313-win_amd64.pyd` | Breakout detection (2-barrier logic) |
| `confluence` | `sigma_core/b2b/detectors/confluence.py` | `confluence.cp313-win_amd64.pyd` | TF confluence scoring |
| `swing_points` | `sigma_core/b2b/detectors/swing_points.py` | `swing_points.cp313-win_amd64.pyd` | Swing high/low detection |
| `zone_manager` | `sigma_core/b2b/detectors/zone_manager.py` | `zone_manager.cp313-win_amd64.pyd` | Zone storage, redundancy pruning |
| `zone_status` | `sigma_core/b2b/detectors/zone_status.py` | `zone_status.cp313-win_amd64.pyd` | Zone lifecycle state management |
| `fractal_geometry` | `sigma_core/b2b/filters/fractal_geometry.py` | `fractal_geometry.cp313-win_amd64.pyd` | Fractal filter (swing refinement) |
| `structures` | `sigma_core/b2b/models/structures.py` | `structures.cp313-win_amd64.pyd` | Shared data structures / models |

**Python version:** 3.13 (cpython-313). Binaries are platform-specific (win-amd64).

---

## sigma-crypto — Python Research Stack

**Location:** `workspace/sigma-crypto/`  
**Role:** SAMTC strategy backtesting and research. Imports sigma_core for detection.

### Core Detection Layer

| File | Role |
|------|------|
| `core/detectors/b2b_engine.py` | Python source (mirrors sigma_core b2b_engine) |
| `core/detectors/swing_points.py` | Swing detection (mirrors sigma_core) |
| `core/detectors/breakouts.py` | Breakout detection (mirrors sigma_core) |
| `core/detectors/confluence.py` | Confluence scoring (mirrors sigma_core) |
| `core/detectors/zone_manager.py` | Zone management (mirrors sigma_core) |
| `core/detectors/zone_status.py` | Zone lifecycle (mirrors sigma_core) |
| `core/models/structures.py` | Shared data models |
| `core/filters/fractal_geometry.py` | Fractal filter |

### Strategy Layer (SAMTC)

| File | Role |
|------|------|
| `core/strategy/orchestrator.py` | SAMTC main orchestrator |
| `core/strategy/scanner.py` | Multi-pair scanner |
| `core/strategy/engines/state_manager.py` | State machine |
| `core/strategy/engines/fracture_engine.py` | Fracture detection |
| `core/strategy/engines/efficiency_governor.py` | Trade efficiency filter |
| `core/risk/sizing.py` | Position sizing |
| `core/execution/trade_manager.py` | Trade lifecycle |
| `core/system/timeframe_mgr.py` | TF management |

---

## sigma-mt5 — MQL5 Live Trading EA

**Location:** `workspace/sigma-mt5/`  
**Entry Point:** `Experts/Sigma_System/Sigma_V5.0.mq5`  
**Role:** Live trading on MetaTrader 5. Parallel implementation of the same B2B logic in MQL5.

See [[mt5-ea-architecture]] for the full 26-module breakdown.

### MQL5 ↔ Python Module Mapping

| MQL5 Module | Python Equivalent |
|-------------|-------------------|
| `SwingPointDetector.mqh` | `sigma_core/b2b/detectors/swing_points.py` |
| `RawBreakoutDetector.mqh` | `sigma_core/b2b/detectors/breakouts.py` |
| `B2BDetector.mqh` | `sigma_core/b2b/detectors/b2b_engine.py` |
| `B2BZoneManager.mqh` | `sigma_core/b2b/detectors/zone_manager.py` |
| `B2BZoneStatus.mqh` | `sigma_core/b2b/detectors/zone_status.py` |
| `B2BConfluence.mqh` | `sigma_core/b2b/detectors/confluence.py` |
| `Structures.mqh` | `sigma_core/b2b/models/structures.py` |
| `TimeFrameManager.mqh` | `core/system/timeframe_mgr.py` |
| `RiskManager.mqh` | `core/risk/sizing.py` |
| `StrategyOrchestrator.mqh` | `core/strategy/orchestrator.py` |

---

## IP Boundary — SEALED

> [!CAUTION]
> **sigma_core source code is NEVER placed in LLM context.**
>
> - The `.py` source files exist at `workspace/sigma_core/sigma_core/b2b/` but are off-limits
> - Only the compiled `.pyd` binaries are distributed to research partners
> - Any AI session touching sigma_core reads only the module names and interfaces — never the source
>
> The Cython compilation was completed April 1, 2026. The `.pyd` files are the canonical artifact.

**What is exposed:**
- Module names and their roles (documented above)
- Function signatures from `sigma_core/__init__.py`
- The fact that sigma-crypto `core/detectors/` mirrors the sigma_core API

**What is sealed:**
- Detection algorithms, parameter weights, pattern recognition logic
- Anything inside `sigma_core/b2b/detectors/*.py` or `sigma_core/b2b/filters/*.py`

---

## Related Pages

- [[b2b-overview]] — B2B detection strategy (what the engine implements)
- [[samtc-overview]] — SAMTC Python strategy using sigma_core
- [[mt5-ea-architecture]] — Full MQL5 module breakdown (26 files)
- [[sigma-crypto-architecture]] — Python research stack details
