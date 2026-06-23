# Handover — June 23, 2026 Afternoon2

## State
- **MFE/MAE per trade SHIPPED** (task 139 done). [brc_trader.mq5](../mt5/Experts/brc_system/brc_trader.mq5) `ExcursionForTrade()` walks the working-TF (`_Period`) bars across each hold → signed `mfe_px/mae_px/mfe_r/mae_r` in the ledger; [ingest_brc_trades.py](../research/code/io/ingest_brc_trades.py) stores them in `tester_trades.meta` and gained a `--model` flag (open_only|real_ticks|1min_ohlc). Compiles 0/0.
- **🔑 Real-tick is now the iteration AND baseline model** (task 136 done, strategy_log #57). 8yr @99% history quality = **3m07s** with `InpVisualize=false` + visual-mode off (the >24h fear was object-churn + empty months, not ticks). 1-min OHLC rejected — can't resolve SL-vs-BE touch ordering, which IS the exit experiment.
- **🚨 Open-prices flattered the baseline ~2x.** CLEAN real-tick IS-01 (tester run #10, 2016-06→2024-06): **net −$0.649/trade** (result_id 3), win 24.1%, SL 66% — vs open-prices **−$0.327/trade** (result_id 2), win 26.9%. Empty pre-June-2016 months produced no trades, so the edge is real (run #9 94%q == run #10 99%q).
- **Split diagnosis (real-tick, result_id 3):** trades surviving the entry bar (range_w>0, **69%**) keep the BE/trail signal — SL losers MFE med +0.69R, **40% ran ≥1R green** before reversing, TIME runners give back **0.81R** to the 6-bar cap. The other **31% are instant same-bar SL** — die at tick speed, never green, carry no 1R (task 138). BE/trail can't save those; they're an **entry-quality** leak.
- **dukas ticks start 2016-06-01** (first `.tkc` = 201606). Always run IS from 2016.06.01, not 2016.01.01.

## Next
1. **#141 (P1) — build BE/trail-stop exit variant** (motivated by result_id 3) on the real-tick model (`InpVisualize=false`, run from 2016.06.01). Break-even-after-+1R and/or trailing-stop modes vs IS-01 flat-stop. Caveat: under open-prices-free tick run the SL/BE orders are evaluated tick-by-tick (faithful); EA still only *arms* BE at next bar open (~1-bar lag, conservative).
2. **#138 (P1) — capture range_w (1R) at ARM time** so the 31% instant same-bar SL trades carry a 1R → unblocks the entry-quality half of the diagnosis (currently unanalysable).
3. **#133 (P1) — max-hold sweep 6/12/24** (DROP the take-profit half — TP shrinks the runners). AFTER stop-mode (#141), on top of the winner.

## Blockers
- None hard. OOS #126 stays blocked until an IS config is FROZEN (no variant beats baseline yet; baseline still no edge, −$0.649/trade real-tick, result_id 3).
