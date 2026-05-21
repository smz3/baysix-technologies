# Session Handover — May 20, 2026 (Afternoon — Engine architecture decision LOCKED + repo versioning fixed)

> Read this with the morning handover (`Session_Handover_2026_05_20_Morning.md`). The morning session
> reframed the B2B research; this afternoon session resolved the **engine architecture** and **source control**.

## What this session was about

Three intertwined problems got resolved:
1. **Two competing engine designs existed** with no winner declared — we were "jumping steps," designing on top of an undecided foundation.
2. **The architecture work was unversioned** — `Research/` (blueprint, ADRs) was in NO git repo due to a silently-broken `.gitignore` rule.
3. **The folder structure felt messy** — the question was whether to flatten `workspace/baysix-engine/` into root.

---

## Problem 1 — Two competing engine designs

| Design | What it was | Verdict |
|---|---|---|
| **`engine-design-v1.md`** (May 13) | Asset-agnostic, cross-sectional IC tearsheet lab. US + ASEAN ETFs, 5 equity signals, 6 layers. Strong statistical rigor (Newey-West, BH, bootstrap) + ADR governance. **Generic, disconnected from Syafiq's edge.** | Stub files (`ic_engine`, `regimes`, `capacity`, `report` — all `NotImplementedError`) belonged to this. Build plan never executed; notebooks 00–03 measured IC inline, bypassing the engine. |
| **Co-Work `engine-architecture/` docs** (May 20) | Gold-specific Sigma Gold System: Data → Context (Kalman/PCA) → Regime (HMM/BOCPD) → Signal/Execution (SAMTC + MT5/Darwinex). Architecturally world-class, grounded in Syafiq's real edge. Lighter on stats hygiene + no governance. Welded to one instrument. | **WINNER.** |

### The decision (now in `ENGINE_BLUEPRINT.md`)
**Adopt the Co-Work Sigma Gold System as canonical.** Transplant v1's statistical rigor + ADR governance into it. Plus three structural ideas neither framework had:

1. **Engine ≠ Strategy split.** The Engine is a universal, instrument-agnostic *measurement instrument* (the career asset). Gold is the *first adapter*. The Co-Work design's flaw was welding Kalman/PCA/HMM to gold — those mechanisms are universal and belong in the Engine; the gold-specific inputs (DFII10, GEX, gold-silver) are an adapter. Each adapter implements 4 functions: `load_data`, `build_signal`, `factor_model`, `cost_assumptions`.
2. **Validate-first, VERTICAL build order.** Both frameworks built horizontally (finish each layer over months). Rejected. Build the thinnest end-to-end slice first; thicken a layer only when a measured IC gain justifies it.
3. **Falsification gate at the top.** KILL CRITERION: if regime-conditioned B2B IC < 0.02 with t-stat < 1.5 OOS, the B2B signal is abandoned as a QR artifact. Write down what would prove you wrong *first* — also exactly what a Balyasny interviewer probes for.

### The dual-IC narrative (how a single-asset engine speaks pod-shop language)
Balyasny/Millennium are equity pod shops whose native metric is **cross-sectional** IC. Gold is time-series. The adapter split solves it:
- `gold/` adapter → **time-series IC** (the B2B/SAMTC signal, regime-conditioned — authentic live-traded edge)
- `commodities/` adapter → **cross-sectional IC** (commodity momentum across gold/silver/oil/copper/natgas + gold-silver stat-arb — pod-shop-native)

### What I'd do differently (the independent critique)
- Don't follow either framework's build order. Build vertically, validate-first.
- Defer 100% of infrastructure (TimescaleDB/Kafka). Point-in-time correctness comes from **FRED ALFRED vintages in parquet** — no database needed for the memo. DB only when live capital is committed.
- The career asset is the *measurement instrument*, not a gold bot. Keep the engine instrument-agnostic.

---

## Problem 2 — Source control was broken (now fixed)

**Topology discovered:** this is a deliberate **polyrepo**. Each project is its own GitHub repo:
- `sigma-brain` → `smz3/sigma-brain` (the brain/orchestration repo — root)
- `sigma-are` → `smz3/sigma-are`  | `sigma-mt5` → `smz3/sigma-mt5`
- `sigma-quant` → `smz3/sigma-quant` (→ Cloudflare) | `sigma-research` → `smz3/sigma-research` (→ Cloud Run) | `sigma-linkedin` → `smz3/sigma-linkedin`

`workspace/` is gitignored by sigma-brain ON PURPOSE — it's the mechanism that lets the brain repo coexist with the project repos checked out inside it.

**The bug:** `.gitignore` *tried* to track `Research/` with `!workspace/baysix-engine/Research/`, but git cannot re-include a path whose parent (`workspace/`) is excluded. So `Research/` — blueprint, ADRs, all architecture — was in **no repo at all**, unversioned.

**The fix (committed):** staged the negation level-by-level (`workspace/*` then `!.../baysix-engine/` then `workspace/baysix-engine/*` then `!.../Research/`). Now tracked by sigma-brain:
- `Research/` (20 files), `brokers/` (6), `workspace/scripts/` (1), `sigma-lean/` **source only** (44 — `backtests/`/`data/`/`storage/` stay ignored; that's 6,113 regenerable files excluded).
- Skipped `quant-data-manager/` — its only content is a `.csv` (correctly ignored as data).
- All five code repos remain independent and ignored — no embedded-repo gitlink mess.

### VS Code clarification (was the root of the confusion)
Editing `sigma-quant` shows **nothing** in sigma-brain's git (`workspace/` ignored). But VS Code's Source Control panel auto-detects all nested `.git` folders and lists each as a separate repo provider side-by-side. That panel makes them *look* linked — they are NOT. Each commits/pushes to its own remote independently.

---

## Problem 3 — Folder structure: DECISION = do not move

Flattening `workspace/baysix-engine/sigma-are` to root would make it MESSIER: sigma-brain would see `sigma-are`'s own `.git` as an embedded repo and add a hollow gitlink (broken-submodule trap). Each nesting level earns its place. **Keep the structure as-is.**

---

## What was committed + pushed this session

- **sigma-brain** `a423747` (pushed `smz3/sigma-brain`): ENGINE_BLUEPRINT.md + architecture/README.md, v1→_superseded, ADR-002 note, SAMTC + Braindump archiving, the `.gitignore` fix, and first-time versioning of Research/brokers/scripts/sigma-lean source. Also committed the existing morning handover.
- **sigma-are** `ded0bde` (pushed `smz3/sigma-are`): archived nb01, added nb03 + builder, consolidated SAMTC files into `_archive/samtc/`, bannered `regimes.py` stub as superseded, fixed `requirements.txt` (npm cruft → Jupyter deps).

### Files moved/archived (all reversible)
- `engine-design-v1.md` → `Research/architecture/_superseded/`
- `Research/SAMTC/` → `Research/_archive/SAMTC/`
- `Braindump/{PRD,BUILD_PLAN,SKILL}_sigma_pm_morning.md` → `Braindump/_archive/`
- `sigma-are/notebooks/01_*.ipynb` → `notebooks/_archive/`
- loose `sigma-are/_archive/*.csv,*.py,*.yml` → `_archive/samtc/`
- deleted empty stray `sigma-are/research/` duplicate

---

## What is NOT done / still open

Carried from the morning handover, unchanged — the architecture decision doesn't change the research path, it frames it:
- **Regime-conditioned B2B IC measurement (nb04)** — still the real research question. This IS Slice 1 of the blueprint.
- H4/D1 Dukascopy data ingestion (Syafiq providing).
- FRED API key (free at fred.stlouisfed.org) for DFII10 real yields.
- CBOE GVZ download (not urgent; realized-vol proxy sufficient for Track A).
- MQL5 simple-mode EA rewrite (after signal validates).
- Context/Regime engine builds — designed, no code. NOT the priority (validate signal first).
- The `core/` code is NOT yet restructured to the Engine/Strategy layout — deliberately deferred to Slice 1 build work (it touches imports + needs pytest runs; not a "cleanup").
- Optional: update root `CLAUDE.md` to point at `ENGINE_BLUEPRINT.md` as canonical architecture (currently references a stale `Braindump/PRD_baysix_ai_hedge_fund_v4.md` that doesn't exist at that path).

---

## Priority for next session — Slice 1 (the kill test)

This is both the blueprint's first slice AND the morning handover's "A1". Same thing.

1. Implement `core/alpha_metrics/ic_engine.py` — `compute_ic`, `compute_icir`, `compute_ic_decay`, `ic_tstat`. Crystallize the IC logic currently inline in notebook 03. (Universal — both paradigms need it.)
2. `gold/` adapter, crude proxy only: FRED **DFII10** 3-month-change z-score + 30-day realized-vol rank from existing H1 data. **No Kalman, no HMM, no PCA.**
3. Re-filter the 1,084 H1 trades to `ry_zscore < 0` AND `rv_rank < 0.4`; re-run cost-adjusted EV + measure IC on the conditioned subset. Build `notebooks/04_b2b_regime_conditioned.ipynb`.
4. **Apply the falsification gate.** Conditioned IC < 0.02 / t-stat < 1.5 OOS → STOP, B2B is not the QR artifact. Pass → license to build the rest.

Do NOT restart notebooks 00–03. Do NOT build Context/Regime engines or TimescaleDB. The next notebook is 04.

---

## Key file locations

- **Authoritative design:** `workspace/baysix-engine/Research/architecture/ENGINE_BLUEPRINT.md`
- **Navigation index:** `workspace/baysix-engine/Research/architecture/README.md` (read-order map)
- **Canonical architecture depth:** `Research/architecture/engine-architecture/*.md`
- **Diagrams:** `Research/architecture/engine-diagram/*.svg`
- **ADRs:** `Research/architecture/ADR-001..005.md` (002 = HMM, extension pending)
- **Engine code:** `workspace/baysix-engine/sigma-are/core/` (own repo `smz3/sigma-are`)
- **First adapter spec:** `sigma-are/strategies/b2b-gold/B2B_STRATEGY_MASTER.md`

## How to start next session
1. Read this handover + the morning handover.
2. Read `ENGINE_BLUEPRINT.md` (§2 falsification gate, §4 build order) — that's the law now.
3. Ask Syafiq: H4/D1 CSVs ready? FRED API key? → determines whether to start nb04 on H1 proxies (always available) or H4 first.
4. Begin Slice 1: `ic_engine.py` + `notebooks/04_b2b_regime_conditioned.ipynb`.
