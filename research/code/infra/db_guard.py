"""db_guard — the thing that makes CLAUDE.md rule 10 true at the database.

THE GAP THIS CLOSES (MEASURED 2026-08-16, task 366)
`protocol_guard` is a shell hook. It fires only when the literal string `sqlite3`,
a database name and a write keyword all appear in ONE Bash command. Five routes
walk straight past it, because it reads command TEXT and cannot see intent:

    1. write a .py file, then run it
    2. pass the path in via $BAYSIX_DB
    3. pandas .to_sql()
    4. an interactive python -i session
    5. any library that opens its own connection

So rule 10 was prose plus a string-match. This makes it a property of the file.

HOW IT WORKS
Every spine table carries BEFORE INSERT / UPDATE / DELETE triggers (migration 045)
whose condition calls a SQL function named `baysix_writer`. SQLite has no such
function built in — it exists only on a connection that registered it, and only
`arm()` below does that. An unarmed connection therefore cannot compile a write
against those tables at all:

    sqlite3.OperationalError: no such function: baysix_writer

Reads are completely unaffected: triggers fire on writes only, so every SELECT,
every dashboard and every snapshot keeps working on a plain connection.

WHY NOT THE TEMP-TABLE VERSION
Task 366 proposed a connection-scoped temp table as the marker. MEASURED and
rejected — SQLite refuses to create the trigger at all:

    trigger guard_step1_ideas cannot reference objects in database temp

A trigger body may only reference the schema it lives in. The function-based marker
has no such restriction, and it is strictly stronger besides: the `sqlite3` CLI
cannot register a user function at all, so that route is closed completely rather
than merely watched.

THE HONEST LIMIT
A script can call `arm()` — or `create_function` — itself. That is deliberate and
unchanged from task 366's own note. This stops the SLIP (a stray to_sql, a
hand-written INSERT, a helpful agent taking a shortcut), not a determined bypass.
Anyone who arms a connection on purpose has read this docstring and owns the write.

USAGE
Every `_conn()` in the code layer calls `arm()` right after opening. A migration
does the same — it is a legitimate writer and is expected to say so:

    conn = sqlite3.connect(DB_PATH)
    db_guard.arm(conn, reason="migration 046")
"""
from __future__ import annotations

import sqlite3

__all__ = ["GUARD_FN", "GUARDED_TABLES", "arm", "is_armed", "connect"]

#: The function name the triggers call. Changing it means re-running the migration.
GUARD_FN = "baysix_writer"

#: The spine. Everything here is a decision record, not a working file — which is
#: exactly why a raw write into one is never routine. Factory ledgers are NOT in
#: this list: they are per-platform working files with their own write layer.
GUARDED_TABLES: tuple[str, ...] = (
    "step1_ideas", "step2_papers", "step3_gates", "step4_results",
    "log_agent", "log_strategy", "log_tasks", "runs",
)


def arm(conn: sqlite3.Connection, *, reason: str = "code layer") -> sqlite3.Connection:
    """Declare this connection a legitimate writer. Returns the same connection.

    `reason` is not stored — SQLite user functions carry no metadata. It exists to
    make the call site say WHY at the point a reader is asking.
    """
    conn.create_function(GUARD_FN, 0, lambda: 1, deterministic=False)
    return conn


def is_armed(conn: sqlite3.Connection) -> bool:
    try:
        conn.execute(f"SELECT {GUARD_FN}()").fetchone()
        return True
    except sqlite3.OperationalError:
        return False


def connect(path, *, reason: str = "code layer") -> sqlite3.Connection:
    """Open an armed connection with the conventions the code layer already uses:
    foreign keys ON (otherwise the FKs added in 044 are decoration) and a Row
    factory."""
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return arm(conn, reason=reason)
