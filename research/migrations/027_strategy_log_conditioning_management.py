"""
Migration 027 — widen log_strategy.component CHECK for Protocol 3.2 (task 81).

Adds two first-class spec components born at Gate 1:
  conditioning = the regime/state giving the CONDITIONAL edge (Gate 3 tests it)
  management   = trade management (trail / partial / breakeven / time-stop)

SQLite can't ALTER a CHECK constraint, so this rebuilds the table (rename → create
with the wider CHECK → copy → drop old → recreate index). FK + verdict/decided_by
checks preserved verbatim. Idempotent: skips if 'conditioning' already admitted.

Run: python research/migrations/027_strategy_log_conditioning_management.py
"""
import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parents[1] / "db" / "research.db"

NEW_TABLE = """
CREATE TABLE log_strategy (
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
)
"""

COLS = ("log_id, idea_id, event, component, from_value, to_value, verdict, "
        "rationale, result_id, git_sha, decided_by, created_at, params_json")


def main():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    sql = cur.execute(
        "SELECT sql FROM sqlite_master WHERE name='log_strategy'"
    ).fetchone()[0]
    if "conditioning" in sql:
        print("migration 027: already widened — skip")
        conn.close()
        return

    n_before = cur.execute("SELECT COUNT(*) FROM log_strategy").fetchone()[0]
    cur.execute("PRAGMA foreign_keys = OFF")
    cur.executescript(f"""
        BEGIN;
        ALTER TABLE log_strategy RENAME TO log_strategy_old;
        {NEW_TABLE};
        INSERT INTO log_strategy ({COLS}) SELECT {COLS} FROM log_strategy_old;
        DROP TABLE log_strategy_old;
        CREATE INDEX idx_strategy_log_idea ON log_strategy(idea_id);
        COMMIT;
    """)
    cur.execute("PRAGMA foreign_key_check")
    bad = cur.fetchall()
    assert not bad, f"FK check failed after rebuild: {bad}"
    n_after = cur.execute("SELECT COUNT(*) FROM log_strategy").fetchone()[0]
    assert n_after == n_before, f"row count changed {n_before}->{n_after}"
    conn.commit()
    conn.close()
    print(f"migration 027 complete — component CHECK widened "
          f"(+conditioning +management); {n_after} rows preserved")


if __name__ == "__main__":
    main()
