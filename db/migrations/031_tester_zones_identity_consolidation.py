"""
Migration 031 — task 127: add zone identity + overlap-consolidation columns to
tester_zones.

Four additive columns (the canonical DDL in core.tester._SCHEMA already
carries them for fresh DBs; this migration ALTERs an EXISTING tester_zones, which
CREATE TABLE IF NOT EXISTS will not touch):

  seq                INTEGER  -- per-TF, 1-based, p4_time order (chart/CSV human id)
  zone_key           TEXT     -- {tf}|{dir}|{p4_epoch}(+|{l2}) stable machine join key
  is_primary         INTEGER  -- 1 unless consolidated away by a bigger overlapping same-dir zone
  consolidated_into  TEXT     -- survivor's zone_key when is_primary=0 (else NULL)

Existing run-2/run-3 rows pre-date the new emitter, so these stay NULL for them —
they must be re-emitted on the task-127 EA to populate. Idempotent: skips any
column that already exists.

Run: python db/migrations/031_tester_zones_identity_consolidation.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from core import tester

_NEW_COLS = [
    ("seq", "INTEGER"),
    ("zone_key", "TEXT"),
    ("is_primary", "INTEGER"),
    ("consolidated_into", "TEXT"),
]


def main():
    path = tester.init_db()  # ensures table exists (fresh DBs already get the cols)
    import sqlite3
    conn = sqlite3.connect(path)
    existing = {r[1] for r in conn.execute("PRAGMA table_info(tester_zones)")}
    added = []
    for name, typ in _NEW_COLS:
        if name not in existing:
            conn.execute(f"ALTER TABLE tester_zones ADD COLUMN {name} {typ}")
            added.append(name)
    conn.commit()
    cols = [r[1] for r in conn.execute("PRAGMA table_info(tester_zones)")]
    conn.close()
    print(f"  added: {added or '(none — already present)'}")
    print(f"  tester_zones: {len(cols)} cols -> {', '.join(cols)}")


if __name__ == "__main__":
    main()
