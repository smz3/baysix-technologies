"""
arctic_io.py — the ONE canonical way to read XAUUSD ticks. Replaces every
`pd.read_parquet(glob('CS-GOLD-DUKAS-TICK/...'))` in the codebase.

Two guarantees the old parquet path could not give:
  1. SORTED ALWAYS. ArcticDB stores a monotonic datetime index; every read is
     time-ordered. The unsorted-tick look-ahead ([[orb_unsorted_tick_lookahead]])
     is structurally impossible here — there is no row-position to argmax over.
  2. SEAL ENFORCED. The IS/OOS boundary (2024-05-02) lives in symbol metadata and
     is checked on every read. Reading OOS requires an explicit `allow_oos=True`
     (or the `oos_ticks` helper) — you cannot leak OOS into IS research by accident.

API:
    read_ticks(start, end, columns=None, allow_oos=False, as_column=False) -> DataFrame
    is_ticks(start=None, end=None, columns=None)    # safe IS-only read (< seal)
    oos_ticks(start=None, end=None, columns=None)    # explicit sealed-OOS read (>= seal)
    seal_date() -> pd.Timestamp
    store_info() -> dict     # version/metadata/row count, no tick rows

Returned frame is time-indexed (DatetimeIndex 'ts_utc') by default; pass
as_column=True to get the legacy parquet shape (ts_utc as a plain column).
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
STORE = REPO / "data" / "arctic"
URI = f"lmdb://{STORE.as_posix()}?map_size=16GB"
LIB = "ticks"
SYMBOL = "XAUUSD"
DATA_COLS = ["bid", "ask", "volume"]


@lru_cache(maxsize=1)
def _library():
    from arcticdb import Arctic
    if not STORE.exists():
        raise FileNotFoundError(
            f"ArcticDB store missing at {STORE}. Run research/code/arctic_migrate.py first.")
    return Arctic(URI).get_library(LIB, create_if_missing=False)


@lru_cache(maxsize=1)
def seal_date() -> pd.Timestamp:
    meta = _library().read_metadata(SYMBOL).metadata or {}
    return pd.Timestamp(meta.get("seal_date", "2024-05-02"))


def _norm(ts) -> pd.Timestamp | None:
    return None if ts is None else pd.Timestamp(ts)


def read_ticks(start=None, end=None, columns=None, *,
               allow_oos: bool = False, as_column: bool = False) -> pd.DataFrame:
    """Read a time-ordered tick slice [start, end] (inclusive). Blocks on the seal
    unless allow_oos=True. `columns` subsets DATA_COLS (default all)."""
    start, end = _norm(start), _norm(end)
    seal = seal_date()

    # seal guard: a read that touches >= seal must be explicit
    touches_oos = (end is None) or (end >= seal)
    if touches_oos and not allow_oos:
        raise PermissionError(
            f"read_ticks range (..{end}) enters the sealed OOS boundary {seal.date()}. "
            f"Use is_ticks() for IS, or pass allow_oos=True / oos_ticks() for OOS.")

    date_range = (start, end) if (start is not None or end is not None) else None
    cols = list(columns) if columns else None
    df = _library().read(SYMBOL, date_range=date_range, columns=cols).data

    # defensive: the index must be monotonic — the whole point of this module
    if not df.index.is_monotonic_increasing:
        raise AssertionError("ArcticDB returned a non-monotonic index — store is corrupt.")

    if as_column:
        df = df.reset_index()  # ts_utc becomes a column (legacy parquet shape)
    return df


def is_ticks(start=None, end=None, columns=None, *, as_column: bool = False) -> pd.DataFrame:
    """IS-only read. Clamps the upper bound to just before the seal — never returns OOS."""
    seal = seal_date()
    end = _norm(end)
    is_end = seal - pd.Timedelta(microseconds=1)
    end = is_end if end is None else min(end, is_end)
    return read_ticks(start, end, columns, allow_oos=False, as_column=as_column)


def oos_ticks(start=None, end=None, columns=None, *, as_column: bool = False) -> pd.DataFrame:
    """Explicit sealed-OOS read. Clamps the lower bound to the seal."""
    seal = seal_date()
    start = _norm(start)
    start = seal if start is None else max(start, seal)
    return read_ticks(start, end, columns, allow_oos=True, as_column=as_column)


def store_info() -> dict:
    """Metadata + row count only — never loads tick rows."""
    lib = _library()
    vit_meta = lib.read_metadata(SYMBOL)
    return {
        "symbol": SYMBOL,
        "library": LIB,
        "store": str(STORE),
        "metadata": vit_meta.metadata,
        "version": vit_meta.version,
    }


if __name__ == "__main__":
    # smoke: print store info + a tiny IS aggregate (firewall — no rows printed)
    import json
    info = store_info()
    print(json.dumps({k: v for k, v in info.items() if k != "metadata"}, default=str, indent=2))
    print("metadata:", json.dumps(info["metadata"], default=str, indent=2))
    print("seal_date:", seal_date().date())
