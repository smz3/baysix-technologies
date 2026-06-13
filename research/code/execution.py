"""
Execution interface for execution.db — the downstream twin of research.db (VPS side).
All writes go through here — no raw SQL elsewhere (CLAUDE.md rule 10).

execution.db tracks the LIFE OF A DEPLOYED STRATEGY in six layers (12 tables):
    1. REGISTER   — d1_accounts, d1_instruments, d1_deployments (what's deployed)
    2. GATE       — d2_deploy_gates (FORWARD checkpoint; FIDELITY is research Gate 7)
    3. OBSERVE    — d3_signals -> d3_orders -> d3_fills -> d3_trades (LIVE d1_accounts only)
    4. STATE      — d4_equity_snapshots (trailing-DD + kill-switch audit)
    5. RECONCILE  — d5_recon_results (live vs model; the lie-detector)
    6. RECORD     — log_deploy, log_incidents

TWO-DATABASE design (re-locked 2026-06-11): the MT5 Strategy-Tester evidence is NOT
here — port-fidelity is the last *research* gate (Gate 7 — FIDELITY) and lives in
research.db (research.code.tester). A deployment cannot be registered until that gate
is 'passed'. Spec: docs/reference/execution_schema.md (what) + execution_protocol.md (why).

Conventions mirror pipeline.py / strategy_log.py: _conn() with PRAGMA foreign_keys=ON
+ row_factory, _now() in MYT, VALID_* tuples. Two time bases — bookkeeping
(created_at/updated_at) = MYT; market (signal_ts, fill_ts, entry_ts, exit_ts,
incident_ts, snapshot_ts) = UTC, supplied by the caller/adapter.

Locked decisions baked in:
  - venue = PROTOCOL ('mt5'/'ibkr', the adapter/code path), NOT the broker. The broker
    is d1_accounts.broker ('justmarkets'/'darwinex'/'ftmo') — all three are venue='mt5'.
  - idea_id is a SOFT key into research.db (no FK); register_deployment() validates it
    AND that its Gate 7 (FIDELITY) is 'passed'.
  - magic_number: readable deterministic map owned here (ORB-001 -> 1001).
  - redeploy = singleton: one d1_deployments row per (idea x account); relaunch flips status.

DB path is env-overridable via EXECUTION_DB_PATH (the smoke test points it at a temp
file). research.db reads (idea validation, Gate 7, live config) always hit the real
research.db regardless.
"""

import os
import json
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path

# research.db code layer — soft-key validation, Gate-7 check, frozen-config snapshot
try:
    from research.code import pipeline, strategy_log, tester
except ImportError:  # running as a loose script with research/code on sys.path
    import pipeline, strategy_log, tester

MYT = timezone(timedelta(hours=8))


def _db_path() -> Path:
    """execution.db path, env-overridable (EXECUTION_DB_PATH) for tests."""
    env = os.environ.get("EXECUTION_DB_PATH")
    if env:
        return Path(env)
    return Path(__file__).parents[1] / "db" / "execution.db"


# ── Enum vocabularies (belt + suspenders: also CHECK-constrained in the DDL) ────
VALID_VENUE          = ("mt5", "ibkr")                 # PROTOCOL (adapter), not broker
VALID_INSTRUMENT_TYPE = ("spot", "fx", "cfd", "future")
VALID_ACCOUNT_TYPE   = ("retail_highlev", "darwinex_alloc", "ftmo_challenge",
                        "ftmo_funded", "ibkr_dma")
VALID_MODE           = ("demo", "live")
VALID_DD_BASIS       = ("static", "trailing")
VALID_ACCOUNT_STATUS = ("active", "breached", "closed")
VALID_STAGE          = ("FORWARD", "STEADY", "RETIRED")
VALID_DEPLOY_STATUS  = ("pending", "active", "paused", "killed", "retired")
VALID_GATE_NAME      = ("FORWARD",)                    # FIDELITY is research Gate 7
VALID_SUB_STAGE      = ("demo", "live")
VALID_GATE_STATUS    = ("open", "passed", "blocked", "killed")
VALID_DIRECTION      = ("long", "short", "flat")
VALID_ORDER_STATUS   = ("sent", "accepted", "rejected", "filled", "cancelled")
VALID_SIDE           = ("buy", "sell")
VALID_LEG            = ("entry", "exit")
VALID_DEPLOY_VERDICT = ("CREATED", "PROMOTED", "PAUSED", "KILLED", "RESUMED", "RETIRED")
VALID_SEVERITY       = ("info", "warn", "critical")
VALID_INCIDENT_KIND  = ("disconnect", "missed_fill", "slippage_spike", "reject",
                        "killswitch_fire", "data_gap", "config_mismatch",
                        "prop_rule_breach", "tz_mismatch", "heartbeat_gap")
VALID_DECIDED_BY     = ("human", "agent")

# Readable deterministic magic-number map (owned here, §Conventions of the spec):
# family base + numeric suffix → ORB-001 = 1001, ORB-002 = 1002, HMM-001 = 2001.
_MAGIC_FAMILY_BASE = {"ORB": 1000, "HMM": 2000, "CUSUM": 3000}

META_SCHEMA_VERSION = "1.0"


# ── Canonical schema (single source of truth — 12 tables) ───────────────────────
_SCHEMA = """
PRAGMA foreign_keys = ON;

-- Layer 1 — REGISTER ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS d1_accounts (
    account_id         TEXT PRIMARY KEY,
    venue              TEXT NOT NULL CHECK(venue IN ('mt5','ibkr')),  -- PROTOCOL, not broker
    broker             TEXT NOT NULL,                 -- 'justmarkets'/'darwinex'/'ftmo'/'ibkr'
    account_type       TEXT NOT NULL CHECK(account_type IN
                         ('retail_highlev','darwinex_alloc',
                          'ftmo_challenge','ftmo_funded','ibkr_dma')),
    mode               TEXT NOT NULL CHECK(mode IN ('demo','live')),
    broker_login       TEXT,
    base_currency      TEXT NOT NULL DEFAULT 'USD',
    leverage           INTEGER,
    initial_balance    REAL,
    max_daily_loss_pct REAL,
    max_total_dd_pct   REAL,
    dd_basis           TEXT CHECK(dd_basis IS NULL OR dd_basis IN ('static','trailing')),
    daily_reset_tz     TEXT,
    profit_target_pct  REAL,
    min_trading_days   INTEGER,
    rules_meta         TEXT CHECK(rules_meta IS NULL OR json_valid(rules_meta)),
    status             TEXT NOT NULL DEFAULT 'active'
                         CHECK(status IN ('active','breached','closed')),
    created_at         DATETIME NOT NULL,
    updated_at         DATETIME NOT NULL
);

CREATE TABLE IF NOT EXISTS d1_instruments (
    symbol           TEXT PRIMARY KEY,                -- 'XAUUSD.s' (broker-specific)
    display_name     TEXT,
    instrument_type  TEXT NOT NULL CHECK(instrument_type IN ('spot','fx','cfd','future')),
    base_asset       TEXT,
    quote_currency   TEXT NOT NULL DEFAULT 'USD',
    tick_size        REAL NOT NULL,                   -- min price increment
    tick_value       REAL,                            -- $ per tick per 1.0 lot
    contract_size    REAL NOT NULL,                   -- oz/lot (XAU=100) or contract multiplier
    min_lot          REAL,
    lot_step         REAL,
    expiry           DATE,                            -- NULL for spot/fx/cfd; set for futures
    meta             TEXT CHECK(meta IS NULL OR json_valid(meta)),
    created_at       DATETIME NOT NULL,
    updated_at       DATETIME NOT NULL
);

CREATE TABLE IF NOT EXISTS d1_deployments (
    deploy_id           TEXT PRIMARY KEY,             -- 'ORB-001@jm-live-01'
    idea_id             TEXT NOT NULL,                -- SOFT key -> research.db (no FK)
    venue               TEXT NOT NULL CHECK(venue IN ('mt5','ibkr')),  -- protocol
    instrument          TEXT NOT NULL REFERENCES d1_instruments(symbol),
    account_id          TEXT NOT NULL REFERENCES d1_accounts(account_id),
    magic_number        INTEGER NOT NULL,
    config_snapshot     TEXT CHECK(config_snapshot IS NULL OR json_valid(config_snapshot)),
    config_source       TEXT,
    meta_schema_version TEXT,
    stage               TEXT NOT NULL DEFAULT 'FORWARD'
                          CHECK(stage IN ('FORWARD','STEADY','RETIRED')),
    status              TEXT NOT NULL DEFAULT 'pending'
                          CHECK(status IN ('pending','active','paused','killed','retired')),
    created_at          DATETIME NOT NULL,
    updated_at          DATETIME NOT NULL,
    UNIQUE(account_id, magic_number)
);

-- Layer 2 — GATE -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS d2_deploy_gates (
    gate_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    deploy_id     TEXT NOT NULL REFERENCES d1_deployments(deploy_id),
    gate_name     TEXT NOT NULL DEFAULT 'FORWARD' CHECK(gate_name IN ('FORWARD')),
    sub_stage     TEXT CHECK(sub_stage IS NULL OR sub_stage IN ('demo','live')),
    attempt       INTEGER NOT NULL DEFAULT 1,
    pass_criteria TEXT,
    gate_answer   TEXT,
    evidence_ref  TEXT,
    status        TEXT NOT NULL DEFAULT 'open'
                  CHECK(status IN ('open','passed','blocked','killed')),
    answered_by   TEXT,
    created_at    DATETIME NOT NULL,
    updated_at    DATETIME NOT NULL,
    answered_at   DATETIME,
    UNIQUE(deploy_id, gate_name, sub_stage, attempt)
);

-- Layer 3 — OBSERVE (LIVE d1_accounts only) -------------------------------------
CREATE TABLE IF NOT EXISTS d3_signals (
    signal_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    deploy_id           TEXT NOT NULL REFERENCES d1_deployments(deploy_id),
    signal_ts           DATETIME NOT NULL,            -- UTC (market time)
    session_date        DATE NOT NULL,                -- anchor-tz session date
    direction           TEXT NOT NULL CHECK(direction IN ('long','short','flat')),
    intended_entry_px   REAL,
    intended_stop_px    REAL,
    intended_target_px  REAL,
    intended_size       REAL,
    expected_R          REAL,
    meta                TEXT CHECK(meta IS NULL OR json_valid(meta)),
    meta_schema_version TEXT,
    created_at          DATETIME NOT NULL             -- MYT (bookkeeping)
);

CREATE TABLE IF NOT EXISTS d3_orders (
    order_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id      INTEGER REFERENCES d3_signals(signal_id),
    deploy_id      TEXT NOT NULL REFERENCES d1_deployments(deploy_id),
    venue_order_id TEXT,
    order_type     TEXT,
    side           TEXT CHECK(side IS NULL OR side IN ('buy','sell')),
    requested_px   REAL,
    requested_size REAL,
    status         TEXT NOT NULL DEFAULT 'sent'
                   CHECK(status IN ('sent','accepted','rejected','filled','cancelled')),
    reject_reason  TEXT,
    placed_ts      DATETIME,                          -- UTC
    created_at     DATETIME NOT NULL                  -- MYT
);

CREATE TABLE IF NOT EXISTS d3_fills (
    fill_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id      INTEGER REFERENCES d3_orders(order_id),
    deploy_id     TEXT NOT NULL REFERENCES d1_deployments(deploy_id),
    venue_deal_id TEXT,
    leg           TEXT NOT NULL CHECK(leg IN ('entry','exit')),
    fill_px       REAL NOT NULL,
    fill_size     REAL NOT NULL,
    fill_ts       DATETIME NOT NULL,                  -- UTC
    slippage_px   REAL,
    commission    REAL,
    swap          REAL,
    magic_number  INTEGER,
    created_at    DATETIME NOT NULL                   -- MYT
);

CREATE TABLE IF NOT EXISTS d3_trades (
    trade_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    deploy_id        TEXT NOT NULL REFERENCES d1_deployments(deploy_id),
    signal_id        INTEGER REFERENCES d3_signals(signal_id),
    entry_ts         DATETIME,                        -- UTC
    entry_px         REAL,
    exit_ts          DATETIME,                        -- UTC
    exit_px          REAL,
    exit_reason      TEXT,
    risk_unit        REAL,
    realized_R       REAL,
    expected_R       REAL,
    realized_pnl_usd REAL,
    created_at       DATETIME NOT NULL                -- MYT
);

-- Layer 4 — STATE ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS d4_equity_snapshots (
    snapshot_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id    TEXT NOT NULL REFERENCES d1_accounts(account_id),
    deploy_id     TEXT REFERENCES d1_deployments(deploy_id),  -- nullable: account-level
    snapshot_ts   DATETIME NOT NULL,                  -- UTC
    equity        REAL NOT NULL,                      -- balance + floating P&L
    balance       REAL NOT NULL,                      -- realized only
    open_pnl      REAL,
    margin_used   REAL,
    created_at    DATETIME NOT NULL                   -- MYT
);

-- Layer 5 — RECONCILE --------------------------------------------------------
CREATE TABLE IF NOT EXISTS d5_recon_results (
    recon_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    deploy_id    TEXT NOT NULL REFERENCES d1_deployments(deploy_id),
    gate_id      INTEGER REFERENCES d2_deploy_gates(gate_id),
    period_start DATE,
    period_end   DATE,
    metric_key   TEXT NOT NULL,
    metric_value REAL NOT NULL,
    n_obs        INTEGER,
    created_at   DATETIME NOT NULL                    -- MYT
);

-- Layer 6 — RECORD -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS log_deploy (
    log_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    deploy_id   TEXT NOT NULL REFERENCES d1_deployments(deploy_id),
    event       TEXT,
    from_stage  TEXT,
    to_stage    TEXT,
    verdict     TEXT NOT NULL CHECK(verdict IN
                  ('CREATED','PROMOTED','PAUSED','KILLED','RESUMED','RETIRED')),
    rationale   TEXT,
    recon_id    INTEGER REFERENCES d5_recon_results(recon_id),
    decided_by  TEXT NOT NULL DEFAULT 'human' CHECK(decided_by IN ('human','agent')),
    created_at  DATETIME NOT NULL                     -- MYT
);

CREATE TABLE IF NOT EXISTS log_incidents (
    incident_id INTEGER PRIMARY KEY AUTOINCREMENT,
    deploy_id   TEXT REFERENCES d1_deployments(deploy_id),   -- nullable: account-level
    account_id  TEXT REFERENCES d1_accounts(account_id),
    incident_ts DATETIME NOT NULL,                    -- UTC
    severity    TEXT NOT NULL CHECK(severity IN ('info','warn','critical')),
    kind        TEXT NOT NULL CHECK(kind IN
                  ('disconnect','missed_fill','slippage_spike','reject',
                   'killswitch_fire','data_gap','config_mismatch',
                   'prop_rule_breach','tz_mismatch','heartbeat_gap')),
    detail      TEXT,
    resolved    INTEGER NOT NULL DEFAULT 0 CHECK(resolved IN (0,1)),
    created_at  DATETIME NOT NULL                     -- MYT
);
"""


# ── Pydantic meta models (validate-on-write, §7 of the protocol) ────────────────
from pydantic import BaseModel, ConfigDict


class ORBMeta(BaseModel):
    """d3_signals.meta for ORB strategies — strategy-private context + feed provenance."""
    model_config = ConfigDict(extra="forbid")
    or_high: float
    or_low: float
    range_w: float
    anchor: str                       # e.g. '09:00 UTC'
    feed_window: str | None = None    # bars recomputed against (recon replay)
    feed_source: str | None = None    # which feed the auditor used


# idea-family prefix → meta model. Extend as new strategy families go live.
_META_MODELS = {"ORB": ORBMeta}


def _validate_meta(idea_id: str, meta: dict | None) -> str | None:
    """Validate meta against the strategy family's Pydantic model; return JSON."""
    if meta is None:
        return None
    family = idea_id.split("-")[0]
    model = _META_MODELS.get(family)
    if model is None:
        return json.dumps(meta)  # no schema yet — store as-is but require valid JSON
    return model(**meta).model_dump_json()


# ── Plumbing ────────────────────────────────────────────────────────────────────
def _conn():
    conn = sqlite3.connect(_db_path())
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def _now() -> str:
    """Bookkeeping timestamp in MYT (when we recorded it)."""
    return datetime.now(MYT).strftime("%Y-%m-%d %H:%M:%S")


def init_db() -> Path:
    """Create execution.db with the full 12-table schema. Idempotent (IF NOT EXISTS)."""
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with _conn() as conn:
        conn.executescript(_SCHEMA)
        conn.commit()
    print(f"[execution] schema ready at {path}")
    return path


def _magic_for(idea_id: str) -> int:
    """Readable deterministic magic number: family base + numeric suffix."""
    family, _, num = idea_id.partition("-")
    base = _MAGIC_FAMILY_BASE.get(family)
    if base is None:
        raise ValueError(
            f"no magic family base for '{family}' (idea_id={idea_id}); "
            f"add it to _MAGIC_FAMILY_BASE"
        )
    try:
        return base + int(num)
    except ValueError:
        raise ValueError(f"idea_id '{idea_id}' has no numeric suffix to map a magic number")


# ── Layer 1 — REGISTER ──────────────────────────────────────────────────────────
def register_account(
    account_id: str,
    venue: str,
    broker: str,
    account_type: str,
    mode: str,
    broker_login: str = None,
    base_currency: str = "USD",
    leverage: int = None,
    initial_balance: float = None,
    max_daily_loss_pct: float = None,
    max_total_dd_pct: float = None,
    dd_basis: str = None,
    daily_reset_tz: str = None,
    profit_target_pct: float = None,
    min_trading_days: int = None,
    rules_meta: dict = None,
    status: str = "active",
) -> str:
    """Register a broker account (the rulebook the EA kill-switch enforces).
    venue = PROTOCOL ('mt5'/'ibkr'); broker = who it is ('justmarkets'...)."""
    if venue not in VALID_VENUE:
        raise ValueError(f"venue must be one of {VALID_VENUE}")
    if account_type not in VALID_ACCOUNT_TYPE:
        raise ValueError(f"account_type must be one of {VALID_ACCOUNT_TYPE}")
    if mode not in VALID_MODE:
        raise ValueError(f"mode must be one of {VALID_MODE}")
    if dd_basis is not None and dd_basis not in VALID_DD_BASIS:
        raise ValueError(f"dd_basis must be one of {VALID_DD_BASIS} or None")
    if status not in VALID_ACCOUNT_STATUS:
        raise ValueError(f"status must be one of {VALID_ACCOUNT_STATUS}")

    now = _now()
    rules_json = json.dumps(rules_meta) if rules_meta is not None else None
    with _conn() as conn:
        conn.execute("""
            INSERT INTO d1_accounts
                (account_id, venue, broker, account_type, mode, broker_login,
                 base_currency, leverage, initial_balance, max_daily_loss_pct,
                 max_total_dd_pct, dd_basis, daily_reset_tz, profit_target_pct,
                 min_trading_days, rules_meta, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (account_id, venue, broker, account_type, mode, broker_login,
              base_currency, leverage, initial_balance, max_daily_loss_pct,
              max_total_dd_pct, dd_basis, daily_reset_tz, profit_target_pct,
              min_trading_days, rules_json, status, now, now))
        conn.commit()
    print(f"[execution] account registered: {account_id} ({venue}/{broker}/{account_type}/{mode})")
    return account_id


def register_instrument(
    symbol: str,
    instrument_type: str,
    tick_size: float,
    contract_size: float,
    display_name: str = None,
    base_asset: str = None,
    quote_currency: str = "USD",
    tick_value: float = None,
    min_lot: float = None,
    lot_step: float = None,
    expiry: str = None,
    meta: dict = None,
) -> str:
    """Register a tradable product (the spec P&L / risk math reads). Returns symbol."""
    if instrument_type not in VALID_INSTRUMENT_TYPE:
        raise ValueError(f"instrument_type must be one of {VALID_INSTRUMENT_TYPE}")
    now = _now()
    meta_json = json.dumps(meta) if meta is not None else None
    with _conn() as conn:
        conn.execute("""
            INSERT INTO d1_instruments
                (symbol, display_name, instrument_type, base_asset, quote_currency,
                 tick_size, tick_value, contract_size, min_lot, lot_step, expiry,
                 meta, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (symbol, display_name, instrument_type, base_asset, quote_currency,
              tick_size, tick_value, contract_size, min_lot, lot_step, expiry,
              meta_json, now, now))
        conn.commit()
    print(f"[execution] instrument registered: {symbol} ({instrument_type}, "
          f"tick={tick_size}, contract={contract_size})")
    return symbol


def register_deployment(
    idea_id: str,
    account_id: str,
    instrument: str,
    venue: str = None,
    magic_number: int = None,
    config_source: str = None,
) -> str:
    """Register a deployment of a research idea onto an account+instrument.

    GUARDRAILS (cross-DB, soft-key): (1) idea_id must exist in research.db; (2) its
    Gate 7 (FIDELITY) must be 'passed' — a failing port never reaches an account.
    Derives venue from the account, assigns the readable magic number, and snapshots
    the frozen live config via strategy_log.get_live_config(). Returns deploy_id.
    """
    # 1) soft-key validation against research.db
    if not pipeline.get_idea(idea_id):
        raise ValueError(
            f"idea_id '{idea_id}' not found in research.db — register the idea first "
            f"(execution.db keys it as a soft key, code-validated)"
        )
    # 2) Gate 7 (FIDELITY) must be passed upstream — the bridge between the two DBs
    if not tester.gate7_passed(idea_id):
        raise ValueError(
            f"Gate 7 (FIDELITY) is not 'passed' for {idea_id} — the MQL5 port has not "
            f"been verified against the research backtest. No deployment until it passes "
            f"(tester.log_fidelity_diff)."
        )
    # 3) account + instrument must exist; inherit venue from the account
    rules = get_account_rules(account_id)
    if not rules:
        raise ValueError(f"account '{account_id}' not registered — register_account() first")
    if not get_instrument(instrument):
        raise ValueError(f"instrument '{instrument}' not registered — register_instrument() first")
    if venue is None:
        venue = rules["venue"]
    elif venue != rules["venue"]:
        raise ValueError(f"venue '{venue}' != account venue '{rules['venue']}'")

    if magic_number is None:
        magic_number = _magic_for(idea_id)

    # 4) snapshot the frozen live config (the contract between the two DBs)
    live = strategy_log.get_live_config(idea_id)
    config_snapshot = json.dumps(live) if live else None
    if config_source is None and live:
        config_source = "strategy_log:" + ",".join(
            str(c["log_id"]) for c in live.values()
        )

    deploy_id = f"{idea_id}@{account_id}"
    now = _now()
    with _conn() as conn:
        conn.execute("""
            INSERT INTO d1_deployments
                (deploy_id, idea_id, venue, instrument, account_id, magic_number,
                 config_snapshot, config_source, meta_schema_version,
                 stage, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'FORWARD', 'pending', ?, ?)
        """, (deploy_id, idea_id, venue, instrument, account_id, magic_number,
              config_snapshot, config_source, META_SCHEMA_VERSION, now, now))
        conn.commit()
    print(f"[execution] deployment registered: {deploy_id} (magic={magic_number}, venue={venue})")
    log_deploy_change(deploy_id, verdict="CREATED", to_stage="FORWARD",
                      rationale=f"registered {idea_id} on {account_id} (Gate 7 passed)")
    return deploy_id


def get_deploy_config(deploy_id: str) -> dict:
    """Return the d1_deployments row as a dict (empty if not found)."""
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM d1_deployments WHERE deploy_id=?", (deploy_id,)
        ).fetchone()
    return dict(row) if row else {}


def get_account_rules(account_id: str) -> dict:
    """Return the d1_accounts row as a dict (empty if not found)."""
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM d1_accounts WHERE account_id=?", (account_id,)
        ).fetchone()
    return dict(row) if row else {}


def get_instrument(symbol: str) -> dict:
    """Return the d1_instruments row as a dict (empty if not found)."""
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM d1_instruments WHERE symbol=?", (symbol,)
        ).fetchone()
    return dict(row) if row else {}


# ── Layer 2 — GATE (FORWARD only; FIDELITY is research Gate 7) ───────────────────
def open_deploy_gate(deploy_id: str, pass_criteria: str, sub_stage: str = None,
                     attempt: int = 1) -> int:
    """Open the FORWARD gate with a pre-committed pass criterion. Returns gate_id.

    GUARDRAIL: refuses to open unless research Gate 7 (FIDELITY) is 'passed' for the
    deployment's idea_id — a failing port never reaches a forward gate. demo sub_stage
    is the normal first leg before live (enforced at pass time)."""
    if sub_stage is not None and sub_stage not in VALID_SUB_STAGE:
        raise ValueError(f"sub_stage must be one of {VALID_SUB_STAGE} or None")
    dep = get_deploy_config(deploy_id)
    if not dep:
        raise ValueError(f"deployment not found: {deploy_id}")
    if not tester.gate7_passed(dep["idea_id"]):
        raise ValueError(
            f"Cannot open FORWARD for {deploy_id}: research Gate 7 (FIDELITY) not passed "
            f"for {dep['idea_id']}."
        )
    now = _now()
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO d2_deploy_gates
                (deploy_id, gate_name, sub_stage, attempt, pass_criteria, status,
                 created_at, updated_at)
            VALUES (?, 'FORWARD', ?, ?, ?, 'open', ?, ?)
        """, (deploy_id, sub_stage, attempt, pass_criteria, now, now))
        conn.commit()
        gate_id = cur.lastrowid
    print(f"[execution] {deploy_id} FORWARD/{sub_stage} attempt {attempt}: opened (gate_id={gate_id})")
    return gate_id


def _has_recon(deploy_id: str, gate_id: int) -> bool:
    with _conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM d5_recon_results WHERE deploy_id=? AND gate_id=? LIMIT 1",
            (deploy_id, gate_id),
        ).fetchone()
    return row is not None


def _gate_row(deploy_id: str, sub_stage: str, attempt: int) -> dict:
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM d2_deploy_gates WHERE deploy_id=? AND gate_name='FORWARD' "
            "AND sub_stage IS ? AND attempt=?",
            (deploy_id, sub_stage, attempt),
        ).fetchone()
    return dict(row) if row else {}


def _sub_stage_passed(deploy_id: str, sub_stage: str) -> bool:
    with _conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM d2_deploy_gates WHERE deploy_id=? AND gate_name='FORWARD' "
            "AND sub_stage IS ? AND status='passed' LIMIT 1",
            (deploy_id, sub_stage),
        ).fetchone()
    return row is not None


def pass_deploy_gate(deploy_id: str, gate_answer: str, sub_stage: str = None,
                     answered_by: str = "human", attempt: int = 1,
                     evidence_ref: str = None, allow_incomplete: bool = False) -> None:
    """Mark a FORWARD gate passed.

    GUARDRAILS: (1) supporting d5_recon_results must exist for the gate (twin of
    pass_gate(6)); (2) the 'live' sub_stage cannot pass until 'demo' has passed.
    allow_incomplete=True bypasses (1) ONLY with a logged waiver in gate_answer."""
    if sub_stage is not None and sub_stage not in VALID_SUB_STAGE:
        raise ValueError(f"sub_stage must be one of {VALID_SUB_STAGE} or None")
    gate = _gate_row(deploy_id, sub_stage, attempt)
    if not gate:
        raise ValueError(f"Gate not found: {deploy_id} FORWARD/{sub_stage} attempt={attempt}")
    if sub_stage == "live" and not _sub_stage_passed(deploy_id, "demo"):
        raise ValueError(
            f"Cannot pass FORWARD/live for {deploy_id}: the demo sub_stage has not passed. "
            f"Demo reconciles before live capital."
        )
    if not allow_incomplete and not _has_recon(deploy_id, gate["gate_id"]):
        raise ValueError(
            f"Cannot pass FORWARD/{sub_stage} for {deploy_id}: no d5_recon_results for "
            f"gate_id={gate['gate_id']}. A forward gate passes on reconciliation evidence "
            f"(log_recon_result first), or pass allow_incomplete=True with a waiver."
        )
    now = _now()
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE d2_deploy_gates
            SET status='passed', gate_answer=?, evidence_ref=COALESCE(?, evidence_ref),
                answered_by=?, updated_at=?, answered_at=?
            WHERE gate_id=?
        """, (gate_answer, evidence_ref, answered_by, now, now, gate["gate_id"]))
        conn.commit()
    print(f"[execution] {deploy_id} FORWARD/{sub_stage}: PASSED")


def block_deploy_gate(deploy_id: str, gate_answer: str, sub_stage: str = None,
                      answered_by: str = "human", attempt: int = 1) -> None:
    """Mark a FORWARD gate blocked with a reason."""
    gate = _gate_row(deploy_id, sub_stage, attempt)
    if not gate:
        raise ValueError(f"Gate not found: {deploy_id} FORWARD/{sub_stage} attempt={attempt}")
    now = _now()
    with _conn() as conn:
        conn.execute("""
            UPDATE d2_deploy_gates
            SET status='blocked', gate_answer=?, answered_by=?, updated_at=?, answered_at=?
            WHERE gate_id=?
        """, (gate_answer, answered_by, now, now, gate["gate_id"]))
        conn.commit()
    print(f"[execution] {deploy_id} FORWARD/{sub_stage}: BLOCKED — {gate_answer[:80]}")


def kill_deployment(deploy_id: str, rationale: str, sub_stage: str = None,
                    attempt: int = 1) -> None:
    """Kill a deployment: flip status to 'killed', kill the open gate if given,
    and record a KILLED row in log_deploy."""
    now = _now()
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE d1_deployments SET status='killed', updated_at=? WHERE deploy_id=?
        """, (now, deploy_id))
        if cur.rowcount == 0:
            raise ValueError(f"deployment not found: {deploy_id}")
        gate = _gate_row(deploy_id, sub_stage, attempt)
        if gate:
            cur.execute("""
                UPDATE d2_deploy_gates
                SET status='killed', gate_answer=?, updated_at=?, answered_at=?
                WHERE gate_id=?
            """, (rationale, now, now, gate["gate_id"]))
        conn.commit()
    print(f"[execution] {deploy_id}: KILLED — {rationale[:80]}")
    log_deploy_change(deploy_id, verdict="KILLED", rationale=rationale)


# ── Layer 3 — OBSERVE ───────────────────────────────────────────────────────────
def log_signal(deploy_id: str, direction: str, signal_ts: str, session_date: str,
               intended_entry_px: float = None, intended_stop_px: float = None,
               intended_target_px: float = None, intended_size: float = None,
               expected_R: float = None, meta: dict = None) -> int:
    """Author an intended trade (d3_signals) — Python's recompute, not the EA.
    signal_ts/session_date are MARKET time (UTC / anchor-tz); meta is Pydantic-
    validated against the idea family's schema. Returns signal_id."""
    if direction not in VALID_DIRECTION:
        raise ValueError(f"direction must be one of {VALID_DIRECTION}")
    idea_id = deploy_id.split("@")[0]
    meta_json = _validate_meta(idea_id, meta)
    now = _now()
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO d3_signals
                (deploy_id, signal_ts, session_date, direction, intended_entry_px,
                 intended_stop_px, intended_target_px, intended_size, expected_R,
                 meta, meta_schema_version, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (deploy_id, signal_ts, session_date, direction, intended_entry_px,
              intended_stop_px, intended_target_px, intended_size, expected_R,
              meta_json, META_SCHEMA_VERSION, now))
        conn.commit()
        signal_id = cur.lastrowid
    print(f"[execution] {deploy_id} signal #{signal_id} {direction} @ {signal_ts}")
    return signal_id


def ingest_order(deploy_id: str, signal_id: int = None, venue_order_id: str = None,
                 order_type: str = None, side: str = None, requested_px: float = None,
                 requested_size: float = None, status: str = "sent",
                 reject_reason: str = None, placed_ts: str = None) -> int:
    """Normalize a broker order into d3_orders. Returns order_id."""
    if side is not None and side not in VALID_SIDE:
        raise ValueError(f"side must be one of {VALID_SIDE} or None")
    if status not in VALID_ORDER_STATUS:
        raise ValueError(f"status must be one of {VALID_ORDER_STATUS}")
    now = _now()
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO d3_orders
                (signal_id, deploy_id, venue_order_id, order_type, side,
                 requested_px, requested_size, status, reject_reason, placed_ts, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (signal_id, deploy_id, venue_order_id, order_type, side,
              requested_px, requested_size, status, reject_reason, placed_ts, now))
        conn.commit()
        order_id = cur.lastrowid
    print(f"[execution] {deploy_id} order #{order_id} {side} {status}")
    return order_id


def ingest_fill(deploy_id: str, order_id: int, leg: str, fill_px: float,
                fill_size: float, fill_ts: str, magic_number: int = None,
                venue_deal_id: str = None, slippage_px: float = None,
                commission: float = None, swap: float = None) -> int:
    """Normalize a broker fill into d3_fills. Asserts the deal's magic matches the
    deployment (mismatch → config_mismatch incident). Returns fill_id."""
    if leg not in VALID_LEG:
        raise ValueError(f"leg must be one of {VALID_LEG}")
    dep = get_deploy_config(deploy_id)
    if not dep:
        raise ValueError(f"deployment not found: {deploy_id}")
    if magic_number is not None and magic_number != dep["magic_number"]:
        log_incident(severity="critical", kind="config_mismatch",
                     detail=f"fill magic {magic_number} != deploy magic {dep['magic_number']} "
                            f"(deal {venue_deal_id})", deploy_id=deploy_id, incident_ts=fill_ts)
        raise ValueError(
            f"magic mismatch on fill: deal magic={magic_number}, deploy magic="
            f"{dep['magic_number']} — logged config_mismatch incident"
        )
    now = _now()
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO d3_fills
                (order_id, deploy_id, venue_deal_id, leg, fill_px, fill_size,
                 fill_ts, slippage_px, commission, swap, magic_number, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (order_id, deploy_id, venue_deal_id, leg, fill_px, fill_size,
              fill_ts, slippage_px, commission, swap, magic_number, now))
        conn.commit()
        fill_id = cur.lastrowid
    print(f"[execution] {deploy_id} fill #{fill_id} {leg} {fill_size}@{fill_px} slip={slippage_px}")
    return fill_id


def ingest_trade(deploy_id: str, signal_id: int = None, entry_ts: str = None,
                 entry_px: float = None, exit_ts: str = None, exit_px: float = None,
                 exit_reason: str = None, risk_unit: float = None,
                 realized_R: float = None, expected_R: float = None,
                 realized_pnl_usd: float = None) -> int:
    """Record a closed round-trip (d3_trades) — the reconciliation unit. Returns trade_id."""
    now = _now()
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO d3_trades
                (deploy_id, signal_id, entry_ts, entry_px, exit_ts, exit_px,
                 exit_reason, risk_unit, realized_R, expected_R, realized_pnl_usd, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (deploy_id, signal_id, entry_ts, entry_px, exit_ts, exit_px,
              exit_reason, risk_unit, realized_R, expected_R, realized_pnl_usd, now))
        conn.commit()
        trade_id = cur.lastrowid
    print(f"[execution] {deploy_id} trade #{trade_id} realized_R={realized_R} pnl={realized_pnl_usd}")
    return trade_id


# ── Layer 4 — STATE ───────────────────────────────────────────────────────────
def log_equity_snapshot(account_id: str, snapshot_ts: str, equity: float,
                        balance: float, open_pnl: float = None,
                        margin_used: float = None, deploy_id: str = None) -> int:
    """Record a periodic account-value reading (trailing-DD + kill-switch audit).
    snapshot_ts is MARKET time (UTC). Keyed at account_id (trailing-DD is an
    account-level rule). Returns snapshot_id."""
    now = _now()
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO d4_equity_snapshots
                (account_id, deploy_id, snapshot_ts, equity, balance,
                 open_pnl, margin_used, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (account_id, deploy_id, snapshot_ts, equity, balance,
              open_pnl, margin_used, now))
        conn.commit()
        snapshot_id = cur.lastrowid
    return snapshot_id


# ── Layer 5 — RECONCILE ─────────────────────────────────────────────────────────
def log_recon_result(deploy_id: str, metric_key: str, metric_value: float,
                     n_obs: int = None, gate_id: int = None,
                     period_start: str = None, period_end: str = None) -> int:
    """Log one reconciliation metric (the step4_results of the live world). Returns recon_id."""
    now = _now()
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO d5_recon_results
                (deploy_id, gate_id, period_start, period_end,
                 metric_key, metric_value, n_obs, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (deploy_id, gate_id, period_start, period_end,
              metric_key, metric_value, n_obs, now))
        conn.commit()
        recon_id = cur.lastrowid
    g = f" gate#{gate_id}" if gate_id is not None else ""
    print(f"[execution] {deploy_id}{g} recon {metric_key}={metric_value} (n={n_obs})")
    return recon_id


# ── Layer 6 — RECORD ────────────────────────────────────────────────────────────
def log_deploy_change(deploy_id: str, verdict: str, from_stage: str = None,
                      to_stage: str = None, rationale: str = "", recon_id: int = None,
                      event: str = None, decided_by: str = "human") -> int:
    """Record one deployment-lineage event (mirror of strategy_log.log_change). Returns log_id."""
    if verdict not in VALID_DEPLOY_VERDICT:
        raise ValueError(f"verdict must be one of {VALID_DEPLOY_VERDICT}")
    if decided_by not in VALID_DECIDED_BY:
        raise ValueError(f"decided_by must be one of {VALID_DECIDED_BY}")
    now = _now()
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO log_deploy
                (deploy_id, event, from_stage, to_stage, verdict, rationale,
                 recon_id, decided_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (deploy_id, event, from_stage, to_stage, verdict, rationale,
              recon_id, decided_by, now))
        conn.commit()
        log_id = cur.lastrowid
    arrow = f" {from_stage}->{to_stage}" if to_stage else ""
    print(f"[execution] {deploy_id} {verdict}{arrow} (log_id={log_id})")
    return log_id


def log_incident(severity: str, kind: str, detail: str = "", deploy_id: str = None,
                 account_id: str = None, incident_ts: str = None, resolved: int = 0) -> int:
    """Record a live incident (the black-box recorder). At least one of deploy_id /
    account_id should be set (some incidents are account-level, e.g. prop_rule_breach).
    incident_ts is MARKET time (UTC); defaults to now-MYT only if unknown. Returns incident_id."""
    if severity not in VALID_SEVERITY:
        raise ValueError(f"severity must be one of {VALID_SEVERITY}")
    if kind not in VALID_INCIDENT_KIND:
        raise ValueError(f"kind must be one of {VALID_INCIDENT_KIND}")
    if resolved not in (0, 1):
        raise ValueError("resolved must be 0 or 1")
    if deploy_id is None and account_id is None:
        raise ValueError("log_incident needs at least one of deploy_id / account_id")
    now = _now()
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO log_incidents
                (deploy_id, account_id, incident_ts, severity, kind, detail, resolved, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (deploy_id, account_id, incident_ts or now, severity, kind, detail, resolved, now))
        conn.commit()
        incident_id = cur.lastrowid
    scope = deploy_id or account_id
    print(f"[execution] {scope} INCIDENT [{severity}/{kind}] #{incident_id}")
    return incident_id


if __name__ == "__main__":
    init_db()
