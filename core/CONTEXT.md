# core/ — shared research-DB code layer

One job: every `research.db` / `execution.db` write goes through this package —
never raw `sqlite3`, never a `.db` hand-edit. [README.md](README.md) is the module
index (which file owns which table); this file is the contract for using it safely,
including from an unattended loop.

## Inputs
- Working (this run): whichever `idea_id` / result the calling session or loop is
  acting on.
- Reference (every run): [README.md](README.md) for the module table, and
  [core/RESEARCH_CODE_PROTOCOL.md](RESEARCH_CODE_PROTOCOL.md) — read before
  touching anything in here or in `research/models/`.

## Process
1. Find the right module via `README.md`'s table first. Don't grep the repo for a
   bare column name — `confirm_time`, `mfe_r` and others collide by coincidence
   across FOB/BRC namespaces (CLAUDE.md rule 4a); an unscoped search drags a parked
   system into a live decision.
2. Call the code-layer function for the job — `open_gate` / `pass_gate` / `kill_idea`
   / `log_result` / `log_agent_call` / `log_dissect_result` / `log_human_decision` /
   `strategy_log.log_change` — never `sqlite3` directly.
3. `.claude/hooks/scripts/protocol_guard.py` blocks raw `sqlite3` writes and `.db`
   hand-edits at PreToolUse. If it fires, fix the call — don't route around the hook.
4. Log immediately, before replying or before the next loop iteration reads state —
   an agent call or decision that isn't logged the same turn is exactly what this
   rule exists to prevent once a loop is running unattended.

## Outputs
- `research.db` / `execution.db` rows, written only via the functions above.

## Human check
New module: does it have a one-line docstring header, a row in `README.md`'s table,
and an export in `__init__.py`? DDL change: is `infra/schema_ledger.py` still the
only place that DDL is written?
