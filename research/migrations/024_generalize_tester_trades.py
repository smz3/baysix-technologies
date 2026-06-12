"""
Migration 024 — generalize tester_trades for high-frequency strategies (task 55).

The original tester_trades was ORB-shaped and breaks for scalpers (100s trades/day):
  1. session_date was treated as the Python join key -> assumes <=1 trade/day.
     New: join on ticket + entry_ts; session_date kept as a nullable convenience col.
  2. or_high / or_low / range_w were first-class columns -> ORB-specific bloat.
     New: folded into a generic `meta` JSON column. risk_unit stays as the generic 1R.
  3. + lots column (sizing matters at scale), + run_id / (run_id, entry_ts) indexes.

SQLite can't transform columns in place, so this is the standard table-rebuild
(new table -> copy+transform rows -> drop -> rename). The 527 existing ORB-001 rows
are preserved: {or_high, or_low, range_w} (non-null only) -> meta JSON.

Spec: braindump/mt5_fidelity_flow.md (Feed B contract).
Run:  python research/migrations/024_generalize_tester_trades.py
"""
import sys
import json
import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parents[1] / "db" / "research.db"

_NEW = """
CREATE TABLE tester_trades_new (
    tt_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id           INTEGER NOT NULL REFERENCES tester_runs(run_id),
    ticket           INTEGER,                       -- MT5 position id (unique within a run)
    session_date     DATE,                          -- nullable convenience (daily strategies)
    direction        TEXT CHECK(direction IS NULL OR direction IN ('long','short','flat')),
    entry_ts         DATETIME,                      -- cross-system join key (with ticket)
    entry_px         REAL,
    exit_ts          DATETIME,
    exit_px          REAL,
    exit_reason      TEXT,
    lots             REAL,                          -- position size
    risk_unit        REAL,                          -- generic 1R denominator (price units)
    realized_R       REAL,
    realized_pnl_usd REAL,
    meta             TEXT CHECK(meta IS NULL OR json_valid(meta)),  -- strategy ctx (ORB: or_high/or_low/range_w)
    created_at       DATETIME NOT NULL
);
"""

_IDX = """
CREATE INDEX IF NOT EXISTS ix_tester_trades_run    ON tester_trades(run_id);
CREATE INDEX IF NOT EXISTS ix_tester_trades_run_ts ON tester_trades(run_id, entry_ts);
"""


def main():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cols = [r[1] for r in cur.execute("PRAGMA table_info(tester_trades)")]
    if "meta" in cols:
        print("migration 024 already applied (meta column present) — no-op")
        conn.close()
        return

    old = cur.execute("SELECT * FROM tester_trades").fetchall()
    print(f"migrating {len(old)} existing rows...")

    cur.execute("PRAGMA foreign_keys = OFF")
    cur.executescript(_NEW)

    for r in old:
        m = {k: r[k] for k in ("or_high", "or_low", "range_w") if r[k] is not None}
        meta = json.dumps(m) if m else None
        cur.execute("""
            INSERT INTO tester_trades_new
                (tt_id, run_id, ticket, session_date, direction, entry_ts, entry_px,
                 exit_ts, exit_px, exit_reason, lots, risk_unit, realized_R,
                 realized_pnl_usd, meta, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (r["tt_id"], r["run_id"], r["ticket"], r["session_date"], r["direction"],
              r["entry_ts"], r["entry_px"], r["exit_ts"], r["exit_px"], r["exit_reason"],
              None, r["risk_unit"], r["realized_R"], r["realized_pnl_usd"], meta,
              r["created_at"]))

    cur.execute("DROP TABLE tester_trades")
    cur.execute("ALTER TABLE tester_trades_new RENAME TO tester_trades")
    cur.executescript(_IDX)
    conn.commit()

    # verify
    new_cols = [r[1] for r in cur.execute("PRAGMA table_info(tester_trades)")]
    n = cur.execute("SELECT COUNT(*) FROM tester_trades").fetchone()[0]
    n_meta = cur.execute("SELECT COUNT(*) FROM tester_trades WHERE meta IS NOT NULL").fetchone()[0]
    idx = [r[0] for r in cur.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='tester_trades'")]
    print(f"  rows preserved : {n} (expected {len(old)})")
    print(f"  rows w/ meta   : {n_meta}")
    print(f"  meta in schema : {'meta' in new_cols}")
    print(f"  or_* dropped   : {not any(c in new_cols for c in ('or_high','or_low','range_w'))}")
    print(f"  indexes        : {[i for i in idx if i.startswith('ix_')]}")
    assert n == len(old), "ROW COUNT MISMATCH — migration aborted state"
    conn.close()
    print("migration 024 complete")


if __name__ == "__main__":
    main()
