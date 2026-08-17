"""Do the schema constraints from migration 044 actually refuse a bad row?

WHY THIS FILE EXISTS
Task 366 recorded that the earlier guard probe "lived only in a scratchpad and is
gone". A constraint nobody re-tests is a claim, not a guarantee: the next table
rebuild can silently drop a CHECK and every test still passes, because the code
layer would have caught the bad value anyway. These tests go around the code layer
on purpose — they write raw SQL at a COPY of the database and assert the DB itself
says no. That is the whole point of pushing the rules down into the schema.

WHY A COPY
Never the live file. Each test gets `tmp_path` and a byte copy, so a test that
somehow succeeds in writing a bad row damages nothing.
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


@pytest.fixture()
def conn(tmp_path):
    dst = tmp_path / "baysix_copy.db"
    shutil.copy(db_path(warn=False), dst)
    c = sqlite3.connect(dst)
    c.execute("PRAGMA foreign_keys = ON")
    # ARMED on purpose. These tests are about the CONSTRAINTS, so the write guard
    # (migration 045) has to be out of the way — otherwise every case below fails
    # with "no such function" and proves nothing about NOT NULL or CHECK. The guard
    # gets its own file, test_db_guard.py.
    db_guard.arm(c, reason="constraint test")
    yield c
    c.close()


TASK = ("INSERT INTO log_tasks (status,priority,title,kind,created_at,updated_at,stream)"
        " VALUES (?,?,?,?,?,?,?)")
RUN = ("INSERT INTO runs (platform,stage,symbol,git_sha,created_at)"
       " VALUES (?,?,?,?,?)")
RESULT = ("INSERT INTO step4_results"
          " (idea_id,gate_number,stage,metric_key,metric_value,n_obs,git_sha,logged_at,run_id)"
          " VALUES (?,?,?,?,?,?,?,?,?)")

NOW = "2026-08-16T00:00:00"


# --------------------------------------------------------------------------- #
#  the rules must refuse
# --------------------------------------------------------------------------- #

def test_an_invented_stream_is_refused(conn):
    """CLAUDE.md rule 17 in the schema. A typo'd stream mints a silent bucket, and
    rule 5's scoped search then misses those rows without ever saying so."""
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(TASK, ("open", "P2", "x", "infra", NOW, NOW, "Bitcoin"))


def test_an_unknown_platform_is_refused(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(RUN, ("MT4", "IS", "XAUUSD", "abc123", NOW))


def test_an_unknown_stage_is_refused(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(RUN, ("MT5", "backtest", "XAUUSD", "abc123", NOW))


def test_a_run_without_a_git_sha_is_refused(conn):
    """Without it there is no answer to 'what code produced this'."""
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO runs (platform,stage,symbol,created_at) VALUES (?,?,?,?)",
            ("MT5", "IS", "XAUUSD", NOW),
        )


def test_a_result_without_n_obs_is_refused(conn):
    """A metric with no sample size cannot be sized by a reader, and the code layer
    has always required it — now the file does too."""
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(RESULT, ("GRW-001", 2, "IS", "k", 1.0, None, "abc123", NOW, None))


def test_a_result_without_a_git_sha_is_refused(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(RESULT, ("GRW-001", 2, "IS", "k", 1.0, 10, None, NOW, None))


def test_a_result_pointing_at_a_nonexistent_run_is_refused(conn):
    """Migration 043 could not declare this FK (SQLite cannot ADD one); 044's table
    rebuild could. A dangling run_id is a result that claims a provenance it has not
    got, which is worse than a NULL."""
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(RESULT, ("GRW-001", 2, "IS", "k", 1.0, 10, "abc123", NOW, 999_999))


def test_a_result_from_an_unregistered_idea_is_refused(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(RESULT, ("NOPE-999", 2, "IS", "k", 1.0, 10, "abc123", NOW, None))


# --------------------------------------------------------------------------- #
#  and must still let legal work through
# --------------------------------------------------------------------------- #

def test_every_legal_stream_is_accepted(conn):
    for stream in ("MT5", "NinjaTrader", "IBKR", "Research", "Ops"):
        conn.execute(TASK, ("open", "P2", f"legal {stream}", "infra", NOW, NOW, stream))
    conn.rollback()


def test_a_legal_run_and_result_are_accepted(conn):
    cur = conn.execute(RUN, ("NinjaTrader", "OOS", "ES", "deadbee", NOW))
    run_id = cur.lastrowid
    conn.execute(RESULT, ("GRW-001", 2, "IS", "k", 1.0, 250, "deadbee", NOW, run_id))
    conn.rollback()


def test_a_null_run_id_is_still_allowed(conn):
    """63 of 71 rows predate the registry. NOT NULL would have meant inventing a run
    for each, and a fabricated owner is worse than an absent one."""
    conn.execute(RESULT, ("GRW-001", 2, "IS", "k", 1.0, 250, "deadbee", NOW, None))
    conn.rollback()
