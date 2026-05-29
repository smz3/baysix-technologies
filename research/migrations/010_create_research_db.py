"""
Migration 010 — Create research.db

Single unified DB replacing ideas_log.db + research_log.db + agent_log.db.
Safe to re-run — CREATE TABLE/VIEW IF NOT EXISTS throughout.

Run: python research/migrations/010_create_research_db.py
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parents[1] / "db" / "research.db"


def run():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()

    cur.executescript("""
        -- ── step1_ideas ─────────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS step1_ideas (
            idea_id        TEXT PRIMARY KEY,
            name           TEXT NOT NULL,
            description    TEXT,
            category       TEXT,
            parent_idea_id TEXT REFERENCES step1_ideas(idea_id)
                           CHECK(parent_idea_id != idea_id),
            status         TEXT NOT NULL DEFAULT 'ideation',
            kill_gate      INTEGER,
            kill_reason    TEXT,
            killed_at      DATETIME,
            created_at     DATETIME NOT NULL,
            updated_at     DATETIME NOT NULL
        );

        -- ── step2_papers ─────────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS step2_papers (
            paper_id           INTEGER PRIMARY KEY AUTOINCREMENT,
            idea_id            TEXT NOT NULL REFERENCES step1_ideas(idea_id),
            title              TEXT NOT NULL,
            authors            TEXT,
            year               INTEGER,
            source             TEXT,
            url                TEXT,
            doi                TEXT,
            local_path         TEXT,
            dissected          INTEGER NOT NULL DEFAULT 0,
            key_equations      TEXT,
            empirical_findings TEXT,
            context_fit        TEXT,
            limitations        TEXT,
            added_at           DATETIME NOT NULL,
            dissected_at       DATETIME
        );

        -- ── step3_gates ──────────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS step3_gates (
            gate_id       INTEGER PRIMARY KEY AUTOINCREMENT,
            idea_id       TEXT NOT NULL REFERENCES step1_ideas(idea_id),
            gate_number   INTEGER NOT NULL CHECK(gate_number BETWEEN 0 AND 6),
            attempt       INTEGER NOT NULL DEFAULT 1,
            gate_question TEXT,
            gate_answer   TEXT,
            pass_criteria TEXT,
            status        TEXT NOT NULL DEFAULT 'open'
                          CHECK(status IN ('open','passed','blocked','killed')),
            answered_by   TEXT,
            created_at    DATETIME NOT NULL,
            updated_at    DATETIME NOT NULL,
            answered_at   DATETIME,
            UNIQUE(idea_id, gate_number, attempt)
        );

        -- ── step4_results ────────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS step4_results (
            result_id      INTEGER PRIMARY KEY AUTOINCREMENT,
            idea_id        TEXT NOT NULL REFERENCES step1_ideas(idea_id),
            gate_number    INTEGER NOT NULL,
            stage          TEXT NOT NULL
                           CHECK(stage IN ('IS','walkforward','montecarlo','OOS')),
            metric_key     TEXT NOT NULL,
            metric_value   REAL NOT NULL,
            cost_adjusted  INTEGER NOT NULL DEFAULT 0
                           CHECK(cost_adjusted IN (0,1)),
            period         TEXT CHECK(period IN ('per_trade','daily','annualised')),
            n_obs          INTEGER,
            n_trials       INTEGER,
            trial_family_id TEXT,
            instrument     TEXT NOT NULL DEFAULT 'XAUUSD',
            data_start     DATE,
            data_end       DATE,
            parameters     TEXT,
            git_sha        TEXT,
            data_hash      TEXT,
            seed           INTEGER,
            code_path      TEXT,
            notes          TEXT,
            logged_at      DATETIME NOT NULL
        );

        -- ── step5_agent_log ──────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS step5_agent_log (
            call_id        INTEGER PRIMARY KEY AUTOINCREMENT,
            idea_id        TEXT NOT NULL REFERENCES step1_ideas(idea_id),
            gate_number    INTEGER,
            gear           TEXT NOT NULL
                           CHECK(gear IN ('GENERATE','DISSECT','VALIDATE')),
            model          TEXT NOT NULL CHECK(model IN ('sonnet','opus')),
            task_summary   TEXT,
            output_summary TEXT,
            paper_id       INTEGER REFERENCES step2_papers(paper_id),
            result_id      INTEGER REFERENCES step4_results(result_id),
            created_at     DATETIME NOT NULL
        );

        -- ── VIEW: idea_lifecycle ─────────────────────────────────────────────────
        DROP VIEW IF EXISTS idea_lifecycle;
        CREATE VIEW idea_lifecycle AS
        SELECT
            i.idea_id,
            i.name,
            i.category,
            i.parent_idea_id,
            i.status,
            COALESCE(p.papers_total, 0)     AS papers_total,
            COALESCE(p.papers_dissected, 0) AS papers_dissected,
            g.highest_gate_passed,
            i.kill_gate,
            i.kill_reason,
            i.created_at,
            i.updated_at
        FROM step1_ideas i
        LEFT JOIN (
            SELECT idea_id,
                   COUNT(*)       AS papers_total,
                   SUM(dissected) AS papers_dissected
            FROM step2_papers
            GROUP BY idea_id
        ) p ON p.idea_id = i.idea_id
        LEFT JOIN (
            SELECT idea_id,
                   MAX(gate_number) AS highest_gate_passed
            FROM step3_gates
            WHERE status = 'passed'
            GROUP BY idea_id
        ) g ON g.idea_id = i.idea_id;

        -- ── VIEW: gate_pipeline ──────────────────────────────────────────────────
        DROP VIEW IF EXISTS gate_pipeline;
        CREATE VIEW gate_pipeline AS
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
        WHERE g.status IN ('open','blocked')
          AND i.status NOT IN ('killed','graduated')
        ORDER BY days_since_activity DESC;

        -- ── VIEW: papers_queue ───────────────────────────────────────────────────
        DROP VIEW IF EXISTS papers_queue;
        CREATE VIEW papers_queue AS
        SELECT
            p.paper_id,
            p.idea_id,
            i.name  AS idea_name,
            p.title,
            p.authors,
            p.year,
            p.source,
            p.url,
            p.added_at
        FROM step2_papers p
        JOIN step1_ideas i ON i.idea_id = p.idea_id
        WHERE p.dissected = 0
          AND i.status NOT IN ('killed','graduated')
        ORDER BY p.added_at ASC;
    """)

    conn.commit()
    conn.close()
    print(f"research.db created -> {DB_PATH}")
    print("Tables: step1_ideas, step2_papers, step3_gates, step4_results, step5_agent_log")
    print("Views:  idea_lifecycle, gate_pipeline, papers_queue")


if __name__ == "__main__":
    run()
