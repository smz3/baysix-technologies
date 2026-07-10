# FOB direction A/B — ARM A (continuation) · EXPLORATORY, NOT A GATE RESULT

**Date:** 2026-07-10 · **Idea:** FOB-001 · **Status:** ⚠️ exploratory — must be re-run before it counts.

## Why this is not a logged result

- The `.ex5` stamps **`git a025224-DIRTY(exploratory)`**. A DIRTY-tree number is not reproducible
  (CLAUDE.md, MT5 workflow / provenance).
- `a025224` is 3 commits behind HEAD; `fob_baysix.mq5`, `fob_csv.mqh`, `fob_types.mqh` all changed since
  (the v1.39.0 session-filter commit). Drift appears benign but is unverified.
- The run window **2016-06-01 → 2026-05-01** swallows the held-out OOS block (2024-07 → 2026-04).
- Adding `InpInvertDir` changes the binary, so **arm A must be re-run on the same binary as arm B**.

Consequently: **no `step4_results` row.** Re-run clean (IS-only), then log both arms.

## Configuration (frozen)

Preset [fob_m30m15_cfALL_trail_k050_A_baseline.set](../../mt5/presets/fob_system/fob_m30m15_cfALL_trail_k050_A_baseline.set).
Setup M30 → CF on M15 · ALL CFs (`InpCfIdxFilter=0`) · no filters · trail-only exit
(`InpTrailStop=true`, activate 1.0R, dist 1.5R) · `InpSlBufferK=0.5` · `CF_MARKET` · real ticks (Model=4) ·
deposit $10,000 · lot 0.01 · magic 3001.

Ledger archived (gitignored): `research/outputs/fob_ab_direction/armA_M30M15_cfALL_trail_k050_FULLSPAN_a025224DIRTY.csv`

## Arm A result (exploratory)

| metric | value |
|---|---|
| n | 8,284 |
| net $/trade | **−0.6188** (SE 0.1299, **t = −4.76**) |
| net R/trade | −0.1795 (t = −11.60) |
| total | −$5,125.90 (10,000 → 4,874.10) |
| win-rate | 29.79% (2,468/8,284) |
| payoff | avg win +$7.156 / avg loss −$3.918 |
| max DD (closed-trade) | $5,371.94 |
| exit mix | 100% `SL` (correct: trail-only ⇒ the trail *is* the stop) |
| mean risk (1R) | $5.613 (median $2.685 — heavy right skew) |

Sub-windows: IS 2016-06→2024-06 n=6,688 −$0.5504 (t−7.74) · 2024-07→2026-04 n=1,596 −$0.9053 (t−1.50).
By direction: BUY n=4,214 −$0.331 (t−1.76) · SELL n=4,070 −$0.917 (t−5.11).

By `range_w` tercile (note $/trade and R/trade rank **opposite** — rank on $/trade, see `er_denominator_illusion`):

| tercile | n | band | $/trade | t | R/trade | win-rate | frac >1R |
|---|---|---|---|---|---|---|---|
| narrow | 2,784 | 0.21–1.84 | −0.3658 | −11.35 | −0.263 | 27.4% | 13.8% |
| mid | 2,738 | 1.85–3.71 | −0.6622 | −9.04 | −0.190 | 29.3% | 14.9% |
| wide | 2,762 | 3.72–280.99 | −0.8307 | −2.18 | −0.085 | 32.7% | 16.9% |

## Defect found: the trail's activation threshold is cosmetic

`InpTrailActivateR=1.0` + `InpTrailDistR=1.5` ⇒ at activation the trailed stop sits **0.5R below entry**.
Nothing locks in profit until the peak exceeds **1.5R**. Only 15.2% of trades ever exceed +1R;
58.3% take a full ≤−0.95R stop. Also 161,133 failed `Invalid stops` trail-modify calls (per-tick re-issue
of an unchanged stop) — log noise, 185 MB tester log, not a correctness bug.

## Pre-registered prediction for ARM B (inverted), logged before the run

Naive mirror, `gross_A = net_R + c/meanRisk`, `net_B = −gross_A − c/meanRisk`:

| spread cost c | c (R) | gross_A (R) | net_B (R) | net_B $/trade |
|---|---|---|---|---|
| $0.20 | 0.036 | −0.144 | +0.108 | +0.61 |
| $0.30 | 0.053 | −0.126 | +0.073 | +0.41 |
| $0.40 | 0.071 | −0.108 | +0.037 | +0.21 |
| $0.50 | 0.089 | −0.090 | +0.001 | +0.01 |
| $0.60 | 0.107 | −0.073 | −0.034 | −0.19 |

**Prediction:** with c ≈ $0.25–0.40, arm B ≈ **+$0.2 to +$0.5/trade, t ≈ +2 to +4**.

Two effects the table does **not** capture:
1. The trail is path-dependent ⇒ arm B is genuinely **not** `−gross_A`.
2. 58.3% of arm-A trades hit a full stop → those become arm-B winners that then trail, while arm-B losers
   stay capped at −1R. This asymmetry **favours the flip** beyond the table.

Falsification: arm B ≤ 0 net $/trade ⇒ the CF carries no exploitable directional information in either
sense at M30-M15, and arm A's loss is spread, not signal.
