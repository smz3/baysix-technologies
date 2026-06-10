# Handover — June 10, 2026 Evening

## State
Full design session on the **execution/deployment pipeline**. Two docs now locked, no code yet.

1. **[execution_protocol.md](../braindump/execution_protocol.md) upgraded to v2** (commit cc4dbbf). Resolved the open §8 fork + closed the gaps from a critical review:
   - **EA/Python boundary RESOLVED:** self-contained **native MQL5 EA** owns everything irreversible (compute ORB signal + place/manage orders + **kill-switch**); **Python** owns everything replayable (read broker ledger → normalize → execution.db; recon). **EA emits NOTHING to Python** — fire-and-forget → zero added latency (separate processes, Python only reads).
   - **Independent auditor:** Python doesn't trust the EA — it **recomputes the signal** itself by pulling live bars (`mt5.copy_rates`) + re-running the research ORB function, and reads the deal ledger (`HistoryDeal*`). Recon = subtract the two. This is shadow-P&L / reconciliation / parallel-run — named institutional controls, solo-scale.
   - **venue ≠ account:** new `accounts` table (typed prop kill-lines). JustMarkets/Darwinex/FTMO all = MT5 → one adapter; only IBKR is a 2nd adapter. **No table-per-broker.**
   - Gaps closed: D0 gains a **feed-divergence** check (ORB signal = one candle's high/low, vendor diff breaks it); D2 gains a **min-trade-count** gate (can't test MC bands on n≈5); swap/commission from ledger not event; new incident kinds (`config_mismatch`, `prop_rule_breach`, `tz_mismatch`); config-handoff mechanism (Python writes EA `.set`, EA self-asserts).

2. **[execution_schema.md](../braindump/execution_schema.md) — SPEC LOCKED** (this session). Full DDL for all 10 tables, every column/type/constraint final. Conventions mirror research.db (`execution.py` = twin of `pipeline.py`). Key locked decisions:
   - **Bookkeeping time = MYT, market time = UTC** — never mixed (schema-level fix for the tz bug).
   - **Magic number** (Syafiq's catch) = the ledger **attribution key** for multi-strategy-per-account. Lives on `deploy_strategies`, `UNIQUE(account_id, magic_number)`. Readable map: ORB-001→1001, ORB-002→1002. Adapter asserts `deal.magic == deploy.magic` on ingest.
   - `idea_id` = the ONE soft key (no native FK — lives in research.db, code-validated).
   - Redeploy = singleton (status flips, history in `log_deploy`).

## Next (clean build run — needs full budget, deferred here at 94%)
1. Migration `020_create_execution_db.py` — the locked DDL → `research/db/execution.db`.
2. `research/code/execution.py` — function inventory in the schema doc + Pydantic `meta` model for ORB.
3. Smoke test — register `jm-live-01` + `ORB-001@jm-live-01` (magic 1001), open D0, assert guardrail blocks premature pass.
4. Then **task 4 proper:** MT5 adapter + recompute auditor + D0 harness (logic parity + feed divergence). NOT a blind code port.

## Blockers
None. Schema is build-ready. Open/deferred (non-blocking): views (`live_deployments`), portfolio layer, ORB Pydantic `meta` shape — all listed at the bottom of the schema doc.

## Backlog unchanged
P2: task 4 (ORB-001 port, now = the D0 build), task 28 (notebooks), task 30 (IBKR — parked, just a `venue` column for now).
