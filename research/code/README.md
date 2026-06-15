# research/code/ — module index

Shared research code. **All `research.db` / `execution.db` writes go through this
layer** (CLAUDE.md rule 10) — never raw `sqlite3`. Modules are flat by design: 68+
external import sites and 12 script entrypoints rely on `from research.code import X`
and the dual-path (`except ImportError: import X`) own-dir fallback, so files stay in
one folder rather than subpackages. This table is the index instead.

## DB write/read layer (the contract surface)

| Module | Table(s) | Role |
|---|---|---|
| [pipeline.py](pipeline.py) | step1_ideas · step3_gates · step4_results | Core: `add_idea`, `open_gate`/`pass_gate`/`block_gate`/`kill_idea`, `log_result`, getters. |
| [strategy_log.py](strategy_log.py) | log_strategy | Strategy lineage (birth → live config): `log_change`, `get_live_config`, `get_spec`. |
| [agent_log.py](agent_log.py) | step2_papers · log_agent | QR find/dissect + human-decision log: `log_agent_call`, `log_dissect_result`, `log_human_decision`. |
| [backlog.py](backlog.py) | log_tasks | Task ledger: `add_task`, `update_task`, `resolve_task`, `get_backlog`. |
| [trial_family.py](trial_family.py) | trial_family · step4_results | N_trials/DSR ledger: `open_family`, `log_trial`, `select_config`, `deflation_inputs`. |
| [protocol.py](protocol.py) | — | Protocol state machine: the ONE next legal gate action; gate questions + significance-test resolution (single source). |
| [execution.py](execution.py) | execution.db | Downstream live-deployment twin (VPS ledger). |
| [db_init.py](db_init.py) | (all) | Build research.db schema from scratch. |

## Gate metric producers

| Module | Gate | Role |
|---|---|---|
| [gate2_sanity.py](gate2_sanity.py) | 2 | Generic 3-category sanity (validity / non-degeneracy / causal cleanliness). |
| [gate5_report.py](gate5_report.py) | 5 | Pre-committed pass bars → PSR/DSR or IC/AUC → QuantStats tearsheet last. Auto-DSR via `trial_family`. |

## Data IO

| Module | Role |
|---|---|
| [arctic_io.py](arctic_io.py) | The ONE canonical XAUUSD tick/daily reader (ArcticDB): `tick_months`, `read_tick_month`, `is_ticks`, `oos_ticks`, `daily_bars`. |
| [export_ticks_mt5.py](export_ticks_mt5.py) | Export ticks → compact binary for the MQL5 import script. |

## Backtest engine + Gate-7 fidelity (MT5 ↔ Python)

| Module | Role |
|---|---|
| [fills.py](fills.py) | The ONE canonical bid/ask fill model — venue-aware, idea-agnostic. |
| [run_and_log.py](run_and_log.py) | The sanctioned way to score a backtest (result + verdict atomically). |
| [run_tracked.py](run_tracked.py) | Launch a long run in a NEW PowerShell window with a DONE-sentinel (live output). |
| [tester.py](tester.py) | Gate-7 FIDELITY writers (tester_runs / tester_trades). |
| [ingest_tester_report.py](ingest_tester_report.py) | Ingest an MT5 Strategy-Tester `.xlsx` into Gate-7 evidence. |

## CLI / tooling

| Module | Role |
|---|---|
| [idea_cli.py](idea_cli.py) | Read-only CLI over the getters: `status`, `next <idea>`, `gatecheck`, `prebrief`. |
| [handover_lint.py](handover_lint.py) | BLOCKING gate: every result-number in a handover must cite a result_id/artifact. |
| [fetch_papers.py](fetch_papers.py) | Download paper PDFs into `research/papers/<family>/`. |

---
_Adding a module? Put it here flat, give it a one-line docstring header matching the
convention, and add a row above. Revisit subpackages only past ~30 files or after
making `research/code` a `pip install -e` package (kills the dual-path fallback)._
