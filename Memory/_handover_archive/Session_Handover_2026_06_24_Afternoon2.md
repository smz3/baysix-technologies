# Handover — June 24, 2026 Afternoon2

> Pivot in motion (task 149): revive the ORIGINAL B2B = the **Sigma_V5.0 MT5 EA**, score it on the same dukas testbed, compare vs BRC (result_id 9 cont −0.213R / result_id 10 fade −0.220R). Goal Q: does multi-TF Russian-doll confluence — the layer BRC stripped — carry the directional edge a single BRC level lacked?

## State
- **"Original B2B" identified = [Sigma_V5.0.mq5](../mt5/Experts/Sigma_System/Sigma_V5.0.mq5)** (~14k lines, full multi-TF detect + B2BConfluence + Russian-doll StrategyOrchestrator + order/risk/trail). The Python `b2b/sigma_core` orchestrator is a DEAD end — never wired to a backtest, BTC-fitted; ignore it.
- **COMPILES CLEAN (0 errors / 0 warnings).** Root cause of the initial 73-error fail = missing MT5 std lib `<Trade\Trade.mqh>`; repo-only `/inc=mt5/` can't see it. Fixed by junctioning `Sigma_System` (Experts+Include) into the **E7DB JustMarkets** terminal and compiling against the terminal MQL5 root. `.ex5` (314KB) is live in Navigator.
  - **Host quirk:** `cmd.exe mklink` opens INTERACTIVELY here (hangs) — use PowerShell `New-Item -ItemType Junction` instead.
- **Config recovered = [Profiles/Tester/Sigma_V5.0.set](../mt5/Experts/Sigma_System) (May 18)** = last-known-good, no need to remember inputs. ExecutionProfile=3 (FULL_MANUAL). TFs ON: MN1/W1/D1/H4/H1/M30/**M5** (sniper); M15/M1 off. Touch T1/T2/T3 alloc 0.2/0.4/0.4. Exit SL350pts + BE(150/50) + trail(450/250), no fixed TP. Risk 1% + **200 positions pyramiding**.
- **CSV is NOT BRC-schema.** Sigma `QuantLogger` → `SIGMA_Quant\Trades\QUANT_*_TESTER.csv` with `pnl_money`(net, incl comm+swap)+`r_multiple`+comm+swap+MAE/MFE — richer but different cols; no ingester exists (task 150). Fully scorable.
- **Tester running on dukas** (cost model matches BRC ✓). First run was mis-set to **intraday** → user redoing.

## Next
1. **Run 1-yr smoke = 2022, REAL TICKS, dukas, full (non-intraday) config** — confirm it trades + CSV lands + plumbing. ~10–12 min. (task 149)
2. **Build the scoring adapter (task 150)** — Sigma CSV → net $/trade + E[R]; `pipeline.log_result` so it's comparable to result_id 9/10.
3. **Then full 8yr (2016.06–2024.06) real-ticks dukas run → score → compare vs result_id 9/10** (task 149). Watch sizing: 200-position pyramid ≠ BRC fixed-risk → build neutralized .set first (task 151) for the real head-to-head.

## Blockers
None. Comparison validity hinges on (a) same dukas+real-ticks model [✓ on dukas], (b) sizing-neutralized run (task 151) before the verdict — running the 200-position config gives a "native" number, not an apples-to-apples one.
