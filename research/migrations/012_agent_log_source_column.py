"""
Migration 012 — Add source column to step5_agent_log.

Changes:
  - model: NOT NULL → nullable (human decisions have no model)
  - source: new column TEXT NOT NULL DEFAULT 'agent' CHECK IN ('agent','human')

Recreates table (SQLite cannot ALTER column constraints in-place).
Existing rows get source='agent'.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parents[1] / "db" / "research.db"


def run():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = OFF")

    conn.executescript("""
        CREATE TABLE step5_agent_log_new (
            call_id        INTEGER PRIMARY KEY AUTOINCREMENT,
            idea_id        TEXT NOT NULL REFERENCES step1_ideas(idea_id),
            gate_number    INTEGER,
            gear           TEXT NOT NULL CHECK(gear IN ('GENERATE','DISSECT','VALIDATE')),
            model          TEXT CHECK(model IN ('sonnet','opus')),
            source         TEXT NOT NULL DEFAULT 'agent'
                           CHECK(source IN ('agent','human')),
            task_summary   TEXT,
            output_summary TEXT,
            paper_id       INTEGER REFERENCES step2_papers(paper_id),
            result_id      INTEGER REFERENCES step4_results(result_id),
            created_at     DATETIME NOT NULL
        );

        INSERT INTO step5_agent_log_new
            (call_id, idea_id, gate_number, gear, model, source,
             task_summary, output_summary, paper_id, result_id, created_at)
        SELECT
            call_id, idea_id, gate_number, gear, model, 'agent',
            task_summary, output_summary, paper_id, result_id, created_at
        FROM step5_agent_log;

        DROP TABLE step5_agent_log;
        ALTER TABLE step5_agent_log_new RENAME TO step5_agent_log;
    """)

    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()
    conn.close()
    print("Migration 012 complete — source column added to step5_agent_log.")


if __name__ == "__main__":
    run()
