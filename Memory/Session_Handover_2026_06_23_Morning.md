# Handover — June 23, 2026 Morning

## State
- **BRC-001 G2 — IS-01 trader EA BUILT + compiles clean (0 errors).** This replaces the reverted query-layer approach (see Afternoon5 incident): MT5 tester is now the arbiter, no Python in the critical path.
- **New files (committed `24460ec`, pushed):**
  - [brc_trader.mq5](../mt5/Experts/brc_system/brc_trader.mq5) — strategy EA, sibling of emitter. Reuses detection pipeline (swing→break→zone→advance) on the chart TF (H1), one-position state machine (FLAT/PENDING/INPOS), raw `OrderSend` (no `CTrade` dep → self-contained against repo include tree).
  - [brc_entry.mqh](../mt5/Include/brc_system/brc_entry.mqh) · [brc_exit.mqh](../mt5/Include/brc_system/brc_exit.mqh) · [brc_sizing.mqh](../mt5/Include/brc_system/brc_sizing.mqh) — swappable modules (enum modes + inputs). Iterate by flipping inputs, NOT editing files.
  - [gen_brc_version.py](../research/code/infra/gen_brc_version.py) → `brc_version.mqh` (gitignored, derivable) — git sha printed on init; DIRTY-tree run = exploratory.
  - CLAUDE.md new **MT5 / EA Workflow** section; CHANGELOG + README + `.set` preset under mt5/.
- **IS-01 atom (strategy_log #55, PROPOSED — NOT yet frozen):** H1 · enter T1=L1 first-retest, continuation · SL=invalidation(L2) · close at 6 H1 bars · no TP · one position · fixed 0.01 lot. Entry = pending LIMIT at L1 (level-based fill → deterministic under Open-prices).
- **KEY data-contract correction:** T1/T2/T3 = touches of L1/mid/L2 (pullback DEPTH), NOT 1st/2nd/3rd retest. IS-01 (L1) unaffected; task #132 reworded accordingly.
- **Backlog restructured:** #110=IS-01 spec · #131=H_alt-1 fade · #132=H_alt-2 entry-depth (T2/mid,T3/L2) · #133=exit robustness (maxhold 6/12/24 + TP) · #126=OOS (blocked on freeze). All "AFTER IS-01 frozen". Multi-TF expansion: HELD OUT (not queued, per Syafiq).
- **Caveat:** committed `.ex5` compiled on DIRTY tree (sha b7aba22). No tester run done yet — NO number produced.

## Next
1. **`git pull` → `python research/code/infra/gen_brc_version.py` → recompile** brc_trader.mq5 (MetaEditor64 `/inc:<repo>\mt5`) so `.ex5` carries clean sha `24460ec` before any trusted run.
2. **Run IS-01 in Strategy Tester** (XAUUSD, H1, model "Open prices only", 2016-01-01→2024-06-30, deposit 50), load `mt5/presets/brc_system/brc_trader-v1.0.0-IS01.set`. **FIRST verify limit-at-L1 fills actually trigger** under Open-prices; if not, fall back to "1 minute OHLC" model.
3. If fills OK: read the MT5 `.xlsx` (→ mt5/strategy_tester_xlsx/) — equity curve smoothness + DD + PF. That xlsx IS the trusted G2 read. Then `pipeline.log_result()` + decide freeze (ADOPT → unblocks OOS #126) or iterate.

## Blockers
- BRC-001 G2 still has NO trusted result; Gate 2 open. Unblocks the moment the tester run in Next-step 2 produces a clean-sha `.xlsx`. Do NOT report any query-layer number as a verdict (Afternoon5 lesson).
