# Execution & Deployment Protocol

The **downstream** half of Baysix. Where [research_protocol.md](research_protocol.md) answers *"does this edge exist?"*, this protocol answers *"does the validated edge survive contact with a live broker — on any venue — and keep tracking the model once real money is on it?"*

Same rigor as the research ladder. Same discipline: pre-committed gates, a guardrail so they can't be skipped, all writes through a code layer, every decision logged to a lineage.

These are not novel inventions — they're the solo-scale collapse of three named institutional controls: **shadow / parallel running** (validate live behaviour before scaling capital), **product control / "shadow P&L"** (an independent function recomputes and reconciles, investigating every *break*), and **back-office reconciliation** (internal records vs the broker's). A bank splits these across three desks; we run them as one Python layer.

Status: **RE-LOCKED 2026-06-11 PM — rebuilding execution.db from scratch, TWO databases.** The earlier 3-store plan (`research.db` / `execution.db` / `tester.db`) collapsed to **two**: `research.db` (workstation) + `execution.db` (VPS). Port-fidelity is the *last research gate* (**Gate 7 — FIDELITY**, in research.db), so the MT5 Strategy Tester evidence (`tester_runs`/`tester_trades`) lives **inside research.db**, not a third file. The live deployment ladder is then a **single FORWARD gate** (demo→live sub-stages; §3). `venue` now = **protocol** (`mt5`/`ibkr`), broker is a column; **`instruments`** + **`equity_snapshots`** are built day-one. Build target is **MT5-only** (Just Markets, XAUUSD live); IBKR is a parked `venue` value, not code (§6). The §8 EA/Python fork was resolved 2026-06-10 (§2).

---

## 0. First principles

1. **research.db owns "what to trade"; execution.db owns "what happened when we traded it."** The execution layer *reads* the frozen config from research via `strategy_log.get_live_config(idea_id)` and **never re-defines it**.
2. **Two physical databases, split on machine + tempo.** `research.db` (workstation — calm, deliberate, validated lineage + the Strategy-Tester FIDELITY evidence, since port-fidelity is the last *research* gate) and `execution.db` (the VPS live deployment ledger — **real fills only**) are separate files. The wall is forced by where they run, not by simulated-vs-real (§1). Simulated fills are still walled off — they sit in `research.db`'s `tester_runs`/`tester_trades` (Gate 7 evidence), never in `execution.db`'s `signals`/`orders`/`fills`/`trades`. Re-locked 2026-06-11 PM (was a 3-store plan with a separate `tester.db`).
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

**Why this is two databases and not three.** The cut is **machine + tempo**, not simulated-vs-real. The MT5 Strategy Tester runs on the *workstation*, in *batch*, on *research data* (Dukascopy) — every property of the research world, none of the VPS world. So its evidence belongs in `research.db` (as **Gate 7 — FIDELITY**, the last research gate), not in a peer file to `execution.db`. A separate `tester.db` would have bought only "isolation," which a separate *table* already gives. And it is venue-specific scaffolding regardless: FIDELITY exists *only because MQL5 is a language port* — a Python→Python deployment (IBKR) has no port and skips it entirely.

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
| Author `signals` (intent + `expected_R` + `meta`) | **Python** | it recomputes the model — see below |
| Recon (live vs model) → `recon_results` | **Python** | must call the research model |
| Incidents from the Journal log | **Python** | forensic, replayable |

**The EA emits *nothing* to Python.** It is fire-and-forget. This is the keystone decision and it buys two things at once — *robustness* (no bridge on the trade path) and *zero added latency* (the EA's `OnTick → OrderSend` path never calls or waits on Python; they're separate OS processes; Python only *reads*).

### The independent auditor (why Python recomputes)
Python does **not** trust the EA's word for what it did. It reconstructs the session from two broker-sourced witnesses, via the `MetaTrader5` package ([reference_mt5_bridge](../memory/)) — never from the EA:

1. **The "should-have"** — Python pulls live bars itself (`mt5.copy_rates`) and **re-runs the exact research ORB function** (the same code the backtest used) → the model's intended trade.
2. **The "what actually happened"** — Python reads the broker's deal ledger (`HistoryDeal*`) → the real orders + fills.

Recon = subtract the two. This makes Python an **independent auditor**, not a stenographer: if it just logged the EA's claim, a buggy EA would look perfectly "matched" to its own mistake. Recomputing is what turns `signal_match_pct` into a lie-detector (the "shadow P&L break" of the live world).

**What it is and isn't:** once live, the auditor is a fast **detector** (catches drift seconds-to-minutes after a trade → pause before the *next* one), **not** a real-time **preventer** — the EA acts autonomously by design. True prevention happens earlier at FIDELITY (port proven on identical data) and FORWARD-demo (before real money), plus the EA's own kill-switch. Detector (Python) and preventer (EA kill-switch) are different jobs.

---

## 3. The gate ladder: research Gate 7 (FIDELITY) → FORWARD

The research ladder validates the edge (Gates 0–6). Two more gates carry it to live: **Gate 7 (FIDELITY)** proves the edge **transferred from research code to the deployed MQL5 artifact**, and **FORWARD** proves it **survives a real broker**. Each has a **pre-committed pass criterion** set before results are seen. A guardrail (twin of the `pass_gate(6)` fix) refuses promotion until the supporting evidence exists.

**Where each gate lives:** FIDELITY is the *last research gate* — it runs on the workstation, in batch, on research data, so it lives in **research.db** (`step3_gates` `gate_number=7`, evidenced by `tester_runs`/`tester_trades`). FORWARD is the *deployment* gate — it lives in **execution.db** (`deploy_gates`). The handoff between the two databases is exactly the handoff between "validated artifact" and "live deployment."

**Why FORWARD is a single gate (D0–D3 collapsed on 2026-06-11):** the old **D0 "feed/logic parity"** gate compared the Python model against the *live broker feed* before any EA existed — and for a path-dependent signal like ORB, a ~$1 feed drift flips long↔short, so "signals don't match" was **noise, not a verdict** ([[d0_feed_drift_reframe]]). The fix is not a better metric; it is **sequencing**. Feed reality can only be judged by P&L with the actual EA running — which is FORWARD. So **D0 is deleted**, its real concern absorbed into FORWARD. Old D1/D2/D3 (demo / live-micro / steady-state) collapse into the **single FORWARD gate** with demo→live sub-stages; steady-state becomes an ongoing *status*, not a promotion checkpoint.

**The principle:** each gate changes one thing.

| Gate | Lives in | Changes | Holds fixed | Isolates |
|------|----------|---------|-------------|----------|
| **7 — FIDELITY** | research.db | the code (Python → MQL5 EA) | the data (Dukascopy) | **port bugs** |
| **FORWARD** | execution.db | the feed + fills (broker reality) | the code (verified EA) | **broker/execution drift** |

```
research.db Gates 0–6 PASS  →  [MQL5 port: build the EA]  →  research.db GATE 7 FIDELITY
                                                                      │ pass
                                                  execution.db  →  FORWARD (demo→live)  →  STEADY (status)
```

### Gate 7 — FIDELITY  (the last research gate — port-fidelity)
**Question:** Does the compiled EA reproduce the research backtest on the *same* data?
**Method:** run the `.ex5` in the **MT5 Strategy Tester** on the **research feed** (Dukascopy custom symbol, 100% real ticks), same OOS window, at a **fair deposit** (large enough that the risk cap never binds — a too-small deposit makes the cap drop the volatile days and the tester takes a biased subsample). Ingest every tester trade into **research.db** (`tester_runs`/`tester_trades`); diff vs the Python research trade list (`step4_results`), per-trade and aggregate — a single-file join, no cross-DB `ATTACH`.
**Pass (statistical-equivalence, pre-committed):** trade-set overlap (same `session_date` + `direction`) ≥ 95%; E[R], win-rate and $/trade each inside the research 95% CI; per-trade R correlation high. The tester runs the *identical data*, so it should **not** drift — any material gap is a **port bug**, not noise.
**Block/Kill:** material divergence → the deployed code is not the validated strategy. Fix the EA; nothing goes near an account. No `deployments` row may even be registered until this passes (`register_deployment` enforces it). *(ORB-001 sits here now — FAILED: win-rate 56.7%→33.2%, trail exit.)*
**Hard rule:** FIDELITY **must** use the research data source (Dukascopy), never the broker's native history — otherwise it conflates a port bug with a feed difference (D0's original mistake). The broker feed is introduced for the first time at FORWARD, on purpose.
**Only for language ports:** FIDELITY exists *because* MQL5 is a re-implementation of the Python research code. A Python→Python deployment (e.g. IBKR via `ib_insync`) runs the same code it was validated on — there is no port to verify, so Gate 7 is N/A and it goes straight to FORWARD.
**Evidence:** research.db `tester_runs` + `tester_trades` — **never** the live execution.db `signals`/`orders`/`fills`/`trades`.

### FORWARD  (the deployment gate — single gate, demo→live sub-stages)
**Question:** Does the FIDELITY-verified EA keep the edge against a real broker feed and real fills?
**Sub-stages (one gate):** **demo** first (feed + execution realism, no capital at risk), then **live micro** ($50, min lot, Mode-A cap — real B-book fills). demo vs live is the deployment's `accounts.mode`; promotion = standing up the live deployment once the demo one tracks.
**Method:** deploy the EA; the Python **independent auditor** (§2) recomputes from live bars and reconciles vs the broker ledger → `recon_results`. Watch slippage vs the modeled spread, `signal_match_pct`, live E[R].
**Pass (pre-committed):** *demo* — fills track the tester within tolerance; slippage ≤ modeled; no catastrophic divergence. *live* — live E[R] / DD inside the **Gate-6 Monte-Carlo survival bands**, assessed only after `n ≥ N_min` trades (below that it is a catastrophic-divergence smoke test, not a statistical verdict).
**Block/Kill:** slippage materially worse than modeled, signals diverging, or live outside MC bands → pause, diagnose, `log_incidents` + `log_deploy`.
**Evidence:** execution.db `signals`/`orders`/`fills`/`trades` (real fills only) + `recon_results` + `equity_snapshots` (trailing-DD / kill-switch audit).

### STEADY — a status, not a gate
Once FORWARD-live passes, the deployment is `status='active'` and **monitored continuously** (rolling live-vs-recompute drift t-stat, incident watch, EA kill-switch). Sustained drift → demote/retire via `log_deploy`. This is ongoing operations, not a promotion checkpoint — which is exactly why FORWARD is a single gate, not three.

---

## 4. The five layers (mental model)

`execution.db` tracks the **life of a deployed strategy**, in the order it lives through:

```
1. REGISTER   →  what's deployed (idea, venue, instrument spec, account, frozen config, stage)
2. GATE       →  the FORWARD checkpoint (FIDELITY is research Gate 7; evidence: recon_results)
3. OBSERVE    →  what it actually did LIVE: signal → order → fill → trade (real fills only)
4. STATE      →  account value over time: equity_snapshots (trailing-DD / kill-switch audit)
5. RECONCILE  →  live vs model (the lie-detector)
6. RECORD     →  decisions made + incidents that happened
```

---

## 5. Schema

> Column lists are the **key** columns, not exhaustive — the full DDL is finalized interactively in `execution_schema.md` before any code. All tables carry `created_at`; mutable rows carry `updated_at`. PK = primary key, FK = foreign key (native within `execution.db`).

### Layer 1 — REGISTER

**`accounts`** — one row per broker account; the rulebook the EA kill-switch enforces. *(The venue-vs-account split, principle 4.)*

| Column | Role |
|--------|------|
| `account_id` (PK) | the account handle |
| `venue` | wire protocol / adapter: `mt5`, `ibkr` (NOT the broker) |
| `broker` | who it is: `justmarkets` / `darwinex` / `ftmo` / `ibkr` — all of the first three are `venue='mt5'` |
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

**`instruments`** — the tradable-product spec; built day-one so P&L / risk math is generic past XAU spot.

| Column | Role |
|--------|------|
| `symbol` (PK) | `XAUUSD.s` |
| `instrument_type` | `spot` / `fx` / `cfd` / `future` |
| `tick_size`, `tick_value`, `contract_size` | the money-math (`realized_pnl_usd`, `risk_unit` depend on these) |
| `expiry` | NULL for spot/fx; set for futures (rollover hook) |

Hardcoding XAU's `contract_size=100` is the regret the day a future arrives. `deployments.instrument` FK-references this.

**`deployments`** — one row per `(idea_id × venue × instrument)` deployment. The anchor every other table references. *(Renamed from `deploy_strategies`.)*

| Column | Role |
|--------|------|
| `deploy_id` (PK) | the handle everything else points to |
| `idea_id` | soft link to research.db (code-layer validated; **must be Gate-7-FIDELITY-passed**) |
| `venue` | `mt5`, `ibkr` — the protocol/adapter |
| `instrument` (FK → `instruments`) | `XAUUSD.s`, … |
| `account_id` (FK → `accounts`) | which account it runs on |
| `config_snapshot` (JSON) | **frozen copy** of the live config at deploy time (the deployment manifest) |
| `config_source` | `strategy_log` log_id / git sha the config came from |
| `stage` | live-side lifecycle: `FORWARD` / `STEADY` / `RETIRED` (FIDELITY is upstream in research.db) |
| `status` | `pending`/`active`/`paused`/`killed`/`retired` |

`config_snapshot` is the **contract** between the two databases: research can re-tune ORB-001 later, but this deployment knows exactly what version it is running. A `deployments` row only exists *after* Gate 7 (FIDELITY) passed upstream.

### Layer 2 — GATE

**`deploy_gates`** — the FORWARD checkpoint; mirror of research `step3_gates`. Kept as its own table (not folded into `log_deploy`) for **symmetry with the research ladder** — decision locked 2026-06-11. Only `FORWARD` lives here (FIDELITY is research Gate 7).

| Column | Role |
|--------|------|
| `gate_id` (PK), `deploy_id` (FK) | which deployment |
| `gate_name` | `FORWARD` (single-value CHECK, room to extend) |
| `sub_stage` | `demo` / `live` |
| `pass_criteria` | the pre-committed kill-line (text, set before results seen) |
| `status` | `open`/`passed`/`blocked`/`killed` |
| `gate_answer` | verdict + the numbers behind it |
| `answered_by`, `answered_at`, `attempt` | |

**Guardrail:** FORWARD cannot *open* until research Gate 7 (FIDELITY) is `passed` for the `idea_id` (cross-DB soft check); cannot *pass* until `recon_results` exist; `live` sub_stage needs `demo` passed.

### Layer 3 — OBSERVE (the live event stream)

A trade's life: **signal → order → fill → trade.**

**`signals`** — what the strategy *wanted* (intent). **Authored by Python's recompute** (§2), not emitted by the EA. *(Un-prefixed: the `exec_` is redundant inside `execution.db`.)*

| Column | Role |
|--------|------|
| `signal_id` (PK), `deploy_id` (FK) | |
| `signal_ts`, `session_date` | when the model decided (tz-explicit) |
| `direction` | `long`/`short`/`flat` — universal |
| `intended_entry_px`, `intended_stop_px`, `intended_target_px` | levels (target nullable for trailers) |
| `intended_size` | lots |
| `expected_R` | model's predicted R — stored here for per-trade recon |
| `meta` (JSON) | **strategy-private context only** — ORB `{or_high, or_low, range_w, anchor}`, MR `{zscore, lookback}`, … authored in Python, schema-validated (§7) |

**`orders`** — what was *sent to the broker*. Normalized from the venue ledger (§6).

`order_id` (PK), `signal_id` (FK), `deploy_id` (FK), `venue_order_id` (broker ticket), `order_type`, `side`, `requested_px`, `requested_size`, `status` (`sent`/`accepted`/`rejected`/`filled`/`cancelled`), `reject_reason`. *(The EA's actual SL/TP live here — Python reads them from the order record, never from the EA.)*

**`fills`** — what the broker *gave us*. Normalized from the venue's native ledger. One order → N fills (partials/scaling) is why `orders` and `fills` stay separate.

`fill_id` (PK), `order_id` (FK), `deploy_id` (FK), `venue_deal_id` (MT5 deal / IBKR execId), `fill_px`, `fill_size`, `fill_ts`, **`slippage_px`** (fill − requested, captured at **both legs** — entry *and* exit), `commission`, `swap`.
→ `slippage_px` is the single most important number at FORWARD. `commission`/`swap` come from `HistoryDealGetDouble(DEAL_COMMISSION / DEAL_SWAP)`, **not** the event payload (§6). Capture `swap` even though Just Markets is swap-free today — swap-free is a broker plugin with a grace period that can start charging.

**`trades`** — the closed round-trip; the reconciliation unit.

| Column | Role |
|--------|------|
| `trade_id` (PK), `deploy_id`, `signal_id` (FK) | |
| `entry_ts/px`, `exit_ts/px`, `exit_reason` | the realized trade |
| `risk_unit` | the 1R distance — generic (ORB `range_w`, ATR stop, …) |
| `realized_R` | what we **actually** got live |
| `expected_R` | what the model **said** (copied from signal) |
| `realized_pnl_usd` | dollars |

`realized_R` and `expected_R` side-by-side make reconciliation a subtraction, not a project.

### Layer 4 — STATE

**`equity_snapshots`** — periodic account-value readings (UTC `snapshot_ts`, `equity`, `balance`, `open_pnl`). Keyed at `account_id` (account-level rule, aggregates across strategies).

`trades` only records *closed* round-trips; trailing drawdown (FTMO) is measured on the **equity peak including floating profit**, so a winning trade can still breach a trailing-DD line mid-flight. Without sampled equity you cannot reconcile a trailing-DD breach or audit whether the EA kill-switch (which acts on `ACCOUNT_EQUITY`) fired correctly. **Cadence is an ingester policy, not schema:** per-fill + a fixed interval (default 1-min while a position is open), **never per-tick** (the real row-volume driver).

### Layer 5 — RECONCILE

**`recon_results`** — the `step4_results` of the live world. Flexible `metric_key`/`metric_value` rows so any strategy logs any metric. Written by the recon job (§9).

| Column | Role |
|--------|------|
| `recon_id` (PK), `deploy_id` (FK) | |
| `gate_id` | which FORWARD gate this recon feeds (nullable FK → `deploy_gates`) |
| `period_start`, `period_end` | window reconciled |
| `metric_key`, `metric_value`, `n_obs` | flexible (twin of step4_results) |

Core metrics: `signal_match_pct` (runtime parity, from the recompute), `slippage_median_px` (cost-model check), `feed_divergence_px` (FORWARD-demo, vs the verified tester baseline), `live_E_R` + `drift_t_vs_IS` (edge tracking). At scalping rates these become **distributional** metrics over a window — same row shape, no schema change. FIDELITY-gate diff metrics (`trade_overlap_pct`, `ER_delta_vs_research`, `R_corr`) live in **research.db** (`tester_runs`), not here.

### Layer 6 — RECORD

**`log_deploy`** — mirror of `log_strategy`. Deployment decision lineage.
`log_id` (PK), `deploy_id` (FK), `event`, `from_stage`, `to_stage`, `verdict` (`CREATED`/`PROMOTED`/`PAUSED`/`KILLED`/`RESUMED`/`RETIRED`), `rationale`, `recon_id` (the evidence), `decided_by`.

**`log_incidents`** — the live black-box recorder; the thing research never has.
`incident_id` (PK), `deploy_id` (FK), `incident_ts`, `severity` (`info`/`warn`/`critical`), `kind` (`disconnect`/`missed_fill`/`slippage_spike`/`reject`/`killswitch_fire`/`data_gap`/`config_mismatch`/`prop_rule_breach`/`tz_mismatch`), `detail`, `resolved`.

---

## 6. Multi-venue: normalize from native ledgers (do NOT hand-journal)

Both brokers maintain an authoritative, structured execution ledger. We **consume and normalize** them — never rebuild a flimsier copy. **Build is MT5-only now**; IBKR is a kept column (`venue`), zero IBKR code, until task 30 is pursued.

- **MetaTrader 5:** [`OnTradeTransaction`](https://www.mql5.com/en/docs/event_handlers/ontradetransaction) is the real-time **doorbell** ("something changed — go look"), **not** the ledger — never compute P&L/commission/swap from its payload. The authoritative numbers come from [`HistorySelect` + `HistoryDealGetTicket`](https://www.mql5.com/en/docs/trading/historydealgetticket): price, volume, `DEAL_COMMISSION`, `DEAL_SWAP`, profit, time. Two caveats the normalizer must handle: deals arrive **asynchronously** (the commission row can land separately from the fill), and **swap** is realized into `DEAL_SWAP` at close (sum across deals — never `POSITION_SWAP`, which double-counts on partial closes).
- **Interactive Brokers (parked):** [`execDetails` + `commissionReport`](https://interactivebrokers.github.io/tws-api/executions_commissions.html) per fill (async; `ib_insync` wraps it), corrections via amended execId.

**The venue-adapter pattern:** one thin, **fully isolated** adapter per venue maps that venue's native records into the canonical `orders` / `fills` / `trades` columns. MT5 and IBKR adapters share **no code** — only the output table shape. `venue_order_id` / `venue_deal_id` retain the broker's native identifiers for audit traceability.

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

1. At deploy, **Python** reads `strategy_log.get_live_config(idea_id)` + the `accounts` row → writes the EA's inputs (an MT5 `.set` file or input block) **and** the `config_snapshot` into `deployments`.
2. On init, the **EA asserts** its loaded params equal `config_snapshot`; any mismatch → `log_incidents(kind='config_mismatch')` and refuse to arm.

This is a **one-time handoff at deploy, not a live dependency** — the EA needs no running Python thereafter. It carries the kill-switch parameters (`max_daily_loss_pct`, `max_total_dd_pct`, `daily_reset_tz`) into the EA, which enforces them live via `AccountInfoDouble(ACCOUNT_EQUITY)`. Time handling uses MT5's native `TimeTradeServer/TimeGMT/TimeGMTOffset/TimeDaylightSavings`; note the Strategy Tester does **not** simulate DST — anchors and `daily_reset_tz` are tested explicitly, never assumed.

---

## 9. Data flow

```
EA decides + places order            (self-contained; emits NOTHING to Python)
broker books the deal                → HistoryDeal* (ground truth)
                       ┌─ Python recomputes signal from live bars  → signals (intent + expected_R)
Python (own process) ──┤
                       ├─ Python reads the ledger                  → orders / fills / trades
                       └─ Python polls account value (per-fill/1-min) → equity_snapshots
end of session         → recon job (subtract recompute vs ledger)  → recon_results
   break?              → log_incidents + log_deploy(pause)
   clean?              → FORWARD-gate review reads recon → log_deploy(promote)
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

## 11. Build order (rebuild from scratch — 2026-06-11)

0. **research.db migration** — add `tester_runs` + `tester_trades`; ensure `step3_gates.gate_number` admits `7` (Gate 7 — FIDELITY). Preserves all research data.
1. **execution.db rebuild migration** — drop the old D0-era `execution.db` (43 obsolete D0-parity signals + biased $50 tester run + the misplaced tester tables from migration 021; nothing precious lost). Create the fresh **12-table** `execution.db` from the locked `execution_schema.md` DDL (`venue`=protocol + `broker`, `instruments`, `equity_snapshots`, real-fills-only `signals`/`orders`/`fills`/`trades`, FORWARD-only `deploy_gates`).
2. **Code layers** — `execution.py` (`_SCHEMA` + validated write functions) for `execution.db`; tester writers (`ingest_tester_run/trade`, `log_fidelity_diff` → `pass_gate(7)`) added to the **research** code layer (they write `research.db`). Smoke test the FORWARD-needs-Gate-7-FIDELITY guardrail.
3. **Gate 7 / FIDELITY for ORB-001** — ingest the $10k tester trades into research.db → diff vs Python research `step4_results` (per-trade + aggregate, statistical-equivalence). This is task 43; currently FAILING (trail-exit port bug — a separate EA fix).
4. MT5 venue adapter (normalize `HistoryDeal*`, triggered by `OnTradeTransaction`; async + swap-at-close) — for FORWARD.
5. Python recompute auditor + recon job (recompute vs ledger → `recon_results`) + equity-snapshot poller.
6. Config-handoff generator (`get_live_config` + `accounts` → EA `.set`; EA self-assert).
7. FORWARD-demo run on Just Markets → reconcile → promote to FORWARD-live.
8. IBKR adapter (task 30, separate venue research) when/if pursued — `venue='ibkr'` + abstract gate names already make this additive; no Gate 7 (Python→Python, no port).

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

*Design agreed 2026-06-10 (Syafiq + Claude). Locked: normalize-from-native-ledgers; JSON-safety; venue≠account (+`accounts` table); EA/Python boundary — self-contained native EA (signal+order+kill-switch) + Python independent auditor (recomputes from live bars, reads ledger, emits-nothing-from-EA); MT5-only build, IBKR a kept column.*

*Redesigned 2026-06-11 AM (Syafiq + Claude). **D0 scrapped** (feed-parity-pre-EA was the wrong tool for a path-dependent signal). **FORWARD** = single gate, demo→live sub-stages; steady-state is a status. (Superseded that morning's tester.db split — see below.)*

*RE-LOCKED 2026-06-11 PM (Syafiq + Claude). Collapsed 3 stores → **2 databases** (cut on machine+tempo, not simulated-vs-real). The MT5 Strategy Tester is the *last research gate* — **Gate 7 — FIDELITY** in `research.db` (`tester_runs`/`tester_trades` next to `step4_results`), not a third file. Live ladder = the single **FORWARD** gate in `execution.db`. `venue` = protocol (`mt5`/`ibkr`) + new `broker` column; **`instruments`** + **`equity_snapshots`** built day-one; `deploy_gates` kept for symmetry but `FORWARD`-only; OBSERVE tables un-prefixed; `deploy_strategies`→`deployments`; all 12 tables built in one migration. FIDELITY is N/A for Python→Python venues (IBKR). Next: research.db migration + execution.db rebuild per the new `execution_schema.md`.*
