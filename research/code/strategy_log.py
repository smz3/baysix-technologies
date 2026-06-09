"""
Strategy evolution log interface for research.db (log_strategy).
All writes go through here — no raw SQL elsewhere (CLAUDE.md rule 15).

The lineage of a strategy: birth -> every tested variant (kept or cut) -> live
config. Distinct from log_agent (activity feed) — this is the structured,
verdict-tagged spine, each row pointing at its evidence in step4_results.

Write:
  log_change()       — record one strategy-defining event
Read:
  get_lineage()      — full chronological lineage for an idea (the whole story)
  get_live_config()  — current live config = latest VALIDATED/ADOPTED per component
"""

import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parents[1] / "db" / "research.db"
MYT     = timezone(timedelta(hours=8))

VALID_VERDICT   = ("CREATED", "VALIDATED", "PROPOSED", "ADOPTED",
                   "REJECTED", "FALSIFIED", "SUPERSEDED")
VALID_COMPONENT = ("exit", "anchor", "sizing", "entry", "filter", "config")
_LIVE_VERDICTS  = ("VALIDATED", "ADOPTED")


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def _now() -> str:
    return datetime.now(MYT).strftime("%Y-%m-%d %H:%M:%S")


def log_change(
    idea_id: str,
    event: str,
    verdict: str,
    component: str = None,
    from_value: str = None,
    to_value: str = None,
    rationale: str = "",
    result_id: int = None,
    git_sha: str = None,
    decided_by: str = "human",
    created_at: str = None,          # override for backfilling historical events
) -> int:
    """Record one strategy-defining event. Returns log_id."""
    if verdict not in VALID_VERDICT:
        raise ValueError(f"verdict must be one of {VALID_VERDICT}")
    if component is not None and component not in VALID_COMPONENT:
        raise ValueError(f"component must be one of {VALID_COMPONENT} or None")
    if decided_by not in ("human", "agent"):
        raise ValueError("decided_by must be 'human' or 'agent'")

    when = created_at or _now()
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO log_strategy
                (idea_id, event, component, from_value, to_value, verdict,
                 rationale, result_id, git_sha, decided_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (idea_id, event, component, from_value, to_value, verdict,
              rationale, result_id, git_sha, decided_by, when))
        conn.commit()
        log_id = cur.lastrowid

    arrow = f" {from_value} -> {to_value}" if to_value else ""
    print(f"[strategy_log] {idea_id} {verdict} {component or '-'}{arrow}  (log_id={log_id})")
    return log_id


def get_lineage(idea_id: str) -> list[dict]:
    """Full chronological lineage — the strategy's whole story, oldest first."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM log_strategy WHERE idea_id=? ORDER BY created_at, log_id",
            (idea_id,)
        ).fetchall()
    return [dict(r) for r in rows]


def get_live_config(idea_id: str) -> dict:
    """
    Current live config: the to_value of the latest VALIDATED/ADOPTED row per
    component. REJECTED/FALSIFIED/PROPOSED/SUPERSEDED do not count as live.
    Returns {component: {"value", "log_id", "result_id", "at"}}.
    """
    live = {}
    for r in get_lineage(idea_id):
        if r["component"] and r["verdict"] in _LIVE_VERDICTS:
            live[r["component"]] = {
                "value": r["to_value"], "log_id": r["log_id"],
                "result_id": r["result_id"], "at": r["created_at"],
            }
    return live


if __name__ == "__main__":
    import sys
    idea = sys.argv[1] if len(sys.argv) > 1 else "ORB-001"
    print(f"=== LIVE CONFIG: {idea} ===")
    for comp, d in get_live_config(idea).items():
        print(f"  {comp:8} = {d['value']:18}  (result #{d['result_id']}, {d['at']})")
    print(f"\n=== LINEAGE: {idea} ===")
    for r in get_lineage(idea):
        arrow = f"{r['from_value'] or '—'} -> {r['to_value'] or '—'}"
        print(f"  {r['created_at'][:10]}  {r['verdict']:10} {str(r['component'] or '-'):8} "
              f"{arrow:28} {r['event']}")
