# Handover — June 22, 2026 Afternoon3

## State — Config-surface reconciled to Protocol 4.0 (no research done; pure doc/path cleanup)
- Follow-on to the 4.0 rebuild (Afternoon2). Audited the WHOLE live tree for stale refs left by the 7→4 gate collapse + the 4-subpackage code move. Two commits, both pushed.
- **Commit 1** — `session_brief.py` (broken `idea_cli` path → `gates/`; 7-gate t-stat line → 4.0 "reported, not auto-kill"); `docs/reference/README.md` rewritten to 4.0 (subpackage paths, dropped deleted gate2_sanity/gate5_report/trial_family refs, ADRs → `_archive/`, current test list); archived `mt5_fidelity_flow.md` → `docs/specs/_archive/` (Gate-7 flow dissolved in 4.0).
- **Commit 2** — fixed stale `python research/code/<file>.py` self-refs inside the moved modules (io/ + infra/ docstrings + **two arctic_io runtime error hints** that misdirected live); `run_tracked` example repointed off archived `orb/reentry.py` → live `brc001/lifecycle.py`; `smoke_execution` usage → `research/tests/`; `protocol_guard` docstring → `gates/idea_cli.py`.
- **Verified clean (no change):** all `from research.code.X` imports use new subpackage form (`imports OK`); dropped cols (n_trials/trial_family_id/config_hash/cost_bps/cost_basis) appear only as "removed" notes, zero live queries; deleted-file names have no live refs; agents' DB queries (`kill_gate`/`gate_number`/`stage`) all still resolve; CLAUDE.md / RESEARCH_CODE_PROTOCOL.md / research/code/README.md already 4.0.
- Driver green: `idea_cli.py next BRC-001` → `gate_2`.

## Next — resume real BRC research (unchanged from Afternoon2)
1. **BRC-001 at G2 (open).** `python research/code/gates/idea_cli.py next BRC-001` → emit IS net ledger, `pipeline.log_result(net)`, then `pass_gate(2)`.
2. G2 work = run BRC MT5 emitter (Open-prices-only) → ingest → read equity curve + DD on a NET-of-cost result. Backlog: P1 130 (hypothesis brainstorm), P2 110 (single-TF D1 edge read), P2 126 (OOS emit, blocked until IS frozen), P2 129 (full 8.5yr emit timing).
3. G1 paper wall satisfied (papers 10/28/29/30); any NEW idea links ≥1 paper before leaving G1.

## Blockers
None. No research numbers produced this session (doc/infra only — handover_lint N/A).
