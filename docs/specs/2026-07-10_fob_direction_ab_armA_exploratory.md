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

---

# VERDICT — 2026-07-10, same day: **PREDICTION FALSIFIED. BOTH DIRECTIONS LOSE.**

Both arms re-run on ONE clean binary (**v1.40.0, git `46216a0`, `FOB_GIT_DIRTY=false`**), presets differing by
`InpInvertDir` **only**. `strategy_log` **112** (FALSIFIED). Ledgers archived to
`research/outputs/fob_ab_direction/armA_normal_*.csv` / `armB_inverted_*.csv`.

| arm | n | net $/trade | SE | t | R/trade | win-rate | maxDD |
|---|---|---|---|---|---|---|---|
| A normal (full-span) | 8,284 | −0.6188 | 0.130 | −4.76 | −0.180 | 29.79% | $5,372 |
| B inverted (full-span) | 8,052 | −0.5721 | 0.130 | −4.39 | −0.208 | 29.00% | $5,244 |

IS slice (2016-06-16 → 2024-06-30), `is_run='IS-DIR-M30M15'`:
**result_id 52** normal −0.5504 (n 6,688, t−7.74) · **result_id 53** inverted −0.4944 (n 6,473, t−7.25) ·
**result_id 54** paired diff **+0.0552, t +0.46**. Full-span paired diff +0.0390, t +0.18.

## Why the flip fails — the finding

Paired on the same 8,049 CF events: A wins 29.8%, B wins 29.0%, **both lose 40.7%**, both win **0.0%**.
`corr(R_A, R_B) = −0.360`, **not −1** ⇒ the flip is *not* a mirror. The 40.7% both-lose bucket is
**spread + trail whipsaw**: price runs against A and stops it, reverses, and stops B. Inverting direction
cannot recover money the structure never paid to either side. Arm A's loss is **not invertible signal**.

The pre-registered claim that path-dependence "favours the flip" was **wrong** — it cuts the other way.

## What this does and does not touch

- **Scope: M30-M15, ALL CFs, trail-only, k=0.50.** It does **not** touch the live H4-CF3 config (result_id 50).
- Sanity: clean arm A reproduced the earlier DIRTY v1.39.0 run **exactly** (−0.6188, n=8,284) ⇒ the
  `invert=false` algebraic identity holds and the baseline is byte-identical, as designed.
- The full-span window consumed the held-out OOS block for M30-M15. **Moot** — there is no winning arm to validate.

Follow-up: **task 268** — is the 40.7% both-lose bucket smaller at H4 (where the live edge lives), and does a
fixed-RR TP shrink it? That bucket, not direction, may be the real TF-selection criterion.
