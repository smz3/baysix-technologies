# Handover — June 23, 2026 Afternoon

## State
- **Trade-ledger automation SHIPPED (the missing front-half).** [brc_trader.mq5](../mt5/Experts/brc_system/brc_trader.mq5) `OnDeinit` now walks the tester deal history and auto-writes `brc_trades_<sym>_v<ver>_<stamp>.csv` to `Common/Files/BRC/` — one row per closed trade (entry/exit ts+px, `exit_reason` via `DEAL_REASON`, lots, `range_w`, `realized_R`, PnL, zone_key). **No manual MT5 "Export XLSX" ever again.** Compiles 0/0. Ingester: [ingest_brc_trades.py](../research/code/io/ingest_brc_trades.py) → `tester_runs`+`tester_trades`. (Closed the task-43 stub; the old [ingest_tester_report.py](../research/code/io/ingest_tester_report.py) only did the parse, never the EA emit — that was the whole gap.)
- **IS-01 re-run ingested = `tester_runs` run #7, 1448 trades.** Reconciles EXACTLY to result_id 2 (net −$472.83 = **−$0.327/trade**) → ledger is faithful.
- **Decomposition (run #7):** win-rate **26.9%**; exits SL 903 (62%) / TIME 545 (38%); profit factor **0.84** (win $2440 / loss $2913). Median hold 180m; 544 SL hit ≤60m at only **−$2.18 avg** (cheap paper cuts). **Winners = the TIME runners cut at the 6-bar/6h cap.**
- **Two findings that steer the exit work:** (1) **A take-profit is the wrong lever** — it would shrink the runners that pay. (2) Sessions are **flat** (Asia 28.5/London 25.6/NY 26.7% — no session edge); "overnight" cohort wins 45.6% net +$93 but that's **survivorship** (the trades that didn't stop early), not a rule.
- **Known ledger gaps (tasks):** SL rows have `range_w=0`/empty zone_key (instant same-bar fills skip the in-pos stash — task 138); **MFE/MAE not recorded** (task 139).

## Next
1. **Task 139 (P1, #1 PRIORITY):** add **MFE/MAE per trade** to the trader ledger (best/worst price over the hold via bar H/L — `CopyRates` returns full OHLC even under open-prices). Re-run → answers the open question: *did the 544 sub-hour SL losers run into profit first, and how far?* Settles whether **break-even/trail** converts them or it's a pure entry problem.
2. **Task 133 (P1, REFRAMED):** max-hold **EXTENSION** sweep 6/12/24 bars — **DROP the TP half**. Run after 139.
3. **Task 140 (P2):** confirm tester server TZ offset for `XAUUSD_dukas` before trusting the Asia/London/NY labels (assumed UTC).

## Blockers
- None hard. OOS #126 stays blocked until an IS config is FROZEN (comes from a variant beating baseline, not IS-01). Baseline still NO edge (−$0.327/trade, result_id 2).
