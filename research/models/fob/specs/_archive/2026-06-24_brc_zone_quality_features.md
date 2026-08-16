# BRC Zone-Quality Feature Emission + Separation Test (task #144)

**Date:** 2026-06-24
**Idea:** BRC-001 · gate context G3 (robustness / conditional edge)
**Status:** DRAFT — pending Syafiq sign-off (nothing built/logged yet)
**Motivation result:** IS-03 (result_id 7) — confluence-as-confirmation failed; bulldozed cohort intact.

---

## 1. Problem (why this spec exists)

- Entry *timing* is exhausted: L1 / MID / depth(T3) / M15-confirm all tested, all net-negative.
- The bleed is one cohort: **~45% of trades are "bulldozed"** — never go green, stopped out, dead in 2–5 min — and they are **~half of all loss** (IS-02 55%, IS-03 48.5%).
- Task 142 proved this cohort is **not** separable by *coarse* labels (session / dir / TF / zone-age).
- Open question, never answered: **is there an arm-time feature that separates bulldozed zones from survivors?** If yes → a zone-picking gate. If no (on OOS) → falsification #3 → kill BRC-continuation.

**This spec = (A) which features to emit, (B) exact no-look-ahead definitions, (C) the pre-registered separation test that decides.**

---

## 2. The no-look-ahead boundary (HARD)

- A zone "exists" and is armable at **`p4_time` (== `confirm_time`)** — the bar that confirms the 5-pointer.
- Two legal decision points, two feature classes:
  - **ARM-time features** — computable from bars **≤ p4_time**. Govern "do I place the L1 limit at all."
  - **FILL-time features** — computable from bars **≤ the L1-touch bar (t1)**. Govern "cancel the resting limit as price arrives."
- **All features computed inside the emitter** ([brc_baysix.mq5](../../mt5/Experts/brc_system/brc_baysix.mq5)), the chronological oracle — **never** a side Python derivation off HTF bars. This is the [[orb_unsorted_tick_lookahead]] trust rule: a query-layer feature that peeks is exactly how the ORB edge was manufactured.
- Open-prices model preserved (close-only detection); features use **closed bars only**.

---

## 3. Features to emit

All emitted as new columns on the zone CSV → `tester_zones`. `N_ATR` default 14 (the ATR lookback), swept later only if a feature shows signal.

### Arm-time (≤ p4) — the primary battery

| # | feature | definition (closed bars ≤ p4) | a-priori story for "bulldozed" |
|---|---|---|---|
| F1 | `width_atr` | `\|l1 − l2\| / ATR(N_ATR)` at p4 | tight zone in high vol → trivially blown through |
| F2 | `break_impulse_atr` | `\|p4_close − p5_price\| / ATR(N_ATR)` | how hard P4 broke P5 = breakout conviction |
| F3 | `break_body_frac` | break-bar body / break-bar range (P4 bar) | weak/wicky break = unconvinced |
| F4 | `prior_touch_count` | # closes that pierced the L1 level between p2_time and p4_time | already-tested level = exhausted demand/supply |
| F5 | `dist_to_p4_atr` | `\|l1 − p4_close\| / ATR(N_ATR)` | how far price must retrace to fill = staleness/odds of fill-then-run |
| F6 | `htf_align_h4` | sign match: H1 zone dir vs **last H4 swing-break dir** at p4 (−1 / 0 / +1) | counter-H4 zones get run over (**your Q1**) |
| F7 | `htf_align_d1` | sign match: H1 zone dir vs **last D1 swing-break dir** at p4 (−1 / 0 / +1) | counter-D1 trend = swimming upstream (**your Q1**) |
| F8 | `htf_break_age_h4` | bars since the governing H4 break (proxy for HTF trend freshness) | stale HTF trend = mean-reversion risk |

- **F6/F7 (your H4+D1 confluence) ship as features, not gates.** The emitter already detects swings/breaks per-TF; H4 & D1 are added as extra detection series, their *break direction at p4* recorded. Sign of effect is unknown (counter-trend bulldoze vs trend gapping past the retest) → **measure first, gate only if it separates.**

### Fill-time (≤ t1 touch bar) — second battery, only if arm-time is weak

| # | feature | definition | story |
|---|---|---|---|
| G1 | `approach_velocity_atr` | displacement over the K bars into the t1 touch / ATR | the bulldozed cohort dies in 2–5 min → speed of arrival is the most causally-direct signal |
| G2 | `approach_bars` | # bars from p4 to t1 touch | fast snap-back vs slow drift |

- G1/G2 enable a **resting-limit cancel** rule (don't fill if price is arriving too violently) — a different control surface than arm-time selection.

**Explicitly deferred:** TPO / Value-Area (LVN-vs-HVN), task #147. Richest story but expensive + unbuilt. Only build if F1–F8/G1–G2 fail to separate. Cheap causally-aligned features get first swing.

---

## 4. Pre-registered separation test (this is the gate that decides)

Mirrors task 142 discipline — registered **before** looking at OOS.

- **Label (primary):** `bulldozed = mfe_r < 0.10` (zone never earned 0.1R in its favour). Secondary robustness label: `never_green = mfe_r <= 0`. Survivors = the complement.
- **Sample:** IS zones 2016-06 → 2024-06 (emitter, all primary zones). **OOS sealed:** 2024-07 → 2026-06 (task #126 emit), untouched until the IS winner is frozen.
- **Method (per feature, univariate first):**
  - point-biserial / AUC of each feature vs the bulldozed label on **IS only**;
  - decile (or sign, for F6/F7) bulldozed-rate table with **min-n ≥ 50 per bin**;
  - report **effect size + bootstrap CI**, not just a p-value (t-stat reported, never an auto-kill).
- **Promotion thresholds (pre-registered):** a feature is a candidate gate only if, on IS, it moves bulldozed-rate by **≥ 10 absolute pts** between its best/worst bin (or aligned/counter for F6/F7) at min-n, **and** the monotonicity/sign is economically sensible.
- **Confirm on OOS:** candidate gate must hold the same sign + **≥ ½ the IS effect** on the sealed OOS. Only then → frozen gate via `strategy_log.log_change`.
- **Multivariate:** only if ≥2 univariate features survive — a small logistic / shallow tree on the survivors, same OOS seal. No kitchen-sink fitting.

### Decision outcomes
- **≥1 feature separates on OOS** → adopt as zone-picking gate, re-score net $/trade vs IS-01 control (result_id 3). This is the path back to a live edge.
- **No feature separates on OOS** → **falsification #3**. Combined with base-edgeless (#1) + confluence-confirm-failed (#2) → BRC-continuation is dead; pivot atom to H_alt-1 fade (#131) or shelve. TPO (#147) is the only reprieve and must be explicitly chosen.

---

## 5. Implementation surface (for the build task, not this draft)

- New `brc_quality.mqh` include: ATR(N) ring + F1–F8/G1–G2 calculators, called at p4 confirm (arm) and at t1 touch (fill).
- Add H4 + D1 swing/break detection series to the emitter (reuse `brc_swings.mqh` / `brc_breakouts.mqh`, parametrized per-TF as IS-03 did for M15).
- Append columns in [brc_csv.mqh](../../mt5/Include/brc_system/brc_csv.mqh); bump `BRC_VERSION`.
- Migration: extend `tester_zones` + [ingest_brc_zones.py](../../research/code/io/ingest_brc_zones.py) for the new columns.
- **Cost:** +HTF series + per-zone ATR/impulse calc. Full 8.5yr emit currently ~13min (task 129); estimate the delta before committing, flag if re-emit cadence makes it painful.

---

## 6. What ships in which order

1. **F1–F8 arm-time battery** (incl. your H4+D1 confluence as features) + the separation test. ← the real experiment.
2. **G1–G2 fill-time** only if arm-time is weak.
3. **TPO (#147)** only if both batteries fail.

**Falsification clock:** if the OOS separation test comes back empty, that is the honest death certificate for BRC-continuation — not another reframe.
