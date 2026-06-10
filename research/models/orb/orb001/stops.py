"""
ORB-001 stop-placement sweep (backlog task 14).

The frozen ORB-001 has ONE stop: 1R = range_w = the opposite opening-range edge
(long entry or_hi, stop or_lo). This is the only stop ever tested. Stop distance
sets the risk unit, so it drives win rate AND the whole downstream DD/survival/cap
package -> it is the biggest untouched core mechanic.

DESIGN (made explicit; alternative considered = hold absolute target, move only the
stop -> rejected because we'd never trade a changed stop at the old target):
  Each arm uses its OWN stop distance D as 1R and keeps the deploy 3:1 reward:risk
  (target = entry +/- 3D). Immediate 08:05 entry is UNCHANGED (entry-trigger axis is
  already exhausted: immediate beats delay/M15/retest). E[R] stays comparable across
  arms because R is always "multiples of that arm's risk", capped [-1, +3].

  base_1R       : D = 1.0 * range_w  (= frozen opposite edge)            [MUST repro +0.3114R]
  rangefrac_*   : D = k * range_w, k in {0.5(=midpoint), 0.75, 1.5, 2.0} (vol-proportional)
  fixedpip_*    : D = ${0.5,1,2,3} absolute price                        (NOT vol-proportional)

ATR stops DEFERRED: range_w IS a per-day volatility measure, so rangefrac_* already
covers the vol-proportional-stop question; a daily-ATR stop is a correlated 3rd vol
proxy needing an extra daily-OHLC build. Noted as a refinement, not run here.

Same bid/ask half-spread convention as orb_backtest (spread = win-rate drag).

Outputs -> research/outputs/orb/stops/
  stops_arms.csv, stops_summary.json, stops.png

    python research/models/orb/stops.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from research.models.orb.orb001.orb_core import _tick_files, IS_END, LONDON_ANCHOR_HOUR

OR_MIN = 5
RR = 3.0                      # reward:risk held at 3:1 in each arm's own R
SPREAD = 2.0 * 0.10           # 2-pip JM Pro round-trip, price units
EOD_HOUR = 21
BASE_REPRO = 0.3114

# (name, kind, param)  kind in {"rangefrac","fixedpip"}
STOP_ARMS = [
    ("base_1R",        "rangefrac", 1.0),    # CONTROL — frozen opposite edge
    ("rangefrac_0p5",  "rangefrac", 0.5),    # = range midpoint stop
    ("rangefrac_0p75", "rangefrac", 0.75),
    ("rangefrac_1p5",  "rangefrac", 1.5),
    ("rangefrac_2p0",  "rangefrac", 2.0),
    ("fixedpip_0p5",   "fixedpip",  0.5),
    ("fixedpip_1p0",   "fixedpip",  1.0),
    ("fixedpip_2p0",   "fixedpip",  2.0),
    ("fixedpip_3p0",   "fixedpip",  3.0),
]

_OUT = Path(__file__).resolve().parents[4] / "research" / "outputs" / "orb" / "stops"
NS_H = 3_600_000_000_000
NS_M = 60_000_000_000
NS_D = 86_400_000_000_000


def _simulate_day(ts, mid, day0, kind, param):
    """One ORB trade for one day with a parameterised stop distance D.
    R is expressed in units of D (this arm's 1R). 3:1 target. Spread = win-rate drag."""
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

    # immediate breakout entry (buy-stop on ask / sell-stop on bid), same as frozen
    up = pmid >= or_hi - half
    dn = pmid <= or_lo + half
    i_up = int(np.argmax(up)) if up.any() else None
    i_dn = int(np.argmax(dn)) if dn.any() else None
    if i_up is None and i_dn is None:
        return None
    if i_dn is None or (i_up is not None and i_up <= i_dn):
        pdir, entry, i_b = 1.0, or_hi, i_up
    else:
        pdir, entry, i_b = -1.0, or_lo, i_dn

    D = param * range_w if kind == "rangefrac" else float(param)
    if D <= 0:
        return None
    stop_lvl = entry - pdir * D
    tgt_lvl = entry + pdir * RR * D

    emid = pmid[i_b:]
    if len(emid) < 2:
        return None
    # exits resolve on the opposite quote (long sells on bid, short buys on ask):
    if pdir > 0:
        hit_t = emid >= tgt_lvl + half
        hit_s = emid <= stop_lvl + half
    else:
        hit_t = emid <= tgt_lvl - half
        hit_s = emid >= stop_lvl - half
    i_t = int(np.argmax(hit_t)) if hit_t.any() else None
    i_s = int(np.argmax(hit_s)) if hit_s.any() else None

    if i_t is not None and (i_s is None or i_t <= i_s):
        outcome, R = "target", RR
    elif i_s is not None:
        outcome, R = "stop", -1.0
    else:                                          # EOD flat, exit on opposite quote
        exit_fill = emid[-1] - pdir * half
        R = float(pdir * (exit_fill - entry) / D)
        outcome = "eod"
    return {"direction": "long" if pdir > 0 else "short", "range_w": float(range_w),
            "D": float(D), "outcome": outcome, "R": float(R)}


def run_is():
    from tqdm import tqdm
    files = _tick_files(None)
    is_cut = np.datetime64(IS_END)
    trades = {a[0]: [] for a in STOP_ARMS}
    for f in tqdm(files, desc="stops IS"):
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
            for name, kind, param in STOP_ARMS:
                tr = _simulate_day(tsd, midd, day0, kind, param)
                if tr is not None:
                    trades[name].append(tr)
    return {a: pd.DataFrame(rows) for a, rows in trades.items()}


def _stat(a, tr):
    R = tr["R"].values
    n = len(R)
    mean, sd = float(R.mean()), float(R.std(ddof=1))
    t = mean / (sd / np.sqrt(n)) if sd > 0 else np.nan
    # DOLLAR expectancy = the deploy metric. R is normalised by the stop, so a tighter
    # stop inflates E[R] mechanically; $/trade = R x dollars-risked tells the real story.
    dollar_R = (tr["R"] * tr["D"]).values            # per-trade $ P&L at 0.01 lot (1oz)
    dollar_E = float(dollar_R.mean())
    return {"arm": a, "n": n, "E_R": mean, "se_R": sd / np.sqrt(n),
            "t_stat": t, "win_rate": float((tr["outcome"] == "target").mean()),
            "stop_rate": float((tr["outcome"] == "stop").mean()),
            "mean_D": float(tr["D"].mean()), "dollar_E_per_trade": dollar_E}


def main():
    _OUT.mkdir(parents=True, exist_ok=True)
    print("=" * 88)
    print("ORB-001 STOP-PLACEMENT SWEEP (task 14) | IS 2016->2024-05 | 3:1 RR | vs frozen +0.3114R")
    print("=" * 88)
    runs = run_is()

    print("\n----- STOP ARMS (IS) -----")
    rows = [_stat(*kv) for kv in [(name, runs[name]) for name, _, _ in STOP_ARMS]]
    for r in rows:
        print(f"  {r['arm']:15s}: E[R] {r['E_R']:+.4f} t {r['t_stat']:+.2f}  "
              f"win {r['win_rate']:.1%}  meanD ${r['mean_D']:.2f}  "
              f"$/trade {r['dollar_E_per_trade']:+.4f}  (n={r['n']})")
    df = pd.DataFrame(rows).set_index("arm")

    base = df.loc["base_1R", "E_R"]
    repro = abs(base - BASE_REPRO) < 0.01
    print(f"\n  baseline repro of +{BASE_REPRO}R: {'OK' if repro else 'MISMATCH'} ({base:+.4f})")
    best_R = df.drop("base_1R")["E_R"].idxmax()
    best_dol = df["dollar_E_per_trade"].idxmax()
    base_dol = df.loc["base_1R", "dollar_E_per_trade"]
    print(f"  best stop by E[R]   : {best_R}  E[R] {df.loc[best_R,'E_R']:+.4f}")
    print(f"  best stop by $/trade: {best_dol}  ${df.loc[best_dol,'dollar_E_per_trade']:+.4f} "
          f"(base_1R ${base_dol:+.4f})")
    best = best_dol

    df.to_csv(_OUT / "stops_arms.csv")
    summary = {"model": "ORB-001", "analysis": "stop_placement_sweep_task14",
               "rr": RR, "spread_price": SPREAD, "baseline_repro_ok": bool(repro),
               "base_E_R": float(base), "base_dollar_E": float(base_dol),
               "arms": df.reset_index().to_dict(orient="records"),
               "best_by_E_R": best_R, "best_by_dollar": best_dol,
               "note": "E[R] ranking (tighter=higher) is a denominator illusion — R is "
                       "normalised by the stop. $/trade is the deploy metric. ATR stops deferred "
                       "(range_w is itself a per-day vol measure). Each arm: own D=1R, 3:1 target, "
                       "immediate entry. IS-only; any winner needs OOS + survival/DD re-run."}
    (_OUT / "stops_summary.json").write_text(json.dumps(summary, indent=2, default=str))

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    colors = ["#888"] + ["#3b7dd8"] * 4 + ["#d8743b"] * 4
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.bar(df.index, df["E_R"], yerr=df["se_R"], capsize=4, color=colors, alpha=0.9)
    ax.axhline(BASE_REPRO, color="green", ls="--", lw=1.1, label=f"frozen +{BASE_REPRO}R")
    ax.axhline(0, color="black", lw=0.8)
    ax.set_ylabel("E[R] per trade (IS, each arm's own R)")
    ax.set_title("ORB-001 stop-placement sweep (task 14) — IS  [blue=range-frac, orange=fixed-pip]")
    ax.legend(fontsize=8)
    plt.xticks(rotation=30, ha="right")
    fig.tight_layout()
    fig.savefig(_OUT / "stops.png", dpi=120)
    print(f"\nWrote outputs -> {_OUT}")

    print("\n" + "=" * 88)
    d_delta = df.loc[best_dol, "dollar_E_per_trade"] - base_dol
    print(f"VERDICT (deploy metric = $/trade): best ${df.loc[best_dol,'dollar_E_per_trade']:+.4f} "
          f"= {best_dol} vs base_1R ${base_dol:+.4f} (delta ${d_delta:+.4f}). "
          f"E[R] 'winner' was {best_R} — a denominator illusion. "
          f"Frozen range_w stop {'NOT beaten in $' if d_delta <= 0.01 else 'beaten in $ — verify fills+OOS'}.")
    print("=" * 88)


if __name__ == "__main__":
    main()
