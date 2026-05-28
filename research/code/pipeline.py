"""
Pipeline interface for research_log.db.
All writes go through here — no raw SQL elsewhere.
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parents[1] / "db" / "research_log.db"

STAGES = [
    "CAPTURED",
    "HYPOTHESIS_SET",
    "IS_SIGNAL",
    "IS_BUILD",
    "WALK_FORWARD",
    "MONTE_CARLO",
    "OOS",
    "LIVE",
]


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


# ── Read ──────────────────────────────────────────────────────────────────────

def get_status(idea_id: int) -> dict:
    """Return current pipeline row + full event history for an idea."""
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM pipeline WHERE idea_id = ?", (idea_id,))
        row = cur.fetchone()
        if not row:
            return {}
        result = dict(row)

        cur.execute(
            "SELECT * FROM pipeline_events WHERE idea_id = ? ORDER BY timestamp",
            (idea_id,)
        )
        result["events"] = [dict(r) for r in cur.fetchall()]
        return result


# ── Write ─────────────────────────────────────────────────────────────────────

def advance_stage(idea_id: int, to_stage: str, reason: str, triggered_by: str = "agent") -> None:
    """Move idea to the next stage and log the transition."""
    if to_stage not in STAGES:
        raise ValueError(f"Unknown stage: {to_stage}. Must be one of {STAGES}")

    now = _now()
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT current_stage FROM pipeline WHERE idea_id = ?", (idea_id,))
        row = cur.fetchone()
        if not row:
            raise ValueError(f"idea_id={idea_id} not found in pipeline")

        from_stage = row["current_stage"]

        cur.execute(
            "UPDATE pipeline SET current_stage = ?, updated_at = ? WHERE idea_id = ?",
            (to_stage, now, idea_id)
        )
        cur.execute("""
            INSERT INTO pipeline_events
                (idea_id, event_type, from_stage, to_stage, triggered_by, reason, timestamp)
            VALUES (?, 'STAGE_ADVANCE', ?, ?, ?, ?, ?)
        """, (idea_id, from_stage, to_stage, triggered_by, reason, now))

        conn.commit()
        print(f"idea_id={idea_id}: {from_stage} -> {to_stage}")


def kill_idea(idea_id: int, reason: str, triggered_by: str = "agent") -> None:
    """Kill an idea at its current stage."""
    now = _now()
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT current_stage FROM pipeline WHERE idea_id = ?", (idea_id,))
        row = cur.fetchone()
        if not row:
            raise ValueError(f"idea_id={idea_id} not found in pipeline")

        cur.execute(
            "UPDATE pipeline SET stage_status = 'killed', kill_reason = ?, updated_at = ? WHERE idea_id = ?",
            (reason, now, idea_id)
        )
        cur.execute("""
            INSERT INTO pipeline_events
                (idea_id, event_type, from_stage, triggered_by, reason, timestamp)
            VALUES (?, 'KILL', ?, ?, ?, ?)
        """, (idea_id, row["current_stage"], triggered_by, reason, now))

        conn.commit()
        print(f"idea_id={idea_id}: KILLED at {row['current_stage']} — {reason}")


def log_metric(
    idea_id: int,
    metric_key: str,
    metric_value: float,
    metric_unit: str,
    test_type: str,
    triggered_by: str = "agent",
    n_simulations: int = None,
    summary: str = None,
) -> None:
    """Log a metric result for an idea at its current stage."""
    now = _now()
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT current_stage FROM pipeline WHERE idea_id = ?", (idea_id,))
        row = cur.fetchone()
        if not row:
            raise ValueError(f"idea_id={idea_id} not found in pipeline")

        cur.execute("""
            INSERT INTO pipeline_events
                (idea_id, event_type, from_stage, triggered_by,
                 validate_summary, metric_key, metric_value,
                 metric_unit, test_type, n_simulations, timestamp)
            VALUES (?, 'METRIC', ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            idea_id, row["current_stage"], triggered_by,
            summary, metric_key, metric_value,
            metric_unit, test_type, n_simulations, now
        ))

        conn.commit()
        print(f"idea_id={idea_id}: logged {metric_key}={metric_value} [{metric_unit}]")
