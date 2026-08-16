"""041 — give log_tasks a `stream` owner column (task 358).

THE BUG THIS FIXES (MEASURED 2026-08-16, during task 352):
`log_tasks.idea_id` is a foreign key to `step1_ideas`, and `step1_ideas` holds ONLY
registered falsifiable strategy ideas (4 rows). Tooling, memory, platform wiring and
ops work therefore has no legal owner — which is why 35 tasks sat with a NULL idea_id.
Task 352 originally said "force an idea_id on the orphans"; doing that would mean
inventing fake idea rows and corrupting the idea ledger. So the owner is a SEPARATE
dimension, not a borrowed one.

WHAT THE TWO COLUMNS MEAN AFTER THIS
  stream   NOT NULL. Which part of the business the task belongs to.
           MT5 / NinjaTrader / IBKR / Research / Ops.
  idea_id  stays OPTIONAL, and now means strictly "serves a live falsifiable idea".

This is also the enforcement surface for CLAUDE.md rule 5 (namespace discipline): a
parked system cannot leak into a live decision if the query filters by stream.

BACKFILL IS DELIBERATELY COARSE. All 266 existing rows go to 'Research', then the
open ones are set by hand. Guessing a stream from keywords in title+detail was measured
to be wrong on 2026-08-16: a grep for grw|fob over the same table hit 13 of 25 open rows
when only 4 were actually that work. A wrong owner on a history row is worse than a
vague one, because the whole point of the column is to be trusted in a filter.

Run: python research/migrations/041_add_task_stream.py
"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from research.code.infra.db_path import DB_PATH  # noqa: E402

VALID_STREAM = ("MT5", "NinjaTrader", "IBKR", "Research", "Ops")
BACKFILL = "Research"

# The open tasks, set by hand rather than guessed. Anything not listed keeps BACKFILL.
OPEN_STREAM = {
    349: "Research",     # outputs/ write convention for research runs
    350: "Ops",          # database snapshot routine
    356: "Research",     # generic runs registry on the spine
    358: "Research",     # this migration
    362: "NinjaTrader",  # NT8 factory table rename
    364: "Research",     # DB flow redesign decisions
}

VIEW_SQL = """
CREATE VIEW open_backlog AS
SELECT b.task_id, b.idea_id, i.name AS idea_name, b.stream, b.status, b.priority,
       b.title, b.kind,
       CAST((julianday('now') - julianday(b.created_at)) AS INTEGER) AS age_days
FROM log_tasks b
LEFT JOIN step1_ideas i ON i.idea_id = b.idea_id
WHERE b.status IN ('open','in_progress')
ORDER BY b.priority ASC, b.created_at ASC
"""


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    cols = [r[1] for r in conn.execute("PRAGMA table_info(log_tasks)")]
    if "stream" in cols:
        print("ABORT: log_tasks.stream already exists — 041 has already run.")
        return 1

    total = conn.execute("SELECT COUNT(*) FROM log_tasks").fetchone()[0]
    print(f"  log_tasks: {total} rows")

    # NOT NULL needs a default on ALTER; every existing row takes BACKFILL.
    conn.execute(
        f"ALTER TABLE log_tasks ADD COLUMN stream TEXT NOT NULL DEFAULT '{BACKFILL}'"
    )
    print(f"  added stream NOT NULL, {total} rows backfilled -> '{BACKFILL}'")

    for task_id, stream in OPEN_STREAM.items():
        if stream not in VALID_STREAM:
            print(f"ABORT: bad stream '{stream}' for task {task_id}")
            return 1
        cur = conn.execute(
            "UPDATE log_tasks SET stream=? WHERE task_id=?", (stream, task_id)
        )
        if cur.rowcount:
            print(f"    task {task_id} -> {stream}")

    # The view has to be rebuilt to expose the new column to SessionStart.
    conn.execute("DROP VIEW IF EXISTS open_backlog")
    conn.execute(VIEW_SQL)
    conn.commit()

    # End-state assertions — abort loudly rather than leave a half-migration.
    cols = [r[1] for r in conn.execute("PRAGMA table_info(log_tasks)")]
    if "stream" not in cols:
        print("FAIL: stream column missing after ALTER.")
        return 1
    nulls = conn.execute(
        "SELECT COUNT(*) FROM log_tasks WHERE stream IS NULL OR stream=''"
    ).fetchone()[0]
    if nulls:
        print(f"FAIL: {nulls} rows have no stream.")
        return 1
    bad = conn.execute(
        "SELECT COUNT(*) FROM log_tasks WHERE stream NOT IN ({})".format(
            ",".join("?" * len(VALID_STREAM))), VALID_STREAM
    ).fetchone()[0]
    if bad:
        print(f"FAIL: {bad} rows carry a stream outside {VALID_STREAM}.")
        return 1

    print("  open backlog after:")
    for r in conn.execute(
            "SELECT task_id, priority, stream, title FROM open_backlog"):
        print(f"    {r['task_id']} [{r['priority']}] {r['stream']:<12} {r['title'][:52]}")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
