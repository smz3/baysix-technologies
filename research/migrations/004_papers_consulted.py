"""
Migration 004 — papers_consulted table + agent_calls cleanup.

Changes:
  1. Create papers_consulted table in agent_log.db — normalized paper storage
     with tiered confidence, XAUUSD translation block, and replication tracking.
  2. Migrate existing papers JSON from agent_calls rows into papers_consulted rows.
  3. Deduplicate agent_calls — keep id=1, delete id=2 (duplicate write from same call).
  4. Drop papers column from agent_calls (replaced by papers_consulted FK relationship).
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone

DB = Path(__file__).parents[1] / "db" / "agent_log.db"


def up():
    conn = sqlite3.connect(DB)

    # 1. Create papers_consulted table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS papers_consulted (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_call_id        INTEGER REFERENCES agent_calls(id),
            title                TEXT NOT NULL,
            url                  TEXT NOT NULL,
            source               TEXT CHECK(source IN ('arxiv', 'ssrn', 'other')),
            relevance            TEXT,
            abstract             TEXT,
            key_equations        TEXT,
            empirical_findings   TEXT,
            baysix_applicability TEXT,
            xauusd_translation   TEXT,
            limitations          TEXT,
            replication_status   TEXT CHECK(replication_status IN ('none','attempted','confirmed','upgraded')) DEFAULT 'none',
            dissected            INTEGER DEFAULT 0,
            timestamp            TEXT
        )
    """)
    print("papers_consulted table created.")

    # 2. Migrate papers from agent_calls JSON into papers_consulted rows
    rows = conn.execute(
        "SELECT id, papers, timestamp FROM agent_calls WHERE papers IS NOT NULL AND papers != '[]' AND papers != ''"
    ).fetchall()

    migrated = 0
    seen_urls = set()
    ts = datetime.now(timezone.utc).isoformat()

    for call_id, papers_json, call_ts in rows:
        try:
            papers = json.loads(papers_json)
        except (json.JSONDecodeError, TypeError):
            print(f"  Skipping call_id={call_id} — invalid JSON")
            continue

        # Only migrate from id=1 (canonical); skip id=2 (duplicate call same papers)
        if call_id != 1:
            print(f"  Skipping call_id={call_id} — duplicate, not migrating papers")
            continue

        for p in papers:
            url = p.get("url", "").strip()
            if url in seen_urls:
                continue
            seen_urls.add(url)

            conn.execute("""
                INSERT INTO papers_consulted
                    (agent_call_id, title, url, source, relevance, dissected, replication_status, timestamp)
                VALUES (?, ?, ?, ?, ?, 0, 'none', ?)
            """, (
                call_id,
                p.get("title", ""),
                url,
                p.get("source", "other"),
                p.get("relevance", ""),
                call_ts or ts,
            ))
            migrated += 1

    conn.commit()
    print(f"Migrated {migrated} papers into papers_consulted.")

    # 3. Delete duplicate agent_calls row (id=2, same call written twice)
    conn.execute("DELETE FROM agent_calls WHERE id = 2")
    conn.commit()
    print("Deleted duplicate agent_calls row id=2.")

    # 4. Drop papers column from agent_calls
    conn.execute("ALTER TABLE agent_calls DROP COLUMN papers")
    conn.commit()
    print("Dropped papers column from agent_calls.")

    # Verify
    print("\n--- agent_calls schema ---")
    for row in conn.execute("PRAGMA table_info(agent_calls)"):
        print(f"  {row}")

    print("\n--- papers_consulted rows ---")
    for row in conn.execute(
        "SELECT id, agent_call_id, title, url, source, dissected, replication_status FROM papers_consulted"
    ):
        print(f"  id={row[0]} | call={row[1]} | source={row[4]} | dissected={row[6]} | {row[2][:60]}")

    conn.close()
    print("\nMigration 004 complete.")


if __name__ == "__main__":
    up()
