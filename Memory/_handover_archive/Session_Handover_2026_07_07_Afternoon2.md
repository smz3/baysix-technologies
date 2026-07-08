# Handover — July 7, 2026 Afternoon2

## State
- **Edge-hunt on run_19 payload** (mid-price EXPLORATORY screens, /tmp/fob_scan{,2,3}.py — NOT arbiter). `mfe_r`/`mae_r` ALREADY populated in run_19 (278,592 non-null) — the excursion re-emit blocker in the prior handover was MOOT.
- **Three clean statistical patterns found on `realized_r`** (plus-2R/minus-1R barrier label, R=raw band, k=0, mid, cost-free; artifact research/outputs/fob_m5_screen_run19/per_tf_base.csv + m5_cfidx_payoff.csv): (1) only **M5** setup_tf positive (base +0.156, cf1 +0.209); H1/H4/D1/M30/M15 all NEGATIVE at mid. (2) `cf_idx` monotone decay, holds in BOTH directions (not gold-bull). (3) short parent-cycle better. Stacked: M5·cf_idx≤2·n_cf 1-2 → +0.215 (n=76,468). Logged strategy_log 93/94.
- **MT5 arbiter KILLED the M5 headline.** Syafiq ran TRADE·M5·cf1·k0.5·RR8 → slowly declining equity ruin. Cause: on M5 the **band (0.13–0.8pt) ≈ spread (~0.2–0.4pt)** → cost ~1R/trade wipes the +0.209 mid edge; RR=8 (my call) is the sparsest-win corner so it bleeds worst.
- Config I gave DIVERGED from the screen (screen was k=0/RR2/cost0; I told him k0.5/RR8/real-ticks) — three deviations, on me.

## Next
1. **(task 249, P1)** Pull M5 CF **band-size distribution vs typical gold spread** from run_19 — the GATING question: does M5 band ever clear cost? If band ≥ 3–4× spread only rarely, M5-at-market is cost-dead and no RR/exit sweep matters. Cheap query, do FIRST.
2. **(task 248, P1 — now GATED by 249)** M5 exit study (RR sweep 2/3/5/8, then trailing/structural) — only meaningful on a **big-R M5 filter** if 249 shows one exists. Hold until 249.
3. **(task 250, P2)** If M5 is cost-dead even big-R: the entry edge is too small vs spread → pivot the lever to payoff asymmetry (let rare winners run huge) or accept FOB CF entry doesn't clear cost.

## Blockers
- **249 gates 248.** Cannot judge any M5 exit/RR config until we know whether M5 bands clear the spread. Everything M5 hinges on band-vs-spread.

## Why
- **Edge-hunt was the right pivot** (Syafiq pushed: stop proposing re-emits, USE the data we have). The screens are real and clean — the patterns exist. The failure was in the LEAP from mid screen → tester config, not in the pattern-finding.
- **M5 is the classic denominator/rule-16 trap:** M5 has the mid edge but R≈spread → cost-dead; higher TFs have R≫spread but NEGATIVE mid edge. Neither corner is a free win — this is WHY every prior H4 sweep was also net-negative (result set: H4 pbo_t1 −4.12 etc). Not a coincidence, it's structural.
- **k=0.5 was Syafiq's correct call** for M5 (0.25 too tight, gets wicked) — but it changes R, so RR is measured against a bigger stop, pushing RR8 target to ~12 band-units (rarely reached).

## Ruled-Out
- **M5 cf1 at market (CF_MARKET), small-band, high-RR — cost-dead in the tester** (Syafiq's live run, declining equity). NOT a clean falsification of the M5 pattern — it's the wrong config (RR8 + all band sizes). The pattern itself is un-refuted; its NET viability at market is what failed. Re-test only under a big-R filter (task 249/248).
- **RR=8 as a first eyeball — bad call (mine).** Sparsest-win corner; a bleeding curve there proves nothing except cost+sparse-wins. Read the full RR curve 2/3/5/8 side-by-side, never RR8 alone.
- **The "excursion re-emit blocker" (prior handover tasks 246/247) — VOID.** `mfe_r`/`mae_r` are already in run_19. No re-emit needed; excursion is queryable now.

## Live-Threads
- **The one unanswered number (task 249):** M5 CF band-size distribution. If a meaningful subset of M5 CFs have band ≥ ~4× spread, the +0.209 edge may survive net on that subset (cost → 0.2R not 1R). If not, M5-at-market is dead. This single query decides the whole M5 direction — pull it before ANY more tester runs.
- **Payoff-asymmetry lever still un-tested (strategy_log 94; artifact research/outputs/fob_m5_screen_run19/m5_cfidx_payoff.csv):** cf1 M5 winners run median MFE ~8.8-14x (band units) vs the 2x-band cap; survives denominator-illusion (big-R quartile winners still run median ~8.8x band). But MFE is PEAK not capture, AND it's the same tiny-R zones that spread eats. Only testable once band-vs-spread (249) says which zones clear cost.
- **Higher-TF negative-at-mid is unexplained** — is it real (higher-TF CF has no continuation edge) or a horizon/window artifact in realized_r's barrier resolution? Not chased. Would reframe the whole "which TF" question if it's an artifact.
