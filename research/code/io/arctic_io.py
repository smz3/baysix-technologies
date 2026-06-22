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

REPO = Path(__file__).resolve().parents[3]
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


def _span() -> tuple[pd.Timestamp, pd.Timestamp]:
    """Cheap [first, last] tick timestamp from symbol description — no rows read."""
    desc = _library().get_description(SYMBOL)
    lo, hi = desc.date_range
    lo, hi = pd.Timestamp(lo), pd.Timestamp(hi)
    if lo.tzinfo is not None:
        lo = lo.tz_localize(None)
    if hi.tzinfo is not None:
        hi = hi.tz_localize(None)
    return lo, hi


def tick_months(year_months=None) -> list[tuple[int, int]]:
    """Drop-in replacement for the old `_tick_files`/`session_files`: the list of
    (year, month) partitions to iterate. With no arg, every month present in the
    store (derived from its index span — no rows read)."""
    if year_months is not None:
        return [(int(y), int(m)) for (y, m) in year_months]
    lo, hi = _span()
    periods = pd.period_range(lo, hi, freq="M")
    return [(p.year, p.month) for p in periods]


def read_tick_month(ym, columns=None, *, as_column: bool = True) -> pd.DataFrame:
    """Read ONE (year, month) partition, time-SORTED, from the Arctic store.

    Drop-in for the old `pd.read_parquet(f, columns=["ts_utc","bid","ask"])` loop
    body. `columns` may still name "ts_utc" (it's the index → returned as a column
    when as_column=True); only bid/ask/volume are actual data columns. Spans the
    seal freely (allow_oos): callers slice IS/OOS by ts themselves, and the sort —
    not the seal — is what kills the look-ahead."""
    y, m = int(ym[0]), int(ym[1])
    start = pd.Timestamp(year=y, month=m, day=1)
    end = start + pd.offsets.MonthBegin(1) - pd.Timedelta(microseconds=1)
    data_cols = None
    if columns:
        data_cols = [c for c in columns if c != "ts_utc"] or None
    return read_ticks(start, end, data_cols, allow_oos=True, as_column=as_column)


M1_SYMBOL = "XAUUSD_M1"


def build_m1_symbol() -> int:
    """One-time (long) derive of a SORTED 1-minute mid-OHLCV base from the tick
    store, written as Arctic symbol XAUUSD_M1. This is the CANONICAL multi-TF base
    (task 76): every higher TF is resampled from it on-read, so there is one source
    of truth and no cross-TF boundary drift.

    Two deliberate choices, locked in struct001_m1_base_timezone_design:
      • STORED IN PURE UTC — the Dukascopy tick index is UTC and NO broker offset is
        baked in here. The venue/DST offset (JM=EET UTC+2/+3, etc.) is applied later
        at derive/resample time, so this one base serves JM / FTMO / Darwinex.
      • FULL OHLCV (mid) per minute — not close-only. Storing true per-minute high/low
        means higher-TF high/low (max/min of M1 H/L) is also exact, so a future
        wick/high-low rule (task 74) needs NO tick re-scan. Basis is MID (matches
        XAUUSD_DAILY); MT5 chart bars are bid → a consistent half-spread offset.

    Run explicitly (rule 12, new window):
        python research/code/io/arctic_io.py build-m1
    Returns the number of M1 rows written."""
    from tqdm import tqdm
    frames = []
    for ym in tqdm(tick_months(), desc="derive M1 OHLCV"):
        df = read_tick_month(ym, columns=["bid", "ask", "volume"], as_column=False)
        if df.empty:
            continue
        mid = (df["bid"] + df["ask"]) * 0.5
        bars = mid.resample("1min").ohlc()
        bars["volume"] = df["volume"].resample("1min").sum()
        bars = bars.dropna(subset=["open"])  # drop minutes with no ticks
        frames.append(bars)
    m1 = pd.concat(frames).sort_index()
    m1 = m1[~m1.index.duplicated(keep="first")]
    m1.index.name = "ts_utc"
    lib = _library()
    lib.write(M1_SYMBOL, m1, metadata={
        "derived_from": SYMBOL, "tz": "UTC", "price_basis": "mid",
        "freq": "1min", "seal_date": str(seal_date().date()),
        "built_at": pd.Timestamp.utcnow().isoformat()})
    return len(m1)


def m1_bars(start=None, end=None, columns=None) -> pd.DataFrame:
    """Sorted 1-minute mid-OHLCV base (open/high/low/close/volume), DatetimeIndex
    'ts_utc' in PURE UTC. Reads the XAUUSD_M1 Arctic symbol. Optional [start, end]
    slice. This is the source the higher-TF derive layer resamples from."""
    lib = _library()
    if M1_SYMBOL not in lib.list_symbols():
        raise FileNotFoundError(
            f"Arctic symbol {M1_SYMBOL} not built. Run (new window): "
            f"python research/code/io/arctic_io.py build-m1")
    date_range = (_norm(start), _norm(end)) if (start is not None or end is not None) else None
    df = lib.read(M1_SYMBOL, date_range=date_range,
                  columns=list(columns) if columns else None).data
    if not df.index.is_monotonic_increasing:
        raise AssertionError("XAUUSD_M1 index non-monotonic — rebuild.")
    return df


# --- multi-TF derive layer (task 76) -----------------------------------------
# All higher TFs are resampled on-read from XAUUSD_M1. One source of truth, no
# cross-TF boundary drift. Bars are bucketed on the BROKER wall clock so edges
# land where MT5's do — venue/DST handled here, NOT baked into the M1 base.

# Real DST-observing zones (NOT fixed "EET"): JM & most MT5 gold brokers run
# EET = UTC+2 winter / UTC+3 summer on the EU calendar. Confirm Darwinex before use.
VENUE_TZ = {
    "JM_EET": "Europe/Bucharest",    # JustMarkets (XAUUSD live) — EET/EEST
    "FTMO_EET": "Europe/Bucharest",  # FTMO — same EET family
    "UTC": "UTC",                    # neutral / Dukascopy-native
}

# pandas resample rule per TF. Bars are labelled by OPEN time (closed/label left),
# matching MT5's bar-open convention.
TF_RULE = {
    "M1": "1min", "M5": "5min", "M15": "15min", "M30": "30min",
    "H1": "1h", "H4": "4h", "D1": "1D", "W1": "W-MON", "MN1": "MS",
}
_OHLCV_AGG = {"open": "first", "high": "max", "low": "min",
              "close": "last", "volume": "sum"}


@lru_cache(maxsize=64)
def _bars_cached(tf: str, venue: str) -> pd.DataFrame:
    rule = TF_RULE[tf]
    tz = VENUE_TZ[venue]
    m1 = m1_bars()  # full XAUUSD_M1, UTC, mid-OHLCV
    if tz != "UTC":
        # to broker wall clock: localize UTC -> convert -> drop tz (keep wall time).
        # Integer-hour offset means M5..H1 already align on absolute time; H4/D1/
        # W1/MN1 need this local anchoring. DST fall-back makes one wall hour repeat
        # -> sort so resample stays monotonic (the dup hour merges, as MT5 does).
        local = m1.index.tz_localize("UTC").tz_convert(tz).tz_localize(None)
        m1 = m1.set_axis(local).sort_index()
    if tf == "M1":
        return m1
    bars = (m1.resample(rule, label="left", closed="left")
              .agg(_OHLCV_AGG).dropna(subset=["open"]))
    bars.index.name = "time"
    return bars


def bars(tf: str, venue: str = "JM_EET", *, start=None, end=None,
         columns=None) -> pd.DataFrame:
    """Higher-TF OHLCV bars derived on-read from XAUUSD_M1, bucketed on the venue's
    broker wall clock (DST-aware). tf in {M1,M5,M15,M30,H1,H4,D1,W1,MN1};
    venue in VENUE_TZ (default JM_EET = JustMarkets). Index 'time' is the bar-OPEN
    in BROKER local wall time (UTC for venue='UTC'). lru_cached per (tf, venue).

    NOTE: D1 and below are the verified path (M5..H1 align on absolute time; H4/D1
    anchor to broker midnight). W1/MN1 anchoring is best-effort EU-calendar —
    cross-check against MT5 before trusting weekly/monthly structure."""
    tf, venue = tf.upper(), venue.upper()
    if tf not in TF_RULE:
        raise ValueError(f"unknown tf {tf!r}; one of {sorted(TF_RULE)}")
    if venue not in VENUE_TZ:
        raise ValueError(f"unknown venue {venue!r}; one of {sorted(VENUE_TZ)}")
    df = _bars_cached(tf, venue)
    if start is not None or end is not None:
        df = df.loc[_norm(start):_norm(end)]
    if columns is not None:
        df = df[list(columns)]
    return df.copy()


DAILY_SYMBOL = "XAUUSD_DAILY"


def build_daily_symbol() -> int:
    """One-time (long) derive of a SORTED daily mid-OHLC series from the tick store,
    written as a second Arctic symbol (XAUUSD_DAILY) — replaces the old, suspect
    data/parquet/daily/xauusd_daily.parquet whose close was a last-by-POSITION tick
    on unsorted data. Run explicitly (rule 12, new window):
        python research/code/io/arctic_io.py build-daily
    Returns the number of daily rows written."""
    from tqdm import tqdm
    frames = []
    for ym in tqdm(tick_months(), desc="derive daily OHLC"):
        df = read_tick_month(ym, columns=["bid", "ask"], as_column=False)
        mid = (df["bid"] + df["ask"]) * 0.5
        bars = mid.resample("1D").ohlc().dropna(how="all")
        frames.append(bars)
    daily = pd.concat(frames).sort_index()
    daily = daily[~daily.index.duplicated(keep="first")]
    daily.index.name = "date"
    lib = _library()
    lib.write(DAILY_SYMBOL, daily, metadata={
        "derived_from": SYMBOL, "seal_date": str(seal_date().date()),
        "built_at": pd.Timestamp.utcnow().isoformat()})
    return len(daily)


def daily_bars(columns=None) -> pd.DataFrame:
    """Sorted daily mid-OHLC (open/high/low/close), DatetimeIndex 'date'. Reads the
    XAUUSD_DAILY Arctic symbol. Drop-in for the old
    `pd.read_parquet("data/parquet/daily/xauusd_daily.parquet")`."""
    lib = _library()
    if DAILY_SYMBOL not in lib.list_symbols():
        raise FileNotFoundError(
            f"Arctic symbol {DAILY_SYMBOL} not built. Run (new window): "
            f"python research/code/io/arctic_io.py build-daily")
    df = lib.read(DAILY_SYMBOL, columns=list(columns) if columns else None).data
    if not df.index.is_monotonic_increasing:
        raise AssertionError("XAUUSD_DAILY index non-monotonic — rebuild.")
    return df


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
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "build-m1":
        n = build_m1_symbol()
        print(f"XAUUSD_M1 built: {n:,} minute rows.")
        sys.exit(0)
    if len(sys.argv) > 1 and sys.argv[1] == "build-daily":
        n = build_daily_symbol()
        print(f"XAUUSD_DAILY built: {n:,} daily rows.")
        sys.exit(0)
    # smoke: print store info + a tiny IS aggregate (firewall — no rows printed)
    import json
    info = store_info()
    print(json.dumps({k: v for k, v in info.items() if k != "metadata"}, default=str, indent=2))
    print("metadata:", json.dumps(info["metadata"], default=str, indent=2))
    print("seal_date:", seal_date().date())
