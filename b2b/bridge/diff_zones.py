"""
Objective parity diff: Python detection vs the live EA's logged zones.

Ground truth = the EA's QUANT_ZONES_*.csv exports (Common/Files/SIGMA_Quant/Zones).
Input        = the broker's own bars pulled via the bridge (same data the EA used).

We run Python detection on the broker bars and match its zones against the EA's
CREATED zones by (direction, L1, L2, created_time). Match rate tells us whether
the Python port reproduces the live system; mismatches pinpoint divergences.

Usage: python b2b/bridge/diff_zones.py [d1|h4|h1]
"""
import glob
import os
import sys

import pandas as pd

B2B_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, B2B_ROOT)
REPO = os.path.abspath(os.path.join(B2B_ROOT, ".."))

from sigma_core.b2b.detectors.swing_points import detect_swings        # noqa: E402
from sigma_core.b2b.detectors.b2b_engine import detect_b2b_zones       # noqa: E402

ZONES_DIR = ("C:/Users/User/AppData/Roaming/MetaQuotes/Terminal/Common/Files/"
             "SIGMA_Quant/Zones")
TF_MAP = {"d1": "PERIOD_D1", "h4": "PERIOD_H4", "h1": "PERIOD_H1"}
DIR_MAP = {"BUY": "BULLISH", "SELL": "BEARISH"}


def load_ea_zones(tf_period):
    frames = []
    for f in sorted(glob.glob(os.path.join(ZONES_DIR, "QUANT_ZONES_*.csv"))):
        try:
            frames.append(pd.read_csv(f, encoding="utf-16", sep=","))
        except Exception:
            pass
    df = pd.concat(frames, ignore_index=True)
    df = df[(df.event_type == "CREATED") & (df.tf == tf_period)].copy()
    df["created_time"] = pd.to_datetime(df["created_time"], format="%Y.%m.%d %H:%M:%S")
    df["dir"] = df["direction"].map(DIR_MAP)
    df["key"] = list(zip(df["dir"], df["l1_price"].round(2),
                         df["l2_price"].round(2), df["created_time"]))
    return df.drop_duplicates("key")   # EA re-logs daily -> dedup to unique zones


def python_zones(tf):
    fp = os.path.join(REPO, "data", "parquet", "bars", "mt5", f"xauusd_{tf}_mt5.parquet")
    df = pd.read_parquet(fp).sort_values("time").reset_index(drop=True)
    swings = detect_swings(df)
    zones = detect_b2b_zones(df, swings, tf=tf.upper())
    keys = set()
    for z in zones:
        keys.add((z.direction.name, round(z.L1_price, 2), round(z.L2_price, 2),
                  pd.Timestamp(z.zone_created_time)))
    return df, zones, keys


def main():
    tf = (sys.argv[1] if len(sys.argv) > 1 else "d1").lower()
    ea = load_ea_zones(TF_MAP[tf])
    ea_keys = set(ea["key"])
    df, zones, py_keys = python_zones(tf)

    matched = ea_keys & py_keys
    ea_only = ea_keys - py_keys          # EA has it, Python missed
    py_only = py_keys - ea_keys          # Python made it, EA didn't

    print(f"=== {tf.upper()} parity: Python vs EA ===")
    print(f"broker bars: {len(df)}  {df.time.min()} -> {df.time.max()}")
    print(f"EA zones (unique CREATED): {len(ea_keys)}")
    print(f"Python zones:              {len(py_keys)}")
    print(f"MATCHED:   {len(matched)}  ({100*len(matched)/max(len(ea_keys),1):.1f}% of EA)")
    print(f"EA-only (Python missed):   {len(ea_only)}")
    print(f"Python-only (extra):       {len(py_only)}")

    def show(label, keys, n=8):
        ks = sorted(keys, key=lambda k: k[3])[:n]
        print(f"\n  {label} (first {len(ks)}):")
        for d, l1, l2, t in ks:
            print(f"    {d:8} L1={l1:>9.2f} L2={l2:>9.2f}  {t}")
    if ea_only:
        show("EA-only", ea_only)
    if py_only:
        show("Python-only", py_only)


if __name__ == "__main__":
    main()
