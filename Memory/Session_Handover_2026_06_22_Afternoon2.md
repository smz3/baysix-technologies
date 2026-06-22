# Handover — June 22, 2026 Afternoon2

## State
- ✅ **Protocol 4.0 "Lean Gates" rebuild COMPLETE — all committed + pushed** (`1ab6d66`→`7012c14`; 7 gates → 4: G1 Premise / G2 Edge+Survival / G3 Robustness / G4 Live; t-stat no longer auto-kills).
- **Full narrative + per-step detail lives in [Session_Handover_2026_06_22_Evening.md](Session_Handover_2026_06_22_Evening.md)** (written earlier this session; its only stale line was "docs commit pending" — that landed as `7012c14`). Read it first.
- research.db rebuilt **BRC-only** from backup via [research/migrations/032_rebuild_brc40.py](../research/migrations/032_rebuild_brc40.py): 72 ideas → BRC-001 (+STRUCT-001 parent), 100,034 run-5 tester_zones kept, integrity ok / 0 FK violations, 102MB→47MB. Rest preserved in `research/db/_backup/research_pre40_20260622_113653.db`.
- `research/code/` repackaged into **gates/lineage/io/infra** subpackages; flat `from research.code import X` preserved via `__init__` re-exports. 3.3 machinery (trial_family/gate2_sanity/gate5_report + DSR/PSR + the result columns) deleted. Gates walled in `pipeline._enforce_gate_walls` (G1 = idea_kind+output_type+≥1 paper; G2 = a logged NET result). protocol.py/idea_cli/docs all 4.0.
- Verified: `pytest research/tests/` all-pass, 0 failures (artifact: `research/tests/`, this session). Driver coherent — `idea_cli next BRC-001` → `1:P 2:o 3:- 4:-`.

## Next
1. **Resume BRC-001 — it sits at G2 (open).** Run `python research/code/gates/idea_cli.py next BRC-001` → "Gate 2 OPEN → emit IS net ledger → `pipeline.log_result(net)` → `pass_gate(2)`".
2. G2 work = run the BRC MT5 emitter (Open-prices-only) → ingest → read equity curve + DD on a NET-of-cost result. Open backlog: **P1 130** (hypothesis brainstorm), **P2 110** (single-TF D1 edge test = the G2 read), **P2 126** (OOS, blocked till IS frozen), **P2 129** (full-8.5yr emit timing).
3. Optional cleanup: delete the gitignored safety copy `research/db/research.db.pre40_rebuild` (the canonical backup is in `_backup/`).

## Blockers
None. Caveats: BRC driver shows `falsified 3/2` (historical, informational); `research/db/_seed/brc_seed.sql` is incomplete (no step2_papers) — the rebuild sourced from the backup, not the seed; migrations 010–031 are now historical (superseded by db_init + migration 032), don't replay.
