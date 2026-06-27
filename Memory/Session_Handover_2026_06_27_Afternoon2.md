# Handover — June 27, 2026 Afternoon2

## State
- **FOB trader v1.19.1** ([fob_trader.mq5](mt5/Experts/fob_system/fob_trader.mq5)) — compiles 0 errors (1 benign Market version warning). Junction-deployed to JM terminal.
- **v1.19.1 = filename fix only:** K+RR now in the trades-ledger filename (`..._kXXX_rrXXX_...csv`, k025=0.25 rr200=2.00) so an OPTIMIZATION sweep writes one CSV per combo instead of clobbering. No logic change vs v1.19.0.
- **v1.19.0 H1→M30 baseline dissected → result_id 16:** net/trade −0.363 (best of 3 vs id12 cont −0.450 / id15 fade −0.521). Clean 2:1 payoff, WR 29.11% vs 33.3% breakeven → 4.2pp hit-rate gap = the ENTIRE deficit. Stop+payoff solved; **entry is the only lever.** (task 186 done.)
- **K-RR sweep (task 175) NOT run** — only the baseline combo (k025/rr200) ever executed; sweep abandoned by design (see Ruled-Out).
- **Syafiq is RIGHT NOW running an H4 setup baseline** (H4→H1, K=0.25 RR=2.0, raw-CF entry) to *see the higher-TF entry logic* — task 187. CSV not landed yet.

## Next
1. **(task 187, P1)** When Syafiq's H4-setup run finishes: pull `fob_trades_*H4*` CSV from `Common/Files/FOB`, compute net/trade + WR, compare vs H1 result_id 16 — does raw market-on-CF get *worse* on H4 (feeds the nested-confirmation hypothesis)? Log via `pipeline.log_result`.
2. **(task 185, P1)** DISCUSS entry-logic rules — mechanism first, NO code. Hypothesis: higher-TF setups can't fire on raw CF; the higher-TF CF needs the LOWER-TF setup cycle (PBO/VR/CF) to complete *inside* the higher-TF zone before entry is valid (nested confirmation). Pin the exact nesting rule before building.
3. **(task 175, P2)** K-RR sweep DEFERRED until entry settled — and only worth it with a deposit big enough to survive (see Live-Threads). Winner must hold OOS, not just top in-sample.

## Blockers
- **None.**

## Why
- **Entry, not SL/RR, is the lever — proven, not assumed.** result_id 16 shows the structural L2 stop + RR=2 already produce a clean 2:1 payoff; the whole net-negative result is the 4.2pp WR shortfall (29.11% vs 33.3% breakeven). Tuning K/RR cannot fix a hit-rate problem → go to entry logic.
- **The trades CSV is custom-schema but 1:1 on money with the MT5 tester** — every $ field (`realized_pnl_usd` = DEAL_PROFIT+SWAP+COMMISSION, prices, exit_reason) is read straight from `HistoryDeal*` ([fob_trader.mq5:677-687](mt5/Experts/fob_system/fob_trader.mq5#L677)). Only `range_w`/`realized_r` are our derived fields. That's WHY we analyze the CSV not the .xlsx report: the report lacks `range_w`/R/TF-context. `ingest_tester_report.py` (.xlsx path) is effectively dead — `tester_runs` table is empty.
- **Sweep needs Optimization MODE, which a `.set` upload does NOT set.** The sweep `.set` is correct (K{0.10,0.30,0.50}×RR{1.5,2.0,2.5,3.0}, both `||...||Y`), but MT5 ignores the ranges unless the Tester **Settings → Optimization** dropdown = "Slow complete algorithm" (NOT Disabled). The second dropdown (Balance Max / PF Max…) is the *criterion* — only matters for genetic; with complete-algorithm it's just display sort order. We re-rank all combos in Python anyway.

## Ruled-Out
- **Lower-TF raw-CF entry (M15→M5) — FALSIFIED, catastrophic.** Account 10000→~$17 by 2022-11-23 (6.4yr into an 8yr window), then 1,821 orders rejected "No money" to the manual stop. ~48k trades (~17× H1's 2,813) at negative edge = blowup. Evidence: tester log `Tester/logs/20260627.log`. No CSV (user-stop skips the OnDeinit ledger write). Disproves "lower TF = better location"; lower TF just compounds a losing per-trade edge faster. **M5-setup test SKIPPED** (would blow even faster).
- **K-RR sweep as the *current* priority — DROPPED for now.** It would only confirm "payoff tuning can't fix a WR problem." Cheap, but low-value vs going straight to entry. Deferred (task 175), not killed.
- **Why MT5 tester never auto-stops on a blown account** — fixed 0.01 lots need only ~$19 margin; once equity < that, the tester just *rejects* new orders and grinds the remaining bars (not a bug, not a stop-out). This is the [[orb_dd_structural_floor]] min-lot floor again.

## Live-Threads
- **H4-setup baseline (task 187) is mid-flight** — Syafiq running it to eyeball higher-TF CF-entry logic. Expectation: H4 raw-CF is also poor (the nested-confirmation gap). Confirm direction when CSV lands; it's the empirical lead-in to the task 185 mechanism discussion.
- **Task 185 nesting rule still un-pinned** — "higher-TF CF needs the lower-TF PBO/VR/CF cycle to complete inside the zone" is a hunch, not a rule. Open questions: does a *full* lower-TF PBO/VR/CF need to nest, or just a lower-TF CF in-zone? How is the higher-TF zone the container (L1/L2 bounds)? Don't build until pinned.
- **Clean lower-TF/multi-TF comparison needs a survivor deposit** — any sweep or TF test where the account can blow mid-window is survivorship-truncated (M15 lesson). Re-run lower/faster TFs with ~100k deposit so the full window samples AND the ledger writes on natural completion.
- **K-RR sweep partial:** only k025/rr200 (baseline) CSV exists on disk; no other combos completed. Nothing to ingest.
