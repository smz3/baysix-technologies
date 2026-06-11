# Handover — June 11, 2026 Evening

## State
**execution.db design RE-LOCKED + all docs reconciled (committed 38c8b55, pushed).** Decisions: **2 DBs not 3** (tester folds into research.db as **Gate 7 — FIDELITY**); `venue`=protocol (`mt5`/`ibkr`) + new `accounts.broker`; **+`instruments` +`equity_snapshots`** day-one; `deploy_gates` kept (symmetry) but FORWARD-only; **12 tables, built at once**; `exec_` prefix dropped; `deploy_strategies`→`deployments`. Full spec: [execution_schema.md](../braindump/execution_schema.md) (DDL) + [execution_protocol.md](../braindump/execution_protocol.md) (why) + Gate 7 in [research_protocol.md](../braindump/research_protocol.md). Summary memory: [[execution_db_design]]. **Nothing built yet — clean slate to build from.**

## Next  *(create log_tasks rows for 1–3 first — [[handover_nextsteps_must_be_tasks]])*
1. Read [research/RESEARCH_CODE_PROTOCOL.md](../research/RESEARCH_CODE_PROTOCOL.md) (CLAUDE.md rule 7) before touching research/code/.
2. **research.db migration** (next # after 021): add `tester_runs` + `tester_trades`; allow `step3_gates.gate_number=7`. Preserves all research data.
3. **execution.db rebuild migration**: DROP old D0-era execution.db + the misplaced tester tables from migration 021 (nothing precious); CREATE the 12 tables per execution_schema.md DDL. Then `research/code/execution.py` + research-side tester writers; smoke-test the FORWARD-needs-Gate-7 guardrail.
4. Then Gate 7 / FIDELITY for ORB-001 (task 43): ingest the $10k tester xlsx → diff vs Python `step4_results`.

## Blockers
- ORB-001 deploy BLOCKED at **Gate 7 FIDELITY** — EA trailing-exit port bug (win 56.7%→33.2%); the EA trail code looked structurally correct on inspection (started systematic-debugging, paused for the DB work). Separate fix; doesn't block the migrations.
