"""
Pin the tester UTC-offset bug from RAW ticks (cache starts 08:00, too late).

EA builds OR over server-time [09:00,09:05]. If server = true_UTC + OFF, the EA's OR
in true UTC is [09:00-OFF, 09:05-OFF]. For each OOS session compute the mid-OR at
candidate UTC anchor hours 6..9 (OFF = 9-h) and find which best matches the EA's
ACTUAL OR boundary (init_sl from the report). Per-month best-hour reveals DST drift.

    python -X utf8 research/models/orb/orb001/fidelity_offset.py
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from research.code.arctic_io import read_tick_month
from tqdm import tqdm

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
from research.models.orb.orb001.orb_core import _tick_files
from research.models.orb.orb001.trail_oos import OR_MIN, IS_END_TS, OOS_MONTHS, NS_D, NS_H, NS_M

OUT = REPO / "research" / "outputs" / "orb" / "fidelity"
HOURS = [6, 7, 8, 9]   # OFF = 9 - h


def main():
    files = _tick_files(OOS_MONTHS)
    is_cut = np.datetime64(IS_END_TS)
    rows = []
    for f in tqdm(files, desc="raw OR"):
        df = read_tick_month(f, columns=["ts_utc", "bid", "ask"])
        ts_all = df["ts_utc"].values.astype("datetime64[ns]").astype(np.int64)
        keep = ts_all >= int(is_cut.astype("datetime64[ns]").astype(np.int64))
        hod = (ts_all % NS_D)
        keep &= (hod >= 6 * NS_H) & (hod < 10 * NS_H)   # only the morning slice we need
        if not keep.any():
            continue
        ts = ts_all[keep]
        mid = (df["bid"].values[keep] + df["ask"].values[keep]) * 0.5
        dk = ts // NS_D
        for d in np.unique(dk):
            mk = dk == d
            tsd, midd, day0 = ts[mk], mid[mk], int(d) * NS_D
            rec = {"session_date": pd.Timestamp(day0).strftime("%Y-%m-%d")}
            for h in HOURS:
                a = day0 + h * NS_H
                in_or = (tsd >= a) & (tsd < a + OR_MIN * NS_M)
                if in_or.any():
                    rec[f"or_lo_{h}"] = midd[in_or].min()
                    rec[f"or_hi_{h}"] = midd[in_or].max()
            rows.append(rec)
    em = pd.DataFrame(rows)

    te = pd.read_csv(OUT / "tester_trades_parsed.csv")[["session_date", "direction", "init_sl"]]
    j = te.merge(em, on="session_date", how="inner")

    # EA's actual OR boundary = init_sl (long->or_low, short->or_high). Per session, best hour.
    def boundary_col(h, direction):
        return f"or_lo_{h}" if direction == "long" else f"or_hi_{h}"

    best_hours = []
    for _, r in j.iterrows():
        errs = {}
        for h in HOURS:
            col = boundary_col(h, r["direction"])
            if col in j.columns and pd.notna(r.get(col)):
                errs[h] = abs(r["init_sl"] - r[col])
        if errs:
            best_hours.append({"session_date": r["session_date"],
                               "month": r["session_date"][:7],
                               "best_h": min(errs, key=errs.get),
                               "best_err": min(errs.values())})
    bh = pd.DataFrame(best_hours)

    print("\n" + "=" * 64)
    print("OFFSET — median |EA init_sl - emulated OR| per anchor hour")
    print("=" * 64)
    longs = j[j.direction == "long"]; shorts = j[j.direction == "short"]
    print("  hour OFF  longs    shorts   combined")
    for h in HOURS:
        lo = f"or_lo_{h}"; hi = f"or_hi_{h}"
        dl = (longs["init_sl"] - longs[lo]).abs().median() if lo in j.columns else float("nan")
        ds = (shorts["init_sl"] - shorts[hi]).abs().median() if hi in j.columns else float("nan")
        print(f"   {h:>2}  {9-h:>2}   {dl:7.3f}  {ds:7.3f}   {(dl+ds)/2:7.3f}")

    print(f"\n  Per-session BEST-matching hour (n={len(bh)}):")
    print("   ", bh["best_h"].value_counts().sort_index().to_dict())
    print(f"   median best-match error: {bh['best_err'].median():.3f}")
    print("\n  Best hour by month (DST drift check):")
    piv = bh.groupby("month")["best_h"].agg(lambda s: s.mode().iloc[0])
    for mth, h in piv.items():
        print(f"    {mth}: anchor {h} (offset {9-h})")
    bh.to_csv(OUT / "offset_best_hours.csv", index=False)


if __name__ == "__main__":
    main()
