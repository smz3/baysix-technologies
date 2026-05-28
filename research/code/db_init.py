"""
Creates ideas_log.db and research_log.db from scratch.
Run this to rebuild either DB if lost or corrupted.
Existing data is preserved — only creates tables that don't exist.
"""

import sqlite3
from pathlib import Path

RESEARCH_DIR = Path(__file__).parents[1]
DB_DIR       = RESEARCH_DIR / "db"
IDEAS_DB     = DB_DIR / "ideas_log.db"
RESEARCH_DB  = DB_DIR / "research_log.db"

STAGES = (
    "CAPTURED",
    "HYPOTHESIS_SET",
    "IS_SIGNAL",
    "IS_BUILD",
    "WALK_FORWARD",
    "MONTE_CARLO",
    "OOS",
    "LIVE",
)

METRIC_KEYS = (
    "IS_SIGNAL_tstat",
    "IS_BUILD_net_edge",
    "WF_sharpe",
    "MC_bootstrap_percentile",
    "MC_shuffle_pvalue",
    "MC_synthetic_percentile",
    "OOS_tstat",
)


def init_ideas_log():
    conn = sqlite3.connect(IDEAS_DB)
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS ideas (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            code           TEXT UNIQUE NOT NULL,
            name           TEXT NOT NULL,
            parent_idea_id INTEGER REFERENCES ideas(id),
            asset_class    TEXT,
            signal_type    TEXT,
            status         TEXT NOT NULL CHECK(status IN ('inbox','promoted','parked','dropped')),
            source         TEXT NOT NULL CHECK(source IN ('agent','human')),
            role           TEXT CHECK(role IN ('infrastructure','strategy')),
            category       TEXT,
            sort_order     INTEGER,
            created_at     DATETIME NOT NULL,
            notes          TEXT
        );

        CREATE TABLE IF NOT EXISTS generate_calls (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp      DATETIME NOT NULL,
            idea_id        INTEGER REFERENCES ideas(id),
            topic          TEXT,
            question       TEXT,
            output_summary TEXT,
            outcome        TEXT CHECK(outcome IN (
                               'ranked_families','dead_end',
                               'needs_more','framework_mapped'))
        );

        CREATE TABLE IF NOT EXISTS build_order (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            idea_code    TEXT NOT NULL,
            phase        TEXT NOT NULL CHECK(phase IN ('research','deployment','scale')),
            sequence     INTEGER NOT NULL,
            build_status TEXT NOT NULL DEFAULT 'not_started'
                         CHECK(build_status IN ('not_started','in_progress','done')),
            unlocks      TEXT,
            locked_at    TEXT NOT NULL,
            UNIQUE(phase, sequence)
        );
    """)

    conn.commit()
    conn.close()
    print(f"ideas_log.db initialised -> {IDEAS_DB}")


def init_research_log():
    stage_check  = ", ".join(f'"{s}"' for s in STAGES)
    metric_check = ", ".join(f"'{k}'" for k in METRIC_KEYS)

    conn = sqlite3.connect(RESEARCH_DB)
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()

    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS pipeline (
            idea_id            INTEGER PRIMARY KEY,
            current_stage      TEXT NOT NULL CHECK(current_stage IN ({stage_check})),
            hypothesis         TEXT,
            kill_condition     TEXT,
            created_at         DATETIME NOT NULL,
            updated_at         DATETIME NOT NULL,
            asset_class        TEXT,
            venue              TEXT,
            approach           TEXT,
            stage_status       TEXT NOT NULL DEFAULT 'active',
            kill_reason        TEXT,
            gross_metric       REAL,
            net_metric         REAL,
            data_fingerprint   TEXT,
            cost_model_version TEXT
        )
    """)

    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS pipeline_events (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            idea_id           INTEGER NOT NULL,
            event_type        TEXT    NOT NULL,
            from_stage        TEXT,
            to_stage          TEXT,
            triggered_by      TEXT    NOT NULL,
            validate_question TEXT,
            validate_summary  TEXT,
            validate_outcome  TEXT,
            reason            TEXT,
            metric_key        TEXT CHECK(metric_key IS NULL OR metric_key IN ({metric_check})),
            metric_value      REAL,
            metric_unit       TEXT,
            test_type         TEXT,
            n_simulations     INTEGER,
            timestamp         DATETIME NOT NULL
        )
    """)

    conn.commit()
    conn.close()
    print(f"research_log.db initialised -> {RESEARCH_DB}")


if __name__ == "__main__":
    init_ideas_log()
    init_research_log()
    print("Done.")
