"""core — shared research-code layer (Protocol 4.0 lean package).

Physically organised into four subpackages — **gates/** (protocol + gate engine),
**lineage/** (the ledgers: strategy / agent / task logs), **io/** (data, paper and
MT5-tester I/O) and **infra/** (DB build, run plumbing, lint, execution twin) — but
the historical *flat* contract is preserved: every public module is re-exported here
so `from core import X` keeps working unchanged across the migrations, the
tests, the dashboard and the brc model.

LAZY re-export (2026-08-16)
---------------------------
These re-exports used to be eager `import` statements at module top level. That made
`from core.lineage import backlog` — a pure-`sqlite3` module with zero third-
party deps — pay for pandas (via `io.arctic_io`) plus requests/pydantic (via
`io.fetch_papers`) on every process start. Measured: 0.05s bare python, 1.05s to reach
`backlog`, of which pandas alone was 0.52s. The handover flow spends that tax once per
`python -c`, several times per session, for modules it never touches.

They are now resolved on first attribute access via PEP 562 `__getattr__`. `from
core import X` still works — Python falls back to the module `__getattr__`
when the attribute is not already bound — but nothing heavy is imported until asked for.

The old eager block was also dependency-ORDERED, to keep modules that do
`from core import <sibling>` at their own top level from hitting a half-built
package. That ordering is no longer load-bearing: every module inside this package now
imports its siblings by fully-qualified subpackage path (`from core.gates
import pipeline`), never through the package root, so there is no cycle to order around.
If you ever add a root-level sibling import inside this package, that changes — use the
subpackage path instead.

`idea_cli` is a CLI entrypoint (run as a script, never imported) and is deliberately
NOT re-exported here.
"""

import importlib

# public name -> module that provides it. Anything listed here is importable as
# `from core import <name>`; it is loaded on first touch, not at import time.
_LAZY_EXPORTS = {
    # leaf engine + ledgers
    "pipeline":             "core.gates.pipeline",
    "protocol":             "core.gates.protocol",
    "strategy_log":         "core.lineage.strategy_log",
    "agent_log":            "core.lineage.agent_log",
    "backlog":              "core.lineage.backlog",
    "db_init":              "core.infra.db_init",
    "execution":            "core.infra.execution",
    "arctic_io":            "core.io.arctic_io",
    # depend on the leaves above
    "tester":               "core.io.tester",
    "run_and_log":          "core.infra.run_and_log",
    "run_tracked":          "core.infra.run_tracked",
    "handover_lint":        "core.infra.handover_lint",
    # ingest_brc_zones / ingest_tester_report MOVED to platforms/mt5/ingest 2026-08-16
    # (task 360 layer split) and are deliberately NOT re-exported here. This package is
    # the SHARED layer; re-exporting one platform's ingest from it would make MT5 code
    # look repo-generic and invite the next platform to add its own alongside.
    "fetch_papers":         "core.io.fetch_papers",
    "extract_pdf":          "core.io.extract_pdf",
    "backfill_dissect_md":  "core.io.backfill_dissect_md",
}


def __getattr__(name: str):
    """PEP 562 — resolve a re-exported module on first access, then cache it in
    globals() so every later lookup is a plain dict hit with no import machinery."""
    target = _LAZY_EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(target)
    globals()[name] = module
    return module


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(_LAZY_EXPORTS))


__all__ = [
    "pipeline", "protocol",
    "strategy_log", "agent_log", "backlog",
    "db_init", "execution",
    "arctic_io", "tester",
    "fetch_papers", "extract_pdf", "backfill_dissect_md",
    "run_and_log", "run_tracked", "handover_lint",
]
