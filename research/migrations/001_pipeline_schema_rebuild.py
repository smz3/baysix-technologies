"""
Migration 001 — Rebuild pipeline + pipeline_events to locked schema.
Run once. Safe to re-run (checks for existing columns before altering).
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parents[1] / "db" / "research_log.db"

METRIC_KEY_VOCAB = (
    "IS_gross_tstat",
    "IS_net_edge",
    "WF_sharpe",
    "OOS_tstat",
    "MC_bootstrap_percentile",
    "MC_shuffle_pvalue",
    "MC_synthetic_percentile",
)


def get_columns(cur, table):
    cur.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cur.fetchall()}


def migrate_pipeline(cur):
    existing = get_columns(cur, "pipeline")
    new_cols = {
        "asset_class":        "TEXT",
        "venue":              "TEXT",
        "approach":           "TEXT",
        "stage_status":       "TEXT NOT NULL DEFAULT 'active'",
        "kill_reason":        "TEXT",
        "gross_metric":       "REAL",
        "net_metric":         "REAL",
        "data_fingerprint":   "TEXT",
        "cost_model_version": "TEXT",
    }
    for col, typedef in new_cols.items():
        if col not in existing:
            cur.execute(f"ALTER TABLE pipeline ADD COLUMN {col} {typedef}")
            print(f"  pipeline: +{col}")


def rebuild_pipeline_events(cur):
    vocab_check = ", ".join(f"'{v}'" for v in METRIC_KEY_VOCAB)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS pipeline_events_new (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            idea_id          INTEGER NOT NULL,
            event_type       TEXT    NOT NULL,
            from_stage       TEXT,
            to_stage         TEXT,
            triggered_by     TEXT    NOT NULL,
            validate_question TEXT,
            validate_summary  TEXT,
            validate_outcome  TEXT,
            reason           TEXT,
            metric_key       TEXT CHECK (metric_key IS NULL OR metric_key IN ({vocab})),
            metric_value     REAL,
            metric_unit      TEXT,
            test_type        TEXT,
            n_simulations    INTEGER,
            timestamp        DATETIME NOT NULL
        )
    """.format(vocab=vocab_check))

    cur.execute("""
        INSERT INTO pipeline_events_new
            (id, idea_id, event_type, from_stage, to_stage, triggered_by,
             validate_question, validate_summary, validate_outcome, reason, timestamp)
        SELECT
            id, idea_id, event_type, from_stage, to_stage, triggered_by,
            validate_question, validate_summary, validate_outcome, reason, timestamp
        FROM pipeline_events
    """)

    cur.execute("DROP TABLE pipeline_events")
    cur.execute("ALTER TABLE pipeline_events_new RENAME TO pipeline_events")
    print("  pipeline_events: rebuilt with metric_key CHECK + 5 new columns")


def patch_hmm001(cur):
    cur.execute("""
        UPDATE pipeline SET
            asset_class        = 'XAUUSD',
            venue              = 'just_markets_mt5',
            approach           = 'ml',
            stage_status       = 'active',
            data_fingerprint   = 'CS-GOLD-DUKAS-TICK-IS-2016-20240502',
            cost_model_version = 'TCM-001'
        WHERE idea_id = 1
    """)
    print(f"  HMM-001 (idea_id=1): new columns populated ({cur.rowcount} row updated)")


def main():
    print(f"Target DB: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()

    print("\n[1] pipeline — adding columns")
    migrate_pipeline(cur)

    print("\n[2] pipeline_events — rebuilding with CHECK constraint")
    existing_pe = get_columns(cur, "pipeline_events")
    if "metric_key" not in existing_pe:
        rebuild_pipeline_events(cur)
    else:
        print("  already rebuilt — skipping")

    print("\n[3] HMM-001 — patching new columns")
    patch_hmm001(cur)

    conn.commit()
    conn.close()
    print("\nMigration 001 complete.")


if __name__ == "__main__":
    main()
