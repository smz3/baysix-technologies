"""
Migration 012 — Create step7_strategy_log

The strategy evolution log: the lineage of each strategy/idea — birth -> every
tested variant (kept or cut) -> current live config. Distinct from step5_agent_log
(activity feed, prose) — this is the structured, verdict-tagged spine of how a
strategy changed, with each row pointing at its evidence in step4_results.

  verdict  : CREATED | VALIDATED | PROPOSED | ADOPTED | REJECTED | FALSIFIED | SUPERSEDED
  component: exit | anchor | sizing | entry | filter | config | NULL (birth)
  live config = latest row per (idea, component) with verdict IN (VALIDATED, ADOPTED)

Safe to re-run — CREATE TABLE/INDEX IF NOT EXISTS.
Run: python research/migrations/012_create_strategy_log.py
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parents[1] / "db" / "research.db"


def run():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS step7_strategy_log (
            log_id      INTEGER PRIMARY KEY AUTOINCREMENT,
            idea_id     TEXT NOT NULL REFERENCES step1_ideas(idea_id),
            event       TEXT NOT NULL,
            component   TEXT,
            from_value  TEXT,
            to_value    TEXT,
            verdict     TEXT NOT NULL,
            rationale   TEXT,
            result_id   INTEGER REFERENCES step4_results(result_id),
            git_sha     TEXT,
            decided_by  TEXT NOT NULL DEFAULT 'human',
            created_at  DATETIME NOT NULL,
            CHECK (verdict IN ('CREATED','VALIDATED','PROPOSED','ADOPTED',
                               'REJECTED','FALSIFIED','SUPERSEDED')),
            CHECK (component IN ('exit','anchor','sizing','entry','filter','config')
                   OR component IS NULL),
            CHECK (decided_by IN ('human','agent'))
        );

        CREATE INDEX IF NOT EXISTS idx_strategy_log_idea
            ON step7_strategy_log(idea_id, created_at);
    """)
    conn.commit()
    n = cur.execute("SELECT COUNT(*) FROM step7_strategy_log").fetchone()[0]
    print(f"[012] step7_strategy_log ready ({n} rows).")
    conn.close()


if __name__ == "__main__":
    run()
