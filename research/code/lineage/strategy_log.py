"""
Strategy evolution log interface for research.db (log_strategy).
All writes go through here — no raw SQL elsewhere (CLAUDE.md rule 10).

The lineage of a strategy: birth -> every tested variant (kept or cut) -> live
config. Distinct from log_agent (activity feed) — this is the structured,
verdict-tagged spine, each row pointing at its evidence in step4_results.

Write:
  log_change()       — record one strategy-defining event (+ optional params_json knobs)
Read:
  get_lineage()      — full chronological lineage for an idea (the whole story)
  get_live_config()  — current live config = latest VALIDATED/ADOPTED per component
  get_spec()         — per-component spec card (live / proposed / dead) + knobs
"""

import json
import re
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path

from research.code.infra.db_path import DB_PATH  # noqa: F401  (task 357: one canonical path)
MYT     = timezone(timedelta(hours=8))

VALID_VERDICT   = ("CREATED", "VALIDATED", "PROPOSED", "ADOPTED",
                   "REJECTED", "FALSIFIED", "SUPERSEDED")
# Protocol 3.2 (Gate 1 spec-birth) made conditioning + management first-class:
#   conditioning = the regime/state that gives the CONDITIONAL edge (mechanism-born
#                  at Gate 0, not fitted); Gate 3 tests the conditioned rule.
#   management   = trade management (trail / partial / breakeven / time-stop).
VALID_COMPONENT = ("exit", "anchor", "sizing", "entry", "filter", "config",
                   "conditioning", "management")
_LIVE_VERDICTS  = ("VALIDATED", "ADOPTED")
_DEAD_VERDICTS  = ("REJECTED", "FALSIFIED")
_PROP_VERDICTS  = ("CREATED", "PROPOSED")
# the design knobs a spec card describes (config = whole-strategy verdict, not a knob)
SPEC_COMPONENTS = ("entry", "exit", "sizing", "anchor", "filter",
                   "conditioning", "management")

# A significance cutoff baked into a hypothesis (t>=2, IC>=0.05, Sharpe t>3) turns a
# Gate-3/5 CONFIRMATION bar into the FRONT gate — exactly how MSM-001 leaked (anchor
# read "interaction must carry IC/Sharpe t>=2-3"). Front gate = economic sense +
# visible structure; t-stat comes LAST. Warn (don't block — anchors may legitimately
# reference metrics) so the agent re-reads before committing it.
_THRESHOLD_PAT = re.compile(
    r"\b(t|t-?stat|ic|sharpe|psr)\b[^.\n]{0,15}[><≥≤=]{1,2}\s*[-+]?\d",
    re.IGNORECASE,
)


def _warn_threshold_in_anchor(component, to_value):
    if component in ("anchor", "filter", "conditioning") and to_value and _THRESHOLD_PAT.search(to_value):
        print(
            f"[strategy_log] ⚠️  WARNING: this {component} embeds a significance "
            f"cutoff — t/IC/Sharpe thresholds belong at Gate 3 (>1.0) / Gate 5 "
            f"(>2.0) as CONFIRMATION, not inside the hypothesis. Front-gate on "
            f"economic sense + visible cell separation; let the t-stat decide LAST."
        )


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
    params_json: dict = None,        # structured knobs for the value this row introduces
) -> int:
    """Record one strategy-defining event. Returns log_id."""
    if verdict not in VALID_VERDICT:
        raise ValueError(f"verdict must be one of {VALID_VERDICT}")
    if component is not None and component not in VALID_COMPONENT:
        raise ValueError(f"component must be one of {VALID_COMPONENT} or None")
    if decided_by not in ("human", "agent"):
        raise ValueError("decided_by must be 'human' or 'agent'")
    if params_json is not None and not isinstance(params_json, dict):
        raise ValueError("params_json must be a dict (a component's knobs) or None")

    _warn_threshold_in_anchor(component, to_value)

    params_str = json.dumps(params_json) if params_json is not None else None
    when = created_at or _now()
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO log_strategy
                (idea_id, event, component, from_value, to_value, verdict,
                 rationale, result_id, git_sha, decided_by, created_at, params_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (idea_id, event, component, from_value, to_value, verdict,
              rationale, result_id, git_sha, decided_by, when, params_str))
        conn.commit()
        log_id = cur.lastrowid

    arrow = f" {from_value} -> {to_value}" if to_value else ""
    print(f"[strategy_log] {idea_id} {verdict} {component or '-'}{arrow}  (log_id={log_id})")
    return log_id


def set_params(log_id: int, params_json: dict) -> None:
    """
    Attach/replace the structured knobs on an existing row (it annotates a value,
    not a new event — so this is an UPDATE, not an append). Used to backfill
    params onto rows logged before the spec workflow existed.
    """
    if not isinstance(params_json, dict):
        raise ValueError("params_json must be a dict (a component's knobs)")
    with _conn() as conn:
        cur = conn.execute(
            "UPDATE log_strategy SET params_json=? WHERE log_id=?",
            (json.dumps(params_json), log_id),
        )
        conn.commit()
        if cur.rowcount == 0:
            raise ValueError(f"no log_strategy row with log_id={log_id}")
    print(f"[strategy_log] params set on log_id={log_id}: {list(params_json)}")


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


def _parse_params(raw):
    return json.loads(raw) if raw else None


def get_spec(idea_id: str) -> dict:
    """
    Per-component spec card. For each design component (entry/exit/sizing/anchor/
    filter) present in the lineage, resolve ONE card by priority:
        live     — latest VALIDATED/ADOPTED row (the chosen knob-set)
        proposed — else latest CREATED/PROPOSED row (born, not yet validated)
        dead     — else only REJECTED/FALSIFIED rows survive
    Each card: {status, value, params, log_id, result_id, at, dead_variants}.
    `config` and birth (NULL-component) rows are not knobs -> excluded.
    Sibling of get_live_config(): that returns only live values; this returns the
    full design surface, including unproven and abandoned components.
    """
    rows = get_lineage(idea_id)  # oldest first
    spec = {}
    for comp in SPEC_COMPONENTS:
        crows = [r for r in rows if r["component"] == comp]
        if not crows:
            continue
        dead_variants = sum(1 for r in crows if r["verdict"] in _DEAD_VERDICTS)

        def _latest(verdicts):
            hits = [r for r in crows if r["verdict"] in verdicts]
            return hits[-1] if hits else None

        chosen = _latest(_LIVE_VERDICTS)
        status = "live"
        if chosen is None:
            chosen = _latest(_PROP_VERDICTS)
            status = "proposed"
        if chosen is None:
            chosen = crows[-1]          # only dead rows remain
            status = "dead"

        spec[comp] = {
            "status": status,
            "value": chosen["to_value"],
            "params": _parse_params(chosen["params_json"]),
            "log_id": chosen["log_id"],
            "result_id": chosen["result_id"],
            "at": chosen["created_at"],
            "dead_variants": dead_variants,
        }
    return spec


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
