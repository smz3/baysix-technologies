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
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # repo root for run-as-script
from research.code.infra.schema_ledger import SCHEMA_MT5, SCHEMA_GRW

# Runnable as a SCRIPT, so the repo root is not on sys.path and the package
# import below would fail with ModuleNotFoundError (caught 2026-08-16 when
# handover_lint broke this way right after the task 357 repointing).
import sys as _sys, pathlib as _pl
_REPO = _pl.Path(__file__).resolve().parents[3]
if str(_REPO) not in _sys.path:
    _sys.path.insert(0, str(_REPO))
from research.code.infra.db_path import DB_PATH  # noqa: F401  (task 357: one canonical path)
from research.code.infra import db_guard

GUARD_MESSAGE = (
    "raw write refused (CLAUDE.md rule 10) - open the connection through "
    "research/code/ (pipeline / strategy_log / backlog / agent_log / runs), or "
    "call db_guard.arm(conn) if you are a migration"
)


def init():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    # Creating the guard triggers below references baysix_writer() by name; arming
    # keeps the whole build on one connection that can also seed if it needs to.
    db_guard.arm(conn, reason="db_init bootstrap")
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
            -- NOT NULL since migration 044: log_result() has always required both,
            -- and a metric with no sample size or no commit cannot be sized or
            -- reproduced by a reader.
            n_obs           INTEGER NOT NULL,
            is_run          TEXT,                   -- 4.0 IS run label (IS-01, IS-02…); count shots via DISTINCT is_run
            what_changed    TEXT,                   -- what was swept on this IS run (was is_runs.what_changed)
            -- GRW-001 multiplicity ledger (task 289, migration 037). BOOKKEEPING ONLY —
            -- nothing auto-kills on these; the 3.3 DSR/PSR deflator machinery stays dropped.
            trial_family_id TEXT,                   -- trials compared for one decision; spans batches
            n_trials        INTEGER,                -- passes actually run to reach this result
            instrument      TEXT NOT NULL DEFAULT 'XAUUSD',
            data_start      DATE,
            data_end        DATE,
            parameters      TEXT,
            git_sha         TEXT NOT NULL,
            data_hash       TEXT,
            seed            INTEGER,
            code_path       TEXT,
            notes           TEXT,
            logged_at       DATETIME NOT NULL,
            -- migration 043 added the column, 044's rebuild made it a real FK.
            -- Nullable on purpose: rows can predate the registry, and inventing a
            -- run for them would be a fabricated owner.
            run_id          INTEGER REFERENCES runs(run_id)
        );

        -- The generic run registry (migration 042). `platform` is a COLUMN, not a
        -- table name: MT5, NinjaTrader and IBKR all file here, and a new strategy
        -- files a row rather than getting a migration.
        CREATE TABLE IF NOT EXISTS runs (
            run_id          INTEGER PRIMARY KEY,
            platform        TEXT NOT NULL
                              CHECK(platform IN ('MT5','NinjaTrader','IBKR')),
            idea_id         TEXT,
            stage           TEXT NOT NULL
                              CHECK(stage IN ('IS','OOS','WF','smoke')),
            symbol          TEXT NOT NULL,
            version         TEXT,
            data_start      DATE,
            data_end        DATE,
            git_sha         TEXT NOT NULL,
            output_dir      TEXT,
            trial_family_id TEXT,
            n_trials        INTEGER,
            notes           TEXT,
            created_at      DATETIME NOT NULL,
            FOREIGN KEY (idea_id) REFERENCES step1_ideas(idea_id)
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
            resolution  TEXT,
            -- CLAUDE.md rule 17 in the schema (migration 044). A typo'd stream mints
            -- a silent bucket, and rule 5's scoped search then misses those rows.
            stream      TEXT NOT NULL DEFAULT 'Research'
                          CHECK(stream IN ('MT5','NinjaTrader','IBKR','Research','Ops'))
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

    # Ledger DDL from the single source of truth (task 287): MT5 spine + FOB payload
    # + GRW factory. Never re-inline these here — a second copy is exactly what drifted.
    cur.executescript(SCHEMA_MT5)
    cur.executescript(SCHEMA_GRW)

    # The rule-10 write guard (migration 045). Built here too, so a database created
    # from scratch is born guarded instead of acquiring the rule four migrations
    # later — an unguarded fresh DB is exactly the copy a shortcut gets written to.
    for table in db_guard.GUARDED_TABLES:
        for op in ("INSERT", "UPDATE", "DELETE"):
            cur.execute(
                f"CREATE TRIGGER IF NOT EXISTS guard_{table}_{op.lower()} "
                f"BEFORE {op} ON {table} "
                f"WHEN {db_guard.GUARD_FN}() IS NOT 1 "
                f"BEGIN SELECT RAISE(ABORT, '{GUARD_MESSAGE}'); END"
            )

    # WAL (task 289): Loop C writes on a timer while Syafiq queries interactively, and
    # the default rollback journal takes an exclusive lock -> 'database is locked'.
    # journal_mode is persisted in the DB file, so this survives every reconnect.
    cur.execute("PRAGMA journal_mode=WAL")

    conn.commit()
    conn.close()
    print(f"baysix.db ready (Protocol 4.0 lean schema, guarded) -> {DB_PATH}")


if __name__ == "__main__":
    init()
