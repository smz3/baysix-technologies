import sqlite3
from pathlib import Path

import pytest

from core import backlog, db_init


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    db = tmp_path / "research.db"
    monkeypatch.setattr(db_init, "DB_PATH", db)
    monkeypatch.setattr(backlog, "DB_PATH", db)
    db_init.init()
    return db


def test_add_and_get(tmp_db):
    tid = backlog.add_task("Build X", kind="infra", detail="why", priority="P1",
                           stream="Research")
    assert isinstance(tid, int)
    rows = backlog.get_backlog(status="open")
    assert len(rows) == 1
    assert rows[0]["title"] == "Build X"
    assert rows[0]["kind"] == "infra"
    assert rows[0]["priority"] == "P1"
    assert rows[0]["status"] == "open"
    assert rows[0]["stream"] == "Research"


def test_update_and_resolve(tmp_db):
    tid = backlog.add_task("Task", kind="sizing", stream="MT5")
    backlog.update_task(tid, status="in_progress", priority="P0")
    r = backlog.get_backlog(status="in_progress")[0]
    assert r["priority"] == "P0"
    backlog.resolve_task(tid, resolution="done it")
    assert backlog.get_backlog(status="open") == []
    done = backlog.get_backlog(status="done")[0]
    assert done["resolution"] == "done it"
    assert done["resolved_at"] is not None


def test_bad_kind_rejected(tmp_db):
    with pytest.raises(sqlite3.IntegrityError):
        backlog.add_task("Bad", kind="nonsense", stream="Research")


def test_stream_required(tmp_db):
    """Rule 17: every task carries an owning stream. Omitting it must fail loudly."""
    with pytest.raises(ValueError, match="stream is required"):
        backlog.add_task("No owner", kind="infra")
    with pytest.raises(ValueError, match="stream is required"):
        backlog.add_task("Bad owner", kind="infra", stream="Nonsense")


def test_filter_by_idea(tmp_db):
    backlog.add_task("A", kind="infra", stream="Research")
    backlog.add_task("B", kind="port", idea_id=None, stream="IBKR")
    rows = backlog.get_backlog(status="open", idea_id=None)
    assert len(rows) == 2
    assert backlog.get_backlog(status="open", stream="IBKR")[0]["title"] == "B"
