"""
Migration 026 — add idea_kind + output_type to step1_ideas (Protocol 3.2 keystone).

Spec: docs/specs/2026-06-15-research-protocol-3.2-generic-gating.md

Two new declared-metadata columns that drive WHICH gate variant applies and WHICH
significance test is mandated — replacing the HMM-coded front half of the protocol.

  idea_kind   : strategy | primitive | overlay | classifier   (picks gate variant)
  output_type : pnl_stream | classifier_score | primitive_output (picks sig-test)

Both NULLable with a CHECK that admits NULL OR an enum member, so existing rows
stay valid; active ideas are backfilled separately (reviewable) by
026b_backfill_idea_kind.py. No table rebuild — ALTER TABLE ADD COLUMN. Idempotent.

Run: python db/migrations/026_idea_kind_output_type.py
"""
import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parents[1] / "db" / "research.db"

COLS = {
    "idea_kind": "TEXT CHECK (idea_kind IS NULL OR idea_kind IN "
                 "('strategy','primitive','overlay','classifier'))",
    "output_type": "TEXT CHECK (output_type IS NULL OR output_type IN "
                   "('pnl_stream','classifier_score','primitive_output'))",
}


def main():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    existing = {r[1] for r in cur.execute("PRAGMA table_info(step1_ideas)")}

    added = []
    for col, decl in COLS.items():
        if col in existing:
            print(f"  {col}: already present — skip")
            continue
        cur.execute(f"ALTER TABLE step1_ideas ADD COLUMN {col} {decl}")
        added.append(col)
    conn.commit()

    now = {r[1] for r in cur.execute("PRAGMA table_info(step1_ideas)")}
    for col in COLS:
        assert col in now, f"ADD COLUMN {col} failed"
    n = cur.execute("SELECT COUNT(*) FROM step1_ideas").fetchone()[0]
    conn.close()
    print(f"migration 026 complete — added {added or '(nothing, idempotent)'}; "
          f"{n} ideas, all NULL until backfill")


if __name__ == "__main__":
    main()
