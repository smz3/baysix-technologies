---
name: 'run-backtest'
description: 'Run a LEAN CLI backtest for B2BZoneStrategy and return a structured performance summary. Specify a date range or period label (IS/OOS). Default runs the full OOS period (2023-2025).'
---

# Skill: run-backtest

Run a LEAN CLI backtest for the B2BZoneStrategy and return a structured performance summary.

**Note:** LEAN CLI is the sole backtest engine. The old sigma-crypto custom Python backtester is archived.

## Usage
```
/run-backtest [optional: IS | OOS | date range e.g. 2023-01-01 to 2025-12-31]
```

## Steps

1. **Navigate to sigma-lean:**
   ```bash
   cd C:\Users\User\Desktop\sigma-brain\workspace\sigma-lean
   ```

2. **Confirm Docker is running** (LEAN requires it):
   ```bash
   docker info
   ```
   If Docker is not running, alert the user — LEAN cannot run without it.

3. **Run the backtest:**
   ```bash
   lean backtest "B2BZoneStrategy"
   ```
   LEAN will use the date range configured in `B2BZoneStrategy/config.json`. If a specific period is requested, check and update the `startDate` / `endDate` fields in config.json first.

4. **Locate the output:**
   - LEAN writes results to `B2BZoneStrategy/backtests/<timestamp>/`
   - HTML tearsheet: `<timestamp>/B2BZoneStrategy.html`
   - JSON results: `<timestamp>/results.json`

5. **Parse key metrics from results.json:**
   - Total Return %
   - CAGR %
   - Sharpe Ratio (annualized)
   - Max Drawdown %
   - Calmar Ratio
   - Win Rate %
   - Total Trades
   - Average Win / Average Loss / Payoff Ratio

6. **Return a structured report:**
   ```markdown
   ## LEAN Backtest Result
   **Strategy**: B2BZoneStrategy
   **Period**: [start date] to [end date]
   **Engine**: LEAN CLI (QuantConnect)
   **CAGR**: X%
   **Sharpe**: X.XX
   **Calmar**: X.XX
   **Max DD**: X%
   **Win Rate**: X%
   **Payoff**: X.XX
   **Total Trades**: N
   **Output**: [path to HTML tearsheet]
   **vs Gate**: Sharpe [pass/fail vs 2.0 gate] | DD [pass/fail vs 10% gate]
   ```

7. **Compare against baseline** if available:
   - Custom engine Test 13A OOS: Sharpe 1.16, Payoff 1.65, Skew 3.43
   - Note: LEAN result is the authoritative figure — custom engine result is reference only

8. **Ask the memory-curator to update `Memory/strategy_state.md`** with the new result.

## Notes
- Never modify strategy source code as part of this skill — run only
- If `lean backtest` fails, check Docker is running and `lean.json` config is valid
- For IS vs OOS cross-validation: run twice with different date ranges in config.json, compare Sharpe
- If Sharpe degrades >30% from IS to OOS, flag as potential overfitting — escalate to mathematician
