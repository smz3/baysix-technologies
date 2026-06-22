"""
Initialises research.db from scratch on the **Protocol 4.0 lean schema**.
Safe to re-run — CREATE TABLE/VIEW IF NOT EXISTS throughout.

4.0 vs 3.2/3.3 (see docs/specs/2026-06-22-protocol-4.0-lean-gates.md):
  - 4 gates (G1 Premise / G2 Edge+Survival / G3 Robustness / G4 Live) — step3_gates
    CHECK(gate_number BETWEEN 1 AND 4).
  - DROPPED: trial_family table + the 3.3 result columns (n_trials, trial_family_id,
    config_hash, cost_bps, cost_basis) — DSR/PSR/N_trials machinery removed.
  - ADDED: step4_results.is_run (+ .what_changed) — per-idea IS run numbering (the only
    deflator kept: counts shots taken before G3). Collapsed into step4_results in
    migration 029 — the separate is_runs registry was dropped (count via DISTINCT is_run).
  - tester tables (tester_runs / tester_trades / tester_zones) folded in here (were
    migrations 021/022/030/031) — the MT5 emit ledger is load-bearing in 4.0.

Run: python research/code/infra/db_init.py
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
            -- declared metadata (4.0 tags these at G1): idea_kind picks the gate
            -- variant, output_type names what the idea emits.
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

        -- 4.0: four gates. G1 Premise / G2 Edge+Survival / G3 Robustness / G4 Live.
        CREATE TABLE IF NOT EXISTS step3_gates (
            gate_id       INTEGER PRIMARY KEY AUTOINCREMENT,
            idea_id       TEXT NOT NULL REFERENCES step1_ideas(idea_id),
            gate_number   INTEGER NOT NULL CHECK(gate_number BETWEEN 1 AND 4),
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
            is_run          TEXT,                   -- 4.0 IS run label (IS-01, IS-02…); count shots via DISTINCT is_run
            what_changed    TEXT,                   -- what was swept on this IS run (was is_runs.what_changed)
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
            params_json TEXT,
            CHECK (verdict IN ('CREATED','VALIDATED','PROPOSED','ADOPTED',
                               'REJECTED','FALSIFIED','SUPERSEDED')),
            CHECK (component IN ('exit','anchor','sizing','entry','filter','config',
                                 'conditioning','management')
                   OR component IS NULL),
            CHECK (decided_by IN ('human','agent'))
        );

        CREATE INDEX IF NOT EXISTS idx_strategy_log_idea
            ON log_strategy(idea_id, created_at);

        -- ── MT5 tester ledger (folded in from migrations 021/022/030/031) ──────
        -- The EA emits this inside the Strategy Tester (causal, bar-by-bar). 4.0's
        -- G2 edge read + G4 live parity both consume it. Python only analyses.
        CREATE TABLE IF NOT EXISTS tester_runs (
            run_id          INTEGER PRIMARY KEY AUTOINCREMENT,
            idea_id         TEXT NOT NULL,                 -- soft FK into step1_ideas
            ea_name         TEXT,
            ea_version      TEXT,
            symbol          TEXT NOT NULL,
            data_source     TEXT NOT NULL CHECK(data_source IN
                               ('dukascopy','broker_history','custom')),
            model_quality   TEXT,
            tester_model    TEXT CHECK(tester_model IS NULL OR tester_model IN
                               ('real_ticks','every_tick','1min_ohlc','open_only')),
            timeframe       TEXT,
            period_start    DATE,
            period_end      DATE,
            tz_offset_hours INTEGER,
            magic_number    INTEGER,
            initial_deposit REAL,
            leverage        INTEGER,
            spread_setting  TEXT,
            params          TEXT CHECK(params IS NULL OR json_valid(params)),
            n_trades        INTEGER,
            net_profit_usd  REAL,
            profit_factor   REAL,
            max_dd_pct      REAL,
            win_rate        REAL,
            -- demo/live parity diff vs research (4.0 G4; fills via tester.log_fidelity_diff)
            research_result_id   INTEGER,
            trade_overlap_pct    REAL,
            ER_delta_vs_research REAL,
            R_corr               REAL,
            fidelity_verdict     TEXT CHECK(fidelity_verdict IS NULL OR
                                    fidelity_verdict IN ('pass','fail','pending')),
            notes           TEXT,
            created_at      DATETIME NOT NULL,
            updated_at      DATETIME NOT NULL
        );

        CREATE TABLE IF NOT EXISTS tester_trades (
            tt_id            INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id           INTEGER NOT NULL REFERENCES tester_runs(run_id),
            ticket           INTEGER,
            session_date     DATE,
            direction        TEXT CHECK(direction IS NULL OR direction IN ('long','short','flat')),
            entry_ts         DATETIME,
            entry_px         REAL,
            exit_ts          DATETIME,
            exit_px          REAL,
            exit_reason      TEXT,
            lots             REAL,
            risk_unit        REAL,
            realized_R       REAL,
            realized_pnl_usd REAL,
            meta             TEXT CHECK(meta IS NULL OR json_valid(meta)),
            created_at       DATETIME NOT NULL
        );

        CREATE TABLE IF NOT EXISTS tester_zones (
            tz_id             INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id            INTEGER NOT NULL REFERENCES tester_runs(run_id),
            csv_zone_id       INTEGER,
            tf                TEXT NOT NULL,
            direction         TEXT CHECK(direction IN ('BUY','SELL')),
            p1_time DATETIME, p1_price REAL,
            p2_time DATETIME, p2_price REAL,
            p3_time DATETIME, p3_price REAL,
            p4_time DATETIME, p4_price REAL,
            p5_time DATETIME, p5_price REAL,
            l1 REAL, l2 REAL, mid REAL,
            break_kind        TEXT CHECK(break_kind IS NULL OR break_kind IN ('sequential','same_bar')),
            t1_time DATETIME, t2_time DATETIME, t3_time DATETIME,
            confirm_time      DATETIME,
            invalidation_time DATETIME,
            alive_at_end      INTEGER,
            continued         INTEGER,
            mfe_r REAL, mae_r REAL, realized_r REAL,
            bars_alive        INTEGER,
            created_at        DATETIME NOT NULL,
            seq INTEGER, zone_key TEXT, is_primary INTEGER, consolidated_into TEXT
        );
        CREATE INDEX IF NOT EXISTS ix_tester_trades_run    ON tester_trades(run_id);
        CREATE INDEX IF NOT EXISTS ix_tester_trades_run_ts ON tester_trades(run_id, entry_ts);
        CREATE INDEX IF NOT EXISTS ix_tester_zones_run     ON tester_zones(run_id);
        CREATE INDEX IF NOT EXISTS ix_tester_zones_run_tf  ON tester_zones(run_id, tf);
        CREATE INDEX IF NOT EXISTS ix_tester_zones_confirm ON tester_zones(run_id, confirm_time);

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
    print(f"research.db ready (Protocol 4.0 lean schema) -> {DB_PATH}")


if __name__ == "__main__":
    init()
