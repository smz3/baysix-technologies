"""
Migration 011 — Migrate ideas + papers into research.db

Reads from:
  research/db/ideas_log.db  → step1_ideas
  research/db/agent_log.db  → step2_papers

Status mapping (old → new):
  inbox    → ideation
  promoted → ideation
  parked   → ideation
  dropped  → killed

parent_idea_id: old schema stored INTEGER FK → mapped to idea code (TEXT).

Run AFTER migration 010.
Run: python research/migrations/011_migrate_data.py
"""

import sqlite3
from pathlib import Path

BASE        = Path(__file__).parents[1]
IDEAS_DB    = BASE / "db" / "ideas_log.db"
AGENT_DB    = BASE / "db" / "agent_log.db"
RESEARCH_DB = BASE / "db" / "research.db"

STATUS_MAP = {
    "inbox":    "ideation",
    "promoted": "ideation",
    "parked":   "ideation",
    "dropped":  "killed",
}


def migrate_ideas(src_conn, dst_conn):
    rows = src_conn.execute(
        "SELECT id, code, name, parent_idea_id, category, status, created_at, notes FROM ideas ORDER BY id"
    ).fetchall()

    # Build id → code map for parent resolution
    id_to_code = {r[0]: r[1] for r in rows}

    inserted = 0
    for r in rows:
        old_id, code, name, parent_int, category, old_status, created_at, notes = r

        parent_code = id_to_code.get(parent_int) if parent_int else None
        new_status  = STATUS_MAP.get(old_status, "ideation")
        kill_gate   = None
        kill_reason = None
        killed_at   = None

        if new_status == "killed":
            kill_reason = "migrated from dropped status"

        dst_conn.execute("""
            INSERT OR IGNORE INTO step1_ideas
                (idea_id, name, description, category, parent_idea_id,
                 status, kill_gate, kill_reason, killed_at, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            code, name, notes, category, parent_code,
            new_status, kill_gate, kill_reason, killed_at,
            created_at or "2026-01-01 00:00:00",
            created_at or "2026-01-01 00:00:00",
        ))
        inserted += 1

    dst_conn.commit()
    print(f"step1_ideas: {inserted} rows migrated")


def migrate_papers(src_conn, dst_conn):
    rows = src_conn.execute("""
        SELECT p.id, a.idea_code, p.title, p.url, p.source,
               p.dissected, p.key_equations, p.empirical_findings,
               p.context_fit, p.limitations, p.timestamp
        FROM papers_consulted p
        LEFT JOIN agent_calls a ON p.agent_call_id = a.id
        ORDER BY p.id
    """).fetchall()

    inserted = 0
    for r in rows:
        (old_id, idea_code, title, url, source,
         dissected, key_eq, emp_find, ctx_fit, limits, timestamp) = r

        if not idea_code:
            print(f"  WARNING: paper_id={old_id} has no idea_code — skipping")
            continue

        dissected_at = timestamp if dissected else None

        dst_conn.execute("""
            INSERT OR IGNORE INTO step2_papers
                (idea_id, title, url, source, dissected,
                 key_equations, empirical_findings, context_fit, limitations,
                 added_at, dissected_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            idea_code, title, url, source, dissected,
            key_eq, emp_find, ctx_fit, limits,
            timestamp or "2026-01-01 00:00:00",
            dissected_at,
        ))
        inserted += 1

    dst_conn.commit()
    print(f"step2_papers: {inserted} rows migrated")


def verify(dst_conn):
    ideas  = dst_conn.execute("SELECT COUNT(*) FROM step1_ideas").fetchone()[0]
    papers = dst_conn.execute("SELECT COUNT(*) FROM step2_papers").fetchone()[0]
    diss   = dst_conn.execute("SELECT COUNT(*) FROM step2_papers WHERE dissected=1").fetchone()[0]
    print(f"\nVerification:")
    print(f"  step1_ideas  : {ideas} rows")
    print(f"  step2_papers : {papers} rows ({diss} dissected)")

    print("\nSample ideas:")
    for r in dst_conn.execute("SELECT idea_id, name, status, parent_idea_id FROM step1_ideas LIMIT 5").fetchall():
        print(f"  {r}")

    print("\nPapers:")
    for r in dst_conn.execute("SELECT paper_id, idea_id, title[:50], dissected FROM step2_papers").fetchall():
        print(f"  {r}")


def run():
    src_ideas = sqlite3.connect(IDEAS_DB)
    src_agent = sqlite3.connect(AGENT_DB)
    dst       = sqlite3.connect(RESEARCH_DB)
    dst.execute("PRAGMA foreign_keys = ON")

    print("Migrating ideas...")
    migrate_ideas(src_ideas, dst)

    print("Migrating papers...")
    migrate_papers(src_agent, dst)

    verify(dst)

    src_ideas.close()
    src_agent.close()
    dst.close()
    print("\nMigration 011 complete.")


if __name__ == "__main__":
    run()
