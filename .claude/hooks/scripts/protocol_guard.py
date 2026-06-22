#!/usr/bin/env python3
"""PreToolUse guard — blocks the research-protocol anti-patterns that code can
catch at the moment of action. The prose rules in CLAUDE.md scroll out of the
warm context window mid-session; these two checks make the highest-value ones
unskippable and cost zero tokens (they run outside the model context).

HARD BLOCKS (exit 2):
  1. Raw sqlite3 WRITE to research.db / execution.db via Bash
     (CLAUDE.md rule 10 — all DB writes go through the research/code/ layer).
     SELECT-only reads pass through.
  2. Edit / Write whose target path ends in .db — never hand-edit a database.

Anything else passes. Gate-state checks for model code are intentionally NOT
here (can't be inferred cheaply without false positives) — that path is covered
by `research/code/gates/idea_cli.py gatecheck` + `... next`.

Convention matches playwright_guard.py: print {"decision":"block","reason":...}
then exit 2 to deny; exit 0 to allow.
"""
import json
import re
import sys

WRITE_SQL = re.compile(r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|REPLACE|CREATE)\b", re.IGNORECASE)
DB_NAMES = ("research.db", "execution.db")


def _block(reason: str) -> None:
    print(json.dumps({"decision": "block", "reason": reason}))
    sys.exit(2)


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    tool = data.get("tool_name", "")
    ti = data.get("tool_input") or {}

    if tool == "Bash":
        cmd = ti.get("command", "")
        if "sqlite3" in cmd and any(db in cmd for db in DB_NAMES) and WRITE_SQL.search(cmd):
            _block(
                "[protocol_guard] Raw sqlite3 WRITE to a research DB is banned "
                "(CLAUDE.md rule 10). Route it through the research/code/ layer: "
                "pipeline.* (gates/results), strategy_log.log_change (lineage), "
                "backlog.* (tasks), agent_log.* (QR/human calls). SELECT reads are fine."
            )
        sys.exit(0)

    if tool in ("Edit", "Write", "NotebookEdit"):
        path = (ti.get("file_path") or ti.get("notebook_path") or "").replace("\\", "/")
        if path.endswith(".db"):
            _block(
                "[protocol_guard] Never hand-edit a .db file — it corrupts "
                "timestamps/constraints. Use the research/code/ write layer (rule 10)."
            )

    sys.exit(0)


if __name__ == "__main__":
    main()
