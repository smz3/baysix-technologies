"""
ORB-001 reconciliation — does the LOGGED Gate-6 OOS edge reproduce TODAY?

result_id 62 (anchor_oos.py) logged 09:00/N5 OOS dollar-per-trade = +7.6222 (n=526).
Fork A (raw parquet, same _simulate_day) gives -0.02 (n=526). Same function, same
trade count, opposite sign. The only difference is the DATA SOURCE: the validated
runs read the SESSION-CACHE; Fork A reads RAW PARQUET.

This script settles which dataset the edge lives in by running the IDENTICAL
anchor_oos._scan/_stats on BOTH sources, then diffing per-day OR + R for samples.

    python -X utf8 research/models/orb/orb001/reconcile_cache_vs_parquet.py
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
from research.models.orb.orb001.orb_core import _tick_files, IS_END
from research.models.orb.orb001.anchor_oos import _simulate_day, _scan, _stats, OOS_MONTHS
from research.code.session_cache import session_files

IS_CUT = np.datetime64(IS_END)
NS_D = 86_400_000_000_000


def stats_from(files, label):
    rows = _scan(files, 9.0, 5, oos=True, slip_extra=0.0, desc=label)
    s = _stats(rows)
    print(f"  {label:<26} n={s['n']:>4}  E[R]={s['E_R']:+.4f}  win={s['win_pct']:>5}%  "
          f"$/t={s['dollar_per_trade']:+.4f}  t={s['t_stat']}")
    return s


def per_day_table(files, source_name):
    """Return {date_int: (or_hi, or_lo, rw, R)} for OOS days, one breakout/day."""
    out = {}
    for f in files:
        df = pd.read_parquet(f, columns=["ts_utc", "bid", "ask"]).sort_values("ts_utc")
        tsv = df["ts_utc"].values
        df = df[tsv >= IS_CUT]
        if df.empty:
            continue
        ts = df["ts_utc"].values.astype("datetime64[ns]").astype(np.int64)
        mid = (df["bid"].values + df["ask"].values) * 0.5
        dk = ts // NS_D
        for d in np.unique(dk):
            mk = dk == d
            r = _simulate_day(ts[mk], mid[mk], int(d) * NS_D, 9.0, 5)
            if r is not None:
                out[int(d)] = (round(r["range_w"], 4), round(r["R"], 4))
    return out


def main():
    print("=" * 92)
    print("ORB-001 RECONCILE — session-cache vs raw parquet, anchor_oos 09:00/N5 OOS")
    print("=" * 92)

    cache_files   = session_files(OOS_MONTHS)
    parquet_files = _tick_files(OOS_MONTHS)
    print(f"  cache files:   {len(cache_files)}")
    print(f"  parquet files: {len(parquet_files)}")
    print()

    print("AGGREGATE (reproduce logged result_id 62 = +7.6222 $/t):")
    s_cache = stats_from(cache_files,   "SESSION-CACHE")
    s_pq    = stats_from(parquet_files, "RAW PARQUET")
    print()
    print(f"  result_id 62 logged value: +7.6222  ->  cache reproduces: "
          f"{'YES' if abs((s_cache['dollar_per_trade'] or 0) - 7.6222) < 0.5 else 'NO'}")
    print()

    # per-day diff on overlapping days
    print("PER-DAY DIFF (first 15 OOS days where cache vs parquet R differ):")
    cache_d = per_day_table(cache_files,   "cache")
    pq_d    = per_day_table(parquet_files, "parquet")
    common = sorted(set(cache_d) & set(pq_d))
    print(f"  cache days={len(cache_d)}  parquet days={len(pq_d)}  common={len(common)}")
    print(f"  {'date':<12} {'rw_cache':>9} {'rw_pq':>9} {'R_cache':>9} {'R_pq':>9}  diff?")
    shown = 0
    n_diff = 0
    for d in common:
        rwc, Rc = cache_d[d]; rwp, Rp = pq_d[d]
        differ = abs(Rc - Rp) > 0.01 or abs(rwc - rwp) > 0.01
        if differ:
            n_diff += 1
            if shown < 15:
                date = str(np.datetime64(d, "D"))
                print(f"  {date:<12} {rwc:>9} {rwp:>9} {Rc:>9} {Rp:>9}  DIFF")
                shown += 1
    print(f"  ... total days with differing R or range_w: {n_diff}/{len(common)}")
    print("=" * 92)


if __name__ == "__main__":
    main()
