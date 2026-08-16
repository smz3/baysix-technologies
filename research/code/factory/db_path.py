"""factory_db_path — the ONE place a platform's factory.db location is decided.

ONE FACTORY PER PLATFORM, ONE FILE EACH
    platforms/mt5/db/factory.db
    platforms/ninjatrader/db/factory.db
    platforms/ibkr/db/factory.db

WHY SEPARATE FILES AND NOT ONE SHARED ONE (Syafiq's call 2026-08-16, extending
task 360 from NT8-only to every platform): SQLite takes a write lock on the WHOLE
file. Two agent loops sweeping at once — the MT5 tab and the NT8 tab — would sit
and wait on each other for hours, and the loops are the entire point. Separate
files means zero contention, at the cost of nothing, because nothing in the
factory layer ever needs to join across platforms. The one number that DOES have
to be shared, the trial count, travels up to baysix.db instead (task 360 rule 2:
send the COUNT, not the ROWS).

WHY IT ANCHORS TO baysix.db AND NOT TO __file__
`infra.db_path` learned this the hard way (task 357, MEASURED): a path built from
`Path(__file__).parents[n]` resolves to whatever checkout the file happens to sit
in, so a git worktree silently gets its own empty database. That failure is worse
here than on the spine — two sweeps counted in two files is a split denominator,
which is the exact dishonesty task 360 was built to prevent. So the repo root is
taken from the RESOLVED baysix.db path (which honours $BAYSIX_DB) rather than
computed independently. One env var pins everything; there is no second knob to
forget to set.

WHAT MUST NEVER BE IN HERE
A factory.db holds the workshop: batches, candidates, per-candidate sweeps,
trades, events, integrity checks. It must NEVER hold `step1_ideas` through
`step4_results`. An idea is a claim about the world, not a platform artifact —
the same claim can be tested on gold via MT5 and on ES via NT8, and if each
factory kept its own copy then "did this pass G2?" would have two answers.
`assert_not_spine()` enforces that rather than trusting the reader to remember.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from research.code.infra.db_path import db_path as _baysix_db_path

__all__ = ["PLATFORMS", "factory_db_path", "repo_root", "assert_not_spine", "SPINE_TABLES"]

#: Same tuple as lineage.runs._VALID_PLATFORM, deliberately duplicated rather than
#: imported: the folder names are lowercase on disk, the ledger values are not.
PLATFORMS: tuple[str, ...] = ("mt5", "ninjatrader", "ibkr")

#: Tables that belong to the spine (db/baysix.db) and to nothing else.
SPINE_TABLES: frozenset[str] = frozenset({
    "step1_ideas", "step2_papers", "step3_gates", "step4_results",
    "log_agent", "log_strategy", "log_tasks", "runs",
})


def repo_root() -> Path:
    """The checkout that owns the databases, derived from the resolved baysix.db.

    `db_path()` returns `<repo>/db/baysix.db`, so two parents up is the root that
    $BAYSIX_DB actually pointed at — not the one this source file lives in.
    """
    return _baysix_db_path(warn=False).resolve().parent.parent


def factory_db_path(platform: str) -> Path:
    """Absolute path to one platform's factory ledger. Does not create it."""
    key = platform.strip().lower()
    if key not in PLATFORMS:
        raise ValueError(
            f"unknown platform {platform!r}; expected one of {PLATFORMS}. "
            f"A new platform needs a folder under platforms/ and an entry here, "
            f"not a hand-built path at the call site."
        )
    return repo_root() / "platforms" / key / "db" / "factory.db"


def assert_not_spine(conn: sqlite3.Connection) -> None:
    """Refuse a factory.db that has grown a spine table.

    Cheap, and it fires at the moment the mistake is made rather than a month
    later when two gate ledgers disagree. The check is on names only — a copy of
    `step3_gates` under any other name is a judgement call this cannot make.
    """
    found = {
        r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table','view')"
        )
    } & SPINE_TABLES
    if found:
        raise RuntimeError(
            f"this factory.db contains spine table(s) {sorted(found)}. Ideas, gates "
            f"and results live in db/baysix.db ONLY — one idea, one gate history, "
            f"one verdict. Promote a finished result upward instead of copying the "
            f"ledger downward."
        )
