# Handover — June 22, 2026 Afternoon2 (latest / authoritative for today)

## State — Protocol 4.0 rebuild COMPLETE (Phase 3 + the Phase-4 doc pass, all committed)
- The lean 4.0 rebuild is done end-to-end: research.db rebuilt, code layer repackaged + stripped, gates walled, driver + docs 4.0.
- Test suite green — pytest `research/tests/` reports all-pass (artifact: `research/tests/`, run this session; 0 failures).
- Four commits this session: `1ab6d66` (step 1), `e429049` (step 2), `bff733e` (steps 3+3b), `7012c14` (step 4 docs) — all pushed.

### What landed
- **Step 1 (`1ab6d66`)** — archived the orb cluster (`research/models/orb/` → `_archive/orb/`) + ORB-era dead code `export_ticks_mt5.py` + `fills.py` (Gate-7 fidelity tooling + Python fill-sim, both dissolved in 4.0) → `code/_archive/`; their tests → `tests/_archive/` (conftest ignores it).
- **Step 2 (`e429049`)** — `research/code/` repackaged into **4 subpackages**: `gates/` (pipeline·protocol·idea_cli) · `lineage/` (strategy_log·agent_log·backlog) · `io/` (arctic_io·tester·ingest_*·fetch/extract/backfill) · `infra/` (db_init·run_and_log·run_tracked·handover_lint·execution). **Flat contract preserved** — `from research.code import X` unchanged everywhere via `__init__` re-exports; intra-package imports made subpackage-qualified; `__file__` path depths bumped +1. **Deleted** the 3.3 machinery: `trial_family.py` / `gate2_sanity.py` / `gate5_report.py` + their tests.
- **Step 3 (`bff733e`)** — `research.db` rebuilt **BRC-only** from the pre-4.0 backup via [research/migrations/032_rebuild_brc40.py](../research/migrations/032_rebuild_brc40.py): 72 ideas → BRC-001 (+STRUCT-001 parent row); 100,034 run-5 tester_zones kept; `integrity_check ok`, `0 FK violations`; 102MB → 47MB. Everything else lives in `research/db/_backup/research_pre40_20260622_113653.db` (recoverable). A session-temp `research.db.pre40_rebuild` (gitignored) is a second safety copy — deletable.
  - **Schema** (db_init): `step3_gates` CHECK `BETWEEN 1 AND 4`; `step4_results` dropped `n_trials/trial_family_id/config_hash/cost_bps/cost_basis`, added `is_run`; new `is_runs` table; tester tables folded in; `trial_family` dropped.
  - **Gate remap** (your call): BRC old gates 0+1 → **G1 Premise = passed** (answers merged); old gate 2 dropped; **G2 = open**.
- **Step 3b (in `bff733e`)** — `pipeline._enforce_gate_walls`: **G1** needs idea_kind+output_type+≥1 paper, **G2** needs a logged NET result (`cost_adjusted=1`). Removed the gate-5 significance wall (t-stat auto-kill) + trial_family_id requirement; added `log_is_run()`/`get_is_runs()`. `protocol.py` rewritten for the 4 gates; `idea_cli` gatecheck on G1, sig_test render dropped.
- **Step 4 docs (`7012c14`)** — [docs/reference/research_protocol.md](../docs/reference/research_protocol.md) rewritten → 4.0; 3.2/3.3 specs → [docs/specs/_archive/](../docs/specs/_archive/); [docs/reference/research_db_schema.md](../docs/reference/research_db_schema.md) updated (is_runs, dropped cols, gate 1-4, tester ledger); CLAUDE.md repo-layout + rule 8/8b → 4.0; `research/code/README.md` → subpackage index; moved-script doc paths fixed.

## Next — resume real BRC research on the 4.0 protocol
- **BRC-001 is at G2 (open).** Driver: `python research/code/gates/idea_cli.py next BRC-001` → "Gate 2 OPEN → emit the IS net ledger, `pipeline.log_result(net)`, then `pass_gate(2)`".
- The G2 work = run the BRC MT5 emitter (Open-prices-only) → ingest → read the equity curve + DD on a NET-of-cost result. Open backlog already holds the BRC tasks: **P1 130** (hypothesis brainstorm from 8yr IS zones), **P2 110** (edge test single-TF D1 atom — was "Gate 3", now the G2 edge read), **P2 126** (OOS emit, blocked until IS config frozen), **P2 129** (full 8.5yr emit timing).
- **G1 paper wall is satisfied** for BRC (4 dissected papers: ids 10/28/29/30). Any NEW idea must link ≥1 paper before leaving G1 ([[g1_requires_linked_paper]]).

## Caveats
- `falsified : 3/2` on BRC's driver line is its historical FALSIFIED count from log_strategy (informational, not blocking).
- The seed file `research/db/_seed/brc_seed.sql` is **incomplete** (missing step2_papers rows) — the rebuild bypassed it and sourced from the backup instead. If you ever re-run the seed directly, add the 4 step2_papers rows first.
- Migrations 010–031 are now historical (the chain is superseded by db_init's lean schema + migration 032). Don't replay them.
