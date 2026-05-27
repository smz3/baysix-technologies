# Session Handover — May 24, 2026 (Night — baysix-engine 5-step restructure + full .claude/docs cleanup, all pushed)

## What Was Accomplished This Session

### 1. baysix-engine restructured to a 5-step spine (merged to main, pushed)
Collapsed three competing naming schemes (framework §-letters, legacy `stepN`, engine-suffix tools) into one. The `alpha-engine` umbrella was **dissolved**.
- **Top level now:** `research-engine/`, `trading-engine/` (was `execution-engine/`), `market-state-engine/`, `context-engine/`, `architecture-decisions/` (was `adr/`).
- **research-engine internals = 5-step funnel:** `step1_ideation` (layers: deployment-profile · hypothesis-metric-lock/ideas · data-structure-gate/vr+regime), `step2_signal` (signal-build · sizing), `step3_in-sample` (gross-baseline · cost-haircut · event-based), `step4_validation` (oos-walkforward-cpcv · full-cost · monte-carlo · snooping-audit), `step5_forward-fit` (paper-forward · portfolio-fit-gate).
- **core/ split:** `core/lib/` (corelib·dataset·db·idea_bank·tools) + `core/engines/` (cost-venue·ic·factor-model·lean) — tools the steps CALL, never filed under a step.
- **Path surgery:** ROOT depth +1 for `core/lib/*` modules; `sys.path` `core`→`core/lib`; `pyproject.toml` pythonpath/testpaths; `idea_bank/signals.py` IDEAS_DIR/DASHBOARD/DB_PATH; `manifest.json` + `.gitignore` depathed. **67 tests pass; scanners + idea-bank verified.** 250 git renames (history preserved).
- Map in [research-engine/MAPPING.md](../workspace/baysix-engine/research-engine/MAPPING.md). Merged `reorg/baysix-framework` → `main` via fast-forward; branch deleted. baysix-engine HEAD `57757e3`, pushed.

### 2. BAYSIX_FRAMEWORK.md is now the single authoritative spec
Folded ALL gate thresholds from the old `QR_pipeline_v3.md` + `QT_framework_unified.md` inline, switched the funnel to the step1–5 vocabulary, removed the §A "B./D." letter clash. **Deleted both source docs** (content absorbed, no live links left). Agent-routing table updated to the slimmed roster.

### 3. Retired the vault; moved B2B/MT5 knowledge into baysix-engine
Vault had gone cold. Live content rehomed (committed in baysix-engine `57757e3`): 7 B2B mechanics pages + backtest-results → `research-engine/strategies/b2b-xauusd/b2b-markdowns/b2b-knowledge/`; mt5-ea-architecture + samtc-overview → `trading-engine/mt5-path/b2b-mt5/Documentation/`. Then **nuked** `vault/`, the 3 vault skills (ingest/lint/query), and stale `sigma-engine-map` (dead `sigma_core`/`sigma-crypto` refs).

### 4. Deleted AI_REFERENCE.md — single brain file now
Its only unique content (Risk Rules, Worktree Protocol) folded into [CLAUDE.md](../CLAUDE.md); the rest duplicated CLAUDE.md and had drifted stale (IC-mandate, 8-step map, `cio`/`peer-reviewer`).

### 5. Slimmed the agent/skill roster (solo-Pro efficiency)
- **Agents 6 → 3:** kept code-reviewer, quant-researcher, quant-developer. **Cut** quant-trader (redundant with health skills). **Converted** risk-manager → `/risk-check` skill; memory-curator → folded into `/update-memory` (now acts directly, no spawn).
- **Refreshed every stale description/path** (dead `sigma-crypto`/`sigma-lean`/`sigma-mt5`/`SAMTC`/8-step → current 5-step/trading-engine paths) across the 3 agents + skills, so they actually auto-trigger. `check-lean-health` was describing the dead BTCUSDT crypto strategy — fixed to the XAUUSD gold algo.
- Repointed all cut-agent references in CLAUDE.md + BAYSIX_FRAMEWORK.md routing table + the 2 agent bodies (`risk-manager`→`/risk-check`, `quant-trader`→health skills, `memory-curator`→`/update-memory`).

### 6. Housekeeping
- Removed 2 stale merged git worktrees (15 MB); untracked `scheduled_tasks.lock` + gitignored it and `agent-memory/`.
- Purged `Memory/agent_log.md` to a clean template (pre-restructure entries removed; append-on-run kept for the 3 agents).
- **Created [DEPLOYMENT_HANDOVER.md](../DEPLOYMENT_HANDOVER.md)** — was referenced 3× in CLAUDE.md but never existed (Cloud Run blocker: Cloud Build org-policy → use native GitHub integration).
- Trimmed CLAUDE.md (removed Cloud Deployment Rules section, collapsed Execution Model).

---

## What Is NOT Done / Still Open

- **State files still empty** (SessionStart hook flags this): `Memory/risk_parameters.md` (3 standing Deployment Profiles: just-markets-solo, darwinex-track, ibkr-pod), `Memory/strategy_state.md`, `Memory/research_queue.md`. Schema is LOCKED; population is the next build.
- **Empty step-layer stubs** in research-engine carry one-line READMEs but no code yet (signal-build, gross-baseline, cost-haircut, event-based, full-cost, monte-carlo, paper-forward, deployment-profile).
- **IB-001 (XAUUSD B2B) has not been run through the new 5-step funnel** end-to-end.
- **LEAN runnability still UNVERIFIED** (Docker runtime + XAUUSD data) — `/run-backtest` and `/check-lean-health` may not actually execute yet.

---

## Running Processes

| Task | Status | Notes |
|------|--------|-------|
| (none) | Stopped | All work committed and pushed |

---

## Priority for Next Session

1. **Populate the state files** now that structure is locked: start with `Memory/risk_parameters.md` (the 3 Deployment Profiles) + a `Memory/strategy_state.md` manifest for IB-001. This also clears the empty-state warning the SessionStart hook prints.
2. **Run IB-001 (XAUUSD B2B) through the new funnel** end-to-end — single-asset timing edge, so primary metric is hit-rate / MAE-MFE / expectancy, NOT IC. Prior finding: honest edge +0.309 R/trade, 1,084 trades, z=+7.19.
3. **Verify LEAN actually runs** (`/check-lean-health` then `/run-backtest`) before trusting any backtest path.

---

## Key Decisions Made

- **One vocabulary end-to-end:** 5 numbered steps are the spine; layers inside; engines are tools in `core/engines/` that steps CALL (never filed under a step). Trading is a separate `trading-engine/`.
- **market-state + context are SHARED, not forked** — same regime code research validates and trading reads, to avoid train/serve skew.
- **BAYSIX_FRAMEWORK.md is the single source of truth**; QR_pipeline_v3 + QT_framework_unified deleted.
- **CLAUDE.md is the single always-on brain file**; AI_REFERENCE deleted; reference detail lives in linked on-demand docs.
- **Agents only where isolation/scale pays** (code-reviewer, quant-researcher, quant-developer); everything else is a `/`-skill run inline. Solo-Pro posture: lean on skills + main thread, agents are occasional heavy machinery.
- **agent_log reliability:** declined a dedicated command (same fragility); a `SubagentStop` hook is the right lever if ever wanted — not built.

---

## Blockers

None. (sigma-research Cloud Run deploy remains blocked by org policy — see DEPLOYMENT_HANDOVER.md — but it's not on the critical path.)

---

## Repo State (all pushed to GitHub)
- **sigma-brain** `master` → `520c5c5` (pushed). Commits this session: framework consolidation, vault retirement, AI_REFERENCE removal, roster slim, ref fixes, deployment doc + trim.
- **baysix-engine** `main` → `57757e3` (pushed). 5-step restructure + B2B/MT5 knowledge import.
