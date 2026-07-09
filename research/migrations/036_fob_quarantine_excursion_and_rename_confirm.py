"""Migration 036 (task 261) — quarantine the two poisoned FOB zone columns.

WHAT
  1. mfe_r / mae_r  -> NULL in every data/fob_payload/run_*/zones.parquet.
  2. confirm_time / confirm_price -> renamed next_cf_time / next_cf_price, in the
     parquet payload and in the fob_zones DB schema.

WHY
  mfe_r/mae_r were produced by derive_fob_excursion.py, which has no FILL GATE: it
  assumes a limit fill at l1 on the CF bar whether or not price could ever have filled
  there. On run_19 (278,592 CF zones), 39% already had price past l1 (never fills, never
  stops, sweep runs to end-of-data -> max mfe_r = 32,120 R = the gold bull) and 56%
  already had price beyond l2 (stops on bar 0 -> mae_r <= -1 by construction). ~95% of
  rows are one or the other, and unresolved sweeps wrote a number instead of NaN.

  confirm_time/confirm_price are a FORWARD POINTER to the next same-cycle CF: non-null
  iff a later CF exists, i.e. exactly `cf_idx < max_cf`. The name reads like a fill time,
  and a screen anchored entries on it and produced a fake t+7.72. The rename is
  labels-only — no value changes, no logic changes.

SCOPE
  FOB payload + fob_zones only. tester_zones is a different schema and is not touched.

Idempotent. Usage:
    python research/migrations/036_fob_quarantine_excursion_and_rename_confirm.py
"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd

from research.code.io import fob_payload, tester

_RENAME = {"confirm_time": "next_cf_time", "confirm_price": "next_cf_price"}
_NULL_OUT = ("mfe_r", "mae_r")


def migrate_parquet() -> list:
    out = []
    for run_dir in sorted(fob_payload.PAYLOAD_DIR.glob("run_*")):
        path = run_dir / "zones.parquet"
        if not path.exists():
            continue
        df = pd.read_parquet(path)
        changed = []

        ren = {k: v for k, v in _RENAME.items() if k in df.columns}
        if ren:
            df = df.rename(columns=ren)
            changed.append(f"renamed {list(ren)}")

        for c in _NULL_OUT:
            if c in df.columns and df[c].notna().any():
                df[c] = pd.NA
                changed.append(f"nulled {c}")

        if changed:
            df.to_parquet(path, index=False)
        out.append(f"{run_dir.name}: {', '.join(changed) or 'already clean'}")
    return out


def migrate_db() -> list:
    out = []
    with sqlite3.connect(tester.DB_PATH) as conn:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(fob_zones)")}
        for old, new in _RENAME.items():
            if old in cols and new not in cols:
                conn.execute(f"ALTER TABLE fob_zones RENAME COLUMN {old} TO {new}")
                out.append(f"fob_zones.{old} -> {new}")
        conn.execute("DROP INDEX IF EXISTS ix_fob_zones_confirm")
        conn.execute("CREATE INDEX IF NOT EXISTS ix_fob_zones_next_cf "
                     "ON fob_zones(run_id, next_cf_time)")
        n = conn.execute("SELECT COUNT(*) FROM fob_zones "
                         "WHERE mfe_r IS NOT NULL OR mae_r IS NOT NULL").fetchone()[0]
        if n:
            conn.execute("UPDATE fob_zones SET mfe_r = NULL, mae_r = NULL")
            out.append(f"nulled mfe_r/mae_r on {n} staging row(s)")
        conn.commit()
    return out or ["fob_zones: already clean"]


def main():
    print("=== migration 036 (task 261) ===")
    for line in migrate_db():
        print(f"  [db]      {line}")
    for line in migrate_parquet():
        print(f"  [parquet] {line}")
    print("done.")


if __name__ == "__main__":
    main()
