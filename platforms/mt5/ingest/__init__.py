"""MT5 ingest — reads MetaTrader 5 Strategy Tester output into the shared ledger.

MOVED here 2026-08-16 (task 360's layer split). These modules are MT5-shaped:
they parse this platform's tester artifacts. They still WRITE through
core, because results are shared truth and must not fork per platform.

STAYED BEHIND in core/io on purpose: tester.py and fob_payload.py.
Six applied migrations (012/022/030/031/036 and core/__init__.py's
chain) import them by their old path, and migrations are a replayable record
that must not be rewritten. Moving those two needs a compatibility shim —
opened as its own task rather than smuggled into this move.
"""
