"""Does the write guard (migration 045) actually refuse an unarmed write?

Task 366 recorded that the probe which MEASURED protocol_guard's five blind spots
"lived only in a scratchpad and is gone". This is that probe, re-authored as a
regression test so the next schema change cannot quietly drop the triggers.

Everything runs against a COPY of the live database. The guard is a property of the
FILE, so a copy carries it — which is itself part of what these tests assert.
"""
from __future__ import annotations

import shutil
import sqlite3

import pytest

from core.infra import db_guard
from core.infra.db_path import db_path

pytestmark = pytest.mark.skipif(
    not db_path(warn=False).exists(), reason="baysix.db not available"
)

WRITE = ("INSERT INTO log_tasks (status,priority,title,kind,created_at,updated_at,"
         "stream) VALUES ('open','P2','guard probe','infra','x','x','Ops')")


@pytest.fixture()
def copied_db(tmp_path):
    dst = tmp_path / "baysix_copy.db"
    shutil.copy(db_path(warn=False), dst)
    return dst


def test_the_triggers_are_actually_installed(copied_db):
    conn = sqlite3.connect(copied_db)
    names = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE 'guard_%'")}
    conn.close()
    expected = {
        f"guard_{t}_{op}"
        for t in db_guard.GUARDED_TABLES
        for op in ("insert", "update", "delete")
    }
    assert expected <= names, f"missing guard triggers: {sorted(expected - names)}"


def test_an_unarmed_connection_cannot_insert(copied_db):
    """The route protocol_guard cannot see: a .py file opening its own connection."""
    conn = sqlite3.connect(copied_db)
    with pytest.raises(sqlite3.OperationalError, match="baysix_writer"):
        conn.execute(WRITE)
    conn.close()


def test_an_unarmed_connection_cannot_update_or_delete(copied_db):
    conn = sqlite3.connect(copied_db)
    for sql in ("UPDATE log_tasks SET title='x' WHERE task_id=1",
                "DELETE FROM log_tasks WHERE task_id=1"):
        with pytest.raises(sqlite3.OperationalError, match="baysix_writer"):
            conn.execute(sql)
    conn.close()


def test_every_guarded_table_refuses_an_unarmed_write(copied_db):
    """Not just log_tasks — a guard with a hole in it is worse than none, because
    the hole is where the next shortcut goes."""
    conn = sqlite3.connect(copied_db)
    for table in db_guard.GUARDED_TABLES:
        with pytest.raises(sqlite3.OperationalError, match="baysix_writer"):
            conn.execute(f"DELETE FROM {table}")
    conn.close()


def test_reads_are_completely_unaffected(copied_db):
    """Dashboards, briefs and the snapshot routine all read on plain connections."""
    conn = sqlite3.connect(copied_db)
    assert conn.execute("SELECT COUNT(*) FROM log_tasks").fetchone()[0] >= 0
    assert conn.execute("SELECT COUNT(*) FROM open_backlog").fetchone()[0] >= 0
    conn.close()


def test_an_armed_connection_writes_normally(copied_db):
    conn = sqlite3.connect(copied_db)
    db_guard.arm(conn, reason="test")
    conn.execute(WRITE)
    conn.commit()
    assert conn.execute(
        "SELECT COUNT(*) FROM log_tasks WHERE title='guard probe'"
    ).fetchone()[0] == 1
    conn.close()


def test_is_armed_reports_the_truth(copied_db):
    plain = sqlite3.connect(copied_db)
    assert db_guard.is_armed(plain) is False
    db_guard.arm(plain)
    assert db_guard.is_armed(plain) is True
    plain.close()


def test_the_connect_helper_returns_an_armed_connection(copied_db):
    conn = db_guard.connect(copied_db, reason="test")
    assert db_guard.is_armed(conn)
    conn.execute(WRITE)
    conn.commit()
    conn.close()


def test_pandas_style_bulk_insert_is_refused(copied_db):
    """`to_sql` opens its own cursor on a plain connection — blind spot #3 in the
    protocol_guard measurement, and the most likely accidental route."""
    conn = sqlite3.connect(copied_db)
    rows = [("open", "P2", f"bulk {i}", "infra", "x", "x", "Ops") for i in range(3)]
    with pytest.raises(sqlite3.OperationalError, match="baysix_writer"):
        conn.executemany(
            "INSERT INTO log_tasks (status,priority,title,kind,created_at,"
            "updated_at,stream) VALUES (?,?,?,?,?,?,?)", rows)
    conn.close()
