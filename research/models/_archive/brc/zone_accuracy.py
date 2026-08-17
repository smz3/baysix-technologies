"""
zone_accuracy.py — BRC Zone-Accuracy Study, Tier-1 (EXPLORATORY).

Spec: docs/specs/2026-06-24_brc_zone_accuracy_study.md

Question (the G2 premise we skipped): does price respect a BRC zone more than a
random level? NO entry rule, NO cost, NO sizing.

Metric = `continued` (oracle): after the L1 retest, a bar CLOSES >= +1R in the break
direction before invalidation, entry=L1, R=|L1-L2|, death=close beyond L2 (=entry∓1R).
=> a SYMMETRIC ±1R close-based first-passage from the retest bar.

KEY STRUCTURAL FACT: a symmetric ±1R close barrier on a (near-)martingale is a coin
flip — its null respect rate is 50.0% BY CONSTRUCTION, independent of whether the level
is "special". Level-selection can only move it via local drift/momentum. So:
    real respect (ORACLE `continued`, from tester_zones) vs null = 50.0%.
We CONFIRM the 50% null empirically with an arctic-internal first-passage from RANDOM
bars, and CONFIRM arctic faithfulness per-TF by reproducing the oracle respect with an
arctic-internal first-passage from the REAL retest bars (entry px = arctic close at the
bar, NOT the dukascopy L1 — mixing sources inflates the favorable side).

Tier-1 EXPLORATORY — go/no-go, NEVER a gate verdict (MT5 tester is the arbiter).
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from research.code.io import arctic_io as aio

RO = f"file:{(REPO / 'research' / 'db' / 'research.db').as_posix()}?mode=ro"
OUT = REPO / "research" / "outputs" / "brc"
RUN_ID = 5
TFS = ["M5", "M15", "M30", "H1", "H4", "D1"]
MAXH = 500
NULL_MULT = 3
NULL_CAP = 40_000
SEED = 7


def load_zones(tf):
    con = sqlite3.connect(RO, uri=True)
    df = pd.read_sql(
        "select direction,l1,l2,t1_time,continued from tester_zones "
        "where run_id=? and tf=? and t1_time is not null",
        con, params=(RUN_ID, tf))
    con.close()
    df["t1_time"] = pd.to_datetime(df["t1_time"]).values.astype("datetime64[ns]")
    df["R"] = (df.l1 - df.l2).abs()
    df["up"] = (df.direction == "BUY").to_numpy()
    return df[df.R > 0].reset_index(drop=True)


def load_bars(tf, venue):
    b = aio.bars(tf, venue=venue, columns=["close"])
    idx = b.index
    if idx.tz is not None:
        idx = idx.tz_localize(None)
    return idx.values.astype("datetime64[ns]"), b["close"].to_numpy(dtype=float)


def first_passage_from_bar(times, closes, entry_time, R, up, maxh=MAXH):
    """±1R close first-passage using the ARCTIC CLOSE at the entry bar as entry px.
    1=favorable first, 0=adverse first, 2=censored, -1=no data."""
    i = int(np.searchsorted(times, np.datetime64(entry_time), side="left"))
    if i >= len(closes):
        return -1
    seg = closes[i:min(i + maxh, len(closes))]
    e = closes[i]
    fav = (seg >= e + R) if up else (seg <= e - R)
    adv = (seg <= e - R) if up else (seg >= e + R)
    fi = int(np.argmax(fav)) if fav.any() else -1
    ai = int(np.argmax(adv)) if adv.any() else -1
    if fi == -1 and ai == -1:
        return 2
    if fi == -1:
        return 0
    if ai == -1:
        return 1
    return 1 if fi < ai else 0


def run(times, closes, et, R, up):
    out = np.empty(len(et), dtype=np.int8)
    for k in range(len(et)):
        out[k] = first_passage_from_bar(times, closes, et[k], R[k], up[k])
    return out


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (p, c - h, c + h)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    res = {"null_model": "martingale 50% (symmetric ±1R close barrier)", "per_tf": {}}
    print("=== BRC Zone-Accuracy (Tier-1 EXPLORATORY) ===")
    print(f"{'TF':4s} {'n':>6s} {'oracle%':>8s} {'z_vs50':>7s} | "
          f"{'arc_real%':>9s} {'arc_null%':>9s} {'parity':>7s}")
    for tf in TFS:
        z = load_zones(tf)
        n = len(z)
        k_or = int(z.continued.sum())
        p_or, lo, hi = wilson(k_or, n)
        z_or = (p_or - 0.5) / np.sqrt(0.25 / n)

        # arctic-internal real (faithfulness) + null (confirm 50%): pick best venue by parity
        best = None
        for venue in ("UTC", "JM_EET"):
            t, c = load_bars(tf, venue)
            rr = run(t, c, z.t1_time.to_numpy(), z.R.to_numpy(), z.up.to_numpy())
            rok = rr >= 0
            p_ar = float(np.where(rr[rok] == 1, 1, 0).mean())
            parity = 1 - abs(p_ar - p_or)
            if best is None or parity > best["parity"]:
                best = {"venue": venue, "arc_real": p_ar, "parity": parity,
                        "t": t, "c": c}
        t, c = best["t"], best["c"]
        nn = min(NULL_MULT * n, NULL_CAP)
        idx = rng.integers(0, max(1, len(c) - MAXH), nn)
        nres = run(t, c, t[idx], rng.choice(z.R.to_numpy(), nn), rng.random(nn) < 0.5)
        nok = nres >= 0
        p_null = float(np.where(nres[nok] == 1, 1, 0).mean())

        res["per_tf"][tf] = {
            "n": n, "oracle_respect": p_or, "oracle_ci": [lo, hi], "z_vs_50": z_or,
            "venue": best["venue"], "arctic_real": best["arc_real"],
            "parity": best["parity"], "arctic_null": p_null,
            "gross_ER_1to1": 2 * p_or - 1,
        }
        print(f"{tf:4s} {n:6d} {p_or*100:8.2f} {z_or:+7.2f} | "
              f"{best['arc_real']*100:9.2f} {p_null*100:9.2f} {best['parity']:7.3f}")

    (OUT / "zone_accuracy_tier1.json").write_text(json.dumps(res, indent=2, default=float))
    print(f"\nwrote {OUT / 'zone_accuracy_tier1.json'}")
    return res


if __name__ == "__main__":
    main()
