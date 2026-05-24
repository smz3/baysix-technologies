---
name: check-lean-health
description: >
  Check the LEAN CLI backtest engine status for the XAUUSD B2B gold algo: Docker running, LEAN CLI
  installed, the algo + config present, and the latest run's metrics vs the profile gates. Invoke
  when asked about LEAN health, backtest engine status, "can I run a backtest", or whether the last
  run is stale. Read-only.
---

# Skill: check-lean-health

Health check for the LEAN CLI backtest engine and the B2B gold algorithm.
Engine lives at `workspace/baysix-engine/research-engine/core/engines/lean-engine/`.
*(Note: per project memory, LEAN Docker runtime + XAUUSD data are UNVERIFIED — flag if the run path isn't actually working yet.)*

## Usage
```
/check-lean-health
```

## Steps
1. **Docker** (LEAN needs it): `docker info --format "{{.ServerVersion}}" 2>/dev/null || echo "DOCKER_OFFLINE"`
2. **LEAN CLI**: `lean --version 2>/dev/null || echo "LEAN_NOT_FOUND"`
3. **Algo + config present** — under `research-engine/core/engines/lean-engine/`:
   - `algorithms/b2b_gold_algo.py` (the XAUUSD B2B algorithm)
   - `lean.json` (engine config), `gate/execution_gate.py` (the survival gate)
4. **Latest run** — newest folder under `lean-engine/runs/`; if none, report "No backtests run yet".
5. **Metrics** — from the latest run, extract Sharpe, Calmar, Max DD, CAGR, Win Rate, Total Trades; compare against the active profile gates in `Memory/risk_parameters.md` (BAYSIX_FRAMEWORK Tier-1: net Sharpe, Calmar > 2.0, ruin < 5%). Flag if the run is > 7 days old.

## Output
```markdown
## LEAN Health Report
**Docker**:     Running (v[X]) / Offline — LEAN cannot run
**LEAN CLI**:   v[X] / Not found
**Algo**:       b2b_gold_algo.py (XAUUSD B2B) — Found / Missing
**Latest run**: [date] ([N]d ago) / none
  Sharpe [X] · Calmar [X] · MaxDD [X%] · CAGR [X%] · WinRate [X%] · Trades [N]
**Status**: HEALTHY / NEEDS ATTENTION / NOT CONFIGURED / UNVERIFIED
**Action**: [next step, or "run /run-backtest"]
```

## Notes
- Read-only — never modify LEAN config or algo files.
- If Docker is offline, say so clearly — LEAN fails silently otherwise.
