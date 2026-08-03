# research.db — Schema (mirror of live DB)

_Last updated: 2026-08-03 — **migration 037** (tasks 287/289): tester DDL de-duplicated into [schema_ledger.py](../../research/code/infra/schema_ledger.py), GRW-001 factory tables added, `journal_mode=WAL`. Prior: 2026-06-22 Protocol 4.0 lean rebuild (migration 032) — 4 gates (G1–G4), `trial_family` + the 3.3 result columns dropped, tester tables folded into `db_init`. Gate semantics in [research_protocol.md](research_protocol.md)._

The DB has **18 tables** + **6 views**. All writes go through the 4 subpackages of [research/code/](../../research/code/) — `gates/` (`pipeline`, `protocol`), `lineage/` (`strategy_log`, `agent_log`, `backlog`), `io/` (`tester`, …), `infra/` (`db_init`, …) — never raw `sqlite3` (CLAUDE.md rule 10, hook-enforced). The flat `from research.code import X` contract is preserved via `__init__` re-exports.

CHECK / UNIQUE / FK constraints below are the **real DB-level constraints** read from the table SQL. "observed:" lists the values actually present today (not a constraint unless a CHECK is noted).

---

## Table groups

```
PIPELINE CORE      step1_ideas · step2_papers · step3_gates · step4_results
LOGS               log_agent · log_strategy · log_tasks
MT5 TESTER LEDGER  tester_runs · tester_trades · tester_zones · tester_run_summary
                   (the EA-emitted ledger; G2 edge read + G4 parity)
FOB-001 PAYLOAD    fob_cycles · fob_zones · fob_events · fob_run_stats
GRW-001 FACTORY    grw_batches · grw_passes   (+ views grw_family_trials, grw_batch_scoreboard)
```

**DDL ownership (task 287).** The MT5 ledger / FOB payload / GRW factory DDL lives in
exactly one place — [research/code/infra/schema_ledger.py](../../research/code/infra/schema_ledger.py)
(`SCHEMA_MT5`, `SCHEMA_GRW`) — and both `db_init.py` and `tester.py` import it.
`db_init.py` used to hold a second, drifted copy that was silently missing
`tester_runs.run_role/git_sha/git_dirty`, `tester_trades.zone_id/gross_usd/cost_usd`,
and every `tester_run_summary`/`fob_*` table. Never re-inline this DDL.

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
| idea_kind | TEXT | **CHECK(idea_kind IS NULL OR idea_kind IN ('strategy','primitive','overlay','classifier'))**. Protocol 3.2 — picks the gate variant (`protocol.GATE_APPLICABILITY`). Migration 026. NULL until declared (untagged → full ladder). |
| output_type | TEXT | **CHECK(output_type IS NULL OR output_type IN ('pnl_stream','classifier_score','primitive_output'))**. Names what the idea emits; tagged at G1 (4.0 wall: G1 needs idea_kind + output_type set). |

---

### step2_papers
Papers read per idea. MANDATORY at G1 (every idea links ≥1 paper).

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
| gate_number | INTEGER | NOT NULL, **CHECK(gate_number BETWEEN 1 AND 4)** — 4.0 gates G1..G4 |
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
| is_run | TEXT | 4.0 IS run label (IS-01, IS-02…); REQUIRED on stage IN ('IS','OOS'). Count shots via `DISTINCT is_run` — the separate `is_runs` registry was collapsed into this column in migration 033 |
| what_changed | TEXT | what this IS run swept/changed (was `is_runs.what_changed`) |
| trial_family_id | TEXT | GRW-001 multiplicity key (migration 037) — trials compared for ONE decision, accumulating across batches. Bookkeeping only; nothing auto-kills on it |
| n_trials | INTEGER | passes actually run to reach this result (migration 037). "A growth rate without its trial count is not a finding" |
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

### ~~is_runs~~ — does not exist (collapsed, migration 033)
**There is no `is_runs` table.** The 4.0 IS-run numbering was folded into
`step4_results.is_run` / `.what_changed` by migration `033_collapse_is_runs.py`; count
shots taken with `SELECT COUNT(DISTINCT is_run) … WHERE idea_id=?`. Read via
`pipeline.get_is_runs(idea_id)`.

This is recorded explicitly because stale references to a phantom `is_runs` table in
CLAUDE.md and the GRW spec were mistaken for a blocking schema gap (verified + closed
by migration 037, task 289).

---

## GRW-001 FACTORY

The compounding-factory ledger. Full semantics in
[grw_autonomous_workflow.md](grw_autonomous_workflow.md) §2 (promotion ladder) / §4 (storage).

### grw_batches
One row per **pre-registered** batch. `prereg.json` on disk stays the source of truth
(hashed + git-committed *before* the batch runs); this table is the queryable index.
Key columns: `batch_id` (PK), `trial_family_id`, `hypothesis`, `mechanism` (why the edge
should exist — no mechanism, no slot), `is_start/is_end`, `oos_start/oos_end`,
`n_trials_budget`, `promote_if`, `kill_if`, `prereg_sha`, `stage`, `oos_spent`.

### grw_passes
One row per optimizer pass. **Passes are raw material, not results** — only an
S3-adjudicated survivor is copied into `step4_results`. The `verdict` column
(`PENDING`/`PROMOTED`/`FALSIFIED`/`KILLED`) is that boundary. Carries `prereg_sha` per
row, so a pass judged under a moved goalpost is self-evident. IS and OOS legs link out
to `tester_runs` via `is_run_id` / `oos_run_id`.

### Views
- `grw_family_trials` — the multiplicity ledger: cumulative `n_trials` per
  `trial_family_id`, across batches.
- `grw_batch_scoreboard` — per-batch promoted/falsified/pending counts; drives the
  "3 consecutive batches with no promotion" hard stop.

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
| component | TEXT | **CHECK(component IN ('exit','anchor','sizing','entry','filter','config','conditioning','management') OR NULL)**. Migration 027 added `conditioning` (regime/state giving the conditional edge — Protocol 3.2 Gate 1 spec-birth) + `management` (trail / partial / breakeven / time-stop). |
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
Undissected papers blocking G1, oldest first. Excludes killed/graduated.

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

tester_runs (soft idea_id)     → MT5 tester ledger (G2 edge read + G4 live-parity evidence)
  └── tester_trades  run_id    → per-trade tester ledger

Views:
  idea_lifecycle  · gate_pipeline · papers_queue · open_backlog
```

---

## Gate Reference (Protocol 4.0 — mirror of `pipeline.GATE_QUESTIONS` / [research_protocol.md](research_protocol.md))

| Gate | Name | Question to answer | Code wall |
|------|------|--------------------|-----------|
| G1 | Premise | Idea + one simple rule + thesis + a linked paper. Why should this edge exist? | `idea_kind`+`output_type` tagged **and** ≥1 `step2_papers` row |
| G2 | Edge & Survival | Does the IS net-of-cost ledger show a smooth curve and acceptable drawdown? | ≥1 `step4_results` row, `cost_adjusted=1` |
| G3 | Robustness | Does the IS edge survive walk-forward + Monte Carlo? | human read (OOS-freeze chokepoint on `open_gate(3)`) |
| G4 | Live | Does the MT5 tester / demo / live ledger match within tolerance? | human read |

`idea_kind` picks which gates apply (`protocol.GATE_APPLICABILITY`): strategy/overlay/classifier run the full G1–G4 ladder; primitives are correctness-only ({G1, G2}). t-stat is **reported**, never an auto-kill — OOS/WF persistence at G3 is the luck-test. Supersedes the old 8-gate (0–7) scheme; full rationale in [docs/specs/2026-06-22-protocol-4.0-lean-gates.md](../specs/2026-06-22-protocol-4.0-lean-gates.md).

---

## Design Rules

1. Everything traces back to `idea_id` — no orphan rows.
2. Gate N cannot pass unless the highest **applicable** gate below N is passed (idea_kind-aware skip, not literally N-1) — enforced in `pipeline._check_previous_gate_passed`.
3. Results without `git_sha`, `n_obs` are rejected by `pipeline.log_result`; `data_hash` mandatory on OOS.
4. Kill reason mandatory when `status=killed`. Kill needs ≥2 FALSIFIED hypotheses in `log_strategy` (rule 8b) unless `force=True`.
5. `cost_adjusted=0` (raw) and `cost_adjusted=1` (net); G2 needs a net (cost_adjusted=1) result to pass.
6. `period` explicit on every metric — never ambiguous between per_trade / daily / annualised.
7. All writes via the `research/code/` layer — raw `sqlite3` writes are hook-blocked.
