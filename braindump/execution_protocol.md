# Execution & Deployment Protocol

The **downstream** half of Baysix. Where [research_protocol.md](research_protocol.md) answers *"does this edge exist?"*, this protocol answers *"does the validated edge survive contact with a live broker — on any venue — and keep tracking the model once real money is on it?"*

Same rigor as the research ladder. Same discipline: pre-committed gates, a guardrail so they can't be skipped, all writes through a code layer, every decision logged to a lineage.

These are not novel inventions — they're the solo-scale collapse of three named institutional controls: **shadow / parallel running** (validate live behaviour before scaling capital), **product control / "shadow P&L"** (an independent function recomputes and reconciles, investigating every *break*), and **back-office reconciliation** (internal records vs the broker's). A bank splits these across three desks; we run them as one Python layer.

Status: **DESIGN — decisions locked, not yet built.** Build target is **MT5-only** (Just Markets, XAUUSD live); IBKR is a parked column, not code (see §6). Updated 2026-06-10 — the §8 EA/Python fork is now resolved (§2).

---

## 0. First principles

1. **research.db owns "what to trade"; execution.db owns "what happened when we traded it."** The execution layer *reads* the frozen config from research via `strategy_log.get_live_config(idea_id)` and **never re-defines it**.
2. **Two physical databases.** `research.db` (calm, deliberate, validated lineage) and `execution.db` (live, high-cadence, real-money record) are separate files. Settled 2026-06-10 — see §1.
3. **Everything is keyed by `idea_id × venue × instrument`, never by strategy name.** This is what makes the schema survive past ORB into any future strategy and any future broker.
4. **Venue ≠ account.** *Venue* = the wire protocol / adapter ("how do I talk to this broker" — MT5 vs IBKR; code). *Account* = the rulebook ("what am I allowed to do" — leverage, prop loss-limits; data). Just Markets, Darwinex, and FTMO are all MT5 → **one adapter**; what differs between them is a *row* in `accounts`, not a code path.
5. **The broker is the source of truth.** We do not hand-journal executions. We *normalize* each venue's native execution ledger into one canonical schema (see §6).
6. **EA = irreversible; Python = replayable.** The EA owns anything where being offline loses money (decide, trade, risk kill-switch). Python owns anything that can lag and catch up (record, normalize, reconcile). The line falls exactly there — see §2.
7. **All writes go through a code layer** (`research/code/execution.py`, the twin of `pipeline.py`). Never raw `sqlite3` elsewhere. Keeps timestamps/validation correct and makes the eventual SQLite→Postgres migration a config change, not a rewrite.
8. **JSON holds only what we store but never join, filter, or reconcile on.** The moment a field matters to reconciliation, it becomes a typed column (see §7).

---

## 1. Why two databases (the hard wall)

A wall earns its cost only when the two sides differ on a **non-negotiable operational dimension**:

| Trigger | What it looks like | Why a shared DB breaks |
|---------|-------------------|------------------------|
| **Uptime** | Live trader runs 24/7; research needs long offline migrations | A research migration write-locks the file → stalls the live writer |
| **Location** | Live on a VPS next to the broker; research on the workstation | Can't reliably share one SQLite file across two machines |
| **Isolation** | Live DB holds account numbers, open positions, real-money record | Keep the research dashboard from ever touching live account state |
| **Throughput** | Many strategies × instruments × tick logging | SQLite allows **one writer at a time** — it becomes the bottleneck |
| **Compliance** | Fills need audit-grade immutable retention | Research is freely editable; real-money records can't be |

The **near-term decisive pair is Uptime + Location**: going live for real puts the writer on a 24/7 VPS next to the broker while research keeps migrating on the workstation — one SQLite file can't straddle that. (Note: broker *credentials* never live in the DB at all — they stay in `.env`. The Isolation trigger is about account/position *data*, not secrets.)

The two DBs link by `idea_id` as a **soft key**, validated in the code layer on every write (the ingester checks the `idea_id` exists in research.db). SQLite `ATTACH` lets the dashboard/recon query across both files when a join is needed; only *constraint enforcement* can't cross the boundary, and code-layer validation replaces it.

---

## 2. The EA / Python boundary (resolved — was §8 fork)

The fork — *native MQL5 EA does everything* vs *Python brain + thin EA* — is **resolved**: a **self-contained native EA** for everything trade-critical, **Python** for everything record/recon. The dividing rule is principle 6: *EA owns what loses money when offline; Python owns what merely lags.*

| Job | Owner | Why |
|-----|-------|-----|
| Compute the ORB signal | **EA (MQL5)** | trade-critical; must run with **no live-Python dependency** |
| Place / modify / close orders | **EA** | same |
| **Kill-switch** (account rules: daily-loss, max-DD) | **EA** | a hard risk-stop cannot wait for Python to be up — irreversible |
| Read broker ledger → normalize → `execution.db` | **Python** | source of truth is `HistoryDeal*`; replayable, can lag |
| Author `exec_signals` (intent + `expected_R` + `meta`) | **Python** | it recomputes the model — see below |
| Recon (live vs model) → `recon_results` | **Python** | must call the research model |
| Incidents from the Journal log | **Python** | forensic, replayable |

**The EA emits *nothing* to Python.** It is fire-and-forget. This is the keystone decision and it buys two things at once — *robustness* (no bridge on the trade path) and *zero added latency* (the EA's `OnTick → OrderSend` path never calls or waits on Python; they're separate OS processes; Python only *reads*).

### The independent auditor (why Python recomputes)
Python does **not** trust the EA's word for what it did. It reconstructs the session from two broker-sourced witnesses, via the `MetaTrader5` package ([reference_mt5_bridge](../memory/)) — never from the EA:

1. **The "should-have"** — Python pulls live bars itself (`mt5.copy_rates`) and **re-runs the exact research ORB function** (the same code the backtest used) → the model's intended trade.
2. **The "what actually happened"** — Python reads the broker's deal ledger (`HistoryDeal*`) → the real orders + fills.

Recon = subtract the two. This makes Python an **independent auditor**, not a stenographer: if it just logged the EA's claim, a buggy EA would look perfectly "matched" to its own mistake. Recomputing is what turns `signal_match_pct` into a lie-detector (the "shadow P&L break" of the live world).

**What it is and isn't:** once live, the auditor is a fast **detector** (catches drift seconds-to-minutes after a trade → pause before the *next* one), **not** a real-time **preventer** — the EA acts autonomously by design. True prevention happens earlier at D0/D1 (demo, before real money) and via the EA's own kill-switch. Detector (Python) and preventer (EA kill-switch) are different jobs.

---

## 3. The deployment-gate ladder (D0 → D3)

The research ladder validates the edge. The deployment ladder validates the edge **transfers to live and keeps tracking**. Each D-gate has a **pre-committed pass criterion** set before results are seen, logged in `deploy_gates`. A guardrail (twin of the `pass_gate(6)` fix) refuses promotion until the supporting `recon_results` exist.

### D0 — Parity
**Question:** Does the live EA reproduce the research backtest, and does the live feed match the research feed?
**Two checks:**
- **Logic parity:** feed the EA and the Python model the *same* bars; diff the trade lists (entry/exit/direction/day). Pass: trade diff = 0 (or a fully explained, bounded discrepancy).
- **Feed divergence:** the ORB signal *is* one candle's high/low, so a vendor difference breaks it. Quantify Just Markets bars vs Dukascopy research bars at the anchor (median |Δhigh|, |Δlow| in pips); pre-commit a tolerance.
**Kill/Block:** unexplained logic divergence → the live code is not the validated strategy; or feed divergence beyond tolerance → the live signal isn't the validated signal. Fix before anything else.

### D1 — Demo fidelity
**Question:** On a live demo feed, do fills match the model's assumptions?
**Method:** broker demo; reconcile live fills vs the Python recompute (§2). Watch slippage vs the spread assumption, `signal_match_pct`, live E[R] vs the IS band.
**Pass (pre-committed):** slippage ≤ modeled spread assumption; `signal_match_pct` ≥ threshold; live E[R] inside IS band. *(Exact tolerances set per deployment before the run.)*
**Kill/Block:** slippage materially worse than modeled, or signals diverging → re-examine cost model / execution logic.

### D2 — Live micro
**Question:** With real money at min lot, does live P&L track expected?
**Method:** $50 live, min lot, Mode-A cap. Reconcile continuously.
**Pass:** live E[R] / drawdown inside the **Gate-6 Monte-Carlo survival bands** (e.g. ORB-002: 0% blow-up, ~9% DD) — **but only assessed after a minimum trade count** (`n ≥ N_min`, pre-committed, e.g. 30). Below that, D2 is a *catastrophic-divergence smoke test only*, not a statistical verdict — you cannot test an MC band on a handful of trades.
**Kill/Block:** live outside MC bands (once powered), or any catastrophic divergence → pause, diagnose.

### D3 — Steady-state
**Question:** Is it still tracking, or drifting/decaying?
**Method:** rolling live-vs-recompute drift t-stat; ongoing incident monitoring; kill-switch criteria.
**Pass (to stay live):** drift t-stat below threshold; no critical unresolved incidents.
**Kill/Block:** sustained drift → demote/retire via `log_deploy`.

---

## 4. The five layers (mental model)

`execution.db` tracks the **life of a deployed strategy**, in the order it lives through:

```
1. REGISTER   →  what's deployed (idea, venue, instrument, account, frozen config, D-gate)
2. GATE       →  the D0–D3 checkpoints
3. OBSERVE    →  what it actually did: signal → order → fill → trade
4. RECONCILE  →  live vs model (the lie-detector)
5. RECORD     →  decisions made + incidents that happened
```

---

## 5. Schema

> Column lists are the **key** columns, not exhaustive — the full DDL is finalized interactively in `execution_schema.md` before any code. All tables carry `created_at`; mutable rows carry `updated_at`. PK = primary key, FK = foreign key (native within `execution.db`).

### Layer 1 — REGISTER

**`accounts`** — one row per broker account; the rulebook the EA kill-switch enforces. *(The venue-vs-account split, principle 4.)*

| Column | Role |
|--------|------|
| `account_id` (PK) | the account handle |
| `venue` | wire protocol / adapter: `justmarkets` (MT5), `ibkr`, … |
| `account_type` | `retail_highlev` / `darwinex_alloc` / `ftmo_challenge` / `ftmo_funded` / `ibkr_dma` |
| `mode` | `demo` / `live` |
| `base_currency`, `leverage` | sizing context |
| `max_daily_loss_pct` | **typed** — kill-switch reads it every tick (FTMO 5%) |
| `max_total_dd_pct` | **typed** — (FTMO 10%) |
| `daily_reset_tz` | **typed** — when the daily counter resets (FTMO midnight CET); kills the reset-bug |
| `profit_target_pct`, `min_trading_days` | **typed** prop targets |
| `rules_meta` (JSON) | non-reconciled rules only (consistency rules, scaling plan) |
| `status` | `active` / `breached` / `closed` |

The prop kill-lines are **typed columns, not JSON** — the kill-switch reconciles on them, so by the §7 golden rule they can't live in `meta`.

**`deploy_strategies`** — one row per `(idea_id × venue × instrument)` deployment. The anchor every other table references.

| Column | Role |
|--------|------|
| `deploy_id` (PK) | the handle everything else points to |
| `idea_id` | soft link to research.db (code-layer validated) |
| `venue` | `justmarkets`, `ibkr`, … — first-class |
| `instrument` | `XAUUSD.s`, … — first-class |
| `account_id` (FK → `accounts`) | which account it runs on |
| `config_snapshot` (JSON) | **frozen copy** of the live config at deploy time (the deployment manifest) |
| `config_source` | `strategy_log` log_id / git sha the config came from |
| `stage` | current D-gate: `D0`/`D1`/`D2`/`D3` |
| `status` | `pending`/`active`/`paused`/`killed`/`retired` |

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

**`exec_signals`** — what the strategy *wanted* (intent). **Authored by Python's recompute** (§2), not emitted by the EA.

| Column | Role |
|--------|------|
| `signal_id` (PK), `deploy_id` (FK) | |
| `signal_ts`, `session_date` | when the model decided (tz-explicit) |
| `direction` | `long`/`short`/`flat` — universal |
| `intended_entry_px`, `intended_stop_px`, `intended_target_px` | levels (target nullable for trailers) |
| `intended_size` | lots |
| `expected_R` | model's predicted R — stored here for per-trade recon |
| `meta` (JSON) | **strategy-private context only** — ORB `{or_high, or_low, range_w, anchor}`, MR `{zscore, lookback}`, … authored in Python, schema-validated (§7) |

**`exec_orders`** — what was *sent to the broker*. Normalized from the venue ledger (§6).

`order_id` (PK), `signal_id` (FK), `deploy_id` (FK), `venue_order_id` (broker ticket), `order_type`, `side`, `requested_px`, `requested_size`, `status` (`sent`/`accepted`/`rejected`/`filled`/`cancelled`), `reject_reason`. *(The EA's actual SL/TP live here — Python reads them from the order record, never from the EA.)*

**`exec_fills`** — what the broker *gave us*. Normalized from the venue's native ledger.

`fill_id` (PK), `order_id` (FK), `deploy_id` (FK), `venue_deal_id` (MT5 deal / IBKR execId), `fill_px`, `fill_size`, `fill_ts`, **`slippage_px`** (fill − requested, captured at **both legs** — entry *and* exit), `commission`, `swap`.
→ `slippage_px` is the single most important number for D1. `commission`/`swap` come from `HistoryDealGetDouble(DEAL_COMMISSION / DEAL_SWAP)`, **not** the event payload (§6). Capture `swap` even though Just Markets is swap-free today — swap-free is a broker plugin with a grace period that can start charging.

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

**`recon_results`** — the `step4_results` of the live world. Flexible `metric_key`/`metric_value` rows so any strategy logs any metric. Written by the recon job (§9).

| Column | Role |
|--------|------|
| `recon_id` (PK), `deploy_id` (FK) | |
| `gate_number` | which D-gate this recon feeds (nullable) |
| `period_start`, `period_end` | window reconciled |
| `metric_key`, `metric_value`, `n_obs` | flexible (twin of step4_results) |

Core metrics: `signal_match_pct` (runtime parity, from the recompute), `slippage_median_px` (cost-model check), `feed_divergence_px` (D0), `live_E_R` + `drift_t_vs_IS` (edge tracking).

### Layer 5 — RECORD

**`log_deploy`** — mirror of `log_strategy`. Deployment decision lineage.
`log_id` (PK), `deploy_id` (FK), `event`, `from_stage`, `to_stage`, `verdict` (`CREATED`/`PROMOTED`/`PAUSED`/`KILLED`/`RESUMED`/`RETIRED`), `rationale`, `recon_id` (the evidence), `decided_by`.

**`log_incidents`** — the live black-box recorder; the thing research never has.
`incident_id` (PK), `deploy_id` (FK), `incident_ts`, `severity` (`info`/`warn`/`critical`), `kind` (`disconnect`/`missed_fill`/`slippage_spike`/`reject`/`killswitch_fire`/`data_gap`/`config_mismatch`/`prop_rule_breach`/`tz_mismatch`), `detail`, `resolved`.

---

## 6. Multi-venue: normalize from native ledgers (do NOT hand-journal)

Both brokers maintain an authoritative, structured execution ledger. We **consume and normalize** them — never rebuild a flimsier copy. **Build is MT5-only now**; IBKR is a kept column (`venue`), zero IBKR code, until task 30 is pursued.

- **MetaTrader 5:** [`OnTradeTransaction`](https://www.mql5.com/en/docs/event_handlers/ontradetransaction) is the real-time **doorbell** ("something changed — go look"), **not** the ledger — never compute P&L/commission/swap from its payload. The authoritative numbers come from [`HistorySelect` + `HistoryDealGetTicket`](https://www.mql5.com/en/docs/trading/historydealgetticket): price, volume, `DEAL_COMMISSION`, `DEAL_SWAP`, profit, time. Two caveats the normalizer must handle: deals arrive **asynchronously** (the commission row can land separately from the fill), and **swap** is realized into `DEAL_SWAP` at close (sum across deals — never `POSITION_SWAP`, which double-counts on partial closes).
- **Interactive Brokers (parked):** [`execDetails` + `commissionReport`](https://interactivebrokers.github.io/tws-api/executions_commissions.html) per fill (async; `ib_insync` wraps it), corrections via amended execId.

**The venue-adapter pattern:** one thin, **fully isolated** adapter per venue maps that venue's native records into the canonical `exec_orders` / `exec_fills` / `exec_trades` columns. MT5 and IBKR adapters share **no code** — only the output table shape. `venue_order_id` / `venue_deal_id` retain the broker's native identifiers for audit traceability.

```
MT5 deal (HistoryDeal*, triggered by OnTradeTransaction) ─┐
                                                          ├─→ [normalizer] → execution.db (canonical, typed)
IBKR Execution + CommissionReport (parked) ───────────────┘
```

The broker is ground truth. This removes the most fragile EA-side work and makes the record audit-grade across venues.

---

## 7. The JSON rule (robustness & safety)

`meta` (and `config_snapshot`) are semi-structured. Semi-structured can fail: no type enforcement, fragile authoring, cross-venue dialect drift, unqueryable, version rot. The rules that keep it safe:

1. **Golden rule — JSON holds only what we STORE but never JOIN, FILTER, or RECONCILE on.** Anything reconciliation depends on (direction, levels, size, R, slippage, prop limits) is a **typed column**. `meta` is audit/debug context only.
2. **Validate on write, in the code layer.** `execution.py` defines a **Pydantic model per strategy type**; the ingester rejects malformed `meta` before insert.
3. **`CHECK(json_valid(meta))`** column constraint — SQLite guarantees at least valid JSON.
4. **Version it** — `meta_schema_version` so old rows stay interpretable/migratable.
5. **Author JSON only in Python, never in MQL5.** MQL5 has **no native JSON** (third-party [JAson.mqh](https://github.com/vivazzi/JAson), scalar-shaped only, verified still true 2025–26). Since the EA emits nothing anyway (§2), this is automatic — Python authors all `meta`.
6. **Never put venue/execution data in JSON.** It comes from each broker's native typed ledger → typed columns (§6).

MQL5 *does* have native SQLite ([`DatabaseOpen/Prepare/Bind`](https://www.mql5.com/en/docs/database)) — an EA *could* write SQLite directly — but the unifying cross-venue + reconcile-against-research layer can only live where it can reach every venue *and* call the research model: Python. MQL5 reaches exactly one venue and can't call the model.

---

## 8. Config handoff (research frozen config → live EA)

The EA must run the *exact* validated config — and prove it. The mechanism:

1. At deploy, **Python** reads `strategy_log.get_live_config(idea_id)` + the `accounts` row → writes the EA's inputs (an MT5 `.set` file or input block) **and** the `config_snapshot` into `deploy_strategies`.
2. On init, the **EA asserts** its loaded params equal `config_snapshot`; any mismatch → `log_incidents(kind='config_mismatch')` and refuse to arm.

This is a **one-time handoff at deploy, not a live dependency** — the EA needs no running Python thereafter. It carries the kill-switch parameters (`max_daily_loss_pct`, `max_total_dd_pct`, `daily_reset_tz`) into the EA, which enforces them live via `AccountInfoDouble(ACCOUNT_EQUITY)`. Time handling uses MT5's native `TimeTradeServer/TimeGMT/TimeGMTOffset/TimeDaylightSavings`; note the Strategy Tester does **not** simulate DST — anchors and `daily_reset_tz` are tested explicitly, never assumed.

---

## 9. Data flow

```
EA decides + places order            (self-contained; emits NOTHING to Python)
broker books the deal                → HistoryDeal* (ground truth)
                       ┌─ Python recomputes signal from live bars  → exec_signals (intent + expected_R)
Python (own process) ──┤
                       └─ Python reads the ledger                  → exec_orders / exec_fills / exec_trades
end of session         → recon job (subtract recompute vs ledger)  → recon_results
   break?              → log_incidents + log_deploy(pause)
   clean?              → D-gate review reads recon → log_deploy(promote)
EA, independently      → kill-switch on ACCOUNT_EQUITY vs accounts rules → (halt) + log_incidents
```

The EA's hot path stays sacred: decide, order, kill-switch. Bookkeeping, normalization, DB writes, validation, and reconciliation are owned by the Python layer — a **separate process** that only *reads* the broker, so it adds zero latency to execution.

---

## 10. Growth path (past ORB, past one venue)

The schema is already idea-agnostic (keyed by `idea_id × venue × instrument`, universals as columns, `meta`/`recon_results` flexible). What we **add** as we scale — additive, never a teardown:

1. **Portfolio layer** (`portfolio_allocations`, `portfolio_risk`) above individual strategies, when 2+ run live together: capital allocation, aggregate risk, correlation netting (e.g. the three ORB anchors sharing a 21:00 EOD). This is also where account-level prop risk aggregates across strategies.
2. **SQLite → Postgres (Supabase) — DECIDED 2026-06-10.** Target = **Supabase (managed Postgres)**: gives managed backups + PITR **and** an auto REST API for the dashboard in one move, and Syafiq already has Supabase experience. **Trigger = building the webapp dashboard / going to real money** — that's when network access + concurrent readers + a cloud server outgrow SQLite's single-writer/one-machine model. Migration is contained to `execution.py`'s `_SCHEMA` DDL + `_conn()` (call sites unchanged): `AUTOINCREMENT`→`IDENTITY`, `json_valid()` CHECK→native `jsonb`, `DATETIME`→`timestamptz`, `sqlite3`→`psycopg`. Hours, not a rewrite — keep `execution.py` free of SQLite-only idioms until then.
3. **Durability ladder.** *Demo phase (now):* SQLite WAL mode + periodic `VACUUM INTO` snapshots to a cloud-synced folder (cheap; RPO = snapshot interval, acceptable because fills are re-pullable from the broker ledger and only signals/recon/incidents are truly irreplaceable). *Live/serious:* Supabase managed PITR. **Litestream evaluated and DEFERRED** — it is the right SQLite-PITR tool (v0.5.x, actively maintained, but restore-then-run + checkpoint-ownership/`busy_timeout` caveats and a silent-replication bug to monitor), yet Supabase's managed backups supersede it for this project. Revisit only if we stay on self-hosted SQLite at higher cadence.
4. **More venue adapters** — each new broker is one isolated normalizer (§6), no schema change.

---

## 11. Build order (when we leave design)

1. `execution.py` code layer (schema DDL + validated write functions) + `execution.db` — finalize `execution_schema.md` with Syafiq first.
2. MT5 venue adapter (normalize `HistoryDeal*`, triggered by `OnTradeTransaction`; handle async + swap-at-close).
3. Python recompute auditor + recon job (recompute vs ledger → `recon_results`).
4. D0 harness for ORB-001: logic parity **and** feed-divergence check (the real content of task 4).
5. Config-handoff generator (`get_live_config` + `accounts` → EA `.set`; EA self-assert).
6. D1 demo run on Just Markets → reconcile → promote.
7. IBKR adapter (task 30, separate venue research) when/if pursued.

---

## References

- MQL5 native SQLite: <https://www.mql5.com/en/docs/database>
- MQL5 `OnTradeTransaction`: <https://www.mql5.com/en/docs/event_handlers/ontradetransaction>
- MQL5 `HistoryDealGetTicket` (commission/swap): <https://www.mql5.com/en/docs/trading/historydealgetticket>
- MQL5 time / DST (`TimeGMT`): <https://www.mql5.com/en/docs/dateandtime/timegmt>
- IBKR executions & commissions: <https://interactivebrokers.github.io/tws-api/executions_commissions.html>
- MQL5 JSON (third-party JAson): <https://github.com/vivazzi/JAson>
- Industry controls: shadow/parallel running ([Quant 2.0 stack](https://altstreet.investments/blog/quant-2-architecture-modern-trading-stack-ai-mlops)); product control / shadow P&L ([Effective Product Control](https://onlinelibrary.wiley.com/doi/10.1002/9781118939789.ch14)).
- Upstream twin: [research_protocol.md](research_protocol.md)

---

*Design agreed 2026-06-10 (Syafiq + Claude). Locked: two DBs (Uptime+Location); normalize-from-native-ledgers; JSON-safety; venue≠account (+`accounts` table); EA/Python boundary — self-contained native EA (signal+order+kill-switch) + Python independent auditor (recomputes from live bars, reads ledger, emits-nothing-from-EA); MT5-only build, IBKR a kept column. D0 gains a feed-divergence check; D2 gains a min-trade-count gate. Next: finalize `execution_schema.md` (full DDL) with Syafiq, then build. No tables built yet.*
