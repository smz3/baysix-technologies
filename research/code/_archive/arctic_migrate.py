"""
arctic_migrate.py — ONE-TIME migration: CS-GOLD-DUKAS-TICK parquet -> ArcticDB.

WHY: the parquet ticks are NOT time-sorted (arctic_spike confirmed month=2016-10
alone has 3.07M ticks out of order). That unsorted storage + row-position indexing
manufactured the ORB-001 look-ahead edge ([[orb_unsorted_tick_lookahead]]). ArcticDB
enforces a SORTED datetime index, so this migration *is* the structural fix (task 51):
once ticks live here, no read can ever be out of time order again.

WHAT IT DOES:
  - Walks every month partition in TRUE chronological order (numeric year/month, not
    lexical — lexical puts month=10 before month=2 and would break the append invariant).
  - Per month: read (ts_utc, bid, ask, volume) -> sort by ts_utc -> set DatetimeIndex.
  - First month: write the symbol; every later month: append (validate_index=True, so
    ArcticDB itself refuses any out-of-order / overlapping append — a second safety net).
  - Stamps symbol metadata: seal_date, source, parquet ground-truth row count, n_months.

TARGET:  lmdb://data/arctic   library 'ticks'   symbol 'XAUUSD'
SEAL:    IS/OOS boundary 2024-05-02 recorded in metadata; enforced at the read adapter.

Firewall: only counts / timestamps / progress reach stdout — never tick rows.
Idempotent: re-run drops + rebuilds the symbol from scratch.
Long run -> launch via run_tracked.py (visible window + sentinel), per CLAUDE.md rule 12.
"""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path

import pandas as pd
from tqdm import tqdm

REPO = Path(__file__).resolve().parents[2]
SRC_DIR = REPO / "data" / "parquet" / "CS-GOLD-DUKAS-TICK"
STORE = REPO / "data" / "arctic"
URI = f"lmdb://{STORE.as_posix()}?map_size=16GB"
LIB = "ticks"
SYMBOL = "XAUUSD"
SEAL_DATE = "2024-05-02"            # IS/OOS boundary (sealed)
COLS = ["ts_utc", "bid", "ask", "volume"]
EXPECTED_TICKS = 511_145_204       # parquet ground truth (pyarrow metadata, 2026-06-12)

_YM = re.compile(r"year=(\d+)[/\\]month=(\d+)")


def _month_files_chronological() -> list[Path]:
    files = list(SRC_DIR.glob("year=*/month=*/*.parquet"))

    def key(p: Path) -> tuple[int, int]:
        m = _YM.search(p.as_posix())
        return (int(m.group(1)), int(m.group(2))) if m else (9999, 99)

    return sorted(files, key=key)


def main() -> None:
    import arcticdb as adb
    from arcticdb import Arctic

    files = _month_files_chronological()
    if not files:
        sys.exit(f"no tick parquet under {SRC_DIR}")

    # --- sanity block before the long run (protocol rule 5) ---
    print("=" * 64)
    print("ARCTICDB MIGRATION — CS-GOLD-DUKAS-TICK -> lmdb 'ticks/XAUUSD'")
    print("=" * 64)
    print(f"arcticdb        : {adb.__version__}")
    print(f"source months   : {len(files)}  ({files[0].parent.parent.name}/{files[0].parent.name}"
          f" .. {files[-1].parent.parent.name}/{files[-1].parent.name})")
    print(f"expected ticks  : {EXPECTED_TICKS:,}")
    print(f"target store    : {STORE}  (map_size=16GB)")
    print(f"seal (IS/OOS)   : {SEAL_DATE}")
    print("-" * 64)

    STORE.mkdir(parents=True, exist_ok=True)
    ac = Arctic(URI)
    lib = ac.get_library(LIB, create_if_missing=True)
    if SYMBOL in lib.list_symbols():
        print(f"[migrate] symbol '{SYMBOL}' exists -> deleting for clean rebuild")
        lib.delete(SYMBOL)

    t0 = time.time()
    running_max: pd.Timestamp | None = None
    total = 0

    for i, f in enumerate(tqdm(files, desc="migrate", unit="month")):
        df = pd.read_parquet(f, columns=COLS)
        df["ts_utc"] = pd.to_datetime(df["ts_utc"])
        df = df.sort_values("ts_utc").set_index("ts_utc")

        if not df.index.is_monotonic_increasing:        # must be true post-sort
            sys.exit(f"FATAL: {f.name} index not monotonic after sort")
        if running_max is not None and df.index[0] <= running_max:
            # cross-month overlap would break the global sort — abort loudly
            sys.exit(f"FATAL: {f.name} first ts {df.index[0]} <= prev max {running_max} "
                     f"(out-of-order partitions; migration would corrupt the time index)")

        if i == 0:
            lib.write(SYMBOL, df)
        else:
            lib.append(SYMBOL, df, validate_index=True)

        running_max = df.index[-1]
        total += len(df)
        tqdm.write(f"  {f.parent.parent.name}/{f.parent.name:<8} +{len(df):>10,}  cum={total:>13,}  "
                   f"[{df.index[0]} .. {df.index[-1]}]")

    # stamp metadata (new version, same data)
    meta = {
        "seal_date": SEAL_DATE,
        "source": "CS-GOLD-DUKAS-TICK parquet (Dukascopy)",
        "parquet_rows_expected": EXPECTED_TICKS,
        "rows_written": total,
        "n_months": len(files),
        "migrated_at": pd.Timestamp.utcnow().isoformat(),
    }
    lib.write_metadata(SYMBOL, meta)

    elapsed = time.time() - t0
    print("-" * 64)
    print(f"[migrate] wrote {total:,} ticks across {len(files)} months in {elapsed/60:.1f} min")
    match = total == EXPECTED_TICKS
    print(f"[migrate] row-count vs parquet ground truth: {'MATCH' if match else 'MISMATCH'} "
          f"({total:,} vs {EXPECTED_TICKS:,})")
    print("=" * 64)
    print(f"VERDICT: {'PASS' if match else 'CHECK — row count mismatch'}")
    sys.exit(0 if match else 1)


if __name__ == "__main__":
    main()
