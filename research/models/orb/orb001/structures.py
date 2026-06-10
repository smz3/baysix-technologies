"""
ORB-001 entry/structure variation sweep (backlog task 9).

Exit_study already swept FIXED targets {1,1.5,2,3R,EOD}xN -> 3R won; not re-tested.
Plain range-minutes N already swept (5 won); not re-tested. This covers the
genuinely-untested space, all on IS (config selection keeps OOS sealed), vs the
frozen +0.3114R baseline:

  base_3R        : frozen (immediate entry, 1R stop, fixed 3R target)  [must repro]
  breakeven_1R   : immediate entry; once +1R reached, stop -> entry (BE); target 3R
  trail_1R       : immediate entry; trail stop 1 range_w behind running peak, let run
  partial_1p5R   : immediate; exit half at +1.5R + move runner to BE, runner target 3R
  retest_3R      : RETEST entry - after breakout wait for pullback to the level, enter
                   on the retest (honest: no retest -> no trade). 1R stop, 3R target.

Plus a cheap range-width EDGE filter: bucket frozen trades by range_w quartile ->
does E[R] depend on opening-range width? (filter signal, not sizing/DD.)

Triggers use the same bid/ask half-spread convention as orb_backtest (spread =
win-rate drag). profit_dir = +1 long / -1 short unifies the two sides.

Outputs -> research/outputs/orb/structures/
  structures_arms.csv, rangewidth_buckets.csv, structures_summary.json, structures.png

    python research/models/orb/structures.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from research.models.orb.orb001.orb_backtest import edge_stats, run_backtest_multi
from research.models.orb.orb001.orb_core import _tick_files, IS_END, LONDON_ANCHOR_HOUR

OR_MIN = 5
TARGET_R = 3.0
SPREAD = 2.0 * 0.10
EOD_HOUR = 21
ARMS = ["base_3R", "breakeven_1R", "trail_1R", "partial_1p5R", "retest_3R"]

_OUT = Path(__file__).resolve().parents[4] / "research" / "outputs" / "orb" / "structures"
NS_H = 3_600_000_000_000
NS_M = 60_000_000_000
NS_D = 86_400_000_000_000


def _exit_R(g, exit_fill_adj, e, range_w, half, arm):
    """Given favorable-distance series g = profit_dir*(emid - e) and the per-tick
    exit-fill adjustment, return (R, done). All exits resolved by index search.
    g >= x  means +x/range_w favorable; stop levels expressed in g-space."""
    rw = range_w
    n = g.shape[0]

    def first(mask):
        return int(np.argmax(mask)) if mask.any() else None

    # common: original 1R stop is g <= -rw + half ; 3R target is g >= 3*rw + half
    i_stop0 = first(g <= -rw + half)
    i_tgt = first(g >= 3 * rw + half)

    if arm == "base_3R":
        cands = [(i_tgt, 3.0), (i_stop0, -1.0)]
    elif arm == "breakeven_1R":
        i_1R = first(g >= 1 * rw + half)           # +1R reached -> arm BE
        if i_1R is not None and (i_stop0 is None or i_1R < i_stop0):
            # BE stop after i_1R: g back to <= 0 + half (entry)
            rel = g[i_1R:] <= 0 + half
            i_be = (i_1R + int(np.argmax(rel))) if rel.any() else None
            be_R = (exit_fill_adj[i_be]) if i_be is not None else None
            cands = [(i_tgt, 3.0), (i_be, be_R)]
        else:
            cands = [(i_tgt, 3.0), (i_stop0, -1.0)]
    elif arm == "trail_1R":
        peak = np.maximum.accumulate(g)
        rel = g <= peak - rw + half                # 1R below running peak
        i_x = first(rel)
        if i_x is not None:
            cands = [(i_x, exit_fill_adj[i_x])]
        else:
            cands = [(None, None)]
    elif arm == "partial_1p5R":
        i_15 = first(g >= 1.5 * rw + half)
        if i_15 is None or (i_stop0 is not None and i_stop0 < i_15):
            cands = [(i_tgt, 3.0), (i_stop0, -1.0)]   # never scaled -> normal trade
        else:
            # half locked at +1.5R; runner BE-stop or 3R target after i_15
            rel_be = g[i_15:] <= 0 + half
            i_be = (i_15 + int(np.argmax(rel_be))) if rel_be.any() else None
            i_t2 = first(g >= 3 * rw + half)
            if i_t2 is not None and (i_be is None or i_t2 <= i_be):
                run_R = 3.0
            elif i_be is not None:
                run_R = exit_fill_adj[i_be]
            else:
                run_R = exit_fill_adj[-1]             # runner to EOD
            return 0.5 * 1.5 + 0.5 * run_R, True
    else:
        cands = [(i_tgt, 3.0), (i_stop0, -1.0)]

    cands = [(i, r) for i, r in cands if i is not None]
    if not cands:
        return exit_fill_adj[-1], False               # EOD flat
    i_best, r_best = min(cands, key=lambda c: c[0])
    return r_best, True


def _simulate_day(ts, mid, day0, arm):
    half = SPREAD * 0.5
    anchor = day0 + LONDON_ANCHOR_HOUR * NS_H
    or_end = anchor + OR_MIN * NS_M
    eod = day0 + EOD_HOUR * NS_H
    in_or = (ts >= anchor) & (ts < or_end)
    if not in_or.any():
        return None
    or_hi, or_lo = mid[in_or].max(), mid[in_or].min()
    range_w = or_hi - or_lo
    if range_w <= 0:
        return None
    post = (ts >= or_end) & (ts < eod)
    if not post.any():
        return None
    pmid = mid[post]

    up = pmid >= or_hi - half
    dn = pmid <= or_lo + half
    i_up = int(np.argmax(up)) if up.any() else None
    i_dn = int(np.argmax(dn)) if dn.any() else None
    if i_up is None and i_dn is None:
        return None
    if i_dn is None or (i_up is not None and i_up <= i_dn):
        pdir, e, i_b = 1.0, or_hi, i_up
    else:
        pdir, e, i_b = -1.0, or_lo, i_dn

    i_entry = i_b
    if arm == "retest_3R":
        # after breakout at i_b, wait for price to PULL BACK to the level, enter there.
        after = pmid[i_b + 1:]
        if len(after) == 0:
            return None
        back = (after <= or_hi + half) if pdir > 0 else (after >= or_lo - half)
        if not back.any():
            return None                                # no retest -> no trade (honest)
        i_entry = i_b + 1 + int(np.argmax(back))

    emid = pmid[i_entry:]
    if len(emid) < 2:
        return None
    g = pdir * (emid - e)
    exit_fill = emid - pdir * half                     # close long on bid, short on ask
    exit_fill_adj = pdir * (exit_fill - e) / range_w   # realized R if exit at each tick
    R, _ = _exit_R(g, exit_fill_adj, e, range_w, half, arm)
    return {"direction": "long" if pdir > 0 else "short", "range_w": range_w,
            "outcome": "x", "R": float(R)}


def run_is():
    from tqdm import tqdm
    files = _tick_files(None)
    is_cut = np.datetime64(IS_END)
    trades = {a: [] for a in ARMS}
    for f in tqdm(files, desc="structures IS"):
        df = pd.read_parquet(f, columns=["ts_utc", "bid", "ask"])
        df = df[df["ts_utc"].values < is_cut]
        if df.empty:
            continue
        ts_all = df["ts_utc"].values.astype("datetime64[ns]").astype(np.int64)
        mid_all = (df["bid"].values + df["ask"].values) * 0.5
        day_key = ts_all // NS_D
        for d in np.unique(day_key):
            m = day_key == d
            tsd, midd, day0 = ts_all[m], mid_all[m], int(d) * NS_D
            for a in ARMS:
                tr = _simulate_day(tsd, midd, day0, a)
                if tr is not None:
                    tr["date"] = pd.Timestamp(day0).date()
                    trades[a].append(tr)
    return {a: pd.DataFrame(rows) for a, rows in trades.items()}


def _stat(a, tr):
    # win = positive R (these exits aren't all clean target/stop)
    R = tr["R"].values
    n = len(R)
    mean, sd = float(R.mean()), float(R.std(ddof=1))
    t = mean / (sd / np.sqrt(n)) if sd > 0 else np.nan
    return {"arm": a, "n": n, "E_R": mean, "se_R": sd / np.sqrt(n),
            "t_stat": t, "win_rate": float((R > 0).mean())}


def main():
    _OUT.mkdir(parents=True, exist_ok=True)
    print("=" * 84)
    print("ORB-001 STRUCTURE SWEEP (task 9)  |  IS 2016->2024-05  |  vs frozen +0.3114R")
    print("=" * 84)
    runs = run_is()

    print("\n----- STRUCTURE ARMS (IS) -----")
    rows = []
    for a in ARMS:
        r = _stat(a, runs[a]); rows.append(r)
        print(f"  {a:13s}: E[R] {r['E_R']:+.4f} +/- {r['se_R']:.4f}  t {r['t_stat']:+.2f}  "
              f"win {r['win_rate']:.1%}  (n={r['n']})")
    df = pd.DataFrame(rows).set_index("arm")
    base = df.loc["base_3R", "E_R"]
    repro = abs(base - 0.3114) < 0.01
    print(f"\n  baseline repro of +0.3114R: {'OK' if repro else 'MISMATCH'} ({base:+.4f})")
    best = df.drop("base_3R")["E_R"].idxmax()
    print(f"  best non-baseline arm: {best}  E[R] {df.loc[best,'E_R']:+.4f} "
          f"(vs base {base:+.4f}, delta {df.loc[best,'E_R']-base:+.4f})")

    # ---- cheap range-width EDGE filter (frozen config trades) -------------
    print("\n----- RANGE-WIDTH EDGE FILTER (frozen 3R trades, IS quartiles) -----")
    frozen = run_backtest_multi(None, n_list=[OR_MIN], is_only=True,
                                spread_price=SPREAD, target_R=TARGET_R)[OR_MIN]
    frozen["q"] = pd.qcut(frozen["range_w"], 4, labels=["Q1_narrow", "Q2", "Q3", "Q4_wide"])
    rw_rows = []
    for q, g in frozen.groupby("q", observed=True):
        s = edge_stats(g)
        rw_rows.append({"quartile": q, "n": s["n_trades"], "E_R": s["E_R"],
                        "t": s["t_stat"], "win": s["win_rate"],
                        "rw_lo": float(g["range_w"].min()), "rw_hi": float(g["range_w"].max())})
        print(f"  {q:10s}: E[R] {s['E_R']:+.4f}  t {s['t_stat']:+.2f}  win {s['win_rate']:.1%}  "
              f"(n={s['n_trades']}, range_w ${g['range_w'].min():.1f}-${g['range_w'].max():.1f})")
    rw_df = pd.DataFrame(rw_rows)

    df.to_csv(_OUT / "structures_arms.csv")
    rw_df.to_csv(_OUT / "rangewidth_buckets.csv", index=False)
    summary = {"model": "ORB-001", "analysis": "structure_sweep_task9",
               "baseline_repro_ok": bool(repro),
               "arms": df.reset_index().to_dict(orient="records"),
               "best_nonbase_arm": best, "best_nonbase_E_R": float(df.loc[best, "E_R"]),
               "range_width_buckets": rw_rows}
    (_OUT / "structures_summary.json").write_text(json.dumps(summary, indent=2, default=str))

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(df.index, df["E_R"], yerr=df["se_R"], capsize=4, color="#3b7dd8", alpha=0.9)
    ax.axhline(0.3114, color="green", ls="--", lw=1.1, label="frozen +0.3114R")
    ax.axhline(0, color="black", lw=0.8)
    ax.set_ylabel("E[R] per trade (IS)")
    ax.set_title("ORB-001 structure variations (task 9) — IS")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(_OUT / "structures.png", dpi=120)
    print(f"\nWrote outputs -> {_OUT}")

    print("\n" + "=" * 84)
    delta = df.loc[best, "E_R"] - base
    print(f"VERDICT: best structure = {best} {df.loc[best,'E_R']:+.4f}R "
          f"({'BEATS' if delta > 0 else 'below'} baseline {base:+.4f} by {delta:+.4f}) | "
          f"range-width edge {'VARIES' if rw_df['E_R'].max()-rw_df['E_R'].min() > 0.15 else 'flat'} "
          f"across quartiles")
    print("=" * 84)


if __name__ == "__main__":
    main()
