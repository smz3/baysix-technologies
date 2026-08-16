"""
Backlog interface for research.db (log_tasks).
Research/eng follow-ups that are NOT falsifiable ideas (ideas live in step1_ideas).
All writes go through here — no raw SQL elsewhere (CLAUDE.md rule 10).
"""
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path

from research.code.infra.db_path import DB_PATH  # noqa: F401  (task 357: one canonical path)
MYT = timezone(timedelta(hours=8))

_VALID_KIND = ("variant", "sizing", "filter", "port", "infra", "data", "cleanup")
_VALID_PRIORITY = ("P0", "P1", "P2")
_VALID_STATUS = ("open", "in_progress", "done", "dropped", "parked")

# Syafiq's cap, 2026-08-16: at most this many tasks open at once. Adding means
# clearing a slot first — a backlog you cannot read is a backlog you don't use.
MAX_OPEN = 6
_OPEN_STATUS = ("open", "in_progress")


class BacklogFullError(RuntimeError):
    """Raised when a write would push the open count past MAX_OPEN."""


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def _now() -> str:
    return datetime.now(MYT).strftime("%Y-%m-%d %H:%M:%S")


def _assert_slot_free(conn) -> None:
    """Block the write if MAX_OPEN tasks are already open. Names them, so the
    caller can pick one to resolve instead of guessing."""
    marks = ",".join("?" * len(_OPEN_STATUS))
    rows = conn.execute(
        f"SELECT task_id, priority, title FROM log_tasks WHERE status IN ({marks})"
        " ORDER BY priority ASC, task_id ASC", _OPEN_STATUS
    ).fetchall()
    if len(rows) < MAX_OPEN:
        return
    listing = "\n".join(f"  {r['task_id']} [{r['priority']}] {r['title']}" for r in rows)
    raise BacklogFullError(
        f"{len(rows)} tasks already open (cap {MAX_OPEN}). "
        f"Resolve one first — backlog.resolve_task(task_id, note):\n{listing}"
    )


def add_task(title: str, kind: str, detail: str = "", idea_id: str = None,
             priority: str = "P2") -> int:
    """Add a backlog task. Returns task_id.
    Raises BacklogFullError if MAX_OPEN tasks are already open."""
    if priority not in _VALID_PRIORITY:
        raise ValueError(f"priority must be one of {_VALID_PRIORITY}")
    now = _now()
    with _conn() as conn:
        _assert_slot_free(conn)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO log_tasks
                (idea_id, title, detail, kind, priority, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 'open', ?, ?)
        """, (idea_id, title, detail, kind, priority, now, now))
        conn.commit()
        task_id = cur.lastrowid
    print(f"[backlog] task_id={task_id} [{kind}|{priority}] {title}")
    return task_id


def update_task(task_id: int, **fields) -> None:
    """Update status / priority / detail / title / kind. Bumps updated_at."""
    allowed = {"status", "priority", "detail", "title", "kind"}
    bad = set(fields) - allowed
    if bad:
        raise ValueError(f"cannot update {bad}; allowed: {allowed}")
    if "status" in fields and fields["status"] not in _VALID_STATUS:
        raise ValueError(f"status must be one of {_VALID_STATUS}")
    if "priority" in fields and fields["priority"] not in _VALID_PRIORITY:
        raise ValueError(f"priority must be one of {_VALID_PRIORITY}")
    sets = ", ".join(f"{k}=?" for k in fields) + ", updated_at=?"
    vals = list(fields.values()) + [_now(), task_id]
    with _conn() as conn:
        # Reopening a resolved task claims a slot just like adding one does.
        if fields.get("status") in _OPEN_STATUS:
            cur_status = conn.execute(
                "SELECT status FROM log_tasks WHERE task_id=?", (task_id,)
            ).fetchone()
            if cur_status is not None and cur_status["status"] not in _OPEN_STATUS:
                _assert_slot_free(conn)
        conn.execute(f"UPDATE log_tasks SET {sets} WHERE task_id=?", vals)
        conn.commit()


def resolve_task(task_id: int, resolution: str, status: str = "done") -> None:
    """Mark a task done/dropped with a resolution note."""
    if status not in ("done", "dropped"):
        raise ValueError("resolve status must be 'done' or 'dropped'")
    now = _now()
    with _conn() as conn:
        conn.execute("""
            UPDATE log_tasks
            SET status=?, resolution=?, resolved_at=?, updated_at=?
            WHERE task_id=?
        """, (status, resolution, now, now, task_id))
        conn.commit()
    print(f"[backlog] task_id={task_id} -> {status}")


def get_backlog(status: str = "open", idea_id: str = "__any__") -> list[dict]:
    """Return backlog rows filtered by status (and optionally idea_id).
    Pass idea_id=None to match rows with NULL idea_id; omit to match any idea_id."""
    q = "SELECT * FROM log_tasks WHERE status=?"
    params = [status]
    if idea_id != "__any__":
        if idea_id is None:
            q += " AND idea_id IS NULL"
        else:
            q += " AND idea_id=?"
            params.append(idea_id)
    q += " ORDER BY priority ASC, created_at ASC"
    with _conn() as conn:
        return [dict(r) for r in conn.execute(q, params).fetchall()]
