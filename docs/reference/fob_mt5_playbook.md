# FOB / MT5 Playbook

Split out of root [CLAUDE.md](../../CLAUDE.md) (2026-07-31) so the root file stays strategy-agnostic. Read this before touching `mt5/` or any FOB code — it is the source of truth so Syafiq doesn't re-explain.

---

## MT5 / EA Workflow (XAUUSD live · Just Markets)

**Trust rule (HARD)** — the **MT5 strategy tester is the arbiter**; a Python/SQL query-layer number is NEVER a gate verdict. This is the ORB look-ahead lesson ([[orb_unsorted_tick_lookahead]]): a query layer manufactured a too-good edge the chronological tester later killed. Cheap query screens are allowed only if explicitly labelled exploratory, never reported as a result.

_This section is **system-agnostic** — it is the standing MT5 workflow for whatever the active `<sys>_system` is. **FOB-001 is the live example** (`fob_system`). BRC is **PARKED** (entry fade ≈ continuation, 2026-06-24 [[brc_fade_parked_finding]]) — its files stay for reference but it is no longer the active system; read FOB's lineage, not BRC's, for current config._

**ONE EA per system, three MODES (merged 2026-07-02, v1.28.0 — was two EAs, superseded).** The old emitter/trader split ran **two different lifecycle engines** (emitter = causal tick accumulator, trader = stateless bar replay) → the live touch ladder disagreed. Collapsed into a single EA with an `InpMode` switch and **ONE causal accumulator engine**, so oracle and strategy can never drift:
- **EMIT** (default) = read-only chronological oracle: ingests **all 9 TFs**, stamps `htf_state` awareness, writes the UTF-8 lifecycle CSV → the strategy's payload tables (FOB → `fob_cycles`/`fob_events`/`fob_zones`). **NO orders — pristine + re-emittable for OOS** (the old emitter's whole reason, kept intact as a mode; order code path never runs).
- **TRADE** = the strategy: ingests only the setup pair `{n-1, n}`, opens a market position per CF on the setup TF; hosts swappable `fob_entry/ledger` modules.
- **STUDY** = T-170 forward-excursion measurement (no orders).
- Active file: **[fob_baysix.mq5](../../mt5/Experts/fob_system/fob_baysix.mq5)** — the SINGLE FOB EA. (`fob_trader.mq5` RETIRED.)

**Iteration model (no file-copy per version):** variants flip **enum modes + numeric inputs** and save a new **`.set` preset** — code is *changed* (extend an enum branch), **never replaced/duplicated**. One file per role; versions distinguished by git sha + `.set` + version stamp, NOT by copied `.mq5`. Duplicating EAs kills the tester sweep + git lineage.

**Version control / provenance (the standard):** a `<SYS>_VERSION` `#define` in `<sys>_types.mqh` + an auto-generated `<sys>_version.mqh` (git sha/branch/dirty/build-time), regenerated before every compile, so the trader EA **prints its sha + dirty flag on init** — a DIRTY-tree number is not reproducible → exploratory only. Frozen tested inputs ship as versioned `.set`.
- **One generator: `python research/code/infra/gen_version.py <system>`** (e.g. `fob` | `brc`) → writes `mt5/Include/<sys>_system/<sys>_version.mqh` (gitignored, derivable). `gen_brc_version.py` is a back-compat shim. **Run it before every headless compile.**
- **FOB is now one EA (all modes) that `#include`s `fob_version.mqh`** and prints `[FOB <MODE>] v<ver> | git <sha>-DIRTY(exploratory) | built …` on init — EMIT included (provenance on the oracle too). BRC-trader still wired the same way; the BRC emitter (read-only, re-emittable) keeps the manual `BRC_VERSION` stamp only.
- Keep `#property version` in lockstep with `<SYS>_VERSION` (they drifted once: fob baysix `1.19.1` vs `1.20.0` — fixed). The MQL5-Market `xxx.yyy` format warning on `1.20.0` is benign; Market layer deferred.
- Releases/`.ex5` artifacts + MQL5-Market protection layer deferred until sharing.

**Build (headless):** compile via MetaEditor64 CLI; `/inc` MUST point at `mt5/` (the MQL5 root containing `Include/`), NOT `mt5/Include` — else error 106 cascade. Compile log is UTF-16. ([[brc_compile_workflow]])

**Deploy:** reach the JM MT5 terminal (hash E7DB) via `mklink /J` junctions in Experts + Include (no elevation; `ln -s`/symlink fail on this host). MetaEditor → Refresh to see new files. ([[brc_terminal_junction_deploy]])

**Tester model (HARD, set 2026-06-29 by Syafiq):** the FOB EA runs and is tested on **REAL TICKS only** (Model=4, dukascopy from 2016-06-01) in **every mode** (EMIT/TRADE/STUDY). **Open-prices is BANNED for FOB** — FOB is a tick-resolution model (intrabar touch/retest path matters), so an open-prices run is invalid, not merely slower. Note: the causal tick accumulator (`FobAcc*`) advances the touch ladder tick-by-tick **in the tester too** (that's the whole point) — only the LIVE-chart backfill + intrabar-dead dimming are `bool live = !MQLInfoInteger(MQL_TESTER)`-gated (chart niceties, kept out of the CSV so OOS re-emits stay byte-identical). Trader fills are level-based (limit at zone level) to stay deterministic ([[brc_trader_realtick_model]]). Tester needs UTC offset.

**Conventions:** new MQL5 files (`.mq5` + `.mqh`) = lowercase snake_case (`fob_system`, `brc_system`); Sigma CamelCase is legacy, leave it ([[mql5_lowercase_filenames]]). ORB EAs live in their own `orb_system` namespace, magic-number per EA. Each system's `.set` presets auto-mirror to the JM terminal via `mklink /J` junctions ([[fob_presets_junction_deploy]]).

---

## FOB-001 — Canonical Knowledge (don't re-derive; deep refs at the bottom)

FOB = First Opposite Breakout, the active XAUUSD idea. **Read this section before any FOB work** — it is the source of truth so Syafiq doesn't re-explain. Authoritative deep docs are linked at the end; this is the load-every-session distilled form.

> **Lifecycle rule (HARD):** only the **ONE active idea** gets a baked canonical section here. When it parks (as BRC did), **collapse it to a one-line "parked, see lineage" pointer** and promote the new active idea's canonical in its place — never leave a stale parked strategy baked as if it were live.

**What FOB IS (the model):** REACTION modeling on **CMP (Current Market Price)**, NOT prediction and NOT a win-rate-lifting classifier. Every PBO/VR/CF is a **tagged fact that already printed**; a trade is *a position within a confirmed nested storyline* (W1⊃D1⊃H4⊃H1⊃M30⊃M5…), not "a signal." Higher TF = **bias/context**, lower TF = **execution trigger**. ([[fob_cmp_storyline_model]])

**Core SOP — `CMP → BO → VR → CF`** (never enter the first BO):
- **PBO** = Primary BreakOut = the CMP breakout / setup anchor. Body must clear the level (wick ≠ count).
- **VR** = Valid Retracement = the **first opposite break, exactly one TF below**; happens **ONCE**; it tells you **which TF you're trading**. When two TFs break together, **whichever made the VR first** dictates the TF.
- **CF** = Confirmation = the continuation you actually enter on (in-zone = best; 2nd CF matters in sideways). **LR CF** = adjacent TF below (safer, premium price). **HRCF** = skip one TF (cheaper entry, higher risk; classifier currently PARKED).

**CYCLE (HARD):** a cycle = **PBO → VR → CF1 → CF2 → CF3…**, anchored by the PBO. **A NEW PBO starts a NEW cycle** — NOT "repeats when price breaks the VR." Maps to EA fields: `seq` = per-setup_tf PBO ordinal (= cycle id), `cf_idx` = CF order within the cycle.

**ALIGNMENT = AWARENESS, not a gate (HARD):** we do **NOT** trade only when all TFs agree. Record each higher TF's **live state** (esp. **W1 = Bias**, **D1 = Direction**) so we trade *aware* of context; the trade direction **depends on which TF setup we choose**. A TF's current direction = the direction of the **live cycle one TF below it** (lower TF controls higher). This is why the full-stack-alignment **trade gate was REJECTED** (result_id 18) — conceptually wrong, not just flat. *Example (gold, 2026-06-29): MN1 bull (live W1 CF5) but W1's dir = live D1 CF1 bear → Bias BEARISH; D1 bear w/ pending H4 CF → long-or-short depends on the setup TF.*

**VR Fresh vs Not-Fresh:** Fresh = price went straight to origin, **no close back into the VR zone** → layer in. Not-Fresh = price **closed back inside** the VR zone (wick ≠ count) = "VR structured" → ride the trend. The single most important behavioral flag on a zone.

**Data capture (schema LIVE, migration 035):** FOB owns its storyline payload — `fob_cycles` / `fob_events` (+ `htf_state` awareness JSON) / `fob_zones` (4-pointer + touches/RT/`vr_fresh`/lifecycle). FOB does **NOT** use `tester_zones` (that's BRC's 5-pointer table — the old P5 confusion). Shared spine: `tester_runs.run_role` (emitter|trader), `tester_run_summary`, `tester_trades`. Emit causally from the EA (path A); never Python-derive lifecycle (look-ahead). Round-1 = basics; CF↔VR distance + setup-type + regime/labels are deferred phase-2.

**Deep refs (open these for full detail, don't paste into context wholesale):** [FOB manual dissection](../../research/papers/fob/FOB_breakout_system.dissect.md) (the full Bonker manual) · [CMP storyline model](../specs/2026-06-27_fob_cmp_storyline_model.md) · [storyline-alignment findings](../specs/2026-06-27_fob_storyline_alignment_findings.md) (⚠️ numbers computed on BRC-contaminated `tester_zones` run_id 5 — VOID for FOB until re-screened on FOB own zones, task 192) · [data-capture + DB rebuild spec](../specs/2026-06-29_fob_data_capture_and_db_rebuild.md).
