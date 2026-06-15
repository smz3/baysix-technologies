# research.db — Schema (mirror of live DB)

_Last updated: 2026-06-15 — regenerated from live `PRAGMA` to match the database exactly. This is a **faithful mirror** (3.1); semantic redesign for clarity is a separate later pass (3.2)._

The DB has **9 tables** + **4 views**. All writes go through [research/code/](../../research/code/) (`pipeline.py`, `agent_log.py`, `strategy_log.py`, `backlog.py`, `tester.py`) — never raw `sqlite3` (CLAUDE.md rule 10, hook-enforced).

CHECK / UNIQUE / FK constraints below are the **real DB-level constraints** read from the table SQL. "observed:" lists the values actually present today (not a constraint unless a CHECK is noted).

---

## Table groups

```
PIPELINE CORE      step1_ideas · step2_papers · step3_gates · step4_results
LOGS               log_agent · log_strategy · log_tasks
GATE-7 FIDELITY    tester_runs · tester_trades
```

---

## PIPELINE CORE

### step1_ideas
The spine. One row per idea. Everything FKs back to `idea_id`.

| Column | Type | Constraints / Note |
|--------|------|--------------------|
| idea_id | TEXT | **PK** (e.g. "HMM-001") |
| name | TEXT | NOT NULL |
| description | TEXT | |
| category | TEXT | free-text. observed: ORB, alpha, cost_utility, diagnostic, execution, guard, infra, regime, signal_processing |
| parent_idea_id | TEXT | FK → step1_ideas, CHECK(parent_idea_id != idea_id) |
| status | TEXT | NOT NULL DEFAULT 'ideation'. observed: ideation, gate_4, gate_6, gate_7, killed (lifecycle: ideation → gate_N → graduated / killed) |
| kill_gate | INTEGER | which gate killed it (null if alive) |
| kill_reason | TEXT | the falsifying finding (mandatory when status=killed) |
| killed_at | DATETIME | |
| created_at | DATETIME | NOT NULL |
| updated_at | DATETIME | NOT NULL |

---

### step2_papers
Papers read per idea. Drives Gate 0.

| Column | Type | Constraints / Note |
|--------|------|--------------------|
| paper_id | INTEGER | **PK** AUTOINCREMENT |
| idea_id | TEXT | NOT NULL, FK → step1_ideas |
| title | TEXT | NOT NULL |
| authors | TEXT | |
| year | INTEGER | |
| source | TEXT | arXiv / SSRN / Journal / etc. |
| url | TEXT | |
| doi | TEXT | |
| local_path | TEXT | path to saved PDF |
| dissected | INTEGER | NOT NULL DEFAULT 0 (0=no, 1=yes) |
| key_equations | TEXT | ⚠️ text-heavy — never SELECT into main context (rule 9) |
| empirical_findings | TEXT | ⚠️ text-heavy |
| context_fit | TEXT | ⚠️ text-heavy — applies to XAUUSD + our TF? |
| limitations | TEXT | ⚠️ text-heavy |
| added_at | DATETIME | NOT NULL |
| dissected_at | DATETIME | |

---

### step3_gates
Protocol gates per idea. One row per (idea, gate, attempt).

| Column | Type | Constraints / Note |
|--------|------|--------------------|
| gate_id | INTEGER | **PK** AUTOINCREMENT |
| idea_id | TEXT | NOT NULL, FK → step1_ideas |
| gate_number | INTEGER | NOT NULL, **CHECK(gate_number BETWEEN 0 AND 7)** |
| attempt | INTEGER | NOT NULL DEFAULT 1, **UNIQUE(idea_id, gate_number, attempt)** |
| gate_question | TEXT | what must be answered (sourced from `pipeline.GATE_QUESTIONS`) |
| gate_answer | TEXT | the actual answer ⚠️ text-heavy (rule 9) |
| pass_criteria | TEXT | what pass looks like |
| status | TEXT | NOT NULL DEFAULT 'open'. **CHECK(status IN ('open','passed','blocked','killed'))** |
| answered_by | TEXT | human / agent |
| created_at | DATETIME | NOT NULL |
| updated_at | DATETIME | NOT NULL |
| answered_at | DATETIME | |

---

### step4_results
All quantitative output. Required-field guard in `pipeline.log_result` (git_sha, n_obs).

| Column | Type | Constraints / Note |
|--------|------|--------------------|
| result_id | INTEGER | **PK** AUTOINCREMENT |
| idea_id | TEXT | NOT NULL, FK → step1_ideas |
| gate_number | INTEGER | NOT NULL — which gate produced this |
| stage | TEXT | NOT NULL, **CHECK(stage IN ('IS','walkforward','montecarlo','OOS'))** |
| metric_key | TEXT | NOT NULL — sharpe / t_stat / win_rate / net_edge / foundation_check / … |
| metric_value | REAL | NOT NULL |
| cost_adjusted | INTEGER | NOT NULL DEFAULT 0, **CHECK(cost_adjusted IN (0,1))** (0=raw, 1=net) |
| period | TEXT | **CHECK(period IN ('per_trade','daily','annualised'))**. observed: per_trade, daily |
| n_obs | INTEGER | observation count (required by code layer) |
| n_trials | INTEGER | for PSR / deflated Sharpe |
| trial_family_id | TEXT | group of trials compared together |
| instrument | TEXT | NOT NULL DEFAULT 'XAUUSD' |
| data_start | DATE | |
| data_end | DATE | |
| parameters | TEXT | JSON string |
| git_sha | TEXT | code version (required by code layer) |
| data_hash | TEXT | proves no data leakage (mandatory on OOS) |
| seed | INTEGER | montecarlo reproducibility |
| code_path | TEXT | script that ran this |
| notes | TEXT | |
| logged_at | DATETIME | NOT NULL |

---

## LOGS

### log_agent
Every agent **and** human protocol call. (Was `step5_agent_log` — renamed in migration 015.)

| Column | Type | Constraints / Note |
|--------|------|--------------------|
| call_id | INTEGER | **PK** AUTOINCREMENT |
| idea_id | TEXT | NOT NULL, FK → step1_ideas |
| gate_number | INTEGER | which gate this belongs to |
| gear | TEXT | NOT NULL, **CHECK(gear IN ('GENERATE','DISSECT','VALIDATE'))** |
| model | TEXT | **CHECK(model IN ('sonnet','opus'))**, NULL when source='human' |
| source | TEXT | NOT NULL DEFAULT 'agent', **CHECK(source IN ('agent','human'))** |
| task_summary | TEXT | |
| output_summary | TEXT | ⚠️ text-heavy (rule 9) |
| paper_id | INTEGER | FK → step2_papers (DISSECT only, else null) |
| result_id | INTEGER | FK → step4_results (VALIDATE only, else null) |
| created_at | DATETIME | NOT NULL |

---

### log_strategy
Strategy-evolution lineage (birth → live config). Read current setup via `strategy_log.get_live_config(idea_id)`. CLAUDE.md rule 11.

| Column | Type | Constraints / Note |
|--------|------|--------------------|
| log_id | INTEGER | **PK** AUTOINCREMENT |
| idea_id | TEXT | NOT NULL, FK → step1_ideas |
| event | TEXT | NOT NULL — free-text event label |
| component | TEXT | **CHECK(component IN ('exit','anchor','sizing','entry','filter','config') OR NULL)** |
| from_value | TEXT | |
| to_value | TEXT | |
| verdict | TEXT | NOT NULL, **CHECK(verdict IN ('CREATED','VALIDATED','PROPOSED','ADOPTED','REJECTED','FALSIFIED','SUPERSEDED'))** |
| rationale | TEXT | |
| result_id | INTEGER | FK → step4_results |
| git_sha | TEXT | |
| decided_by | TEXT | NOT NULL DEFAULT 'human', **CHECK(decided_by IN ('human','agent'))** |
| created_at | DATETIME | NOT NULL |
| params_json | TEXT | proposed/adopted knobs (spec-birth) |

INDEX: `idx_strategy_log_idea` ON (idea_id, created_at).
_Note: `pipeline._falsified_count` counts rows here with verdict='FALSIFIED' — drives the ≥2-FALSIFIED kill guard (rule 8b)._

---

### log_tasks
Backlog. Surfaced by the SessionStart brief via the `open_backlog` view.

| Column | Type | Constraints / Note |
|--------|------|--------------------|
| task_id | INTEGER | **PK** AUTOINCREMENT |
| idea_id | TEXT | FK → step1_ideas (nullable — cross-cutting tasks) |
| status | TEXT | NOT NULL DEFAULT 'open', **CHECK(status IN ('open','in_progress','done','dropped'))** |
| title | TEXT | NOT NULL |
| detail | TEXT | |
| kind | TEXT | NOT NULL, **CHECK(kind IN ('variant','sizing','filter','port','infra','data','cleanup'))** |
| priority | TEXT | NOT NULL DEFAULT 'P2', **CHECK(priority IN ('P0','P1','P2'))** |
| created_at | DATETIME | NOT NULL |
| updated_at | DATETIME | NOT NULL |
| resolved_at | DATETIME | |
| resolution | TEXT | |

---

## GATE-7 FIDELITY

### tester_runs
One row per MT5 Strategy-Tester run + its fidelity-diff verdict vs Python research. Filled by `tester.log_fidelity_diff`. `pass_gate(7)` is code-blocked until a row here has `fidelity_verdict='pass'`.

| Column | Type | Constraints / Note |
|--------|------|--------------------|
| run_id | INTEGER | **PK** AUTOINCREMENT |
| idea_id | TEXT | NOT NULL — soft FK into step1_ideas |
| ea_name | TEXT | e.g. 'baysix_orb_001' |
| ea_version | TEXT | |
| symbol | TEXT | NOT NULL — e.g. 'XAUUSD_dukas' |
| data_source | TEXT | NOT NULL, **CHECK IN ('dukascopy','broker_history','custom')** |
| model_quality | TEXT | MT5 history quality, e.g. '100% real ticks' |
| tester_model | TEXT | **CHECK IN ('real_ticks','every_tick','1min_ohlc','open_only') OR NULL** |
| timeframe | TEXT | 'M1' |
| period_start | DATE | |
| period_end | DATE | |
| tz_offset_hours | INTEGER | tester server→UTC offset (0 = UTC dukas) |
| magic_number | INTEGER | |
| initial_deposit | REAL | fair deposit (cap non-binding) |
| leverage | INTEGER | |
| spread_setting | TEXT | 'real' \| 'fixed:N' |
| params | TEXT | **CHECK(json_valid)** — EA inputs snapshot |
| n_trades | INTEGER | run-level summary ↓ |
| net_profit_usd | REAL | |
| profit_factor | REAL | |
| max_dd_pct | REAL | |
| win_rate | REAL | |
| research_result_id | INTEGER | soft ref → step4_results (fidelity diff ↓) |
| trade_overlap_pct | REAL | same session_date+direction |
| ER_delta_vs_research | REAL | |
| R_corr | REAL | |
| fidelity_verdict | TEXT | **CHECK IN ('pass','fail','pending') OR NULL**. observed: fail |
| notes | TEXT | |
| created_at | DATETIME | NOT NULL |
| updated_at | DATETIME | NOT NULL |

---

### tester_trades
Per-trade tester ledger (join key = `session_date`).

| Column | Type | Constraints / Note |
|--------|------|--------------------|
| tt_id | INTEGER | **PK** AUTOINCREMENT |
| run_id | INTEGER | NOT NULL, FK → tester_runs |
| ticket | INTEGER | MT5 position id (unique within a run) |
| session_date | DATE | |
| direction | TEXT | **CHECK IN ('long','short','flat') OR NULL** |
| entry_ts | DATETIME | |
| entry_px | REAL | |
| exit_ts | DATETIME | |
| exit_px | REAL | |
| exit_reason | TEXT | |
| lots | REAL | |
| risk_unit | REAL | |
| realized_R | REAL | |
| realized_pnl_usd | REAL | |
| meta | TEXT | **CHECK(json_valid)** — strategy ctx (ORB: or_high/or_low/range_w) |
| created_at | DATETIME | NOT NULL |

INDEXES: `ix_tester_trades_run` ON (run_id); `ix_tester_trades_run_ts` ON (run_id, entry_ts).

---

## Views — Command Centre

### idea_lifecycle
One row per idea: status, paper counts, highest gate passed, kill info.

### gate_pipeline
Ideas at open/blocked gates (latest attempt only), ordered by days since last activity. Excludes killed/graduated.

### papers_queue
Undissected papers blocking Gate 0, oldest first. Excludes killed/graduated.

### open_backlog
Open/in_progress `log_tasks`, ordered by priority then age. Powers the SessionStart brief.

---

## Full Connection Map

```
step1_ideas (spine)
  ├── step2_papers       idea_id → papers read per idea
  ├── step3_gates        idea_id → protocol gates 0–7
  ├── step4_results      idea_id → all quantitative output
  ├── log_agent          idea_id → every agent/human call
  │     ├── paper_id   → ties DISSECT to paper
  │     └── result_id  → ties VALIDATE to result
  ├── log_strategy       idea_id → strategy lineage (birth → live config)
  │     └── result_id  → ties a lineage event to its result
  └── log_tasks          idea_id → backlog (nullable for cross-cutting)

tester_runs (soft idea_id)     → Gate-7 fidelity run + diff verdict
  └── tester_trades  run_id    → per-trade tester ledger

Views:
  idea_lifecycle  · gate_pipeline · papers_queue · open_backlog
```

---

## Gate Reference (mirror of protocol — fixed in `pipeline.GATE_QUESTIONS`)

| Gate | Name | Question to answer |
|------|------|--------------------|
| 0 | Understand | Do we know the model's mathematical truth from the literature? |
| 1 | Frame | What is the simple human-readable rule and null hypothesis? |
| 2 | Foundation | Does the simplest possible implementation produce sane output? |
| 3 | Baseline | Does the dumb rule from Gate 1 have any edge, raw and after costs? |
| 4 | Model | Does the sophisticated model confirm or challenge the baseline? |
| 5 | Signal | Is there a tradeable signal with positive net edge? |
| 6 | Validate | Does the edge survive walk-forward and out-of-sample? |
| 7 | Fidelity | Does the deployed artifact reproduce the validated backtest on the same data? |

Gate semantics (from `protocol.py`): **evidence gates** = 3 (t>1.0), 5 (t>2.0), 6 (OOS) require a logged `step4_results` row; **fidelity gate** = 7 requires a `tester_runs` pass; the rest (0,1,2,4) are sense/structure gates needing no metric.

---

## Design Rules

1. Everything traces back to `idea_id` — no orphan rows.
2. Gate N cannot pass unless Gate N-1 is passed — enforced in `pipeline._check_previous_gate_passed`.
3. Results without `git_sha`, `n_obs` are rejected by `pipeline.log_result`; `data_hash` mandatory on OOS.
4. Kill reason mandatory when `status=killed`. Kill needs ≥2 FALSIFIED hypotheses in `log_strategy` (rule 8b) unless `force=True`.
5. `cost_adjusted=0` (raw) and `cost_adjusted=1` (net) both logged for Gate 3 and Gate 5.
6. `period` explicit on every metric — never ambiguous between per_trade / daily / annualised.
7. All writes via the `research/code/` layer — raw `sqlite3` writes are hook-blocked.
