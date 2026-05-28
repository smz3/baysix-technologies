"""
Migration 002 — Lock correct stage flow + metric_key vocabulary.

Changes:
- pipeline.current_stage CHECK: replace stale stages with locked flow
  (CAPTURED, HYPOTHESIS_SET, IS_SIGNAL, IS_BUILD, WALK_FORWARD, MONTE_CARLO, OOS, LIVE)
  Removes: IS_DEVELOPMENT, COST_CHECK, OOS_VALIDATION, PROMOTED, KILLED, PARKED
- pipeline_events.metric_key CHECK: rename IS_gross_tstat → IS_SIGNAL_tstat,
  IS_net_edge → IS_BUILD_net_edge
- Removes KILLED/PARKED from current_stage (they belong in stage_status column only)

Safe to re-run.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parents[1] / "db" / "research_log.db"

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

STAGE_MAP = {
    "IS_DEVELOPMENT":  "IS_SIGNAL",
    "OOS_VALIDATION":  "OOS",
    "PROMOTED":        "LIVE",
    "COST_CHECK":      "IS_BUILD",
    "KILLED":          "IS_SIGNAL",
    "PARKED":          "IS_SIGNAL",
}

METRIC_MAP = {
    "IS_gross_tstat": "IS_SIGNAL_tstat",
    "IS_net_edge":    "IS_BUILD_net_edge",
}


def rebuild_pipeline(cur):
    stage_check = ", ".join(f'"{s}"' for s in STAGES)

    cur.execute(f"""
        CREATE TABLE pipeline_new (
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

    cur.execute("SELECT * FROM pipeline")
    rows = cur.fetchall()
    cur.execute("PRAGMA table_info(pipeline)")
    cols = [c[1] for c in cur.fetchall()]

    for row in rows:
        data = dict(zip(cols, row))
        old_stage = data["current_stage"]
        data["current_stage"] = STAGE_MAP.get(old_stage, old_stage)
        if data["current_stage"] not in STAGES:
            data["current_stage"] = "CAPTURED"
        placeholders = ", ".join("?" for _ in cols)
        cur.execute(
            f"INSERT INTO pipeline_new ({', '.join(cols)}) VALUES ({placeholders})",
            [data[c] for c in cols]
        )
        if old_stage != data["current_stage"]:
            print(f"  idea_id={data['idea_id']}: {old_stage} → {data['current_stage']}")

    cur.execute("DROP TABLE pipeline")
    cur.execute("ALTER TABLE pipeline_new RENAME TO pipeline")
    print("  pipeline: stage CHECK constraint updated")


def rebuild_pipeline_events(cur):
    vocab_check = ", ".join(f"'{v}'" for v in METRIC_KEYS)

    cur.execute(f"""
        CREATE TABLE pipeline_events_new (
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
            metric_key        TEXT CHECK (metric_key IS NULL OR metric_key IN ({vocab_check})),
            metric_value      REAL,
            metric_unit       TEXT,
            test_type         TEXT,
            n_simulations     INTEGER,
            timestamp         DATETIME NOT NULL
        )
    """)

    cur.execute("SELECT * FROM pipeline_events")
    rows = cur.fetchall()
    cur.execute("PRAGMA table_info(pipeline_events)")
    cols = [c[1] for c in cur.fetchall()]

    for row in rows:
        data = dict(zip(cols, row))
        if data.get("metric_key") in METRIC_MAP:
            data["metric_key"] = METRIC_MAP[data["metric_key"]]
        placeholders = ", ".join("?" for _ in cols)
        cur.execute(
            f"INSERT INTO pipeline_events_new ({', '.join(cols)}) VALUES ({placeholders})",
            [data[c] for c in cols]
        )

    cur.execute("DROP TABLE pipeline_events")
    cur.execute("ALTER TABLE pipeline_events_new RENAME TO pipeline_events")
    print("  pipeline_events: metric_key vocab updated")


def main():
    print(f"Target DB: {DB_PATH}\n")
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = OFF")
    cur = conn.cursor()

    print("[1] Rebuilding pipeline table")
    rebuild_pipeline(cur)

    print("\n[2] Rebuilding pipeline_events table")
    rebuild_pipeline_events(cur)

    conn.commit()
    conn.execute("PRAGMA foreign_keys = ON")
    conn.close()
    print("\nMigration 002 complete.")


if __name__ == "__main__":
    main()
