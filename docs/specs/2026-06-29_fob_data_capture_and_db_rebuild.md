# FOB Data Capture + DB Rebuild — Spec

**Date:** 2026-06-29 · **Idea:** FOB-001 · **Status:** schema BUILT (migration 035); CSV contract + ingest + EA-emit = OPEN tasks.

This is the durable plan for the next agent. It supersedes the ad-hoc `tester_zones`
(BRC-shaped) capture for FOB. Read [[fob_cmp_storyline_model]] first.

---

## 1. Why we rebuilt

Three problems with the old `tester_*` schema:

1. **`tester_runs` could not tell emitter from trader** — no `run_role`; trader-only PnL
   columns (`n_trades`, `net_profit_usd`, …) sat on emitter runs as dead blanks.
2. **`tester_zones` was BRC-shaped** — 5-pointer `p1..p5`, `break_kind`, `consolidated_into`.
   FOB is a 4-pointer (P1, P3, L1, L2). The "P5 you saw" was BRC's coat on FOB's back.
   This is also how the **storyline screen silently queried BRC zones** (the id18 contamination).
3. **FOB is a SEQUENCE/CYCLE model, not a flat zone bag.** A universal zone table throws
   away the storyline linkage (`seq` = cycle, `cf_idx` = CF order) that FOB's edge depends on.

**Design principle (so we never rebuild again):**
- **Stable spine = shared, universal** (the run, the asset, the trades, the scorecard).
- **Volatile payload = strategy-owned** (FOB's cycles/events/zones; BRC later gets `brc_zones`).
- Anything genuinely common to every asset+model gets a real column; everything model-specific
  rides in a `meta` JSON column or a strategy-owned table. New asset = new `instruments` row;
  new model = new payload tables; new param = `params`/`meta` JSON. **No more ALTER-driven rebuilds.**

---

## 2. The FOB system (so capture matches the method)

Core SOP: **CMP → BO → VR → CF** (never enter the first BO).
- **PBO** = Primary BreakOut = the CMP breakout, the setup anchor.
- **VR** = Valid Retracement = the **first opposite break, exactly one TF below**; happens **once**;
  it tells you **which TF you're trading**. Body must clear (wick doesn't count).
- **CF** = Confirmation = the continuation you actually enter on (in-zone = best). 2nd CF matters in sideways.
- **HRCF** = High-Risk CF (skip a TF; cheaper entry). LR CF = adjacent TF below (pricier, safer). HRCF currently PARKED in the classifier.

**CYCLE (corrected 2026-06-29):** a cycle = **PBO → VR → CF1 → CF2 → CF3…**, anchored by the PBO.
**A NEW PBO starts a NEW cycle.** (NOT "repeats when price breaks the VR" — that was wrong.)
Maps to EA fields: `seq` = per-setup_tf PBO ordinal (= cycle id), `cf_idx` = CF order in the cycle.

**ALIGNMENT = AWARENESS, not a gate (corrected 2026-06-29):** we do **not** trade only when all TFs agree.
We record each higher TF's **live state** (esp. **W1 = Bias**, **D1 = Direction**) so we trade *aware* of context.
Which way we trade **depends on which TF setup we pick**. A TF's current direction = the direction of the
**live cycle one TF below it** (lower TF controls higher). This is why the full-stack align gate (id18) was
conceptually wrong, not just empirically flat. Gold example (2026-06-29): MN1 bullish (live W1 CF5, strong bull)
BUT W1's breakout dir = live D1 CF1 → **Bias BEARISH**; D1 bearish w/ pending H4 CF. Long-or-short = depends on setup TF.

**VR Fresh vs Not-Fresh:** Fresh = price went straight to origin, **no close back into the VR zone** → layer in.
Not-Fresh = price **closed back inside** the VR zone (wick doesn't count) = "VR structured" → ride the trend.
Single most important behavioral flag on the zone.

---

## 3. What we capture — ROUND ONE (basics)

Per Syafiq, basics first to fuel simulations; nuances deferred (§5).

1. **Every sequence PBO → VR → CF → CF…** — per event: TF, broken level, close price, time/date, role in chain,
   `cf_idx`, and whether the close **cleared by body** (not just a wick).
2. **Direction of the sequence** (BUY/SELL story) + the Bias (W1) and Direction (D1) reads at that moment.
3. **Cycles** — each event's `cycle_id`; cycle start/end; whether it continued or died; the governing setup TF.
   **New PBO = new cycle.**
4. **T-touches & RTs on the VR** — every touch of L1/mid/L2 (+ counts), retests (`rt_count`/`rt_time`),
   and **VR Fresh vs Not-Fresh**.
5. **Per-TF awareness snapshot (MN1–W1–D1–H4–H1)** — for every event, the **live direction + CF depth** of each
   higher TF at that bar. **This is a snapshot for awareness, NOT an "all-agree" boolean filter.** The emitter
   already walks all 8 TFs in one chronological pass, so it stamps this **for free and causally** (no look-ahead).
   Stored as `fob_events.htf_state` JSON, e.g. `{"MN1":{"dir":"BUY","cf":5},"W1":{"dir":"SELL","cf":1},...}`.

Plus three FOB-essentials the basics need:
- **Which TF made the VR first** (when two TFs break together, the VR decides which TF you trade).
- **High-Risk vs Low-Risk tag** on each CF (skip-TF vs adjacent-TF).
- **VR-zone broken with a strong close** (the reversal / Full-Margin trigger).

---

## 4. The schema (built by migration 035)

**Causality rule:** every derived/joined feature must use only data ≤ the event's `bar_time`.
Prefer emitting from the EA (the chronological oracle can't see the future) — see [[orb_unsorted_tick_lookahead]].
All edges measured in **R** (asset-agnostic); $ only on trader runs, tied to an `instruments` row.

### Shared spine (universal, multi-asset)
- **`instruments`** — asset dimension; mirrors execution.db `d1_instruments`. `instrument_type` carries the
  asset class. New market = one new row. (`symbol` PK, tick_size/value, contract_size, lots, data_source, meta JSON.)
- **`tester_runs`** — provenance parent. **`run_role` ('emitter'|'trader')** + `git_sha`/`git_dirty`. No PnL columns.
- **`tester_run_summary`** — 1:1, **trader runs only** (the MT5 "Excel scorecard": n_trades, net/gross/cost, PF, DD,
  win_rate, expectancy_r, sharpe, + fidelity fields). Emitter runs simply have no row here.
- **`tester_trades`** — trader payload. + `zone_id` link to the triggering zone; gross/cost/net split.

### FOB-owned payload (the storyline)
- **`fob_cycles`** — one row per PBO sequence. Identity `(run_id, setup_tf, seq)`. Anchor PBO, VR, `n_cf`,
  status (alive/invalidated/complete), invalidation. **New PBO = new row.**
- **`fob_events`** — chronological PBO/VR/CF ledger. `cycle_id`, `event_tf`, `label`, `cf_idx`, direction,
  swing/bar times, level, close, `body_clears`, and **`htf_state` JSON (the per-TF awareness snapshot)**.
- **`fob_zones`** — tradeable 4-pointer + full behaviour: `l1/l2/mid`, `p1/p3`, touches `t1/t2/t3` (+counts),
  retests `rt_count/rt_time`, **`vr_fresh`**, lifecycle (`confirm/invalidation/continued/alive_at_end/bars_alive`),
  excursion `mfe_r/mae_r/realized_r`, `zone_key/is_primary/superseded_by`.

BRC payload (`brc_zones`, 5-pointer, russian-doll) is deferred to its own future migration — it does **not** share FOB's tables.

---

## 5. Phase 2 — deferred edge-sharpeners (noted, not lost)

- **Distance** of CF from the VR and from zone edges (in price/ATR/R).
- **Setup *type* per TF** — in-zone vs above vs before; high-risk vs low-risk; fresh vs structured.
- **Regime/context features** (ATR ratio, session, ADX, efficiency ratio) sampled causally at confirm time.
- **Outcome labels** at multiple horizons/TP defs for supervised modelling.
These layer on top of the basics once round-one data is feeding simulations.

---

## 6. OPEN tasks (build order)

1. **CSV contract (path A):** extend `fob_csv.mqh` (+ `brc_csv.mqh` for parity) to one canonical zone-lifecycle CSV
   that emits touches/RT/`vr_fresh`/lifecycle **and** the `htf_state` snapshot — causally from the tester.
2. **`ingest_fob`** in `research/code/io/tester.py`: `fob_events` CSV → `fob_cycles`/`fob_events`/`fob_zones`,
   tagged `idea_id='FOB-001'`, reconstructing cycle linkage. (Mirror retired `ingest_brc_zones`.)
3. **Emitter run (task 190):** `fob_baysix` on XAUUSD_dukas, 8 TF, 2016–2024, Open-prices.
4. **Re-screen storyline on FOB OWN zones (task 192):** pin run_id + assert `idea_id='FOB-001'` (isolation guard).
5. **`realized_r` SELL-sign convention (task 189):** freeze into the CSV contract.
6. Later: `brc_zones` payload migration when BRC is revived.

**Migration 035 was ADDITIVE (no drops)** — zero breakage to the 6 live BRC/seed files that read `tester_zones`.
`tester_zones` is now understood as **BRC's** 5-pointer table (it always was); **FOB stops borrowing it and uses `fob_*`**.
So the "P5 confusion" is gone: FOB no longer touches `tester_zones`. `ingest_brc_zones` stays for BRC; FOB needs the
new `ingest_fob` (task above). `delete_run` updated to clear `fob_cycles/events/zones` + `tester_run_summary` too.
