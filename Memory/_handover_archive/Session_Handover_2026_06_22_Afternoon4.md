# Handover — June 22, 2026 Afternoon4

## State — DB schema simplification + repo hygiene (no research; all pushed)
- **Collapsed `is_runs` into `step4_results`** (migration 033). The separate registry duplicated the IS-run label the result row already carries + forced a pre-register step. Now: `is_run` is a plain label on the result row, shot-count = `COUNT(DISTINCT is_run)`.
  - `step4_results` gained `what_changed` col; `is_runs` table DROPPED.
  - `pipeline.log_is_run()` deleted; `log_result()` gained `what_changed` param (no pre-register friction); `get_is_runs()` now reads DISTINCT off `step4_results`. `run_and_log` forwards `what_changed`. 7/7 `test_run_and_log` green.
- **Naming decision:** Syafiq kept `stepN_` table prefixes as-is (NOT renamed to `pipe_`). Only is_runs collapsed. `trial_family` confirmed already-dead (not in live DB; only in backup + historical migrations 010/028 — leave those).
- **Repo cleanup:** deleted orphan `research/code/__pycache__/` husks (trial_family/gate2_sanity/gate5_report .pyc); deleted gitignored `research/outputs/` + stray `ssrn_dl.bin` (failed SSRN download = Cloudflare block page); moved root `hedge_fund_method_10_steps.md` → `docs/reference/`; added `.pytest_cache/` to `.gitignore`.
- **`research.db` stays git-TRACKED by design** ([.gitignore:48](.gitignore#L48) "shareable research state" = workstation↔VPS sync + off-site backup). Syafiq confirmed keep. Caveat noted: the 98M `_backup/research_pre40_*.db` is gitignored → NOT disaster-recoverable; copy off-repo if the 71 archived ideas matter.

## Next — resume BRC-001 G2 (real research, untouched this session)
1. `python research/code/gates/idea_cli.py next BRC-001` → **Gate 2 OPEN** → emit/read net ledger → `pipeline.log_result(net)` → `pass_gate(2)`.
2. **Recommended pick = backlog P2 #110**: single-TF D1 atom net edge on the EXISTING run-5 zone ledger (~100k rows in `tester_zones`, no re-emit) — `E[$/trade]` net for H_base (continuation-retest) vs H_alt-1 (fade) vs H_alt-2 (single vs two-break). This is what unblocks G2.
3. Then P1 #130 (hypothesis brainstorm run 5). P2 #126 OOS emit stays BLOCKED until IS config frozen.

## Blockers
None. No research numbers produced (schema/infra only — handover_lint N/A).
