---
name: 'check-lean-health'
description: 'Sigma brain skill: check-lean-health — check LEAN CLI engine status, B2BZoneStrategy config, and latest backtest results'
---

# Skill: check-lean-health

Check the health and status of the sigma-lean LEAN CLI backtesting engine and B2BZoneStrategy.

## Usage
```
/check-lean-health
```

## Steps

1. **Check Docker** — LEAN requires Docker to be running:
   ```bash
   docker info --format "{{.ServerVersion}}" 2>/dev/null || echo "DOCKER_OFFLINE"
   ```

2. **Check LEAN CLI version**:
   ```bash
   lean --version 2>/dev/null || echo "LEAN_NOT_FOUND"
   ```

3. **Read strategy config** — parse IS/OOS date ranges and description:
   - `C:\Users\User\Desktop\sigma-brain\workspace\sigma-lean\B2BZoneStrategy\config.json`

4. **Find latest backtest run** — list backtest folders and find the most recent:
   - `C:\Users\User\Desktop\sigma-brain\workspace\sigma-lean\B2BZoneStrategy\backtests\`
   - Sort by folder name (timestamp-based) and take the latest
   - If no backtests found, report "No backtests run yet"

5. **Read latest results** — if a backtest exists:
   - Read `results.json` from the latest backtest folder
   - Extract: Sharpe Ratio, Calmar Ratio, Max Drawdown, CAGR, Win Rate, Total Trades
   - Compare against validation gates from `Memory\risk_parameters.md`:
     - Sharpe > 1.0 (crypto OOS gate)
     - Max DD < 10%
     - Calmar > 2.0
   - Flag if latest run is stale (last modified > 7 days ago)

6. **Check main strategy file exists**:
   - Look for `C:\Users\User\Desktop\sigma-brain\workspace\sigma-lean\B2BZoneStrategy\main.py`

7. **Return health report**:
   ```markdown
   ## sigma-lean Health Report

   **Docker**:        ✅ Running (v[X.X]) / ❌ Offline — LEAN cannot run
   **LEAN CLI**:      v[X.X.X] / ❌ Not found
   **Strategy**:      B2BZoneStrategy (BTCUSDT H1, Binance)
   **Strategy File**: Found / ❌ Missing

   **Latest Backtest**: [date] ([N] days ago) / No backtests found
     Sharpe:          [X.XX]  [✅ gate >1.0 / ❌ below gate]
     Max DD:          [X.X%]  [✅ gate <10% / ❌ above gate]
     Calmar:          [X.XX]  [✅ gate >2.0 / ❌ below gate]
     CAGR:            [X.X%]
     Win Rate:        [X.X%]
     Total Trades:    [N]

   **Status**: HEALTHY / NEEDS ATTENTION / NOT CONFIGURED
   **Action**: [specific next step if needed, or "None — ready to run"]
   ```

## Notes
- Read-only — never modify LEAN config or strategy files during this check
- If Docker is offline, report clearly — LEAN will fail silently otherwise
- If no backtest exists, remind user to run `/run-backtest` first
- If any gate fails, flag which metric and by how much
