# FOB Storyline-Alignment — Empirical Findings (exploratory screens)

> ⚠️ **VOID — DO NOT CITE THESE NUMBERS (banner added 2026-07-25).** Every figure here was computed on **`tester_zones` run_id 5, which is BRC-contaminated** (not FOB's own zones), so it is invalid for FOB pending a re-screen on FOB zones (task 192). Separately, §2's "real directional-alignment edge" was subsequently shown to be a **circularity / look-ahead artifact**: a guarded, independent re-screen (results 20/21) collapsed the lift to ~0, and Setup↔Direction is **not** a usable conditioner. Retained for lineage only.

**Date:** 2026-06-27 · **Idea:** FOB-001 · **Status:** Exploratory selection screens on emitter event log (`tester_zones` run_id 5, 100,034 confirmed zones, 8 TFs, one chronological pass). **NOT MT5-netted — MT5 tester remains the money arbiter.** Companion to [2026-06-27_fob_cmp_storyline_model.md](2026-06-27_fob_cmp_storyline_model.md).

Outcome metrics = emitter proxies: `continued` (did the zone continue, ~hit-rate) and `realized_r` (continuation magnitude in R). Method is **causal/reactive**: condition each execution-TF CF on the higher-TF **bias stack already confirmed and alive at entry**; measure the CF's own continuation **forward**. No look-ahead.

## 1. Nesting (spatial) — FLAT on hit-rate (the discarded version was right to discard)
Conditioning an inner CF on being spatially inside an outer same-dir zone → continued-rate flat (M30-in-H1 0.518 vs 0.516 baseline). Spatial containment is NOT the signal. The earlier "+14pp" (outer H1 conditioned on a *future* nested child) was look-ahead — measured the outer's outcome from before the child existed. Discarded.

## 2. Storyline alignment (directional) — REAL hit-rate edge
`alignment = # higher-TF ladder members whose current alive bias == entry direction`. Full-stack-aligned lift vs baseline (all causal):

| exec TF | bias ladder | cont-rate lift | E[R] lift | n(full) |
|---|---|---|---|---|
| H1 | H4/D1/W1 | **+4.8pp** (0.508→0.556) | +3.58 | 1,383 |
| M30 | H1/H4/D1/W1 | +3.1pp | +3.16 | 2,166 |
| M15 | M30/H1/H4/D1 | +2.0pp | +3.39 | 4,933 |
| M5 | M15/M30/H1/H4/D1 | +1.5pp | +3.57 | 10,786 |

Lift is **largest at higher execution TFs** — the macro story matters more the higher the cycle you trigger on. H1 lift two-prop z≈3.8.

## 3. BUY/SELL symmetry split — hit-rate symmetric, magnitude BUY-only
| exec·dir | base cont/E[R] | full cont/E[R] | cont lift |
|---|---|---|---|
| H1 BUY | 0.513 / +7.10 | 0.568 / +11.89 | +5.5pp (z≈3.8) |
| H1 SELL | 0.503 / −2.21 | 0.540 / −2.14 | +3.7pp (z≈2.0) |

- **Hit-rate lift is SYMMETRIC** (both directions, every TF) → not trend-beta.
- **Magnitude is asymmetric**: BUY runs +7→+15R, SELL stays **negative** even fully aligned. The "+3.5R bigger TP" signal is **BUY-only**.

## 4. Regime check (price vs 200D SMA; UP 71.6% / DOWN 28.4%)
- **Hit-rate lift positive in EVERY year (9/9, +1.0 to +13.5pp) and every regime×dir cell.** Durable, regime-independent.
- **SELL E[R] stays negative even in DOWN regimes; BUY E[R] positive in both.** BUT "DOWN" here = shallow corrections inside an 8-yr secular bull — **no genuine gold bear in sample.** ∴ the long-magnitude bias is **confounded with the secular bull, not validated directional alpha.**

## 5. Conclusions
1. **FOB's durable edge = the storyline-alignment HIT-RATE filter** (~+2–8pp, symmetric, all years/regimes). This is the thing to take to the MT5 trader.
2. **Long-bias payoff is sample-specific** (no real bear) → do NOT hard-code a long bias; flag for a genuine-bear test (pre-2016 / another asset). Possible `realized_r` directional convention also worth a sanity check.
3. **Hit-rate edge concentrates at higher execution TFs** — trading H1 (with H4/D1/W1 aligned) captures the most alignment lift; dropping to M5 buys precision/RR, not hit-rate.
4. Next: MT5-net validation of a full-stack-alignment entry gate on H1; the genuine-bear confound test.
