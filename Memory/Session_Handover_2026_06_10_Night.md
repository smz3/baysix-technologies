# Handover — June 10, 2026 Night

## State
**execution.db is BUILT and verified** (task 31 done). [execution.py](../research/code/execution.py) = canonical 10-table `_SCHEMA` + `init_db()` + full validated write-fn inventory + `pass_deploy_gate` recon-guardrail + ORB Pydantic meta. [migration 020](../research/migrations/020_create_execution_db.py) creates `research/db/execution.db`; [smoke_execution.py](../research/code/smoke_execution.py) passes **14/14** (guardrail block-then-pass, magic=1001, soft-key reject, dup reject, meta reject). `execution.db` is **gitignored** (live real-money DB, rebuildable via migration; protocol §1 Isolation) — `research.db` stays tracked. Tree clean, pushed.

## Next — full-swing build + (hopefully) deploy ORB-001 — **task 4 (now P1)**
1. **MT5 adapter** — normalize `HistoryDeal*` (OnTradeTransaction = doorbell only; handle async deals + swap-at-close) → `ingest_order/fill/trade`.
2. **Python recompute auditor** — re-run the research ORB fn on live bars (`mt5.copy_rates`) → `log_signal`; read ledger → fills.
3. **D0 harness** — logic parity (trade-list diff vs backtest = 0) **and** feed-divergence (JM vs Dukascopy at 09:00 UTC anchor, pre-commit pip tol) → `log_recon_result` → `pass_deploy_gate(D0)`.
4. Then config-handoff (`get_live_config` + accounts → EA `.set`, EA self-assert) → **D1 demo run** on Just Markets.
   LIVE CONFIG: anchor **09:00 UTC / N=5 / trail_1R** / Mode-A 5% cap.

## Decisions logged tonight (don't re-litigate)
- **Supabase = the Postgres target** (protocol §10), trigger = dashboard/real-money. Migration contained to `_SCHEMA`+`_conn()`. **Litestream deferred** (Supabase managed PITR supersedes). Interim demo durability = WAL + `VACUUM INTO` snapshots → cloud folder (**task 32**). Supabase migration = **task 33**.
- New rule: handover "Next" steps must also be `log_tasks` rows ([[handover_nextsteps_must_be_tasks]]).

## Blockers
None. Build-ready. Backlog: **#4 (P1)** → #32/#33 (P2 infra) → #28/#30. execution.db rebuilds via `python research/migrations/020_create_execution_db.py`.
