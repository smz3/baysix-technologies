---
name: 'run-backtest'
description: 'Sigma brain skill: run-backtest'
---

# Skill: run-backtest

Run a sigma-crypto SAMTC backtest and return a structured performance summary.

## Usage
```
/run-backtest [optional: phase number or date range]
```

## Steps

1. Navigate to the sigma-crypto project:
   ```
   cd C:\Users\User\Desktop\sigma-crypto
   ```

2. Check which backtest script to run:
   - Default: `scripts/run_phase_4_simulation.py`
   - If a specific phase is requested, check `scripts/` for the matching script

3. Run the backtest:
   ```bash
   python scripts/run_phase_4_simulation.py
   ```

4. Parse the output — look for these key metrics:
   - CAGR %
   - Sharpe Ratio
   - Calmar Ratio
   - Max Drawdown %
   - Sortino Ratio
   - Win Rate %
   - Payoff Ratio
   - Total Trades

5. Check `research/reports/` for any HTML tearsheet or CSV output generated

6. Return a structured report:
   ```markdown
   ## Backtest Result
   **Script**: [which script was run]
   **Period**: [date range tested]
   **CAGR**: X%
   **Sharpe**: X.XX
   **Calmar**: X.XX
   **Max DD**: X%
   **Sortino**: X.XX
   **Win Rate**: X%
   **Payoff**: X.XX
   **Total Trades**: N
   **Output Files**: [paths to tearsheet/CSV]
   **vs Baseline**: [comparison to previous approved result if available]
   ```

7. Ask the memory-curator to update `Memory/strategy_state.md` with the result.

## Notes
- Never modify source code as part of this skill — read and run only
- If the script errors, report the full traceback to the user
- If tests fail, run `pytest tests/` first and report before running the simulation
