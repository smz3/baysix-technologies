# Session Handover — May 22, 2026 (Evening #2 — pipeline foundation: DuckDB spine + tested math library + Monte Carlo lock-in)

## ⚠️ READ FIRST
This session built the **data + math foundation** for the research pipeline and committed/pushed both repos. The pipeline can now run end-to-end once the first dataset is loaded. Next session = the **Step 2 honesty audit** (first real data in). Discuss-before-build and brevity still in force.

---

## What Was Accomplished This Session

### 1. Architecture decided + locked as ADR-0001
[adr/0001-research-pipeline-data-and-math-foundation.md](../workspace/baysix-engine/alpha-engine/adr/0001-research-pipeline-data-and-math-foundation.md) (NEW `adr/` convention at alpha-engine level). Locks:
- **DuckDB + Parquet** as the whole local data layer. Research tracking (signals/results/trials) → DuckDB tables. Step-2 market bars → Parquet files queried by DuckDB (NOT a relational DB). One engine covers both.
- **Math = a canonical tested Python library**, not a database. Formulas are logic → version-controlled + unit-tested.
- **Supabase = parked** (Syafiq has a free account). It's the future home for (a) the deferred AI-agent swarm coordination layer and (b) feeding the live sigma-quant web dashboard. NOT in the critical path now.
- Includes alternatives + revisit-triggers per the ADR-governance rule.

### 2. DuckDB spine built + installed
- **Installed** a clean venv at `research-engine/.venv` with `duckdb 1.5.3, pandas 3.0.3, numpy 2.4.6, scipy 1.17.1, pyarrow, pytest`.
- **6-table schema** in [core/db/schema.sql](../workspace/baysix-engine/alpha-engine/research-engine/core/db/schema.sql): `signals · step_runs · metrics · trials · datasets · oos_budget`. Built by `core/db/init_db.py` → `core/db/research.duckdb` (git-ignored).
- **Signal-centric, not step-centric:** one signal = one row, its step results link to it (fixes the "IB-001 cloned across 6 step folders" smell Syafiq flagged). Markdown scoreboards become generated views (not yet auto-generated — manual for now).
- **Read the DB:** `python core/tools/db_view.py` (terminal) or `python core/tools/db_ui.py` (browser at :4213).

### 3. Canonical math library + 19 passing tests
[core/corelib/](../workspace/baysix-engine/alpha-engine/research-engine/core/corelib/) — single source of truth, every step imports it:
- `metrics.py`: information_coefficient (Spearman), cross_sectional_ic, icir, effective_n (Newey-West/Bartlett), ic_tstat_timeseries (t=IC·√N_eff), ic_tstat_cross_sectional (t=ICIR·√T).
- `significance.py`: sharpe_ratio (per-period), probabilistic_sharpe_ratio (PSR, kurt non-excess so (kurt-1)/4), expected_max_sharpe + deflated_sharpe_ratio (DSR), block_bootstrap_ic (MC var 2), permutation_test_ic (MC var 1), optimal_block_length (n^(1/3) heuristic; Politis-White = upgrade path).
- `FORMULAS.md`: plain-language reference (what/why/mental model per metric) — for Syafiq + recruiters.
- **UNITS RULE locked** (per-period everywhere) with a test that fails on annualised input — kills the bug that recurred 3× ([[per-period-sharpe-units-rule]]).
- Run the lock: `python -m pytest -q` from research-engine → **19 passed**.

### 4. Monte Carlo locked into the pipeline (3 variations)
- HTML map [Braindump/quant_pipeline_flow.html](../Braindump/quant_pipeline_flow.html): Step 5 gained Gate 5 (shuffle + block bootstrap = significance); Step 8 gained synthetic-path risk sim (drawdown dist / risk-of-ruin / fractional-Kelly).
- Recorded as locked decisions in [OOS_RIGOR_SCOREBOARD.md](../workspace/baysix-engine/alpha-engine/research-engine/step5-oos-rigor-gate/OOS_RIGOR_SCOREBOARD.md) #10 and [RISK_DEPLOY_SCOREBOARD.md](../workspace/baysix-engine/alpha-engine/research-engine/step8-risk-deploy/RISK_DEPLOY_SCOREBOARD.md) #9.
- **Why the split:** synthetic paths (var 3) can't live in Step 5 — they need net-of-cost sized returns that only exist after Step 6.

### 5. IB-001 reset (NOT deleted) + folder tidy
- Reset only the research chain: deleted step3 run + 3 notebooks. **KEPT** b2b-py engine (14 files) + b2b-markdowns (7 files incl. the +0.309 R/trade phase-B evidence) per Syafiq's explicit "do not delete the engine code."
- Tidied: all new machinery grouped under `core/` (corelib + db + tools). `requirements.txt` folded into `pyproject.toml`. pytest cache redirected into `.venv`. Root now only has step folders + 2 config files.

### 6. Committed + pushed both repos
- **baysix-engine** `acb8d41` on `main` (pushed to github.com/smz3/baysix-engine).
- **sigma-brain** `de404fd` on `master` (pushed to github.com/smz3/sigma-brain).

---

## What Is NOT Done / Still Open

- **Leftover IB-001 stub folders** under steps 4, 5, 6, 8 + RN-001 (step7) + scoreboard rows — these were NOT cleaned (Syafiq moved on before deciding). The DB approach will dissolve them eventually. `b2b_gold_algo.py` (step6, real LEAN code) should be KEPT if cleaning. Decide next session.
- **Markdown scoreboards are still hand-edited**, not yet auto-generated from DuckDB (the ADR's end state).
- **Step 2 honesty audit not started** — the actual first-data unblocker.
- **AI-agent swarm** — deliberately deferred to a future ADR-0002.

---

## Running Processes

None.

---

## Priority for Next Session

1. **Step 2 honesty audit — CS-GOLD-JM-H1.** Load XAUUSD H1 → clean PIT → write Parquet → register a row in the `datasets` table → seal the OOS (Horizon Lock) → init `oos_budget`. This is the first real data into the system and the original unblocker. Use the `core/` machinery (DuckDB + the catalog) — don't rebuild it.
2. Re-express the kept B2B signal (b2b-py) as a standardized forecast, then **Step 3 IC** using `corelib.metrics` → write the first `metrics` rows + a `step_runs` verdict. First real end-to-end pass.
3. (Optional cleanup) clear the leftover IB-001 stub folders in steps 4/5/6/8 — keep b2b_gold_algo.py.

---

## Key Decisions Made

- **DuckDB + Parquet, one local engine** for both research tracking and market data (ADR-0001). SQLite rejected (weaker analytics); Postgres/Supabase reserved for the swarm + web dashboard.
- **Math lives in tested code, not data.** corelib is the single source; UNITS RULE enforced by tests.
- **Monte Carlo = 3 variations**, split Step 5 (significance) / Step 8 (risk).
- **IB-001 reset ≠ delete.** Engine code + evidence preserved; only the un-run measurement chain wiped.
- **Folder hygiene:** machinery under `core/`; `.venv` and root config files (`pyproject.toml`, `.gitignore`) stay at root by convention.

---

## Blockers

None. Foundation is in place and tested; Step 2 can start immediately.

## Process notes (honor next session)
- Run pipeline Python from `research-engine/` with `./.venv/Scripts/python.exe` (or activate the venv). `python -m pytest -q` must stay green.
- baysix-engine is ONE git repo (`main`); sigma-brain is separate (`master`). Commit research code to baysix-engine, the HTML map + handovers to sigma-brain.
- Discuss-before-build still in force ([[feedback_discuss_before_build]]). Brevity mandatory. Spell out abbreviations in research docs ([[feedback_doc_abbreviations]]). Confirm before irreversible/outward actions.
