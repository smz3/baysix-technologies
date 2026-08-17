"""
Migration 029 — Rename idea B2B-001 -> BRC-001 (Break · Retest · Continuation).

The "B2B / Break of Two Barriers" branding carried unfalsifiable narrative
("institutional positioning / trapped traders") and collided with the bloated live
MT5 B2B EA. The research idea is rebranded to BRC — three OBSERVABLE, testable
events: Break (struct rawbreakout) -> Retest (pullback to broken level) ->
Continuation (forward return). STRUCT-001 is UNTOUCHED (it stays the shared
"Break" primitive; BRC imports it, never forks it).

Rewrites idea_id (and parent_idea_id) 'B2B-001' -> 'BRC-001' in every research.db
table that carries the column, and updates the step1_ideas display name. No table
is FK-enforced, so the rewrite is safe. Idempotent — re-running is a no-op once the
old id is gone.

Run: python db/migrations/029_rename_b2b_to_brc.py
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parents[1] / "db" / "research.db"
OLD, NEW = "B2B-001", "BRC-001"
NEW_NAME = "BRC — Break-Retest-Continuation (structural breakout/pullback continuation)"


def run():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    tables = [r[0] for r in cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")]

    total = 0
    for t in tables:
        cols = {r[1] for r in cur.execute(f"PRAGMA table_info({t})")}
        for col in ("idea_id", "parent_idea_id"):
            if col not in cols:
                continue
            n = cur.execute(
                f"SELECT COUNT(*) FROM {t} WHERE {col}=?", (OLD,)).fetchone()[0]
            if n:
                cur.execute(f"UPDATE {t} SET {col}=? WHERE {col}=?", (NEW, OLD))
                print(f"  {t}.{col:14} {n:>3} row(s)  {OLD} -> {NEW}")
                total += n

    # refresh the display name on the idea row
    if "step1_ideas" in tables:
        cur.execute("UPDATE step1_ideas SET name=? WHERE idea_id=?", (NEW_NAME, NEW))

    conn.commit()

    # verify: zero B2B-001 left, BRC-001 present in step1_ideas
    leftover = 0
    for t in tables:
        cols = {r[1] for r in cur.execute(f"PRAGMA table_info({t})")}
        for col in ("idea_id", "parent_idea_id"):
            if col in cols:
                leftover += cur.execute(
                    f"SELECT COUNT(*) FROM {t} WHERE {col}=?", (OLD,)).fetchone()[0]
    present = cur.execute(
        "SELECT COUNT(*) FROM step1_ideas WHERE idea_id=?", (NEW,)).fetchone()[0]
    ok = leftover == 0 and present == 1
    print(f"[029] rewrote {total} ref(s). {OLD} leftover={leftover}  "
          f"{NEW} idea_row={present}  -> {'OK' if ok else '*** INCOMPLETE'}")
    conn.close()


if __name__ == "__main__":
    run()
