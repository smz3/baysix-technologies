# sigma-lean — LEAN CLI Backtesting Engine

## What This Is
LEAN CLI backtesting for the B2B Zone Strategy (SAMTC). This is the **primary validation engine** — results here are authoritative. The custom sigma-crypto backtester is a reference only.

## Current Task
Port the full SAMTC logic from `workspace/sigma-crypto/` into LEAN CLI's `B2BZoneStrategy/`. Components to port:
1. FlowState (market structure detection)
2. Storyline Latches (B2B zone identification)
3. Siege Detection (confluence filter)
4. Gate A / Gate B / Gate C (entry filters)

## Validation Targets

| Metric | IS (2020–2022) | OOS (2023–2025) | Gate |
|--------|---------------|-----------------|------|
| Sharpe | — | ≥ 1.0 (crypto) | Hard |
| Max DD | — | < 10% | Hard |
| Calmar | — | > 2.0 | Hard |
| Baseline | Reference: Test 13A | Sharpe 1.16, DD 8.2% | Beat or match |

OOS Sharpe must not degrade more than 30% below IS Sharpe (overfitting flag).

## Key Files

```
sigma-lean/
├── B2BZoneStrategy/
│   ├── main.py          ← strategy entry point (QCAlgorithm subclass)
│   ├── config.json      ← LEAN project config (BTCUSDT H1, Binance)
│   └── backtests/       ← results folders (timestamp-named)
├── lean.json            ← LEAN workspace config
└── CLAUDE.md            ← this file
```

## Development Rules

1. **Never modify the OOS date range** (2023-01-01 to 2025-12-31) during active development — data leakage risk
2. **Docker must be running** before `lean backtest` — check with `/check-lean-health`
3. **Run `/run-backtest` after any strategy change** — compare IS and OOS separately
4. **All code changes go through quant-developer** (isolated worktree) + code-reviewer sign-off
5. **Baseline to beat**: Test 13A OOS — Sharpe 1.16, Payoff 1.65, Skew 3.43

## Run Backtest
```bash
# From sigma-lean root:
lean backtest "B2BZoneStrategy"
```
Or use the `/run-backtest` skill which parses results automatically.

## Source Strategy (sigma-crypto)
The SAMTC logic to port lives in:
- `workspace/sigma-crypto/core/detectors/b2b_engine.py` — B2B zone detection
- `workspace/sigma-crypto/core/strategy/orchestrator.py` — SAMTC orchestrator (Gate A/B/C)
- `workspace/sigma-crypto/core/strategy/engines/state_manager.py` — FlowState
- `workspace/sigma-crypto/core/strategy/engines/storyline.py` — Storyline Latches

## sigma_core — Operational Mirror
`sigma-lean/sigma_core/` is a **read-only operational mirror** of `sigma-crypto/core/b2b/`. LEAN's Docker container mounts `sigma-lean/` as the workspace root, so the core must live here — it cannot be installed as a package from a sibling folder. When you update B2B detection logic in `sigma-crypto`, sync it here before running a backtest:
```bash
# From sigma-brain root:
bash workspace/scripts/sync_core.sh
```

## Health Check
Run `/check-lean-health` before and after any major change to verify Docker, LEAN version, and latest backtest results.
