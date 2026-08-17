"""
Migration 017 — Rebuild gate_pipeline view to dedupe to the latest attempt per gate.

Bug (task 23, found 2026-06-09): gate_pipeline joined ALL step3_gates rows then
filtered status IN ('open','blocked'). A gate later PASSED on a retry (higher
attempt) still surfaced its stale blocked attempts — HMM-001 showed false-blocked
G2 + G4 (attempts 1 & 2 blocked, attempt 3 passed), duplicated to 4 rows.

Fix: a `latest` CTE picks MAX(attempt) per (idea_id, gate_number); the view joins
only that row, THEN filters. ORB-001 (all G0-G6 passed) stays correctly absent.

View-only change — no table rebuild, no data touched, reversible by re-running
db_init.py. Idempotent: DROP VIEW IF EXISTS then CREATE.
Run: python db/migrations/017_dedupe_gate_pipeline_view.py
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parents[1] / "db" / "research.db"

NEW_VIEW = """
CREATE VIEW gate_pipeline AS
WITH latest AS (
    SELECT idea_id, gate_number, MAX(attempt) AS max_attempt
    FROM step3_gates
    GROUP BY idea_id, gate_number
)
SELECT
    i.idea_id,
    i.name,
    g.gate_number,
    g.attempt,
    g.status        AS gate_status,
    g.gate_question,
    CAST((julianday('now') - julianday(g.updated_at)) AS INTEGER)
                    AS days_since_activity
FROM step1_ideas i
JOIN step3_gates g ON g.idea_id = i.idea_id
JOIN latest l ON l.idea_id = g.idea_id
             AND l.gate_number = g.gate_number
             AND l.max_attempt = g.attempt
WHERE g.status IN ('open','blocked')
  AND i.status NOT IN ('killed','graduated')
ORDER BY days_since_activity DESC;
"""


def run():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    before = cur.execute(
        "SELECT idea_id, gate_number, attempt, gate_status FROM gate_pipeline"
    ).fetchall()
    print(f"  before: {len(before)} row(s) -> {before}")

    cur.execute("DROP VIEW IF EXISTS gate_pipeline")
    cur.execute(NEW_VIEW)
    conn.commit()

    after = cur.execute(
        "SELECT idea_id, gate_number, attempt, gate_status FROM gate_pipeline"
    ).fetchall()
    print(f"  after : {len(after)} row(s) -> {after}")

    # Sanity: every surfaced row must be the MAX attempt for its (idea, gate).
    bad = cur.execute("""
        SELECT gp.idea_id, gp.gate_number, gp.attempt
        FROM gate_pipeline gp
        JOIN (SELECT idea_id, gate_number, MAX(attempt) m
              FROM step3_gates GROUP BY idea_id, gate_number) l
          ON l.idea_id = gp.idea_id AND l.gate_number = gp.gate_number
        WHERE gp.attempt != l.m
    """).fetchall()
    ok = not bad
    print(f"[017] gate_pipeline rebuilt {'OK' if ok else '*** FAILED'} — "
          f"stale non-latest attempts removed (bad={bad}).")
    conn.close()
    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    run()
