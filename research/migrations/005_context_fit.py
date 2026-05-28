"""
Migration 005 — papers_consulted schema cleanup.

Changes:
  1. Rename xauusd_translation → context_fit (asset-agnostic, covers XAUUSD/GC/equities/ETFs)
  2. Drop baysix_applicability (redundant — applicability score lives inside context_fit block)
"""

import sqlite3
from pathlib import Path

DB = Path(__file__).parents[1] / "db" / "agent_log.db"


def up():
    conn = sqlite3.connect(DB)

    # context_fit already exists (table was created with this name before migration 004)
    # Just drop the redundant baysix_applicability column
    conn.execute("ALTER TABLE papers_consulted DROP COLUMN baysix_applicability")
    print("Dropped baysix_applicability.")

    conn.commit()

    print("\n--- papers_consulted schema ---")
    for row in conn.execute("PRAGMA table_info(papers_consulted)"):
        print(f"  {row[1]:25s}  {row[2]}")

    conn.close()
    print("\nMigration 005 complete.")


if __name__ == "__main__":
    up()
