# Session Handover — May 24, 2026 (Evening — Framework reset + research-engine physical reorg)

## What Was Accomplished This Session

### 1. Diagnosed and fixed the core error: IC was being forced onto the wrong strategy types
Syafiq flagged that we'd been forcing IC/ICIR metrics onto strategies where they don't belong. Root cause: IC is a **cross-sectional return-prediction** metric, not a universal one. Forcing it onto a single-asset timing edge (XAUUSD B2B) is a category error and reads as a red flag to a real pod PM.

**Fix:** metrics are now a 3-tier stack — Tier 0 Validity → Tier 1 Survival (universal) → Tier 2 Edge (idea-specific, asset-mode-gated). IC is now just one row in the Tier-2 table, legal only when asset mode = cross-sectional/multi.

### 2. Authored two source docs (Syafiq + Claude drafted), analyzed them across multiple rounds
- [QR_pipeline_v3.md](../QR_pipeline_v3.md) — 5-step research funnel with 3-tier metrics, `N_trials` snooping counter, metric→Sharpe bridge, CPCV-primary validation.
- [QT_framework_unified.md](../QT_framework_unified.md) — full system map; B (sizing) + D (costs) are **upstream inputs** to validation, C (portfolio risk) + E (monitoring) are **downstream**.

### 3. Built the canonical framework doc: [BAYSIX_FRAMEWORK.md](../BAYSIX_FRAMEWORK.md)
One Research+Trading pipeline, **parameterized by a Layer-0 Deployment Profile**, agnostic to asset (single/multi) and context (pod/fund/pod-shop). Key additions over the source docs:
- **Layer 0 Deployment Profile** — the parametric switch; sets binding kill constraint per context (ruin / capacity / drawdown-stop), venue cost model, benchmark book. Same funnel, profile swaps thresholds.
- **§C Portfolio-Fit Gate** — promotion gate (marginal Sharpe vs book, corr-to-book, capacity). Makes it pod/fund-worthy.
- **Agent routing map** — CoS-routed model (Chief of Staff holds state, dispatches one owning agent per gate; agents don't self-trigger). Two mandatory signoffs: code-reviewer before code runs, risk-manager before capital moves.
- **`N_trials` family definition LOCKED**: family = the set of trials you *compared* to pick the winner. Key = `idea-type × asset-class`. Platform NOT in the key. Declared at Step 1.

### 4. Updated CLAUDE.md + memory for the new metric-flexibility rule
- [CLAUDE.md](../CLAUDE.md): rewrote the "Who You're Talking To" IC bullet + the "Tier C QR Framing Rule" → now **strategy-dependent metric language** (do NOT default to IC). Updated the "Architecture" section (IC bullet) and the Workspace Layout tree to the new structure.
- New memories: [framework_metric_flexibility.md](../../.claude/projects/c--Users-User-Desktop-sigma-brain/memory/framework_metric_flexibility.md), [framework_schema_locked.md](../../.claude/projects/c--Users-User-Desktop-sigma-brain/memory/framework_schema_locked.md). MEMORY.md index updated.

### 5. Full physical reorg of research-engine to the framework (COMMITTED)
Reorganized `workspace/baysix-engine/alpha-engine/research-engine/` from legacy `step1-8` numbering to the BAYSIX_FRAMEWORK layout. All moves done as `git mv` (history preserved).
- `step2-dataset/`→`data/`; b2b-xauusd strategy→top-level `strategies/`; step1+vr/regime engines→`B-funnel/step1-ideation/`; cost-engine+justmarkets model→`A-inputs/cost-venue/`; step3 ic-engine→`B-funnel/step3-in-sample/`; step4/step5(oos)/step6(lean)→`B-funnel/step4-validation/`; step8 sizing→`A-inputs/`, limits+attribution→`execution-engine/` (Part 2 Trading). New empty dirs: `layer0-profile/`, `C-portfolio-fit/`, `B-funnel/step5-forward/`.
- **Path fixes:** ROOT depth +1 for relocated `vr-engine/scan.py` and `regime-engine/regime_scan.py` (else `from corelib` breaks); all `step2-dataset` data paths → `data/`; manifest.json absolute paths; IB-001.yaml data ref; .gitignore.
- **Verified:** 67 tests pass, both relocated scanners import cleanly (`--help` OK), idea-bank reads IB-001/IB-002 at new path.
- Map documented in [research-engine/MAPPING.md](../workspace/baysix-engine/alpha-engine/research-engine/MAPPING.md).

---

## What Is NOT Done / Still Open

- **baysix-engine reorg is on a branch, not merged.** Branch `reorg/baysix-framework` (commit `6e4298e`); WIP checkpoint at `6ce1c08`; base `main`. Awaiting decision: merge to main vs. route through code-reviewer first.
- **sigma-brain repo is uncommitted.** CLAUDE.md, BAYSIX_FRAMEWORK.md, QR_pipeline_v3.md, QT_framework_unified.md, and the 2 new memory files are written but not committed.
- **The three state files are still empty** (SessionStart hook flags this): `risk_parameters.md` (profile library — 3 standing profiles: just-markets-solo, darwinex-track, ibkr-pod), `strategy_state.md` (manifests), `research_queue.md` (idea inbox). Schema is LOCKED; population is the next build.
- **New framework dirs are empty stubs:** `layer0-profile/`, `C-portfolio-fit/`, `B-funnel/step5-forward/`.
- A few scoreboard `.md` files still mention legacy step names in *prose* (methodology, not paths) — harmless; auto-generated ones rewrite on next scan run.

---

## Running Processes

| Task | Status | Notes |
|------|--------|-------|
| (none) | Stopped | All background greps completed and consumed |

---

## Priority for Next Session

1. **Decide merge vs review** for branch `reorg/baysix-framework` in `workspace/baysix-engine`, then merge to `main` (or spawn code-reviewer). Then commit the sigma-brain repo.
2. **Populate the schema files** now that the structure is locked: start with `layer0-profile/` (3 standing Deployment Profiles) + an `strategy_state.md` manifest for IB-001 as the first live test of the pipeline. Schema details in [framework_schema_locked.md](../../.claude/projects/c--Users-User-Desktop-sigma-brain/memory/framework_schema_locked.md).
3. **Run IB-001 (XAUUSD B2B) through the new funnel** end-to-end as the first real validation — it's a single-asset timing edge, so primary metric is hit-rate/MAE-MFE/expectancy, NOT IC. Prior finding: honest edge +0.309 R/trade, 1,084 trades, z=+7.19 (see [b2b_h1_phase_b_naive_finding.md](../../.claude/projects/c--Users-User-Desktop-sigma-brain/memory/b2b_h1_phase_b_naive_finding.md)).

---

## Key Decisions Made

- **Metric language is strategy-dependent, not always-IC** — match primary metric to idea type (Tier-2 table); asset mode gates legality. Supersedes the old "always IC/ICIR" directive.
- **Framework is tri-purpose + asset-agnostic via a single Layer-0 Deployment Profile** — one funnel, profile swaps thresholds. No forking.
- **CoS-routed agents** — Chief of Staff holds state and dispatches; agents don't self-trigger (cheapest on Pro plan, deterministic).
- **`N_trials` family = trials you compared to pick the winner; key = idea-type × asset-class; platform excluded; declared at Step 1.**
- **Schema locked:** profile library (1 per venue) → many manifests; asset_mode in manifest, venue in profile; YAML frontmatter + markdown body; CoS commits state transitions (append-only history).
- **research-engine physically reorganized** to match the framework rather than keeping legacy step1-8 numbering.

---

## Blockers

None. (Reorg verified working; remaining work is decision + population, not debugging.)
