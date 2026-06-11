# execution.db — Schema Specification

The full DDL for `execution.db`, the downstream twin of `research.db`. This is the **build spec**: every table, column, type, and constraint is final here before `execution.py` is written. Design rationale lives in [execution_protocol.md](execution_protocol.md); this doc is the *what*, that one is the *why*.

Status: **SPEC RE-LOCKED 2026-06-11 (session 2) — rebuilding from scratch, TWO databases.** The earlier 3-store design (`research.db` / `execution.db` / `tester.db`) collapsed to **two**: `research.db` (workstation) and `execution.db` (VPS). The MT5 Strategy Tester evidence is **not** a third database — port-fidelity is the *last research gate* (**Gate 7 — FIDELITY**), so `tester_runs` + `tester_trades` live **inside `research.db`** next to `step4_results`. See [§ research.db — Gate 7 evidence](#researchdb--gate-7-evidence-fidelity).

Build = a **research.db migration** (adds `tester_runs` + `tester_trades`, enables `gate_number=7`) **+** an **execution.db rebuild migration** (drops the old D0-era DB + the misplaced tester tables from migration 021, creates the 12 tables below). MT5-only; IBKR is a kept `venue` value, no code.

> **Naming update (2026-06-11 PM2, built):** tables carry a **layer-number prefix** so a DB browser lists them in pipeline order (mirrors research's `step1_`…`step4_`). The DDL blocks below use the bare names for readability; the **live names** are: REGISTER → `d1_accounts` / `d1_instruments` / `d1_deployments`; GATE → `d2_deploy_gates`; OBSERVE → `d3_signals` / `d3_orders` / `d3_fills` / `d3_trades`; STATE → `d4_equity_snapshots`; RECONCILE → `d5_recon_results`; RECORD → `log_deploy` / `log_incidents` (ledgers keep `log_`, as in research.db). The canonical schema is [research/code/execution.py](../research/code/execution.py) `_SCHEMA`.

---

## What changed vs the 2026-06-10 spec (read this if you knew the old one)

| Change | Old | New |
|--------|-----|-----|
| **# of databases** | 3 (research / execution / **tester.db**) | **2** (research / execution) |
| **Tester evidence** | separate `tester.db` file | **`research.db`** tables — Gate 7 (FIDELITY) is the last *research* gate |
| **`venue` meaning** | broker name (`justmarkets`) | **protocol** (`mt5` / `ibkr`); broker → new `accounts.broker` column |
| **`deploy_gates` rows** | `FIDELITY` + `FORWARD` | **`FORWARD` only** (FIDELITY now lives in research.db) — table KEPT for symmetry with `step3_gates` |
| **`instruments` table** | deferred (growth path) | **built day-one** — P&L / risk math needs tick value before futures arrive |
| **`equity_snapshots` table** | absent | **built day-one** — the only way to reconcile trailing-DD + audit the kill-switch |
| **OBSERVE table names** | `exec_signals` / `exec_orders` / `exec_fills` / `exec_trades` | `signals` / `orders` / `fills` / `trades` (prefix redundant inside `execution.db`) |
| **`deploy_strategies`** | name | renamed **`deployments`** |
| **Phasing** | build 6 core now, grow to 10 | **build all 12 at once** — one migration, no schema churn |

`execution.db` = **12 tables**. `research.db` gains **2** (tester evidence).

---

## Conventions (inherited from research.db — `execution.py` mirrors `pipeline.py`)

| Rule | Convention |
|------|-----------|
| **PK — anchor tables** | readable `TEXT PRIMARY KEY` (`accounts`, `deployments`, `instruments`) |
| **PK — child/event tables** | `INTEGER PRIMARY KEY AUTOINCREMENT` |
| **Enums** | belt **and** suspenders: inline `CHECK(col IN (...))` **+** `VALID_*` tuple raising `ValueError` in the code layer |
| **Booleans** | `INTEGER ... CHECK(col IN (0,1)) DEFAULT 0` |
| **FKs** | native `REFERENCES`, `PRAGMA foreign_keys = ON` — **except `idea_id`** (soft key, code-validated, lives in research.db) |
| **JSON columns** | `TEXT CHECK(col IS NULL OR json_valid(col))` + `meta_schema_version` + Pydantic validation in code layer |
| **Bookkeeping time** (`created_at`, `updated_at`) | **MYT (UTC+8)**, `"%Y-%m-%d %H:%M:%S"` — mirrors research `_now()`. "When we recorded it." |
| **Market time** (`signal_ts`, `fill_ts`, `entry_ts`, `exit_ts`, `incident_ts`, `snapshot_ts`) | **UTC**, normalized on ingest (MT5 hands broker-server time → adapter converts). "When the market did it." |
| **`session_date`** | `DATE` in the anchor's reference tz (e.g. ET session date), stored explicitly |

**Three locked decisions baked in:**
- **`venue` = protocol, not broker.** `venue IN ('mt5','ibkr')` is the *adapter / code path*. The broker is `accounts.broker` (`justmarkets` / `darwinex` / `ftmo` — all `mt5`). This is what lets one MT5 adapter serve three brokers (protocol §4).
- **Magic scheme:** readable deterministic map owned by the code layer — `ORB-001 → 1001`, `ORB-002 → 1002`, … A magic spotted in the MT5 terminal is self-identifying. `UNIQUE(account_id, magic_number)`.
- **Redeploy = singleton:** one `deployments` row per `(idea × account × instrument)`; relaunching a killed deployment flips its `status` (`killed → pending`); the lifecycle history lives in `log_deploy`. No instance suffixes.

---

## Layer 1 — REGISTER

### `accounts` — the rulebook the EA kill-switch enforces
```sql
CREATE TABLE accounts (
    account_id         TEXT PRIMARY KEY,            -- readable slug, e.g. 'jm-live-01'
    venue              TEXT NOT NULL CHECK(venue IN ('mt5','ibkr')),  -- PROTOCOL (adapter), not broker
    broker             TEXT NOT NULL,               -- 'justmarkets' / 'darwinex' / 'ftmo' / 'ibkr'
    account_type       TEXT NOT NULL CHECK(account_type IN
                         ('retail_highlev','darwinex_alloc',
                          'ftmo_challenge','ftmo_funded','ibkr_dma')),
    mode               TEXT NOT NULL CHECK(mode IN ('demo','live')),  -- real capital y/n
    broker_login       TEXT,                        -- MT5 login # (join key to terminal; NOT a secret)
    base_currency      TEXT NOT NULL DEFAULT 'USD',
    leverage           INTEGER,                     -- 1:N → store N
    initial_balance    REAL,                        -- baseline for the % rules
    -- prop kill-lines: typed (kill-switch reconciles on them); NULL = no such rule
    max_daily_loss_pct REAL,
    max_total_dd_pct   REAL,
    dd_basis           TEXT CHECK(dd_basis IS NULL OR dd_basis IN ('static','trailing')),
    daily_reset_tz     TEXT,                        -- IANA, e.g. 'Europe/Prague' (FTMO midnight CET)
    profit_target_pct  REAL,
    min_trading_days   INTEGER,
    rules_meta         TEXT CHECK(rules_meta IS NULL OR json_valid(rules_meta)),
    status             TEXT NOT NULL DEFAULT 'active'
                         CHECK(status IN ('active','breached','closed')),
    created_at         DATETIME NOT NULL,
    updated_at         DATETIME NOT NULL
);
```
`mode` (real capital?) and `account_type` (which ruleset?) are orthogonal: an FTMO challenge is `mode='demo'` + `type='ftmo_challenge'`. The kill-switch keys off `account_type` rules regardless of `mode`. `venue` says *how we talk to it*; `broker` says *who it is*. Darwinex + FTMO + Just Markets are all `venue='mt5'`, different `broker`.

### `instruments` — the tradable-product spec (makes the ledger generic past XAU spot)
```sql
CREATE TABLE instruments (
    symbol           TEXT PRIMARY KEY,              -- 'XAUUSD.s' (broker-specific symbol)
    display_name     TEXT,                          -- 'Gold spot'
    instrument_type  TEXT NOT NULL CHECK(instrument_type IN
                       ('spot','fx','cfd','future')),
    base_asset       TEXT,                          -- 'XAU'
    quote_currency   TEXT NOT NULL DEFAULT 'USD',
    tick_size        REAL NOT NULL,                 -- min price increment (0.01 for XAUUSD.s)
    tick_value       REAL,                          -- $ per tick per 1.0 lot (futures: contract-specific)
    contract_size    REAL NOT NULL,                 -- oz/lot for XAU = 100; contract multiplier for futures
    min_lot          REAL,                          -- 0.01
    lot_step         REAL,
    expiry           DATE,                           -- NULL for spot/fx/cfd; set for futures (rollover hook)
    meta             TEXT CHECK(meta IS NULL OR json_valid(meta)),
    created_at       DATETIME NOT NULL,
    updated_at       DATETIME NOT NULL
);
```
Built day-one even though XAUUSD is the only row: `realized_pnl_usd` and `risk_unit` math depend on `tick_value`/`contract_size`. Hardcoding XAU's `100` is the regret the day a future (own `tick_value`, `expiry`) arrives. `deployments.instrument` FK-references this.

### `deployments` — one row per `(idea × venue × instrument)` deployment; the anchor
```sql
CREATE TABLE deployments (
    deploy_id        TEXT PRIMARY KEY,              -- 'ORB-001@jm-live-01'
    idea_id          TEXT NOT NULL,                 -- SOFT key → research.db (code-validated, NO FK)
    venue            TEXT NOT NULL CHECK(venue IN ('mt5','ibkr')),  -- protocol
    instrument       TEXT NOT NULL REFERENCES instruments(symbol),
    account_id       TEXT NOT NULL REFERENCES accounts(account_id),
    magic_number     INTEGER NOT NULL,              -- EA stamp → ledger attribution key
    config_snapshot  TEXT CHECK(config_snapshot IS NULL OR json_valid(config_snapshot)),
    config_source    TEXT,                          -- strategy_log log_id / git sha
    meta_schema_version TEXT,
    stage            TEXT NOT NULL DEFAULT 'FORWARD'  -- live-side lifecycle (FIDELITY is upstream in research.db)
                       CHECK(stage IN ('FORWARD','STEADY','RETIRED')),
    status           TEXT NOT NULL DEFAULT 'pending'
                       CHECK(status IN ('pending','active','paused','killed','retired')),
    created_at       DATETIME NOT NULL,
    updated_at       DATETIME NOT NULL,
    UNIQUE(account_id, magic_number)                -- no magic collision on one account
);
```
`config_snapshot` is the **contract** between the two databases: research can re-tune ORB-001 later, but this deployment knows exactly what version it is running. Note `stage` starts at `FORWARD` — a deployment only exists *after* Gate 7 (FIDELITY) passed upstream in research.db.

---

## Layer 2 — GATE

### `deploy_gates` — the FORWARD checkpoint (mirror of research `step3_gates`)
```sql
CREATE TABLE deploy_gates (
    gate_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    deploy_id     TEXT NOT NULL REFERENCES deployments(deploy_id),
    gate_name     TEXT NOT NULL DEFAULT 'FORWARD' CHECK(gate_name IN ('FORWARD')),  -- FIDELITY is research Gate 7
    sub_stage     TEXT CHECK(sub_stage IS NULL OR sub_stage IN ('demo','live')),
    attempt       INTEGER NOT NULL DEFAULT 1,
    pass_criteria TEXT,                             -- pre-committed kill-line (set BEFORE results seen)
    gate_answer   TEXT,                             -- verdict + numbers
    evidence_ref  TEXT,                             -- recon window: 'recon_results:period=...'
    status        TEXT NOT NULL DEFAULT 'open'
                  CHECK(status IN ('open','passed','blocked','killed')),
    answered_by   TEXT,
    created_at    DATETIME NOT NULL,
    updated_at    DATETIME NOT NULL,
    answered_at   DATETIME,
    UNIQUE(deploy_id, gate_name, sub_stage, attempt)
);
```
Kept as its own table (not folded into `log_deploy`) for **symmetry with research's `step3_gates`** — decision locked 2026-06-11. Only `FORWARD` lives here; `gate_name` is a single-value CHECK with room to extend.

**Two guardrails (code layer):**
1. **FORWARD cannot OPEN** until **Gate 7 (FIDELITY) is `passed` in research.db** for this deployment's `idea_id` (cross-DB soft check — code-layer query / `ATTACH`, twin of the `idea_id` existence check). A failing port never reaches an account.
2. **FORWARD cannot PASS** until supporting `recon_results` exist (twin of the `pass_gate(6)` fix). `demo` sub_stage must pass before `live` sub_stage opens.

---

## Layer 3 — OBSERVE (signal → order → fill → trade) — LIVE accounts only

> Real broker fills only (demo-account-live *and* real-money-live — both are broker reality). Strategy-Tester (simulated) trades never land here — they go to `research.db` (Gate 7 evidence).

### `signals` — intent (authored by Python's recompute, NOT emitted by EA)
```sql
CREATE TABLE signals (
    signal_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    deploy_id          TEXT NOT NULL REFERENCES deployments(deploy_id),
    signal_ts          DATETIME NOT NULL,           -- UTC (market time)
    session_date       DATE NOT NULL,               -- anchor-tz session date
    direction          TEXT NOT NULL CHECK(direction IN ('long','short','flat')),
    intended_entry_px  REAL,
    intended_stop_px   REAL,
    intended_target_px REAL,                         -- nullable (trailers)
    intended_size      REAL,                         -- lots
    expected_R         REAL,
    meta               TEXT CHECK(meta IS NULL OR json_valid(meta)),  -- {or_high,or_low,range_w,anchor,feed_window,feed_source}
    meta_schema_version TEXT,
    created_at         DATETIME NOT NULL             -- MYT (bookkeeping)
);
```
`meta` also carries **feed provenance** (`feed_window`, `feed_source`) — which bars the auditor recomputed against, so a recon break can be replayed without a bar-archive table.

### `orders` — what was sent to the broker (normalized from venue)
```sql
CREATE TABLE orders (
    order_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id      INTEGER REFERENCES signals(signal_id),
    deploy_id      TEXT NOT NULL REFERENCES deployments(deploy_id),
    venue_order_id TEXT,                             -- broker ticket
    order_type     TEXT,                             -- market/limit/stop
    side           TEXT CHECK(side IS NULL OR side IN ('buy','sell')),
    requested_px   REAL,
    requested_size REAL,                             -- lots
    status         TEXT NOT NULL DEFAULT 'sent'
                   CHECK(status IN ('sent','accepted','rejected','filled','cancelled')),
    reject_reason  TEXT,
    placed_ts      DATETIME,                         -- UTC
    created_at     DATETIME NOT NULL                 -- MYT
);
```
The EA's actual SL/TP live on the broker order record → read here by Python, never from the EA.

### `fills` — what the broker gave us (normalized from native ledger)
```sql
CREATE TABLE fills (
    fill_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id      INTEGER REFERENCES orders(order_id),
    deploy_id     TEXT NOT NULL REFERENCES deployments(deploy_id),
    venue_deal_id TEXT,                              -- MT5 deal / IBKR execId
    leg           TEXT NOT NULL CHECK(leg IN ('entry','exit')),  -- slippage on BOTH
    fill_px       REAL NOT NULL,
    fill_size     REAL NOT NULL,
    fill_ts       DATETIME NOT NULL,                 -- UTC
    slippage_px   REAL,                              -- fill − requested
    commission    REAL,                              -- HistoryDealGetDouble(DEAL_COMMISSION)
    swap          REAL,                              -- HistoryDealGetDouble(DEAL_SWAP) — capture even if swap-free
    magic_number  INTEGER,                           -- echoed from deal → attribution assert
    created_at    DATETIME NOT NULL                  -- MYT
);
```
`slippage_px` is the single most important number at FORWARD. `commission`/`swap` come from the deal ledger, **not** the `OnTradeTransaction` payload. On ingest the adapter asserts `magic_number == deployment.magic_number`; mismatch → `config_mismatch` incident. One order → N fills (partials/scaling) is why `orders` and `fills` are separate.

### `trades` — the closed round-trip (the reconciliation unit)
```sql
CREATE TABLE trades (
    trade_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    deploy_id        TEXT NOT NULL REFERENCES deployments(deploy_id),
    signal_id        INTEGER REFERENCES signals(signal_id),
    entry_ts         DATETIME,                       -- UTC
    entry_px         REAL,
    exit_ts          DATETIME,                       -- UTC
    exit_px          REAL,
    exit_reason      TEXT,                           -- stop/target/trail/manual/eod
    risk_unit        REAL,                           -- the 1R distance (ORB range_w, ATR, …)
    realized_R       REAL,                           -- what we ACTUALLY got
    expected_R       REAL,                           -- what the model SAID (copied from signal)
    realized_pnl_usd REAL,                           -- via instruments.tick_value/contract_size
    created_at       DATETIME NOT NULL               -- MYT
);
```

---

## Layer 4 — STATE

### `equity_snapshots` — periodic account-value readings (trailing-DD + kill-switch audit)
```sql
CREATE TABLE equity_snapshots (
    snapshot_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id    TEXT NOT NULL REFERENCES accounts(account_id),
    deploy_id     TEXT REFERENCES deployments(deploy_id),  -- nullable: account-level snapshots span strategies
    snapshot_ts   DATETIME NOT NULL,                 -- UTC
    equity        REAL NOT NULL,                     -- balance + floating P&L of open positions
    balance       REAL NOT NULL,                     -- realized only
    open_pnl      REAL,                              -- floating
    margin_used   REAL,
    created_at    DATETIME NOT NULL                  -- MYT
);
```
**Why it exists:** `trades` only records *closed* round-trips. Trailing drawdown (FTMO) is measured on the **equity peak including floating profit** — a winning trade can still breach a trailing-DD line mid-flight. Without sampled equity you cannot reconcile a trailing-DD breach or audit whether the EA kill-switch fired correctly (it acts on `ACCOUNT_EQUITY`, not closed trades).
**Cadence is an ingester policy, not schema:** sample **per-fill** and on a **fixed interval (default 1-min while a position is open)** — **never per-tick** (that is the real row-volume driver, not trade count). Keyed at `account_id` because trailing-DD is an account-level rule that aggregates across strategies.

---

## Layer 5 — RECONCILE

### `recon_results` — the step4_results of the live world
```sql
CREATE TABLE recon_results (
    recon_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    deploy_id    TEXT NOT NULL REFERENCES deployments(deploy_id),
    gate_id      INTEGER REFERENCES deploy_gates(gate_id),  -- which FORWARD gate this feeds (nullable)
    period_start DATE,
    period_end   DATE,
    metric_key   TEXT NOT NULL,                      -- signal_match_pct, slippage_median_px,
    metric_value REAL NOT NULL,                      --   feed_divergence_px, live_E_R, drift_t_vs_IS
    n_obs        INTEGER,
    created_at   DATETIME NOT NULL                   -- MYT
);
```
At hundreds-of-trades/day (scalping) reconciliation shifts from per-trade matching to **distributional** (slippage distribution, hit-rate, windowed live E[R]) — the flexible `metric_key`/`metric_value` + `n_obs` shape already absorbs that with no schema change.

---

## Layer 6 — RECORD

### `log_deploy` — deployment decision lineage (mirror of log_strategy)
```sql
CREATE TABLE log_deploy (
    log_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    deploy_id   TEXT NOT NULL REFERENCES deployments(deploy_id),
    event       TEXT,
    from_stage  TEXT,
    to_stage    TEXT,
    verdict     TEXT NOT NULL CHECK(verdict IN
                  ('CREATED','PROMOTED','PAUSED','KILLED','RESUMED','RETIRED')),
    rationale   TEXT,
    recon_id    INTEGER REFERENCES recon_results(recon_id),  -- the evidence
    decided_by  TEXT NOT NULL DEFAULT 'human' CHECK(decided_by IN ('human','agent')),
    created_at  DATETIME NOT NULL                    -- MYT
);
```

### `log_incidents` — the live black-box recorder
```sql
CREATE TABLE log_incidents (
    incident_id INTEGER PRIMARY KEY AUTOINCREMENT,
    deploy_id   TEXT REFERENCES deployments(deploy_id),  -- nullable: some incidents are account-level
    account_id  TEXT REFERENCES accounts(account_id),
    incident_ts DATETIME NOT NULL,                   -- UTC (when it happened)
    severity    TEXT NOT NULL CHECK(severity IN ('info','warn','critical')),
    kind        TEXT NOT NULL CHECK(kind IN
                  ('disconnect','missed_fill','slippage_spike','reject',
                   'killswitch_fire','data_gap','config_mismatch',
                   'prop_rule_breach','tz_mismatch','heartbeat_gap')),
    detail      TEXT,
    resolved    INTEGER NOT NULL DEFAULT 0 CHECK(resolved IN (0,1)),
    created_at  DATETIME NOT NULL                    -- MYT
);
```

---

## research.db — Gate 7 evidence (FIDELITY)

**These two tables physically live in `research.db`, not `execution.db`.** Port-fidelity is the *last research gate* — it compares the compiled EA (run in the MT5 Strategy Tester on Dukascopy) against the Python research backtest *on the same data*, both workstation/batch activities. The verdict is a `step3_gates` row with `gate_number=7`; these tables are its evidence, next to `step4_results`. The diff is then a single-file join — no cross-DB `ATTACH`. (Spec kept here so the whole FIDELITY story reads in one place; physically it is a research.db migration.)

### `tester_runs` — one row per Strategy-Tester run (the FIDELITY run header)
```sql
CREATE TABLE tester_runs (
    run_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    idea_id         TEXT NOT NULL,                 -- FK-soft into step1_ideas (same DB now)
    ea_name         TEXT,                          -- 'baysix_orb_001'
    ea_version      TEXT,
    symbol          TEXT NOT NULL,                 -- e.g. 'XAUUSD_dukas'
    data_source     TEXT NOT NULL CHECK(data_source IN ('dukascopy','broker_history','custom')),
    model_quality   TEXT,                          -- MT5 history quality, e.g. '100% real ticks'
    tester_model    TEXT CHECK(tester_model IS NULL OR tester_model IN
                       ('real_ticks','every_tick','1min_ohlc','open_only')),
    timeframe       TEXT,                          -- 'M1'
    period_start    DATE,
    period_end      DATE,
    tz_offset_hours INTEGER,                        -- tester server→UTC offset (0 = UTC dukas)
    magic_number    INTEGER,
    initial_deposit REAL,                           -- fair deposit (cap non-binding)
    leverage        INTEGER,
    spread_setting  TEXT,                           -- 'real' | 'fixed:N'
    params          TEXT CHECK(params IS NULL OR json_valid(params)),  -- EA inputs snapshot
    -- run-level summary --
    n_trades        INTEGER,
    net_profit_usd  REAL,
    profit_factor   REAL,
    max_dd_pct      REAL,
    win_rate        REAL,
    -- FIDELITY diff vs Python research (filled by log_fidelity_diff) --
    research_result_id   INTEGER,                   -- soft ref to step4_results
    trade_overlap_pct    REAL,                      -- same session_date+direction
    ER_delta_vs_research REAL,
    R_corr               REAL,
    fidelity_verdict     TEXT CHECK(fidelity_verdict IS NULL OR
                            fidelity_verdict IN ('pass','fail','pending')),
    notes           TEXT,
    created_at      DATETIME NOT NULL,
    updated_at      DATETIME NOT NULL
);
```

### `tester_trades` — per-trade tester ledger (join key to the Python backtest)
```sql
CREATE TABLE tester_trades (
    tt_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id           INTEGER NOT NULL REFERENCES tester_runs(run_id),
    ticket           INTEGER,
    session_date     DATE,                          -- join key to the Python backtest
    direction        TEXT CHECK(direction IS NULL OR direction IN ('long','short','flat')),
    entry_ts         DATETIME,
    entry_px         REAL,
    exit_ts          DATETIME,
    exit_px          REAL,
    exit_reason      TEXT,
    risk_unit        REAL,                          -- range_w (1R)
    realized_R       REAL,
    realized_pnl_usd REAL,
    or_high          REAL,
    or_low           REAL,
    range_w          REAL,
    created_at       DATETIME NOT NULL
);
```

---

## Code layer — `research/code/execution.py` (writes `execution.db`)

All writes go through here (CLAUDE.md rule 10). Mirrors `pipeline.py`/`strategy_log.py`: `_conn()` with `PRAGMA foreign_keys=ON` + `row_factory`, `_now()` in MYT, `VALID_*` tuples, returns the new id, prints a confirmation line.

**REGISTER**
- `register_account(account_id, venue, broker, account_type, mode, …)` → validates enums.
- `register_instrument(symbol, instrument_type, tick_size, contract_size, …)` → product spec.
- `register_deployment(idea_id, account_id, instrument, …)` → **validates `idea_id` exists in research.db AND its Gate 7 (FIDELITY) is `passed`** (soft-key + gate check), assigns `magic_number` from the readable map, snapshots config via `strategy_log.get_live_config(idea_id)`, returns `deploy_id`.
- `get_deploy_config(deploy_id)`, `get_account_rules(account_id)`, `get_instrument(symbol)`.

**GATE**
- `open_deploy_gate(deploy_id, pass_criteria, sub_stage)` — `gate_name='FORWARD'`. **Guardrail:** refuses to open unless research Gate 7 (FIDELITY) `passed` for the idea_id.
- `pass_deploy_gate(deploy_id, gate_answer, sub_stage)` → **guardrail:** refuses to pass until `recon_results` exist; `live` sub_stage needs `demo` passed.
- `block_deploy_gate(...)`, `kill_deployment(...)`.

**OBSERVE / STATE** (called by the MT5 adapter / recompute — LIVE accounts only)
- `log_signal(deploy_id, direction, levels, expected_R, meta)` → Pydantic-validates `meta`.
- `ingest_order(...)`, `ingest_fill(...)` (asserts magic), `ingest_trade(...)` — normalized from the venue.
- `log_equity_snapshot(account_id, equity, balance, open_pnl, deploy_id=None)`.

**RECONCILE / RECORD**
- `log_recon_result(deploy_id, metric_key, metric_value, n_obs, gate_id=None)`
- `log_deploy_change(deploy_id, verdict, from_stage, to_stage, rationale, recon_id)`
- `log_incident(severity, kind, detail, deploy_id=None, account_id=None)`

### Code layer — Gate 7 / tester writes (write `research.db`)
Tester now lives in research.db, so its writers belong with the research code layer (`research/code/`, e.g. extend `pipeline.py` or a `tester.py` module) — **not** `execution.py`. Same `_conn()`/`_now()`/`VALID_*` conventions, pointed at `research.db`.
- `ingest_tester_run(idea_id, ea_name, symbol, data_source, period, deposit, params, summary)` → returns `run_id`.
- `ingest_tester_trade(run_id, session_date, direction, entry/exit, realized_R, range_w, …)`.
- `log_fidelity_diff(run_id, research_result_id, trade_overlap_pct, ER_delta, R_corr)` → writes the diff + sets `fidelity_verdict` against the pre-committed statistical-equivalence thresholds, then calls `pass_gate(idea_id, 7, …)` / blocks. This is what `register_deployment` / `open_deploy_gate('FORWARD')` read.

---

## Build order (rebuild from scratch — 2026-06-11, two databases)

1. **research.db migration** (next number after 021) — add `tester_runs` + `tester_trades`; ensure `step3_gates.gate_number` admits `7`. (Preserves all research data — `step1_ideas`, `step2_papers`, etc.)
2. **execution.db rebuild migration** — **drop** the old D0-era `execution.db` (obsolete: 43 D0-parity signals, the JM-DEMO-ORB D0 deployment, the biased $50 tester run; and the misplaced tester tables from migration 021 — nothing precious). Recreate from the **12-table DDL above**. `PRAGMA foreign_keys=ON`.
3. `research/code/execution.py` — `_SCHEMA` + the function inventory above + Pydantic `meta` models (ORB first). Tester writers added to the research code layer.
4. Smoke test — register `XAUUSD.s` instrument + `jm-demo-01` account (`venue='mt5'`, `broker='justmarkets'`) + `ORB-001@jm-demo-01` deployment (magic 1001); assert `register_deployment` / FORWARD refuses to open until research Gate 7 (FIDELITY) is `passed`; assert FORWARD refuses to pass without `recon_results`.
5. **Gate 7 / FIDELITY for ORB-001 (task 43):** parse the $10k tester xlsx → `ingest_tester_run`/`ingest_tester_trade` → `log_fidelity_diff` vs Python research. Currently FAILS (trail-exit port bug) — the gate doing its job. *(EA trail bug is a separate fix, tracked downstream.)*
6. Then FORWARD: MT5 adapter (`HistoryDeal*` normalize) + recompute auditor + recon job → demo run → reconcile → promote to live.

---

## Open / deferred (not blocking the build)
- **Views** (e.g. `live_deployments`, `deploy_pipeline`) — add when the dashboard needs them; mirror research's view pattern.
- **Portfolio layer** (`portfolio_allocations`, `portfolio_risk`) — additive, when 2+ strategies run live (capital allocation, aggregate risk, correlation netting). Schema undetermined until then — building it now = guessing wrong.
- **Pydantic `meta` schema per strategy** — define ORB's shape (`or_high, or_low, range_w, anchor, feed_window, feed_source`) at build time.
- **Heartbeat table** — if VPS liveness needs more than `log_incidents(kind='heartbeat_gap')` + external uptime ping.

---

*Spec locked 2026-06-10; **revised 2026-06-11 AM** (D0–D3 → FIDELITY → FORWARD, tester.db split). **RE-LOCKED 2026-06-11 PM** (Syafiq + Claude): collapsed 3 stores → **2 databases** (tester → research.db as **Gate 7 FIDELITY**); `venue` = protocol + new `broker` column; **+`instruments`**, **+`equity_snapshots`** day-one; `deploy_gates` kept (symmetry) but `FORWARD`-only; OBSERVE tables un-prefixed; `deploy_strategies`→`deployments`; build all 12 at once. Conventions still mirror research.db.*
