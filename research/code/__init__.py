"""research.code — shared research-code layer (Protocol 4.0 lean package).

Physically organised into four subpackages — **gates/** (protocol + gate engine),
**lineage/** (the ledgers: strategy / agent / task logs), **io/** (data, paper and
MT5-tester I/O) and **infra/** (DB build, run plumbing, lint, execution twin) — but
the historical *flat* contract is preserved: every public module is re-exported here
so `from research.code import X` keeps working unchanged across hooks, the dashboard,
the brc model and the migrations.

Import order below is dependency-ordered (leaf modules first) so the modules that do
`from research.code import <sibling>` at their own top level find the attribute already
bound — no circular import. `idea_cli` is a CLI entrypoint (run as a script, never
imported) and is deliberately NOT re-exported here.
"""

# leaf engine + ledgers (no intra-package deps)
from research.code.gates import pipeline, protocol, grw
from research.code.lineage import strategy_log, agent_log, backlog
from research.code.infra import db_init, execution
from research.code.io import arctic_io

# depend on the leaves above
from research.code.io import tester                       # -> pipeline
from research.code.infra import run_and_log, run_tracked, handover_lint  # run_and_log -> pipeline, strategy_log
from research.code.io import ingest_brc_zones, ingest_tester_report      # -> tester
from research.code.io import fetch_papers, extract_pdf, backfill_dissect_md

__all__ = [
    "pipeline", "protocol",
    "strategy_log", "agent_log", "backlog",
    "db_init", "execution",
    "arctic_io", "tester", "ingest_brc_zones", "ingest_tester_report",
    "fetch_papers", "extract_pdf", "backfill_dissect_md",
    "run_and_log", "run_tracked", "handover_lint",
]
