"""
Migration 022 — Gate 7 (FIDELITY) in research.db.

Two changes, both additive / data-preserving:
  1. Create tester_runs + tester_trades (canonical schema in research.code.tester).
     These hold the MT5 Strategy-Tester evidence — the LAST research gate, not a
     separate DB. (The misplaced copies in execution.db are dropped in migration 023.)
  2. Widen step3_gates.gate_number CHECK from BETWEEN 0 AND 6 to BETWEEN 0 AND 7,
     so Gate 7 rows can exist. SQLite can't ALTER a CHECK, so this is the standard
     table-rebuild (new table -> copy rows -> drop -> rename). Views reference the
     table by name and keep working; no FK points at step3_gates.

Spec: braindump/execution_schema.md + braindump/research_protocol.md (Gate 7).
Run: python research/migrations/022_gate7_tester_schema.py
"""
import sys
import sqlite3
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from research.code import tester

DB = Path(__file__).resolve().parents[1] / "db" / "research.db"

_NEW_GATES = """
CREATE TABLE step3_gates_new (
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
"""


def widen_gate_check():
    conn = sqlite3.connect(DB)
    sql = conn.execute(
        "SELECT sql FROM sqlite_master WHERE name='step3_gates'"
    ).fetchone()[0]
    if "BETWEEN 0 AND 7" in sql:
        print("step3_gates already admits gate 7 — skipping rebuild")
        conn.close()
        return
    if "BETWEEN 0 AND 6" not in sql:
        raise RuntimeError(f"unexpected step3_gates CHECK, refusing to rebuild:\n{sql}")
    before = conn.execute("SELECT COUNT(*) FROM step3_gates").fetchone()[0]
    conn.execute("PRAGMA foreign_keys = OFF")
    # legacy_alter_table: RENAME must NOT rewrite/validate the views (idea_lifecycle,
    # gate_pipeline) that reference step3_gates by name — they resolve at query time.
    conn.execute("PRAGMA legacy_alter_table = ON")
    conn.execute("DROP TABLE IF EXISTS step3_gates_new")
    conn.execute(_NEW_GATES)
    conn.execute("""
        INSERT INTO step3_gates_new
            (gate_id, idea_id, gate_number, attempt, gate_question, gate_answer,
             pass_criteria, status, answered_by, created_at, updated_at, answered_at)
        SELECT gate_id, idea_id, gate_number, attempt, gate_question, gate_answer,
               pass_criteria, status, answered_by, created_at, updated_at, answered_at
        FROM step3_gates
    """)
    conn.execute("DROP TABLE step3_gates")
    conn.execute("ALTER TABLE step3_gates_new RENAME TO step3_gates")
    conn.commit()
    after = conn.execute("SELECT COUNT(*) FROM step3_gates").fetchone()[0]
    fk = conn.execute("PRAGMA foreign_key_check").fetchall()
    conn.execute("PRAGMA foreign_keys = ON")
    conn.close()
    assert before == after, f"row count changed during rebuild: {before} -> {after}"
    assert not fk, f"FK violations after rebuild: {fk}"
    print(f"step3_gates rebuilt: gate_number now 0-7, {after} rows preserved, FK clean")


def main():
    tester.init_db()
    widen_gate_check()
    # report
    conn = sqlite3.connect(DB)
    for t in ("tester_runs", "tester_trades"):
        cols = [r[1] for r in conn.execute(f"PRAGMA table_info({t})")]
        print(f"  {t}: {len(cols)} cols")
    chk = conn.execute("SELECT sql FROM sqlite_master WHERE name='step3_gates'").fetchone()[0]
    print("  step3_gates CHECK:", "0 AND 7" in chk and "BETWEEN 0 AND 7" or "??")
    conn.close()
    print("migration 022 complete")


if __name__ == "__main__":
    main()
