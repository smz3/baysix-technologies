"""db_snapshot — routine backups of baysix.db (task 350).

THE GAP THIS CLOSES (MEASURED 2026-08-16)
`db/baysix.db` is gitignored (untracked since 2026-07-01, task 203). Git is therefore
NOT a backup for it. The newest snapshot in `research/db/_backup/` before this was
dated 2026-06-23 — an 8-week hole covering all of FOB and GRW — and `G:` held a git
bundle and CSVs but no database at all. One bad write and the whole research record,
including the trial counts that keep the work honest, was gone.

WHY A NEW FOLDER INSTEAD OF research/db/_backup/
Syafiq has said twice that `research/db/_backup/` is hands-off for deletion. A routine
with keep-last-N has to be allowed to delete, so it gets its own folder — `db/_snapshots/`
— and never looks at the old one. The rule survives without an exception to it.

HOW IT COPIES
sqlite3's `Connection.backup()` API, not a file copy. It takes a consistent snapshot of
a live database with WAL on; copying the file by hand while another session is mid-write
gives you a corrupt .db and no warning.

THROTTLE
Called on both SessionStart and SessionEnd, so an abandoned session still gets caught by
the next one. `MIN_AGE_HOURS` stops that turning into a snapshot every few minutes.
"""
from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

from research.code.infra.db_path import DB_PATH

MYT = timezone(timedelta(hours=8))
SNAP_DIR = Path(DB_PATH).parent / "_snapshots"
KEEP_LAST = 10
MIN_AGE_HOURS = 4
PREFIX = "baysix_"


def _newest_age_hours() -> float | None:
    """Hours since the most recent snapshot, or None if there are none."""
    snaps = sorted(SNAP_DIR.glob(f"{PREFIX}*.db"), key=lambda p: p.stat().st_mtime)
    if not snaps:
        return None
    newest = datetime.fromtimestamp(snaps[-1].stat().st_mtime, tz=MYT)
    return (datetime.now(MYT) - newest).total_seconds() / 3600


def prune(keep: int = KEEP_LAST) -> list[Path]:
    """Delete all but the newest `keep` snapshots. Only ever touches SNAP_DIR."""
    snaps = sorted(SNAP_DIR.glob(f"{PREFIX}*.db"), key=lambda p: p.stat().st_mtime)
    dropped = []
    for old in snaps[:-keep] if keep else snaps:
        old.unlink()
        dropped.append(old)
    return dropped


def snapshot(reason: str = "manual", force: bool = False) -> Path | None:
    """Write a consistent copy of baysix.db. Returns the path, or None if throttled."""
    src = Path(DB_PATH)
    if not src.exists():
        print(f"[db_snapshot] no database at {src} — nothing to snapshot", file=sys.stderr)
        return None

    SNAP_DIR.mkdir(parents=True, exist_ok=True)
    age = _newest_age_hours()
    if not force and age is not None and age < MIN_AGE_HOURS:
        return None

    stamp = datetime.now(MYT).strftime("%Y%m%d_%H%M%S")
    safe_reason = "".join(c for c in reason if c.isalnum() or c in "-_")[:24] or "manual"
    dest = SNAP_DIR / f"{PREFIX}{safe_reason}_{stamp}.db"

    source = sqlite3.connect(f"file:{src}?mode=ro", uri=True)
    target = sqlite3.connect(dest)
    try:
        source.backup(target)
    finally:
        target.close()
        source.close()

    # A snapshot that cannot be opened is not a backup. Prove it before pruning.
    check = sqlite3.connect(f"file:{dest}?mode=ro", uri=True)
    try:
        ok = check.execute("PRAGMA integrity_check").fetchone()[0]
        tables = check.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
    finally:
        check.close()
    if ok != "ok" or tables == 0:
        dest.unlink(missing_ok=True)
        print(f"[db_snapshot] FAILED integrity check ({ok}) — snapshot discarded",
              file=sys.stderr)
        return None

    dropped = prune()
    mb = dest.stat().st_size / 1048576
    tail = f", pruned {len(dropped)}" if dropped else ""
    print(f"[db_snapshot] {dest.name} ({mb:.2f}MB, {tables} tables){tail}")
    return dest


if __name__ == "__main__":
    args = sys.argv[1:]
    reason = args[0] if args else "manual"
    snapshot(reason, force="--force" in args)
