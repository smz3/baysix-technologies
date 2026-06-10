# execution.db — Schema Specification

The full DDL for `execution.db`, the downstream twin of `research.db`. This is the **build spec**: every table, column, type, and constraint is final here before `execution.py` is written. Design rationale lives in [execution_protocol.md](execution_protocol.md); this doc is the *what*, that one is the *why*.

Status: **SPEC LOCKED 2026-06-10 — not yet built.** Build = migration `020_create_execution_db.py` + `research/code/execution.py` code layer. MT5-only; IBKR is a kept column, no code.

---

## Conventions (inherited from research.db — `execution.py` mirrors `pipeline.py`)

| Rule | Convention |
|------|-----------|
| **PK — anchor tables** | readable `TEXT PRIMARY KEY` (`accounts`, `deploy_strategies`) |
| **PK — child/event tables** | `INTEGER PRIMARY KEY AUTOINCREMENT` |
| **Enums** | belt **and** suspenders: inline `CHECK(col IN (...))` **+** `VALID_*` tuple raising `ValueError` in the code layer |
| **Booleans** | `INTEGER ... CHECK(col IN (0,1)) DEFAULT 0` |
| **FKs** | native `REFERENCES`, `PRAGMA foreign_keys = ON` — **except `idea_id`** (soft key, code-validated, lives in research.db) |
| **JSON columns** | `TEXT CHECK(col IS NULL OR json_valid(col))` + `meta_schema_version` + Pydantic validation in code layer |
| **Bookkeeping time** (`created_at`, `updated_at`) | **MYT (UTC+8)**, `"%Y-%m-%d %H:%M:%S"` — mirrors research `_now()`. "When we recorded it." |
| **Market time** (`signal_ts`, `fill_ts`, `entry_ts`, `exit_ts`, `incident_ts`) | **UTC**, normalized on ingest (MT5 hands broker-server time → adapter converts). "When the market did it." |
| **`session_date`** | `DATE` in the anchor's reference tz (e.g. ET session date), stored explicitly |

**Two locked decisions baked in:**
- **Magic scheme:** readable deterministic map owned by the code layer — `ORB-001 → 1001`, `ORB-002 → 1002`, … So a magic spotted in the MT5 terminal is self-identifying. `UNIQUE(account_id, magic_number)`.
- **Redeploy = singleton:** one `deploy_strategies` row per `(idea × account × instrument)`; relaunching a killed deployment flips its `status` (`killed → pending`); the lifecycle history lives in `log_deploy`. No instance suffixes.

---

## Layer 1 — REGISTER

### `accounts` — the rulebook the EA kill-switch enforces
```sql
CREATE TABLE accounts (
    account_id         TEXT PRIMARY KEY,            -- readable slug, e.g. 'jm-live-01'
    venue              TEXT NOT NULL CHECK(venue IN ('justmarkets','ibkr')),
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
`mode` (real capital?) and `account_type` (which ruleset?) are orthogonal: an FTMO challenge is `mode='demo'` + `type='ftmo_challenge'`. The kill-switch keys off `account_type` rules regardless of `mode`.

### `deploy_strategies` — one row per `(idea × venue × instrument)` deployment; the anchor
```sql
CREATE TABLE deploy_strategies (
    deploy_id        TEXT PRIMARY KEY,              -- 'ORB-001@jm-live-01'
    idea_id          TEXT NOT NULL,                 -- SOFT key → research.db (code-validated, NO FK)
    venue            TEXT NOT NULL CHECK(venue IN ('justmarkets','ibkr')),
    instrument       TEXT NOT NULL DEFAULT 'XAUUSD.s',
    account_id       TEXT NOT NULL REFERENCES accounts(account_id),
    magic_number     INTEGER NOT NULL,              -- EA stamp → ledger attribution key
    config_snapshot  TEXT CHECK(config_snapshot IS NULL OR json_valid(config_snapshot)),
    config_source    TEXT,                          -- strategy_log log_id / git sha
    meta_schema_version TEXT,
    stage            TEXT NOT NULL DEFAULT 'D0' CHECK(stage IN ('D0','D1','D2','D3')),
    status           TEXT NOT NULL DEFAULT 'pending'
                       CHECK(status IN ('pending','active','paused','killed','retired')),
    created_at       DATETIME NOT NULL,
    updated_at       DATETIME NOT NULL,
    UNIQUE(account_id, magic_number)                -- no magic collision on one account
);
```

---

## Layer 2 — GATE

### `deploy_gates` — D0–D3 checkpoints (mirror of research `step3_gates`)
```sql
CREATE TABLE deploy_gates (
    gate_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    deploy_id     TEXT NOT NULL REFERENCES deploy_strategies(deploy_id),
    gate_number   INTEGER NOT NULL CHECK(gate_number BETWEEN 0 AND 3),
    attempt       INTEGER NOT NULL DEFAULT 1,
    pass_criteria TEXT,                             -- pre-committed kill-line
    gate_answer   TEXT,                             -- verdict + numbers
    status        TEXT NOT NULL DEFAULT 'open'
                  CHECK(status IN ('open','passed','blocked','killed')),
    answered_by   TEXT,
    created_at    DATETIME NOT NULL,
    updated_at    DATETIME NOT NULL,
    answered_at   DATETIME,
    UNIQUE(deploy_id, gate_number, attempt)
);
```
**Guardrail (code layer):** `pass_deploy_gate()` refuses unless supporting `recon_results` exist for that `deploy_id`/`gate_number` — twin of the `pass_gate(6)` fix.

---

## Layer 3 — OBSERVE (signal → order → fill → trade)

### `exec_signals` — intent (authored by Python's recompute, NOT emitted by EA)
```sql
CREATE TABLE exec_signals (
    signal_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    deploy_id          TEXT NOT NULL REFERENCES deploy_strategies(deploy_id),
    signal_ts          DATETIME NOT NULL,           -- UTC (market time)
    session_date       DATE NOT NULL,               -- anchor-tz session date
    direction          TEXT NOT NULL CHECK(direction IN ('long','short','flat')),
    intended_entry_px  REAL,
    intended_stop_px   REAL,
    intended_target_px REAL,                         -- nullable (trailers)
    intended_size      REAL,                         -- lots
    expected_R         REAL,
    meta               TEXT CHECK(meta IS NULL OR json_valid(meta)),  -- {or_high,or_low,range_w,anchor}
    meta_schema_version TEXT,
    created_at         DATETIME NOT NULL             -- MYT (bookkeeping)
);
```

### `exec_orders` — what was sent to the broker (normalized from venue)
```sql
CREATE TABLE exec_orders (
    order_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id      INTEGER REFERENCES exec_signals(signal_id),
    deploy_id      TEXT NOT NULL REFERENCES deploy_strategies(deploy_id),
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

### `exec_fills` — what the broker gave us (normalized from native ledger)
```sql
CREATE TABLE exec_fills (
    fill_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id      INTEGER REFERENCES exec_orders(order_id),
    deploy_id     TEXT NOT NULL REFERENCES deploy_strategies(deploy_id),
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
`slippage_px` is the single most important number for D1. `commission`/`swap` come from the deal ledger, **not** the `OnTradeTransaction` payload. On ingest the adapter asserts `magic_number == deploy.magic_number`; mismatch → `config_mismatch` incident.

### `exec_trades` — the closed round-trip (the reconciliation unit)
```sql
CREATE TABLE exec_trades (
    trade_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    deploy_id        TEXT NOT NULL REFERENCES deploy_strategies(deploy_id),
    signal_id        INTEGER REFERENCES exec_signals(signal_id),
    entry_ts         DATETIME,                       -- UTC
    entry_px         REAL,
    exit_ts          DATETIME,                       -- UTC
    exit_px          REAL,
    exit_reason      TEXT,                           -- stop/target/trail/manual/eod
    risk_unit        REAL,                           -- the 1R distance (ORB range_w, ATR, …)
    realized_R       REAL,                           -- what we ACTUALLY got
    expected_R       REAL,                           -- what the model SAID (copied from signal)
    realized_pnl_usd REAL,
    created_at       DATETIME NOT NULL               -- MYT
);
```

---

## Layer 4 — RECONCILE

### `recon_results` — the step4_results of the live world
```sql
CREATE TABLE recon_results (
    recon_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    deploy_id    TEXT NOT NULL REFERENCES deploy_strategies(deploy_id),
    gate_number  INTEGER,                            -- which D-gate this feeds (nullable)
    period_start DATE,
    period_end   DATE,
    metric_key   TEXT NOT NULL,                      -- signal_match_pct, slippage_median_px,
    metric_value REAL NOT NULL,                      --   feed_divergence_px, live_E_R, drift_t_vs_IS
    n_obs        INTEGER,
    created_at   DATETIME NOT NULL                   -- MYT
);
```

---

## Layer 5 — RECORD

### `log_deploy` — deployment decision lineage (mirror of log_strategy)
```sql
CREATE TABLE log_deploy (
    log_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    deploy_id   TEXT NOT NULL REFERENCES deploy_strategies(deploy_id),
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
    deploy_id   TEXT NOT NULL REFERENCES deploy_strategies(deploy_id),
    incident_ts DATETIME NOT NULL,                   -- UTC (when it happened)
    severity    TEXT NOT NULL CHECK(severity IN ('info','warn','critical')),
    kind        TEXT NOT NULL CHECK(kind IN
                  ('disconnect','missed_fill','slippage_spike','reject',
                   'killswitch_fire','data_gap','config_mismatch',
                   'prop_rule_breach','tz_mismatch')),
    detail      TEXT,
    resolved    INTEGER NOT NULL DEFAULT 0 CHECK(resolved IN (0,1)),
    created_at  DATETIME NOT NULL                    -- MYT
);
```

---

## Code layer — `research/code/execution.py` (function inventory)

All writes go through here (CLAUDE.md rule 10). Mirrors `pipeline.py`/`strategy_log.py`: `_conn()` with `PRAGMA foreign_keys=ON` + `row_factory`, `_now()` in MYT, `VALID_*` tuples, returns the new id, prints a confirmation line.

**REGISTER**
- `register_account(account_id, venue, account_type, mode, …)` → validates enums.
- `register_deployment(idea_id, account_id, instrument, …)` → **validates `idea_id` exists in research.db** (soft-key check), assigns `magic_number` from the readable map, snapshots config via `strategy_log.get_live_config(idea_id)`, returns `deploy_id`.
- `get_deploy_config(deploy_id)`, `get_account_rules(account_id)`.

**GATE**
- `open_deploy_gate(deploy_id, gate_number, pass_criteria)`
- `pass_deploy_gate(deploy_id, gate_number, gate_answer)` → **guardrail: refuses unless `recon_results` exist** for it.
- `block_deploy_gate(...)`, `kill_deployment(...)`.

**OBSERVE** (called by the MT5 adapter / recompute)
- `log_signal(deploy_id, direction, levels, expected_R, meta)` → Pydantic-validates `meta`.
- `ingest_order(...)`, `ingest_fill(...)` (asserts magic), `ingest_trade(...)` — normalized from the venue.

**RECONCILE / RECORD**
- `log_recon_result(deploy_id, metric_key, metric_value, n_obs, gate_number=None)`
- `log_deploy_change(deploy_id, verdict, from_stage, to_stage, rationale, recon_id)`
- `log_incident(deploy_id, severity, kind, detail)`

---

## Build order (next session)

1. Migration `020_create_execution_db.py` — this DDL, `CREATE TABLE IF NOT EXISTS` throughout, `PRAGMA foreign_keys=ON`. Creates `research/db/execution.db`.
2. `research/code/execution.py` — the function inventory above + Pydantic `meta` models per strategy type (ORB first).
3. Smoke test — register `jm-live-01` account + `ORB-001@jm-live-01` deployment (magic 1001), open D0, assert guardrail blocks a premature pass.
4. Then task 4 proper: MT5 adapter + recompute auditor + D0 harness (logic parity + feed divergence).

---

## Open / deferred (not blocking the build)
- **Views** (e.g. `live_deployments`, `deploy_pipeline`) — add when the dashboard needs them; mirror research's view pattern. Not required for tables.
- **Portfolio layer** (`portfolio_allocations`, `portfolio_risk`) — §10 growth path, additive, when 2+ strategies run live.
- **Pydantic `meta` schema per strategy** — define ORB's shape (`or_high, or_low, range_w, anchor`) at build time.

---

*Spec locked 2026-06-10 (Syafiq + Claude). All column/type/constraint decisions final. Conventions mirror research.db. Build is a clean next-session run from this doc.*
