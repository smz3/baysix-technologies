"""045 — refuse raw writes at the DATABASE, not at the shell (task 366).

WHAT WAS WRONG
Rule 10 ("writes via the code layer only") was enforced by `protocol_guard`, a hook
that string-matches one Bash command. MEASURED 2026-08-16: it sees `sqlite3` + a DB
name + a write keyword in a single command, and nothing else. Writing a .py file and
running it, passing the path via $BAYSIX_DB, or pandas `to_sql` all sail past. Five
routes, one watched.

WHAT THIS DOES
24 triggers — BEFORE INSERT / UPDATE / DELETE on each of the 8 spine tables — whose
WHEN clause calls `baysix_writer()`. That function is not built into SQLite; it exists
only on a connection that registered it, and only `research/code/infra/db_guard.arm()`
does that. An unarmed connection cannot even COMPILE a write:

    sqlite3.OperationalError: no such function: baysix_writer

Reads are untouched — triggers fire on writes only.

WHY NOT TASK 366'S TEMP-TABLE MARKER
MEASURED here before writing this: SQLite refuses to create such a trigger at all —
"trigger ... cannot reference objects in database temp". A trigger body may only
reference its own schema. The function marker has no such limit and closes MORE: the
`sqlite3` CLI cannot register a user function under any circumstances, so that route
is shut rather than merely watched.

THE ESCAPE HATCH IS THE SAME DOOR
A migration is a legitimate writer and arms itself exactly like the code layer does.
There is no separate bypass, no magic table, nothing to leave switched on by accident.

THE HONEST LIMIT (unchanged from task 366's own wording)
A script can arm itself. This stops the slip, not the determined bypass. Recorded here
so nobody later mistakes it for a security boundary — it is a correctness rail.

Run: python research/migrations/045_write_guard_triggers.py
"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from research.code.infra import db_guard  # noqa: E402
from research.code.infra.db_path import DB_PATH  # noqa: E402

MESSAGE = (
    "raw write refused (CLAUDE.md rule 10) - open the connection through "
    "research/code/ (pipeline / strategy_log / backlog / agent_log / runs), or "
    "call db_guard.arm(conn) if you are a migration"
)


def trigger_sql(table: str, op: str) -> tuple[str, str]:
    name = f"guard_{table}_{op.lower()}"
    return name, f"""
        CREATE TRIGGER {name} BEFORE {op} ON {table}
        WHEN {db_guard.GUARD_FN}() IS NOT 1
        BEGIN SELECT RAISE(ABORT, '{MESSAGE}'); END
    """


def main() -> int:
    conn = sqlite3.connect(DB_PATH)
    db_guard.arm(conn, reason="migration 045")

    existing = {
        r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE 'guard_%'"
        )
    }
    if existing:
        print(f"ABORT: {len(existing)} guard trigger(s) already present — 045 has run.")
        return 1

    missing = [
        t for t in db_guard.GUARDED_TABLES
        if not conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?", (t,)
        ).fetchone()[0]
    ]
    if missing:
        print(f"ABORT: spine table(s) missing: {missing}")
        return 1

    conn.execute("BEGIN")
    try:
        made = 0
        for table in db_guard.GUARDED_TABLES:
            for op in ("INSERT", "UPDATE", "DELETE"):
                _, sql = trigger_sql(table, op)
                conn.execute(sql)
                made += 1
        conn.execute("COMMIT")
    except Exception as exc:
        conn.execute("ROLLBACK")
        print(f"FAIL: rolled back, database unchanged -> {exc}")
        conn.close()
        return 1

    n = conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='trigger' AND name LIKE 'guard_%'"
    ).fetchone()[0]
    print(f"  {made} triggers created, {n} present on {len(db_guard.GUARDED_TABLES)} tables")

    # -- prove it, on the live file, inside a rolled-back transaction ---------- #
    print("\nVERIFY:")
    ok = True

    unarmed = sqlite3.connect(DB_PATH)
    try:
        unarmed.execute(
            "INSERT INTO log_tasks (status,priority,title,kind,created_at,updated_at,"
            "stream) VALUES ('open','P2','GUARD PROBE','infra','x','x','Ops')"
        )
        unarmed.rollback()
        print("  BAD unarmed connection WROTE — the guard is not working")
        ok = False
    except sqlite3.OperationalError as exc:
        print(f"  OK  unarmed write refused -> {exc}")
    finally:
        unarmed.close()

    reader = sqlite3.connect(DB_PATH)
    try:
        n_tasks = reader.execute("SELECT COUNT(*) FROM log_tasks").fetchone()[0]
        print(f"  OK  unarmed SELECT still works ({n_tasks} tasks)")
    except sqlite3.Error as exc:
        print(f"  BAD unarmed SELECT broke -> {exc}")
        ok = False
    finally:
        reader.close()

    try:
        conn.execute(
            "INSERT INTO log_tasks (status,priority,title,kind,created_at,updated_at,"
            "stream) VALUES ('open','P2','GUARD PROBE','infra','x','x','Ops')"
        )
        conn.rollback()
        print("  OK  armed write allowed (rolled back)")
    except sqlite3.Error as exc:
        print(f"  BAD armed write refused -> {exc}")
        ok = False

    conn.close()
    if not ok:
        print("\nFAIL: verification did not pass.")
        return 1
    print("\n045 applied. Rule 10 is now enforced by the file, not only by the hook.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
