# Handover — June 27, 2026 Afternoon

## State
- **FOB trader CF-entry SL rewired → structural.** v1.18.3 → **v1.19.0** (all 3 stamps: FOB_VERSION define + both `.mq5` `#property`). Compiles 0 errors (1 benign Market version-format warning).
- **New SL** ([fob_trader.mq5:274-285](mt5/Experts/fob_system/fob_trader.mq5#L274)): `SL = L2 ∓ InpSlBufferK × |L1−L2|` (beyond zone FAR edge by a fraction of band height). Was `L1 ± k×penetration`. `FobOpenMarket` now takes the `FobEvent` (reads `e.zone.l2` + `e.zone.valid` guard). Logged `strategy_log` change_id 78. `InpSlBufferK` default 0.25, sweepable.
- **TP unchanged** = `entry ± risk × InpRMultTP`; risk auto-scales off the new SL (RR stays a pure ratio — not tied to zone size).
- **Confirmed (no change, just verified):** multi-CF concurrent entries ON (`InpCfIdxFilter=0` = all CFs, no `PositionsTotal` cap); entry fires market-on-CF-confirmation bar, NOT on retest of L1–L2 band (retest = task 171, unbuilt).
- **Presets:** wiped ALL old `.set`/`.ini` (repo + terminal). New canonical presets in [mt5/presets/fob_system/](mt5/presets/fob_system/): `fob_trader-v1.19.0-baseline.set` (H1→M30, K=0.25, RR=2.0, filter=0) + `fob_trader-v1.19.0-sweep-K-RR.set` (K{0.10,0.30,0.50}×RR{1.5,2.0,2.5,3.0}). **Presets now auto-mirror** to JM terminal via 2 new `mklink /J` junctions ([[fob_presets_junction_deploy]]).
- **Open finding (Syafiq's read of the baseline run):** SL too TIGHT in some cases, too WIDE in others → conclusion is the fix belongs in **ENTRY logic, not the SL formula** (task 185).

## Next
1. **(task 186, P1)** Next agent: dissect the latest fob_trader v1.19.0 baseline backtest (H1→M30, L2 SL, RR=2.0, real ticks) — pull MT5 report (net, win-rate, trades, PF, maxDD, curve), log via `pipeline.log_result`, read whether structural SL+RR moved the curve and whether the too-tight/too-wide SL pattern shows in the trade distribution.
2. **(task 185, P1)** DISCUSS entry-logic rules: higher-TF setups can't fire on raw CF confirmation — hypothesis the higher-TF CF needs the LOWER-TF setup cycle (PBO/VR/CF) to repeat/complete inside the higher-TF zone before entry is valid (nested confirmation). Mechanism first, no code.
3. **(task 175, P2)** AFTER entry-logic settled: run the K×RR sweep preset (12 combos) to tune SL buffer + RR; winner must hold OOS, not just top in-sample.

## Blockers
- **None.** (GitHub auto-push working — token cached.)

## Why
- **SL moved from L1 to L2 because L1 was path-dependent.** Old buffer scaled with *penetration* (how far price ran past the broken swing by fill time) — arbitrary, not structural. L2 is the zone's true invalidation edge (first CLOSE beyond L2 = breakout dead), and `K×|L1−L2|` makes the buffer a fraction of zone height → scale-free across TF and price regime, no ATR (respects the v1.12.0 ATR-strip).
- **Tested on H1→M30 by design, not preference.** Hold ONE setup-TF constant to isolate the SL/RR change; sweeping TF simultaneously would confound the read. Full TF sweep is task 172, deferred until entry+SL locked. H1 chosen as the sample-vs-cost balance (lower TF = spread noise, higher TF = too few trades).
- **RR kept as a pure ratio, NOT scaled to the new SL.** risk already carries the L2 SL; scaling RR too would double-count zone size. The *value* of RR likely shifted (wider stop → wider risk-unit → lower hit-rate/bigger wins), so the right move is re-sweep (K,RR) jointly, not hand-edit. Structural-TP (task 167) deferred — premature before CF directional edge is confirmed (task 174).
- **Presets needed their own junction** — the Experts/Include junctions don't cover `MQL5\Presets` or `Profiles\Tester`, so repo `.set` files were invisible to the tester. Junctioned both terminal folders → single source = repo. `mklink /J` from Git Bash needs `MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL='*'` or `/J` gets path-mangled.

## Ruled-Out
- **Static-points SL buffer (e.g. 300 pts beyond L2) — REJECTED in discussion.** TF-blind and regime-blind: a fixed $ buffer is a whole M5 zone but trivial vs a D1 zone, and gold's price doubled 2016→2026. Chose band-fraction instead.
- **Adjusting RR by formula to match the new SL — REJECTED.** Double-counts zone size (already in the risk denominator). RR stays dimensionless; only its swept *value* changes.
- **SL formula itself as the fix for too-tight/too-wide — REJECTED by Syafiq after the baseline run.** The variance isn't a buffer-sizing problem; it's that raw CF-confirmation entry is wrong for higher TFs. Fix moves to entry logic (task 185), not the SL math.

## Live-Threads
- **Task 185 hypothesis is mid-formed:** "higher TFs have granularity → the CF needs the lower-TF setup cycle to repeat inside the higher-TF zone before entry is valid." Not yet a concrete rule — needs mechanism discussion (what exactly nests: a full lower-TF PBO/VR/CF? just a lower-TF CF in-zone? how is the higher-TF zone the container?). Don't build until the nesting rule is pinned down.
- **Baseline run numbers not yet logged** — Syafiq read the curve/SL behaviour visually but the MT5 report isn't ingested to `step4_results` yet. Task 186 closes this; until then there's NO result_id for the v1.19.0 baseline.
- **Task 184 (D1 RT not firing) still open & deferred** — unrelated to today's CF-entry work, parked from the morning session. Gates RT entry testing (181/182).
