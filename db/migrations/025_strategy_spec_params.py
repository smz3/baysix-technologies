"""
Migration 025 — add params_json to log_strategy (task 57, strategy-spec workflow).

One new column. log_strategy already carries the verdict-tagged spine of how a
strategy changed (component/from/to/verdict). What it could NOT carry was the
*structured knobs* behind each value — e.g. exit="trail_1R" with no record of the
trail distance, breakeven trigger, etc. params_json closes that: a JSON blob of
the component's knobs, attached to the row that introduces a value. This is what
get_spec() assembles into a per-component spec card.

No table rebuild, no DB reset — just ALTER TABLE ADD COLUMN (NULL for all existing
rows; backfilled selectively for ORB-001 as the worked example). Idempotent.

Spec-birth (CLAUDE.md / research_protocol.md): the mandatory Gate-1 step now emits
one CREATED row per component, each carrying its proposed params_json.

Run: python db/migrations/025_strategy_spec_params.py
"""
import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parents[1] / "db" / "research.db"


def main():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cols = [r[1] for r in cur.execute("PRAGMA table_info(log_strategy)")]
    if "params_json" in cols:
        print("migration 025 already applied (params_json present) — no-op")
        conn.close()
        return

    cur.execute("ALTER TABLE log_strategy ADD COLUMN params_json TEXT")
    conn.commit()

    new_cols = [r[1] for r in cur.execute("PRAGMA table_info(log_strategy)")]
    n = cur.execute("SELECT COUNT(*) FROM log_strategy").fetchone()[0]
    print(f"  params_json in schema : {'params_json' in new_cols}")
    print(f"  rows (all NULL so far): {n}")
    assert "params_json" in new_cols, "ADD COLUMN failed"
    conn.close()
    print("migration 025 complete")


if __name__ == "__main__":
    main()
