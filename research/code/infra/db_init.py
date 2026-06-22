"""
Initialises research.db from scratch.
Safe to re-run — CREATE TABLE/VIEW IF NOT EXISTS throughout.
For first-time setup with data migration, run migrations 010 + 011 instead.

Run: python research/code/db_init.py
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parents[2] / "db" / "research.db"


def init():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()

    cur.executescript("""
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
            -- Protocol 3.2 declared metadata (migration 026): idea_kind picks the
            -- gate variant, output_type picks the mandated Gate-5 significance test.
            idea_kind      TEXT CHECK (idea_kind IS NULL OR idea_kind IN
                           ('strategy','primitive','overlay','classifier')),
            output_type    TEXT CHECK (output_type IS NULL OR output_type IN
                           ('pnl_stream','classifier_score','primitive_output')),
            created_at     DATETIME NOT NULL,
            updated_at     DATETIME NOT NULL
        );

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

        CREATE TABLE IF NOT EXISTS step3_gates (
            gate_id       INTEGER PRIMARY KEY AUTOINCREMENT,
            idea_id       TEXT NOT NULL REFERENCES step1_ideas(idea_id),
            gate_number   INTEGER NOT NULL CHECK(gate_number BETWEEN 0 AND 7),
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

        CREATE TABLE IF NOT EXISTS step4_results (
            result_id       INTEGER PRIMARY KEY AUTOINCREMENT,
            idea_id         TEXT NOT NULL REFERENCES step1_ideas(idea_id),
            gate_number     INTEGER NOT NULL,
            stage           TEXT NOT NULL
                            CHECK(stage IN ('IS','walkforward','montecarlo','OOS')),
            metric_key      TEXT NOT NULL,
            metric_value    REAL NOT NULL,
            cost_adjusted   INTEGER NOT NULL DEFAULT 0
                            CHECK(cost_adjusted IN (0,1)),
            period          TEXT CHECK(period IN ('per_trade','daily','annualised')),
            n_obs           INTEGER,
            n_trials        INTEGER,
            trial_family_id TEXT,                   -- FK-ish to trial_family (migration 028)
            config_hash     TEXT,                   -- identifies a swept config (migration 028)
            cost_bps        REAL,                   -- measured cost in bps (AQR, migration 028)
            cost_basis      TEXT,                   -- 'measured'|'modeled' (migration 028)
            instrument      TEXT NOT NULL DEFAULT 'XAUUSD',
            data_start      DATE,
            data_end        DATE,
            parameters      TEXT,
            git_sha         TEXT,
            data_hash       TEXT,
            seed            INTEGER,
            code_path       TEXT,
            notes           TEXT,
            logged_at       DATETIME NOT NULL
        );

        -- N_trials ledger (migration 028, task 96). One row per selection
        -- decision: n_configs = N, var_sr = V[SR_n] for the deflated Sharpe.
        -- Scope is PER-IDEA — never pooled across strategies.
        CREATE TABLE IF NOT EXISTS trial_family (
            family_id            TEXT PRIMARY KEY,
            idea_id              TEXT NOT NULL REFERENCES step1_ideas(idea_id),
            description          TEXT,
            n_configs            INTEGER NOT NULL DEFAULT 0,
            var_sr               REAL,
            selected_config_hash TEXT,
            data_start           DATE,
            data_end             DATE,
            created_at           DATETIME NOT NULL,
            updated_at           DATETIME NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_trial_family_idea
            ON trial_family(idea_id, created_at);

        CREATE TABLE IF NOT EXISTS log_agent (
            call_id        INTEGER PRIMARY KEY AUTOINCREMENT,
            idea_id        TEXT NOT NULL REFERENCES step1_ideas(idea_id),
            gate_number    INTEGER,
            gear           TEXT NOT NULL
                           CHECK(gear IN ('GENERATE','DISSECT','VALIDATE')),
            model          TEXT CHECK(model IN ('sonnet','opus')),
            source         TEXT NOT NULL DEFAULT 'agent'
                           CHECK(source IN ('agent','human')),
            task_summary   TEXT,
            output_summary TEXT,
            paper_id       INTEGER REFERENCES step2_papers(paper_id),
            result_id      INTEGER REFERENCES step4_results(result_id),
            created_at     DATETIME NOT NULL
        );

        CREATE TABLE IF NOT EXISTS log_tasks (
            task_id     INTEGER PRIMARY KEY AUTOINCREMENT,
            idea_id     TEXT REFERENCES step1_ideas(idea_id),
            status      TEXT NOT NULL DEFAULT 'open'
                          CHECK(status IN ('open','in_progress','done','dropped','parked')),
            title       TEXT NOT NULL,
            detail      TEXT,
            kind        TEXT NOT NULL CHECK(kind IN
                          ('variant','sizing','filter','port','infra','data','cleanup')),
            priority    TEXT NOT NULL DEFAULT 'P2'
                          CHECK(priority IN ('P0','P1','P2')),
            created_at  DATETIME NOT NULL,
            updated_at  DATETIME NOT NULL,
            resolved_at DATETIME,
            resolution  TEXT
        );

        CREATE TABLE IF NOT EXISTS log_strategy (
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
            params_json TEXT,                       -- structured knobs (migration 025)
            CHECK (verdict IN ('CREATED','VALIDATED','PROPOSED','ADOPTED',
                               'REJECTED','FALSIFIED','SUPERSEDED')),
            CHECK (component IN ('exit','anchor','sizing','entry','filter','config',
                                 'conditioning','management')
                   OR component IS NULL),
            CHECK (decided_by IN ('human','agent'))
        );

        CREATE INDEX IF NOT EXISTS idx_strategy_log_idea
            ON log_strategy(idea_id, created_at);

        DROP VIEW IF EXISTS open_backlog;
        CREATE VIEW open_backlog AS
        SELECT b.task_id, b.idea_id, i.name AS idea_name, b.status, b.title,
               b.kind, b.priority,
               CAST((julianday('now') - julianday(b.created_at)) AS INTEGER) AS age_days
        FROM log_tasks b
        LEFT JOIN step1_ideas i ON i.idea_id = b.idea_id
        WHERE b.status IN ('open','in_progress')
        ORDER BY b.priority ASC, b.created_at ASC;

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

        DROP VIEW IF EXISTS gate_pipeline;
        CREATE VIEW gate_pipeline AS
        -- Dedupe to the LATEST attempt per (idea, gate) BEFORE filtering, so a gate
        -- later passed on a retry no longer surfaces its stale blocked attempts
        -- (task 23 — HMM-001 G2/G4 false-blocked). See migration 017.
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
    print(f"research.db ready -> {DB_PATH}")


if __name__ == "__main__":
    init()
