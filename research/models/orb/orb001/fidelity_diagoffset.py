"""
Measure the tester time-base offset EXACTLY from the EA's diagnostic CSV.

The EA logged, per session, the OHLC of the bar it labelled "09:00" (a bid M1 bar).
Match that 4-value fingerprint to true 1-minute BID bars from the research parquet;
the true minute it matches reveals offset = 09:00 - true_minute. Per-month -> DST.

    python -X utf8 research/models/orb/orb001/fidelity_diagoffset.py
"""
from __future__ import annotations
import os
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from tqdm import tqdm

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
from research.models.orb.orb001.orb_core import _tick_files
from research.models.orb.orb001.trail_oos import NS_D, NS_H

DIAG = Path(os.environ["APPDATA"]) / "MetaQuotes" / "Terminal" / "Common" / "Files" / "orb001_diag.csv"
OUT = REPO / "research" / "outputs" / "orb" / "fidelity"


def main():
    dg = pd.read_csv(DIAG)
    dg["date"] = dg["utc_date"].str.replace(".", "-", regex=False)
    months = sorted({(int(x[:4]), int(x[5:7])) for x in dg["date"]})

    # Build true 1-min BID bars (hours 04-12) over the diag months
    bars = []
    for f in tqdm(_tick_files(months), desc="raw->1min bid"):
        d = pd.read_parquet(f, columns=["ts_utc", "bid"])
        ts = d["ts_utc"].values.astype("datetime64[ns]").astype(np.int64)
        hod = ts % NS_D
        keep = (hod >= 4 * NS_H) & (hod < 12 * NS_H)
        if not keep.any():
            continue
        t = pd.DataFrame({"min": (ts[keep] // (60_000_000_000)) * 60_000_000_000,
                          "bid": d["bid"].values[keep]})
        g = t.groupby("min")["bid"].agg(["first", "max", "min", "last"])
        g.columns = ["o", "h", "l", "c"]
        bars.append(g.reset_index())
    bb = pd.concat(bars).drop_duplicates("min").set_index("min").sort_index()
    bb_ts = bb.index.values
    O, H, L, C = bb["o"].values, bb["h"].values, bb["l"].values, bb["c"].values

    rows = []
    for _, r in dg.iterrows():
        day0 = pd.Timestamp(r["date"]).value // NS_D * NS_D
        # candidate minutes on that date in [04:00, 11:00)
        lo = day0 + 4 * NS_H
        hi = day0 + 11 * NS_H
        sel = (bb_ts >= lo) & (bb_ts < hi)
        if not sel.any():
            continue
        idx = np.where(sel)[0]
        err = (np.abs(O[idx] - r["bar0_o"]) + np.abs(H[idx] - r["bar0_h"])
               + np.abs(L[idx] - r["bar0_l"]) + np.abs(C[idx] - r["bar0_c"]))
        j = idx[int(np.argmin(err))]
        matched_min = int(bb_ts[j])
        true_hod_min = (matched_min - day0) / NS_H * 60.0   # minutes-of-day /60 -> hours; keep minutes
        true_hhmm = pd.Timestamp(matched_min).strftime("%H:%M")
        offset_min = (9 * 60) - int(round((matched_min - day0) / 60_000_000_000))
        rows.append({"date": r["date"], "month": r["date"][:7],
                     "ea_bar0_hhmm": "09:00", "true_match_hhmm": true_hhmm,
                     "offset_hours": offset_min / 60.0, "match_err": float(err.min())})
    res = pd.DataFrame(rows)
    res.to_csv(OUT / "diag_offset.csv", index=False)

    print("\n" + "=" * 60)
    print("TESTER TIME-BASE OFFSET (from EA 09:00 bar vs true bid bars)")
    print("=" * 60)
    good = res[res["match_err"] < 0.5]
    print(f"  sessions matched (err<0.5): {len(good)}/{len(res)}   median match_err={res['match_err'].median():.3f}")
    print(f"  offset_hours: median={good['offset_hours'].median():.2f}  "
          f"distribution={good['offset_hours'].round(1).value_counts().sort_index().to_dict()}")
    print("\n  offset by month (DST drift):")
    for m, g in good.groupby("month"):
        print(f"    {m}: offset {g['offset_hours'].median():.2f}h  (n={len(g)}, err={g['match_err'].median():.3f})")


if __name__ == "__main__":
    main()
