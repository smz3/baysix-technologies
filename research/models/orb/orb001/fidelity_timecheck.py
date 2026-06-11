"""
Definitive time-base test: at which UTC offset does the EA's entry FILL price match
the true Dukascopy price at (entry_ts - offset)? A long fills at ask (~mid+half), a
short at bid (~mid-half), so the correct offset gives small signed gap (~+/-0.1).

If NO offset yields a clean match, the tester's custom symbol data is not the same
series as data/parquet (a DATA problem, not an EA port-logic problem).

    python -X utf8 research/models/orb/orb001/fidelity_timecheck.py
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from tqdm import tqdm

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
from research.models.orb.orb001.orb_core import _tick_files
from research.models.orb.orb001.trail_oos import OOS_MONTHS, NS_D, NS_H

OUT = REPO / "research" / "outputs" / "orb" / "fidelity"


def main():
    # Build a true-UTC tick table (mid) over the morning..evening band (hours 4-22)
    mids = []
    for f in tqdm(_tick_files(OOS_MONTHS), desc="raw load"):
        d = pd.read_parquet(f, columns=["ts_utc", "bid", "ask"])
        ts = d["ts_utc"].values.astype("datetime64[ns]").astype(np.int64)
        hod = ts % NS_D
        keep = (hod >= 4 * NS_H) & (hod < 22 * NS_H)
        d = d[keep]
        d["mid"] = (d["bid"].values + d["ask"].values) * 0.5
        mids.append(d[["ts_utc", "mid"]])
    tk = pd.concat(mids).sort_values("ts_utc").reset_index(drop=True)
    tk["ts_utc"] = pd.to_datetime(tk["ts_utc"]).astype("datetime64[ns]")

    te = pd.read_csv(OUT / "tester_trades_parsed.csv")
    te["entry_ut"] = pd.to_datetime(
        te["entry_ts"].str.replace(".", "-", regex=False).str.slice(0, 10) + " "
        + te["entry_ts"].str.slice(11), errors="coerce").astype("datetime64[ns]")
    te = te.dropna(subset=["entry_ut"])

    print("\n" + "=" * 60)
    print("ENTRY-PRICE TIME-BASE TEST  (entry_px vs true mid at entry_ts - offset)")
    print("=" * 60)
    print("  offset  matched   median|gap|   %|gap|<0.5   mean(signed)")
    for off in [0, 1, 2, 3, 4]:
        t2 = te.copy()
        t2["q"] = (t2["entry_ut"] - pd.Timedelta(hours=off)).astype("datetime64[ns]")
        t2 = t2.sort_values("q")
        m = pd.merge_asof(t2, tk, left_on="q", right_on="ts_utc",
                          direction="nearest", tolerance=pd.Timedelta("90s"))
        ok = m["mid"].notna()
        gap = m.loc[ok, "entry_px"] - m.loc[ok, "mid"]
        ag = gap.abs()
        print(f"    {off}     {ok.sum():>4}/{len(m)}   {ag.median():9.3f}    "
              f"{(ag<0.5).mean()*100:7.1f}     {gap.mean():+.3f}")

    print("\n  Interpretation: the offset with median|gap|~0.1-0.3 and high %<0.5 is the")
    print("  true server->UTC offset. If none is clean, tester data != data/parquet.")


if __name__ == "__main__":
    main()
