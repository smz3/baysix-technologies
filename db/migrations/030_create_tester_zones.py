"""
Migration 030 — add tester_zones to research.db (task 119, BRC zone-lifecycle ledger).

The table is defined in the canonical core.tester._SCHEMA (single source of
truth, alongside tester_runs/tester_trades); this migration just re-runs init_db(),
which is additive + idempotent (CREATE TABLE IF NOT EXISTS), so existing tables are
untouched and tester_zones appears. Each BRC emit is a tester_runs header (provenance:
symbol/data_source/tester_model/period) with one tester_zones row per confirmed zone
per TF, parsed from the brc_csv.mqh UTF-8 lifecycle CSV via ingest_brc_zones.py.

Run: python db/migrations/030_create_tester_zones.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from core import tester


def main():
    path = tester.init_db()
    import sqlite3
    conn = sqlite3.connect(path)
    cols = [r[1] for r in conn.execute("PRAGMA table_info(tester_zones)")]
    conn.close()
    print(f"  tester_zones: {len(cols)} cols -> {', '.join(cols)}")


if __name__ == "__main__":
    main()
