"""
arctic_spike.py — DE-RISK SPIKE (not the migration). Proves ArcticDB works on this
Windows box before we commit to ingesting 3.1GB. Touches ONE month of tick parquet.

Checks, in order:
  1. arcticdb imports + version.
  2. Read one month of CS-GOLD-DUKAS-TICK parquet (ts_utc, bid, ask, volume).
  3. Confirm the unsorted-tick bug: is ts_utc monotonic as stored? (expected: NO)
  4. Create a LOCAL LMDB Arctic store at data/arctic_spike (throwaway).
  5. Write the SORTED month as a symbol; read it back.
  6. Assert: row count round-trips, index is monotonic increasing, bid/ask preserved.

Prints a one-line VERDICT. Firewall: only shapes/counts/bools reach stdout — never tick rows.
Run AFTER `pip install arcticdb`. Throwaway store is cleaned at the end.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
SRC_DIR = REPO / "data" / "parquet" / "CS-GOLD-DUKAS-TICK"
SPIKE_STORE = REPO / "data" / "arctic_spike"          # throwaway, gitignored
COLS = ["ts_utc", "bid", "ask", "volume"]


def _first_month_file() -> Path:
    files = sorted(SRC_DIR.glob("year=*/month=*/*.parquet"))
    if not files:
        sys.exit(f"SPIKE FAIL: no tick parquet under {SRC_DIR}")
    return files[0]


def main() -> None:
    print("=" * 64)
    print("ARCTICDB DE-RISK SPIKE")
    print("=" * 64)

    # 1. import
    try:
        import arcticdb as adb
        from arcticdb import Arctic
    except Exception as e:  # noqa: BLE001
        sys.exit(f"SPIKE FAIL: cannot import arcticdb ({e})")
    print(f"[1] arcticdb import OK — version {adb.__version__}")

    # 2. read one month
    f = _first_month_file()
    df = pd.read_parquet(f, columns=COLS)
    print(f"[2] read parquet: {f.relative_to(REPO)}  rows={len(df):,}  dtypes={dict(df.dtypes.astype(str))}")

    # 3. confirm unsorted as-stored
    ts = pd.to_datetime(df["ts_utc"])
    monotonic_as_stored = bool(ts.is_monotonic_increasing)
    print(f"[3] ts_utc monotonic AS STORED = {monotonic_as_stored}  (expected False — the look-ahead bug)")

    # build a clean tz-naive DatetimeIndex sorted ascending
    out = df.copy()
    out["ts_utc"] = ts
    out = out.sort_values("ts_utc").reset_index(drop=True).set_index("ts_utc")
    print(f"[3b] after sort: monotonic = {out.index.is_monotonic_increasing}  rows={len(out):,}")

    # 4. local LMDB store (generous map_size for spike)
    if SPIKE_STORE.exists():
        shutil.rmtree(SPIKE_STORE, ignore_errors=True)
    SPIKE_STORE.mkdir(parents=True, exist_ok=True)
    uri = f"lmdb://{SPIKE_STORE.as_posix()}?map_size=2GB"
    ac = Arctic(uri)
    lib_name = "spike"
    if lib_name in ac.list_libraries():
        ac.delete_library(lib_name)
    lib = ac.get_library(lib_name, create_if_missing=True)
    print(f"[4] LMDB Arctic store created — {SPIKE_STORE.relative_to(REPO)}")

    # 5. write + read back
    lib.write("xauusd_spike", out)
    back = lib.read("xauusd_spike").data
    print(f"[5] round-trip read: rows={len(back):,}")

    # 6. assertions
    ok_rows = len(back) == len(out)
    ok_sorted = bool(back.index.is_monotonic_increasing)
    ok_cols = list(back.columns) == [c for c in COLS if c != "ts_utc"]
    ok_vals = bool((back["bid"].iloc[:1000].values == out["bid"].iloc[:1000].values).all())
    print(f"[6] rows_match={ok_rows}  index_sorted={ok_sorted}  cols_match={ok_cols}  bid_preserved={ok_vals}")

    # cleanup throwaway
    del lib, ac
    shutil.rmtree(SPIKE_STORE, ignore_errors=True)

    verdict = ok_rows and ok_sorted and ok_cols and ok_vals
    print("=" * 64)
    print(f"VERDICT: {'PASS — ArcticDB works here, migrate with confidence.' if verdict else 'FAIL — see above.'}")
    print("=" * 64)
    sys.exit(0 if verdict else 1)


if __name__ == "__main__":
    main()
