# research/code/ — module index (Protocol 4.0 lean package)

Shared research code. **All `research.db` / `execution.db` writes go through this
layer** (CLAUDE.md rule 10) — never raw `sqlite3`.

Organised into four subpackages, but the historical flat contract is **preserved**:
[`__init__.py`](__init__.py) re-exports every public module, so `from research.code
import X` keeps working unchanged across hooks, the dashboard, the brc model and the
migrations. Intra-package code uses the subpackage-qualified path
(`from research.code.gates import pipeline`) to stay immune to `__init__` ordering;
script entrypoints prepend a repo-root `sys.path` bootstrap.

## gates/ — protocol + gate engine
| Module | Table(s) | Role |
|---|---|---|
| [gates/pipeline.py](gates/pipeline.py) | step1_ideas · step3_gates · step4_results | Core: `add_idea`, `open_gate`/`pass_gate`/`block_gate`/`kill_idea`, `log_result`, getters. |
| [gates/protocol.py](gates/protocol.py) | — | Protocol state machine: the ONE next legal gate action (4 gates: G1 Premise / G2 Edge+Survival / G3 Robustness / G4 Live). |
| [gates/idea_cli.py](gates/idea_cli.py) | (read-only) | CLI over the getters: `status`, `next <idea>`, `gatecheck`, `prebrief`. Run: `python research/code/gates/idea_cli.py …`. |

## lineage/ — the ledgers
| Module | Table(s) | Role |
|---|---|---|
| [lineage/strategy_log.py](lineage/strategy_log.py) | log_strategy | Strategy lineage (birth → live config): `log_change`, `get_live_config`, `get_spec`. |
| [lineage/agent_log.py](lineage/agent_log.py) | step2_papers · log_agent | QR find/dissect + human-decision log: `log_agent_call`, `log_dissect_result`, `log_human_decision`. |
| [lineage/backlog.py](lineage/backlog.py) | log_tasks | Task ledger: `add_task`, `update_task`, `resolve_task`, `get_backlog`. |

## io/ — data · paper · MT5-tester I/O
| Module | Role |
|---|---|
| [io/arctic_io.py](io/arctic_io.py) | The ONE canonical XAUUSD tick/daily reader (ArcticDB): `tick_months`, `read_tick_month`, `is_ticks`, `oos_ticks`, `daily_bars`. |
| [io/tester.py](io/tester.py) | MT5 Strategy-Tester evidence writers (tester_runs / tester_trades / tester_zones). |
| [io/ingest_tester_report.py](io/ingest_tester_report.py) | Ingest an MT5 tester report into the tester tables. |
| [io/ingest_brc_zones.py](io/ingest_brc_zones.py) | Ingest a BRC zone-lifecycle CSV → tester_zones. |
| [io/fetch_papers.py](io/fetch_papers.py) | Download paper PDFs into `research/papers/<family>/`. |
| [io/extract_pdf.py](io/extract_pdf.py) | Docling PDF → `<stem>.md` source text (the DISSECT input). |
| [io/backfill_dissect_md.py](io/backfill_dissect_md.py) | Reconstruct a `<stem>.dissect.md` from the DB dissection log. |

## infra/ — DB build · run plumbing · lint · execution twin
| Module | Role |
|---|---|
| [infra/db_init.py](infra/db_init.py) | Build research.db schema from scratch (lean 4.0). |
| [infra/run_and_log.py](infra/run_and_log.py) | The sanctioned way to score a backtest (result + verdict atomically). |
| [infra/run_tracked.py](infra/run_tracked.py) | Launch a long run in a NEW PowerShell window with a DONE-sentinel (live output). |
| [infra/handover_lint.py](infra/handover_lint.py) | BLOCKING gate: every result-number in a handover must cite a result_id/artifact. |
| [infra/execution.py](infra/execution.py) | execution.db — downstream live-deployment twin (VPS ledger). |

---
_Adding a module? Put it in the right subpackage, give it a one-line docstring header,
add it to the re-export list in [`__init__.py`](__init__.py), and add a row above.
Archived/superseded modules live in [_archive/](_archive/)._
