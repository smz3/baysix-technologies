"""
Session-slice cache (Event-Cache Layer A) — scan the 24GB tick tree ONCE, reuse
for every ORB variant (anchor / window / stop / trail / fill-model).

Design note: braindump/event_cache_layerA.md

WHAT IT IS
    A column-identical, row-reduced copy of the source tick parquet: same schema
    (ts_utc, bid, ask), but only rows inside the 07:00-22:00 UTC session window.
    Drop-in for orb_core._tick_files — consumers read it identically.

WHY IT CANNOT LEAK / LOOK AHEAD
    Pure causal row REDUCTION. We keep raw, point-in-time values only (no
    normalization, no cross-day stats). Each row's (ts_utc, bid, ask) is unchanged
    from source. The IS/OOS boundary is untouched — consumers still slice by
    ts_utc < IS_END exactly as before. Reusing a filtered row is identical to
    re-filtering it live. The window (07:00-22:00) is a strict SUPERSET of every
    anchor (08:00/08:30/09:00) + EOD exit (21:00), with NY-session headroom.

TRUST GUARD
    `verify` re-derives N random month-partitions from raw source and asserts
    byte-equality against the cache. Divergence -> halt. (Second proof: every ORB
    harness reproduces its IS reference E[R] before proceeding and halts on
    mismatch — so a faithless cache would trip the control-repro gate too.)

USAGE
    python research/code/session_cache.py build          # one-time long scan
    python research/code/session_cache.py verify [N=8]    # trust check
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from tqdm import tqdm

_REPO        = Path(__file__).resolve().parents[2]
SRC_DIR      = _REPO / "data" / "parquet" / "CS-GOLD-DUKAS-TICK"
SESSION_DIR  = _REPO / "data" / "parquet" / "session"
COLS         = ["ts_utc", "bid", "ask"]

# Session window (LOCKED 2026-06-09, braindump/event_cache_layerA.md).
WIN_START_H  = 7     # 07:00 UTC inclusive
WIN_END_H    = 22    # 22:00 UTC exclusive
NS_H         = 3_600_000_000_000
NS_D         = 86_400_000_000_000


# ---------------------------------------------------------------------------
# Path helpers — session cache mirrors the source year=Y/month=M partitioning
# ---------------------------------------------------------------------------

def _src_files(year_months=None) -> list[str]:
    if year_months is None:
        return sorted(str(p) for p in SRC_DIR.glob("year=*/month=*/*.parquet"))
    out = []
    for yr, mo in year_months:
        out += [str(p) for p in SRC_DIR.glob(f"year={yr}/month={mo}/*.parquet")]
    return sorted(out)


def session_files(year_months=None) -> list[str]:
    """Drop-in replacement for orb_core._tick_files, reading the session cache."""
    if year_months is None:
        return sorted(str(p) for p in SESSION_DIR.glob("year=*/month=*/*.parquet"))
    out = []
    for yr, mo in year_months:
        out += [str(p) for p in SESSION_DIR.glob(f"year={yr}/month={mo}/*.parquet")]
    return sorted(out)


def _dest_for(src_path: str) -> Path:
    """year=2016/month=10/<name>.parquet under SESSION_DIR (mirror partitioning)."""
    p = Path(src_path)
    return SESSION_DIR / p.parts[-3] / p.parts[-2] / p.name


# ---------------------------------------------------------------------------
# Core filter — keep only rows whose UTC time-of-day is in [07:00, 22:00)
# ---------------------------------------------------------------------------

def _session_mask(ts_ns: np.ndarray) -> np.ndarray:
    tod = ts_ns % NS_D
    return (tod >= WIN_START_H * NS_H) & (tod < WIN_END_H * NS_H)


def _filter_session(df: pd.DataFrame) -> pd.DataFrame:
    ts_ns = df["ts_utc"].values.astype("datetime64[ns]").astype(np.int64)
    return df.loc[_session_mask(ts_ns)].reset_index(drop=True)


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build_session_cache() -> None:
    files = _src_files(None)
    if not files:
        raise FileNotFoundError(f"No source tick parquet under {SRC_DIR}")

    print("=" * 80)
    print("SESSION-SLICE CACHE BUILD (Event-Cache Layer A)")
    print(f"  source     : {SRC_DIR}")
    print(f"  dest       : {SESSION_DIR}")
    print(f"  window     : {WIN_START_H:02d}:00-{WIN_END_H:02d}:00 UTC (superset of all ORB anchors+exit)")
    print(f"  partitions : {len(files)} source files")
    print("=" * 80)

    tot_in = tot_out = 0
    for f in tqdm(files, desc="session-slice", unit="file"):
        df = pd.read_parquet(f, columns=COLS)
        n_in = len(df)
        sess = _filter_session(df)
        n_out = len(sess)
        dest = _dest_for(f)
        dest.parent.mkdir(parents=True, exist_ok=True)
        sess.to_parquet(dest, index=False)
        tot_in += n_in
        tot_out += n_out
        pct = (n_out / n_in * 100.0) if n_in else 0.0
        ym = f"{Path(f).parents[1].name}/{Path(f).parent.name}"
        tqdm.write(f"  {ym:>16}: {n_in:>10,} -> {n_out:>10,} ticks kept ({pct:4.1f}%)")

    kept = (tot_out / tot_in * 100.0) if tot_in else 0.0
    print("-" * 80)
    print(f"  TOTAL: {tot_in:,} -> {tot_out:,} ticks kept ({kept:.1f}%)")
    print(f"  cache written -> {SESSION_DIR}")
    print(f"  next: run  python research/code/session_cache.py verify  before trusting it")
    print("=" * 80)


# ---------------------------------------------------------------------------
# Verify — re-derive N random month-partitions from raw, assert equality
# ---------------------------------------------------------------------------

def verify(n: int = 8, seed: int = 42) -> bool:
    src = _src_files(None)
    if not src:
        raise FileNotFoundError(f"No source tick parquet under {SRC_DIR}")
    rng = np.random.default_rng(seed)
    sample = sorted(rng.choice(len(src), size=min(n, len(src)), replace=False).tolist())

    print("=" * 80)
    print(f"SESSION-CACHE VERIFY — {len(sample)} random month-partitions re-derived from raw")
    print("=" * 80)
    all_ok = True
    for i in sample:
        f = src[i]
        ym = f"{Path(f).parents[1].name}/{Path(f).parent.name}"
        dest = _dest_for(f)
        if not dest.exists():
            print(f"  {ym:>16}: *** MISSING cache file -> {dest}")
            all_ok = False
            continue
        expected = _filter_session(pd.read_parquet(f, columns=COLS))
        cached = pd.read_parquet(dest, columns=COLS).reset_index(drop=True)
        try:
            pd.testing.assert_frame_equal(expected, cached, check_dtype=True)
            days = pd.to_datetime(cached["ts_utc"]).dt.normalize().nunique() if len(cached) else 0
            print(f"  {ym:>16}: OK  ({len(cached):>9,} ticks, {days} days)")
        except AssertionError as e:
            print(f"  {ym:>16}: *** MISMATCH\n      {str(e).splitlines()[0]}")
            all_ok = False

    print("-" * 80)
    print("  VERIFY PASSED — cache faithful to source." if all_ok
          else "  *** VERIFY FAILED — cache stale/corrupt. Rebuild before use.")
    print("=" * 80)
    return all_ok


# ---------------------------------------------------------------------------

def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"
    if cmd == "build":
        build_session_cache()
    elif cmd == "verify":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 8
        ok = verify(n)
        sys.exit(0 if ok else 1)
    else:
        print(f"unknown command: {cmd!r}. use 'build' or 'verify'.")
        sys.exit(2)


if __name__ == "__main__":
    main()
