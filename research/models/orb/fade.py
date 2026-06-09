"""
ORB-001 failed-breakout FADE — exploratory peek (backlog task 20).

Question: when the first opening-range breakout FAILS (pokes the level then reverses
back inside the range), does FADING it — entering the opposite direction — carry its
own edge? This is the OPPOSITE thesis to ORB-001's (robust breakout-continuation)
edge, so prior is low. Cheap IS-only peek; if it pays, it is a SEPARATE idea (ORB-003
with its own gate ladder), NOT an ORB-001 variant.

DESIGN:
  * Failed breakout = first breakout pokes or_hi (long) / or_lo (short), then price
    returns back INSIDE the range within FAIL_WINDOW minutes. Swept: 15/30/60/None(EOD).
  * Fade entry = opposite direction, on the re-cross back inside. FILLED AT THE ACTUAL
    TICK PRICE (not the level) — the task-19 idealised-fill lesson: a fill booked at a
    level price already left would fabricate edge. Half-spread drag on EXIT only.
  * Mechanics mirror live for comparability: stop 1R = range_w, trail_1R exit.
  * Metric = $/trade (deploy metric; E[R] is a denominator illusion). IS-only.

LIVE CONFIG anchor 09:00/N5 (task 22). Hardcoded to match, like reentry.py.

    python research/code/run_tracked.py fade -- python -X utf8 research/models/orb/fade.py

Outputs -> research/outputs/orb/fade/
    fade_arms.csv  fade_summary.json  fade.png
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from tqdm import tqdm

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from research.models.orb.orb_core import IS_END
from research.models.orb.reentry import _trail_exit, CONTRACT_OZ, MIN_LOT
from research.code.session_cache import session_files

ANCHOR_HOUR = 9
OR_MIN      = 5
SPREAD      = 2.0 * 0.10
EOD_HOUR    = 21
FAIL_WINDOWS = [15, 30, 60, None]      # minutes to "fail back inside"; None = anytime before EOD
NS_H = 3_600_000_000_000
NS_M =    60_000_000_000
NS_D = 86_400_000_000_000
_OUT = REPO / "research" / "outputs" / "orb" / "fade"


def _simulate_day(ts, mid, day0, fail_win_min):
    """First breakout; if it FAILS back inside within fail_win_min, fade the opposite
    direction (honest fill at the actual re-cross tick), trail_1R exit. Returns dict or None."""
    half = SPREAD * 0.5
    anchor = day0 + ANCHOR_HOUR * NS_H
    or_end = anchor + OR_MIN * NS_M
    eod = day0 + EOD_HOUR * NS_H

    in_or = (ts >= anchor) & (ts < or_end)
    if not in_or.any():
        return None
    or_hi, or_lo = mid[in_or].max(), mid[in_or].min()
    rw = or_hi - or_lo
    if rw <= 0:
        return None

    post_mask = (ts >= or_end) & (ts < eod)
    if not post_mask.any():
        return None
    pmid = mid[post_mask]
    pts = ts[post_mask]

    # first breakout (poke) of either side
    up = pmid >= or_hi - half
    dn = pmid <= or_lo + half
    i_up = int(np.argmax(up)) if up.any() else None
    i_dn = int(np.argmax(dn)) if dn.any() else None
    if i_up is None and i_dn is None:
        return None
    if i_dn is None or (i_up is not None and i_up <= i_dn):
        poke_dir, level, i_poke = 1.0, or_hi, i_up      # long poke -> fade short
    else:
        poke_dir, level, i_poke = -1.0, or_lo, i_dn     # short poke -> fade long

    # failure = price returns back inside the range after the poke, within the window
    win_end = pts[i_poke] + (fail_win_min * NS_M if fail_win_min is not None else (eod - pts[i_poke]))
    seg = pmid[i_poke + 1:]
    seg_t = pts[i_poke + 1:]
    if len(seg) == 0:
        return None
    inside = (seg < or_hi) if poke_dir > 0 else (seg > or_lo)   # strictly back inside
    in_win = seg_t <= win_end
    fail_mask = inside & in_win
    if not fail_mask.any():
        return None                                      # breakout did not fail (in window) -> no fade
    i_fail = i_poke + 1 + int(np.argmax(fail_mask))

    # fade entry: opposite direction, HONEST fill at the actual re-cross tick price
    fdir = -poke_dir
    e = float(pmid[i_fail])
    emid = pmid[i_fail:]
    if len(emid) < 2:
        return None
    R, _, _ = _trail_exit(emid, e, fdir, rw, half)
    return {"date": pd.Timestamp(day0).date(), "rw": float(rw),
            "fade_dir": "long" if fdir > 0 else "short",
            "entry": e, "level": float(level),
            "fill_gap": float(fdir * (e - level)),       # >0 = entered worse than level (honest); ~0 ideal
            "R": float(R)}


def run_is(fail_win_min):
    files = session_files(None)
    is_cut = np.datetime64(IS_END)
    rows = []
    for f in tqdm(files, desc=f"fade win={fail_win_min}", leave=False):
        df = pd.read_parquet(f, columns=["ts_utc", "bid", "ask"])
        df = df[df["ts_utc"].values < is_cut]
        if df.empty:
            continue
        ts_all = df["ts_utc"].values.astype("datetime64[ns]").astype(np.int64)
        mid_all = (df["bid"].values + df["ask"].values) * 0.5
        day_key = ts_all // NS_D
        for d in np.unique(day_key):
            m = day_key == d
            r = _simulate_day(ts_all[m], mid_all[m], int(d) * NS_D, fail_win_min)
            if r is not None:
                rows.append(r)
    return pd.DataFrame(rows)


def _stat(df, label):
    if len(df) == 0:
        return {"arm": label, "n": 0}
    R = df["R"].values
    n = len(R)
    mean, sd = float(R.mean()), float(R.std(ddof=1)) if n > 1 else 0.0
    t = mean / (sd / np.sqrt(n)) if sd > 0 else np.nan
    dpt = float((df["R"] * df["rw"] * CONTRACT_OZ * MIN_LOT).mean())
    return {"arm": label, "n": n, "E_R": mean, "se_R": (sd / np.sqrt(n)) if n > 1 else np.nan,
            "t_stat": t, "win_rate": float((R > 0).mean()), "dollar_per_trade": dpt,
            "mean_fill_gap": float(df["fill_gap"].mean())}


def main():
    _OUT.mkdir(parents=True, exist_ok=True)
    print("=" * 90)
    print("ORB-001 FAILED-BREAKOUT FADE (task 20, peek) | IS 2016->2024-05 | trail_1R | "
          "anchor 09:00/N5 | NET @ 2-pip")
    print("=" * 90)

    rows = []
    for fw in FAIL_WINDOWS:
        df = run_is(fw)
        label = f"fade_fail<={fw}m" if fw is not None else "fade_fail<=EOD"
        s = _stat(df, label)
        rows.append(s)
        if s["n"] == 0:
            print(f"  {label:18s}: (no failed breakouts)"); continue
        print(f"  {label:18s}: n={s['n']:>4}  E[R] {s['E_R']:+.4f}  t {s['t_stat']:+.2f}  "
              f"win {s['win_rate']:.1%}  $/trade {s['dollar_per_trade']:+.4f}  "
              f"fill_gap ${s['mean_fill_gap']:+.3f}")

    df_arms = pd.DataFrame(rows)
    df_arms.to_csv(_OUT / "fade_arms.csv", index=False)

    valid = [r for r in rows if r["n"] > 0]
    best = max(valid, key=lambda r: r["dollar_per_trade"]) if valid else None
    promising = bool(best and best["dollar_per_trade"] > 0 and (best["t_stat"] or 0) > 2)

    summary = {"model": "ORB-001", "analysis": "failed_breakout_fade_peek_task20",
               "config": {"anchor_hour": ANCHOR_HOUR, "or_min": OR_MIN, "exit": "trail_1R",
                          "spread_price": SPREAD, "fail_windows_min": FAIL_WINDOWS},
               "arms": rows, "best_arm": best["arm"] if best else None,
               "promising": promising,
               "note": "Exploratory IS-only peek. Fade = enter OPPOSITE a failed breakout, "
                       "honest fill at actual re-cross tick (task-19 lesson). $/trade is the "
                       "deploy metric. If promising -> spin out as ORB-003 with its own gate "
                       "ladder; do NOT bolt onto ORB-001."}
    (_OUT / "fade_summary.json").write_text(json.dumps(summary, indent=2, default=str))

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    labels = [r["arm"] for r in valid]
    dpts = [r["dollar_per_trade"] for r in valid]
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(labels, dpts, color=["#3b7dd8" if d > 0 else "#d8743b" for d in dpts], alpha=0.9)
    ax.axhline(0, color="black", lw=0.8)
    ax.set_ylabel("$/trade (IS, min lot)")
    ax.set_title("ORB-001 failed-breakout fade (task 20, peek) — IS")
    ax.tick_params(axis="x", rotation=20)
    fig.tight_layout()
    fig.savefig(_OUT / "fade.png", dpi=120)
    print(f"\nWrote outputs -> {_OUT}")

    print("\n" + "=" * 90)
    if best:
        print(f"VERDICT: best fade arm = {best['arm']}  $/trade {best['dollar_per_trade']:+.4f}  "
              f"t {best['t_stat']:+.2f}  -> {'PROMISING: spin out as ORB-003' if promising else 'FALSIFIED peek (fade has no edge)'}")
    else:
        print("VERDICT: no failed-breakout fade trades found.")
    print("=" * 90)


if __name__ == "__main__":
    main()
