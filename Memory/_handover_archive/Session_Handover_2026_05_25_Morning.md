# Session Handover — May 25, 2026 (Morning — DuckDB schema fixes, worktree cleanup, model routing)

## What Was Accomplished This Session

### 1. DuckDB schema fixed — two framework alignment issues resolved
Both issues were in `workspace/baysix-engine/research-engine/core/lib/db/schema.sql`:

**Issue A — `family_key` added to `signals` table.**
The existing `family` column was a strategy category (`trend | mean_reversion | ...`), not the framework-defined family key (`idea_type × asset_class`, e.g. `metals-timing`). Added `family_key VARCHAR` column after `primary_metric`. This is the N_trials grouping key used by Step-4 DSR queries.

**Issue B — `family_key` denormalised into `trials` table.**
Added `family_key VARCHAR` to `trials` so DSR queries ("total trials in this family") don't require a join back through `signals`.

**signals.py updated** (`core/lib/idea_bank/signals.py`): `rebuild()` now computes `family_key = f"{rec['asset_class']}-{rec['idea_type']}"` and includes it in the INSERT.

**test_signals.py updated** (`core/lib/idea_bank/tests/test_signals.py`): added assertion `family_key == "metals-timing"` in `test_roundtrip_yaml_to_db_to_render`.

**DB was stale** — `research.duckdb` was missing `asset_mode`, `idea_type`, `primary_metric` columns (created from old schema, never rebuilt after last session's restructure). Deleted and recreated from fresh schema. All 21 tests pass.

### 2. Orphaned worktree folder deleted + CLAUDE.md worktree path convention fixed
`workspace/baysix-engine-wt-metriclock/` was an orphaned directory — not registered in `git worktree list`, left over from a prior session. Deleted.

Root cause: worktrees were being placed as siblings in `workspace/` (e.g. `git worktree add ../baysix-engine-wt-<name>`) instead of under `.claude/worktrees/`. Fixed in `CLAUDE.md` Worktree Protocol section (line ~123): now specifies the path explicitly:
```
git worktree add ../../.claude/worktrees/<name> -b <branch>
```
(run from sub-project root, e.g. `workspace/baysix-engine/`)

### 3. Model routing confirmed + quant-researcher bumped to Opus
Clarified that hooks cannot switch models mid-session — model routing works via `model:` frontmatter in agent definitions only.

Current routing (all live):
- `quant-researcher`: **opus** (changed from sonnet — major decisions, edge validation)
- `quant-developer`: sonnet (execution, code)
- `code-reviewer`: opus (was already set — high-stakes gate)
- Main CoS thread: whatever model the session started with (Sonnet 4.6 default)

---

## What Is NOT Done / Still Open

- **State files still empty**: `Memory/risk_parameters.md`, `Memory/strategy_state.md`, `Memory/research_queue.md` — schema locked but not yet populated. SessionStart hook warns each session.
- **IB-001 (XAUUSD B2B) not yet run through the new 5-step funnel** — prior finding: +0.309 R/trade, 1,084 trades, z=+7.19. Still needs cost-adjusted check and full funnel pass.
- **LEAN runnability unverified** — Docker + XAUUSD data not confirmed. Run `/check-lean-health` before any backtest.
- **Empty step-layer stubs** in research-engine have one-line READMEs but no code (signal-build, gross-baseline, cost-haircut, etc.).

---

## Running Processes

None. All work complete, no background processes.

---

## Priority for Next Session

1. **Populate state files** — `Memory/risk_parameters.md` (3 Deployment Profiles: just-markets-solo, darwinex-track, ibkr-pod) + `Memory/strategy_state.md` (IB-001 manifest). Clears the SessionStart warning.
2. **Run IB-001 through the funnel** — start at step1 (deployment profile + hypothesis-metric-lock). Primary metric = hit_rate (timing, single-asset). Prior z=+7.19 is a gross signal; cost-haircut (step3 layer2) is the next gate.
3. **Verify LEAN** — run `/check-lean-health` then `/run-backtest` before trusting any step4 backtest path.

---

## Key Decisions Made

- **`family_key` format**: `{asset_class}-{idea_type}` (e.g. `metals-timing`) — matches BAYSIX_FRAMEWORK.md example (`metals-momentum`)
- **`family_key` in `signals` is a regular VARCHAR** (not a generated column) — computed in `rebuild()` for simplicity and DuckDB version safety
- **`family_key` denormalised into `trials`** — DSR queries need family-level N_trials without joins
- **Hooks cannot route models** — only `model:` frontmatter in agent definitions and the `model=` param on Agent tool calls work
- **quant-researcher → opus** — all "is this edge real?" calls now use the strongest model automatically

---

## Blockers

None. (sigma-research Cloud Run deploy remains blocked by org policy — see `DEPLOYMENT_HANDOVER.md` — but not on critical path.)

---

## Repo State

- **sigma-brain** `master` — CLAUDE.md updated (worktree path convention). Not yet committed this session.
- **baysix-engine** `main` — schema.sql, signals.py, test_signals.py updated. research.duckdb recreated. Not yet committed this session.
