# Execution & Deployment Protocol

The **downstream** half of Baysix. Where [research_protocol.md](research_protocol.md) answers *"does this edge exist?"*, this protocol answers *"does the validated edge survive contact with a live broker — on any venue — and keep tracking the model once real money is on it?"*

Same rigor as the research ladder. Same discipline: pre-committed gates, a guardrail so they can't be skipped, all writes through a code layer, every decision logged to a lineage.

Status: **DESIGN — not yet built.** This doc is the blueprint we agreed before writing a single table or `.mqh` line (2026-06-10).

---

## 0. First principles

1. **research.db owns "what to trade"; execution.db owns "what happened when we traded it."** The execution layer *reads* the frozen config from research via `strategy_log.get_live_config(idea_id)` and **never re-defines it**.
2. **Two physical databases.** `research.db` (calm, deliberate, validated lineage) and `execution.db` (live, high-cadence, real-money record) are separate files. Decision settled 2026-06-10 — see §1.
3. **Everything is keyed by `idea_id × venue × instrument`, never by strategy name.** This is what makes the schema survive past ORB into any future strategy and any future broker.
4. **The broker is the source of truth for fills.** We do not hand-journal executions. We *normalize* each venue's native execution ledger into one canonical schema (see §5).
5. **All writes go through a code layer** (`research/code/execution.py`, the twin of `pipeline.py`). Never raw `sqlite3` elsewhere. This keeps timestamps/validation correct and makes the eventual SQLite→Postgres migration a config change, not a rewrite.
6. **JSON holds only what we store but never join, filter, or reconcile on.** The moment a field matters to reconciliation, it becomes a typed column (see §6).

---

## 1. Why two databases (the hard wall)

A wall earns its cost only when the two sides differ on a **non-negotiable operational dimension**. The triggers:

| Trigger | What it looks like | Why a shared DB breaks |
|---------|-------------------|------------------------|
| **Uptime** | Live trader runs 24/7; research needs long offline migrations | A research migration write-locks the file → stalls the live writer |
| **Location** | Live on a VPS next to the broker; research on the workstation | Can't reliably share one SQLite file across two machines |
| **Security** | Live DB holds broker creds / account numbers / open positions | Expose research to a dashboard without leaking live account data |
| **Throughput** | Many strategies × instruments × tick logging | SQLite allows **one writer at a time** — it becomes the bottleneck |
| **Compliance** | Fills need audit-grade immutable retention | Research is freely editable; real-money records can't be |

At ORB scale today, none have fired yet — but **going live for real fires Uptime + Security + Location simultaneously** (VPS, credentials, 24/7). We build for the wall now so the transition is clean. The two DBs link by `idea_id` as a **soft key**, validated in the code layer on every write (the ingester checks the `idea_id` exists in research.db). SQLite `ATTACH` lets the dashboard/recon query across both files when a join is needed; only *constraint enforcement* can't cross the boundary, and code-layer validation replaces it.

---

## 2. The deployment-gate ladder (D0 → D3)

The research ladder validates the edge. The deployment ladder validates the edge **transfers to live and keeps tracking**. Each D-gate has a **pre-committed pass criterion** set before results are seen, and is logged in `deploy_gates`. A guardrail (twin of the `pass_gate(6)` fix) refuses promotion until the supporting `recon_results` exist.

### D0 — Parity
**Question:** Does the live execution code reproduce the Python research backtest *trade-for-trade* on the same bars?
**Method:** Feed both the same history; diff the trade lists (entry/exit/direction/day).
**Pass:** Trade diff = 0 (or a fully explained, bounded discrepancy).
**Kill/Block:** Any unexplained divergence → the live code is not the validated strategy. Fix before anything else.
**Why first:** Everything downstream assumes the live code *is* the thing we validated. Parity proves it.

### D1 — Demo fidelity
**Question:** On a live demo feed, do fills match the model's assumptions?
**Method:** Run on broker demo; reconcile live fills vs modeled (see §5). Watch slippage vs the 2-pip assumption, signal-match %, live E[R] vs the IS confidence band.
**Pass (pre-committed):** slippage ≤ modeled spread assumption; signal-match ≥ threshold; live E[R] inside IS band. *(Exact tolerances set per deployment before the run.)*
**Kill/Block:** Slippage materially worse than modeled, or signals diverging → re-examine cost model / execution logic.

### D2 — Live micro
**Question:** With real money at min lot, does live P&L track expected?
**Method:** $50 live, min lot, Mode-A cap. Reconcile continuously.
**Pass:** Live E[R] / drawdown inside the **Monte-Carlo survival bands** computed at Gate 6 (e.g. ORB-002: 0% blow-up, ~9% DD).
**Kill/Block:** Live outside MC bands → pause, diagnose.

### D3 — Steady-state
**Question:** Is it still tracking, or drifting/decaying?
**Method:** Rolling live-vs-modeled drift t-stat; ongoing incident monitoring; kill-switch criteria.
**Pass (to stay live):** drift t-stat below threshold; no critical unresolved incidents.
**Kill/Block:** Significant sustained drift → demote/retire via `log_deploy`.

---

## 3. The five layers (mental model)

`execution.db` tracks the **life of a deployed strategy**, in the order it lives through:

```
1. REGISTER   →  what's deployed (idea, venue, instrument, frozen config, current D-gate)
2. GATE       →  the D0–D3 checkpoints
3. OBSERVE    →  what it actually did: signal → order → fill → trade
4. RECONCILE  →  live vs model (the lie-detector)
5. RECORD     →  decisions made + incidents that happened
```

---

## 4. Schema

> Column lists below are the **key** columns, not exhaustive. All tables carry `created_at`; mutable rows carry `updated_at`. PK = primary key, FK = foreign key (native within `execution.db`).

### Layer 1 — REGISTER

**`deploy_strategies`** — one row per `(idea_id × venue × instrument)` deployment. The anchor every other table references.

| Column | Role |
|--------|------|
| `deploy_id` (PK) | the handle everything else points to |
| `idea_id` | soft link to research.db (code-layer validated) |
| `venue` | `justmarkets`, `ibkr`, … — first-class |
| `instrument` | `XAUUSD.s`, … — first-class |
| `config_snapshot` (JSON) | **frozen copy** of the live config at deploy time (the deployment manifest) |
| `config_source` | `strategy_log` log_id / git sha the config came from |
| `stage` | current D-gate: `D0`/`D1`/`D2`/`D3` |
| `status` | `pending`/`active`/`paused`/`killed`/`retired` |
| `account_id` | broker account (demo vs live) |

`config_snapshot` is the **contract** between the two databases: research can re-tune ORB-002 later, but this deployment knows exactly what version it is running.

### Layer 2 — GATE

**`deploy_gates`** — mirror of research `step3_gates`, for D0–D3.

| Column | Role |
|--------|------|
| `gate_id` (PK), `deploy_id` (FK) | which deployment |
| `gate_number` | 0–3 |
| `pass_criteria` | the pre-committed kill-line (text) |
| `status` | `open`/`passed`/`blocked`/`killed` |
| `gate_answer` | verdict + the numbers behind it |
| `answered_by`, `answered_at`, `attempt` | |

### Layer 3 — OBSERVE (the live event stream)

A trade's life: **signal → order → fill → trade.**

**`exec_signals`** — what the strategy *wanted* (intent).

| Column | Role |
|--------|------|
| `signal_id` (PK), `deploy_id` (FK) | |
| `signal_ts`, `session_date` | when it decided |
| `direction` | `long`/`short`/`flat` — universal |
| `intended_entry_px`, `intended_stop_px`, `intended_target_px` | levels (target nullable for trailers) |
| `intended_size` | lots |
| `expected_R` | model's predicted R — stored here for per-trade recon |
| `meta` (JSON) | **strategy-private context only** — ORB `{or_high, or_low, range_w, anchor}`, MR `{zscore, lookback}`, … Authored in Python, schema-validated (§6) |

**`exec_orders`** — what was *sent to the broker*. Normalized from the venue (§5).

`order_id` (PK), `signal_id` (FK), `deploy_id` (FK), `venue_order_id` (broker ticket), `order_type`, `side`, `requested_px`, `requested_size`, `status` (`sent`/`accepted`/`rejected`/`filled`/`cancelled`), `reject_reason`.

**`exec_fills`** — what the broker *gave us*. Normalized from the venue's native ledger.

`fill_id` (PK), `order_id` (FK), `deploy_id` (FK), `venue_deal_id` (MT5 deal / IBKR execId), `fill_px`, `fill_size`, `fill_ts`, **`slippage_px`** (fill − requested), `commission`, `swap`.
→ `slippage_px` is the single most important number for D1.

**`exec_trades`** — the closed round-trip; the reconciliation unit.

| Column | Role |
|--------|------|
| `trade_id` (PK), `deploy_id`, `signal_id` (FK) | |
| `entry_ts/px`, `exit_ts/px`, `exit_reason` | the realized trade |
| `risk_unit` | the 1R distance — generic (ORB `range_w`, ATR stop, …) |
| `realized_R` | what we **actually** got live |
| `expected_R` | what the model **said** (copied from signal) |
| `realized_pnl_usd` | dollars |

`realized_R` and `expected_R` side-by-side make reconciliation a subtraction, not a project.

### Layer 4 — RECONCILE

**`recon_results`** — the `step4_results` of the live world. Flexible `metric_key`/`metric_value` rows so any strategy logs any metric. Written by the recon job (§7).

| Column | Role |
|--------|------|
| `recon_id` (PK), `deploy_id` (FK) | |
| `gate_number` | which D-gate this recon feeds (nullable) |
| `period_start`, `period_end` | window reconciled |
| `metric_key`, `metric_value`, `n_obs` | flexible (twin of step4_results) |

Core metrics: `signal_match_pct` (runtime parity), `slippage_median_px` (cost-model check), `live_E_R` + `drift_t_vs_IS` (edge tracking).

### Layer 5 — RECORD

**`log_deploy`** — mirror of `log_strategy`. Deployment decision lineage.
`log_id` (PK), `deploy_id` (FK), `event`, `from_stage`, `to_stage`, `verdict` (`CREATED`/`PROMOTED`/`PAUSED`/`KILLED`/`RESUMED`/`RETIRED`), `rationale`, `recon_id` (the evidence), `decided_by`.

**`log_incidents`** — the live black-box recorder; the thing research never has.
`incident_id` (PK), `deploy_id` (FK), `incident_ts`, `severity` (`info`/`warn`/`critical`), `kind` (`disconnect`/`missed_fill`/`slippage_spike`/`reject`/`killswitch_fire`/`data_gap`), `detail`, `resolved`.

---

## 5. Multi-venue: normalize from native ledgers (do NOT hand-journal)

Both brokers already maintain an authoritative, structured execution ledger. We **consume and normalize** them — we never rebuild a flimsier copy.

- **MetaTrader 5:** [`OnTradeTransaction`](https://www.mql5.com/en/docs/event_handlers/ontradetransaction) pushes every execution event in real time; [`HistorySelect` + `HistoryDealGetTicket`](https://www.mql5.com/en/docs/trading/historydealgetticket) give the full deal ledger with price, volume, **commission, swap, profit, time**. MT5 already models order→deal→position natively.
- **Interactive Brokers:** [`execDetails` + `commissionReport`](https://interactivebrokers.github.io/tws-api/executions_commissions.html) events deliver `Execution` + `CommissionReport` per fill (async; `ib_insync` wraps it), and handle execution corrections via amended execId.

**The venue-adapter pattern:** one thin adapter per venue maps that venue's native records into the canonical `exec_orders` / `exec_fills` / `exec_trades` columns. `venue_order_id` / `venue_deal_id` retain the broker's native identifiers for audit traceability.

```
MT5 deal (HistoryDeal* / OnTradeTransaction) ─┐
                                              ├─→ [normalizer] → execution.db (canonical, typed)
IBKR Execution + CommissionReport ────────────┘
```

The broker is ground truth. This removes the most fragile EA-side work and makes the record audit-grade across venues.

---

## 6. The JSON rule (robustness & safety)

`meta` (and `config_snapshot`) are semi-structured. Semi-structured can fail: no type enforcement (silent typo/drift), fragile authoring, cross-venue dialect drift, unqueryable, version rot. The rules that keep it safe:

1. **Golden rule — JSON holds only what we STORE but never JOIN, FILTER, or RECONCILE on.** Anything reconciliation depends on (direction, levels, size, R, slippage) is a **typed column**. `meta` is audit/debug context only.
2. **Validate on write, in the code layer.** `execution.py` defines a **Pydantic model per strategy type**; the ingester rejects malformed `meta` before insert. This replaces the type-safety the DB gave up.
3. **`CHECK(json_valid(meta))`** column constraint — SQLite guarantees at least valid JSON (JSON1 built in; JSONB on newer builds).
4. **Version it** — `meta_schema_version` so old rows stay interpretable/migratable.
5. **Author JSON only where it's safe — in Python, never in MQL5.** MQL5 has **no native JSON** (needs the third-party [JAson.mqh](https://github.com/vivazzi/JAson), limited to simple scalar shapes). Python has first-class JSON + Pydantic. Therefore strategy-meta authoring belongs to a Python layer.
6. **Never put venue/execution data in JSON.** It comes from each broker's native typed ledger → typed columns (§5).

MQL5 *does* have native SQLite with bound queries ([`DatabaseOpen/Prepare/Bind`](https://www.mql5.com/en/docs/database)), so an EA could write SQLite directly — but because we want **one normalized cross-venue store**, the unifying layer is a Python normalizer, not per-venue EA writes.

---

## 7. Data flow

```
signal engine decides → exec_signals   (intent + expected_R, meta validated in Python)
order sent            → exec_orders     (normalized from venue)
broker fills          → exec_fills      (normalized from native ledger; + slippage)
trade closes          → exec_trades     (realized_R vs expected_R)
end of session        → recon job       → recon_results   (live vs model)
   breach?            → log_incidents + log_deploy(pause) + kill-switch
   clean?             → D-gate review reads recon → log_deploy(promote)
```

The EA's hot path stays sacred: it manages orders. Bookkeeping, normalization, DB writes, validation, and reconciliation are owned by the Python code layer.

---

## 8. Open decision (resolve before schema is finalized)

**Signal generation: Python brain + thin EA executor, vs. native MQL5 EA does everything.**

The JSON robustness rules (§6) push strategy-meta authoring into Python, which nudges toward a **Python brain** (generates signals, owns DB/recon) with the **EA as a thin executor** (places orders, reports fills). We already have the MT5↔Python bridge ([reference_mt5_bridge](../memory/), `MetaTrader5` pkg). For ORB (one daily anchor, not latency-sensitive) this is comfortably fine. The counter-case: a self-contained native EA has no live-Python dependency. **This is the one fork to settle before tables are written.**

---

## 9. Growth path (past ORB, past one venue)

The schema is already idea-agnostic (keyed by `idea_id × venue × instrument`, universals as columns, `meta`/`recon_results` flexible). What we **add** as we scale — additive, never a teardown:

1. **Portfolio layer** (`portfolio_allocations`, `portfolio_risk`) above individual strategies, when 2+ run live together: capital allocation, aggregate risk, correlation netting (e.g. the three ORB anchors sharing a 21:00 EOD).
2. **SQLite → Postgres** when throughput hits SQLite's single-writer wall — painless because all writes go through `execution.py`.
3. **More venue adapters** — each new broker is one normalizer (§5), no schema change.

---

## 10. Build order (when we leave design)

1. `execution.py` code layer (schema DDL + validated write functions) + `execution.db`.
2. MT5 venue adapter (normalize `HistoryDeal*` / `OnTradeTransaction`).
3. Recon job (compare `exec_trades` vs research backtest → `recon_results`).
4. D0 parity harness for ORB-001 (the real content of task 4).
5. D1 demo run on Just Markets → reconcile → promote.
6. IBKR adapter (task 30, separate venue research) when/if pursued.

---

## References

- MQL5 native SQLite: <https://www.mql5.com/en/docs/database>
- MQL5 `OnTradeTransaction`: <https://www.mql5.com/en/docs/event_handlers/ontradetransaction>
- MQL5 `HistoryDealGetTicket`: <https://www.mql5.com/en/docs/trading/historydealgetticket>
- IBKR executions & commissions: <https://interactivebrokers.github.io/tws-api/executions_commissions.html>
- MQL5 JSON (third-party JAson): <https://github.com/vivazzi/JAson>
- Upstream twin: [research_protocol.md](research_protocol.md)

---

*Design agreed 2026-06-10 (Syafiq + Claude). Two-DB decision settled. Normalize-from-native-ledgers and JSON-safety rules adopted after verifying MT5/IBKR capabilities. Python-brain-vs-EA fork remains open (§8). No tables built yet.*
