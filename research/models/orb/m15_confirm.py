"""
ORB-001 M15-confirmation entry (backlog task 8).

Hypothesis (Syafiq's trader intuition): the first 15-min candle's DIRECTION is a
bias filter on the M5 opening-range breakout. Only take the breakout if the M15
candle agrees -> trim wrong-side breakouts, keep entry quality.

This is NOT the plain N=15 opening range (already tested, lost: 0.24 vs 0.31R).
The M5 range and its levels are UNCHANGED; M15 is only a directional gate.

Look-ahead guard: the M15 candle (08:00-08:15) does not close until 08:15, but M5
breakouts can fire from 08:05. So ALL gated arms move the entry search to 08:15+.
That delay has its own cost, so we run a 'delay-only' control to separate the
filter's value from the wait's cost.

Three arms (IS only, 2016 -> 2024-05-02; new-config selection keeps OOS sealed):
  baseline      : frozen config, entry from 08:05, both directions   (must repro +0.3114R)
  delay_only    : entry from 08:15, both directions, NO filter        (cost of waiting)
  direction_only: entry from 08:15, ONLY the M15-agreed side          (the hypothesis)
Attribution: direction_only - delay_only = filter value;
             delay_only - baseline       = wait cost.

Config: M5 range, target 3R / stop 1R, 2-pip spread (win-rate-drag), EOD 21:00 UTC.

Outputs -> research/outputs/orb/m15_confirm/
  m15_arms.csv, m15_summary.json, m15_confirm.png

    python research/models/orb/m15_confirm.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from research.models.orb.orb_backtest import edge_stats
from research.models.orb.orb_core import _tick_files, IS_END, LONDON_ANCHOR_HOUR

# ---- FROZEN config -------------------------------------------------------
OR_MIN = 5           # M5 opening range (unchanged from +0.31R config)
CONFIRM_MIN = 15     # M15 confirmation candle
TARGET_R = 3.0
SPREAD = 2.0 * 0.10
EOD_HOUR = 21
ARMS = ["baseline", "delay_only", "direction_only"]

_OUT = Path(__file__).resolve().parents[3] / "research" / "outputs" / "orb" / "m15_confirm"

NS_H = 3_600_000_000_000
NS_M = 60_000_000_000
NS_D = 86_400_000_000_000


def _simulate_day(ts: np.ndarray, mid: np.ndarray, day0: int, arm: str) -> dict | None:
    """One ORB trade for a given arm. Mirrors orb_backtest._simulate_day exit logic;
    differs only in entry-start time and the optional M15 directional filter."""
    half = SPREAD * 0.5
    anchor = day0 + LONDON_ANCHOR_HOUR * NS_H
    or_end = anchor + OR_MIN * NS_M
    confirm_end = anchor + CONFIRM_MIN * NS_M
    eod = day0 + EOD_HOUR * NS_H

    in_or = (ts >= anchor) & (ts < or_end)
    if not in_or.any():
        return None
    or_hi = mid[in_or].max()
    or_lo = mid[in_or].min()
    range_w = or_hi - or_lo
    if range_w <= 0:
        return None

    # M15 bias from the confirmation candle [08:00, 08:15): close - open.
    in_cf = (ts >= anchor) & (ts < confirm_end)
    if not in_cf.any():
        return None
    cf_mid = mid[in_cf]
    bias = "long" if cf_mid[-1] > cf_mid[0] else ("short" if cf_mid[-1] < cf_mid[0] else "none")

    # entry search window depends on arm
    entry_start = or_end if arm == "baseline" else confirm_end
    post = (ts >= entry_start) & (ts < eod)
    if not post.any():
        return None
    pts, pmid = ts[post], mid[post]

    # breakout candidates (fills on bid/ask): long fills on ask, short on bid
    up = pmid >= or_hi - half
    dn = pmid <= or_lo + half
    i_up = int(np.argmax(up)) if up.any() else None
    i_dn = int(np.argmax(dn)) if dn.any() else None

    # direction_only: keep only the M15-agreed side
    if arm == "direction_only":
        if bias == "long":
            i_dn = None
        elif bias == "short":
            i_up = None
        else:
            return None  # flat M15 candle -> no trade

    if i_up is None and i_dn is None:
        return None
    if i_dn is None or (i_up is not None and i_up <= i_dn):
        direction, i_entry, entry = "long", i_up, or_hi
        stop, target = or_lo, or_hi + TARGET_R * range_w
    else:
        direction, i_entry, entry = "short", i_dn, or_lo
        stop, target = or_hi, or_lo - TARGET_R * range_w

    # walk ticks from entry; exits resolve on the opposite quote
    emid = pmid[i_entry:]
    if direction == "long":
        hit_t = emid >= target + half
        hit_s = emid <= stop + half
    else:
        hit_t = emid <= target - half
        hit_s = emid >= stop - half
    i_t = int(np.argmax(hit_t)) if hit_t.any() else None
    i_s = int(np.argmax(hit_s)) if hit_s.any() else None

    if i_t is not None and (i_s is None or i_t <= i_s):
        outcome, R = "target", float(TARGET_R)
    elif i_s is not None:
        outcome, R = "stop", -1.0
    else:
        exit_fill = (emid[-1] - half) if direction == "long" else (emid[-1] + half)
        R = ((exit_fill - entry) if direction == "long" else (entry - exit_fill)) / range_w
        outcome = "eod"

    return {"direction": direction, "range_w": range_w, "bias": bias,
            "outcome": outcome, "R": float(R)}


def run() -> dict[str, pd.DataFrame]:
    from tqdm import tqdm
    files = _tick_files(None)
    if not files:
        raise FileNotFoundError("No tick parquet found")
    is_cut = np.datetime64(IS_END)

    trades = {a: [] for a in ARMS}
    for f in tqdm(files, desc="m15-confirm IS"):
        df = pd.read_parquet(f, columns=["ts_utc", "bid", "ask"])
        df = df[df["ts_utc"].values < is_cut]      # IS only
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


def main() -> None:
    print("=" * 84)
    print("ORB-001 M15-CONFIRMATION ENTRY  |  M5 range, 3R, 2-pip  |  IS 2016->2024-05")
    print("=" * 84)
    _OUT.mkdir(parents=True, exist_ok=True)

    runs = run()
    rows = []
    for a in ARMS:
        tr = runs[a]
        s = edge_stats(tr)
        se = s["sd_R"] / np.sqrt(s["n_trades"]) if s["n_trades"] else np.nan
        rows.append({"arm": a, "n": s["n_trades"], "E_R": s["E_R"], "se_R": se,
                     "t_stat": s["t_stat"], "win_rate": s["win_rate"]})
        print(f"  {a:14s}: E[R] {s['E_R']:+.4f} +/- {se:.4f}  t {s['t_stat']:+.2f}  "
              f"win {s['win_rate']:.1%}  (n={s['n_trades']})")
    df = pd.DataFrame(rows).set_index("arm")

    base, delay, dirn = df.loc["baseline"], df.loc["delay_only"], df.loc["direction_only"]
    wait_cost = delay["E_R"] - base["E_R"]
    filter_val = dirn["E_R"] - delay["E_R"]
    net_vs_base = dirn["E_R"] - base["E_R"]

    # significance of the filter effect: Welch on the two trade pools
    from scipy import stats
    welch = stats.ttest_ind(runs["direction_only"]["R"].values,
                            runs["delay_only"]["R"].values, equal_var=False)

    print("\n----- ATTRIBUTION -----")
    print(f"  wait cost      (delay - base) : {wait_cost:+.4f} R")
    print(f"  FILTER value   (dir - delay)  : {filter_val:+.4f} R   "
          f"(Welch t {welch.statistic:+.2f}, p {welch.pvalue:.4f})")
    print(f"  net vs baseline(dir - base)   : {net_vs_base:+.4f} R")
    repro = abs(base["E_R"] - 0.3114) < 0.01
    print(f"\n  baseline repro of +0.3114R    : {'OK' if repro else 'MISMATCH'} ({base['E_R']:+.4f})")

    df.to_csv(_OUT / "m15_arms.csv")
    summary = {
        "config": {"OR_MIN": OR_MIN, "CONFIRM_MIN": CONFIRM_MIN, "target_R": TARGET_R,
                   "spread_price": SPREAD},
        "is_span": ["2016", "2024-05-02"],
        "arms": df.reset_index().to_dict(orient="records"),
        "wait_cost_R": wait_cost, "filter_value_R": filter_val, "net_vs_base_R": net_vs_base,
        "filter_welch_t": welch.statistic, "filter_welch_p": welch.pvalue,
        "baseline_repro_ok": bool(repro),
    }
    (_OUT / "m15_summary.json").write_text(json.dumps(summary, indent=2))

    # plot: E[R] by arm with +/-1 SE
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(8, 5))
    colors = ["#888888", "#3b7dd8", "#2e9e5b"]
    ax.bar(df.index, df["E_R"], yerr=df["se_R"], capsize=5, color=colors, alpha=0.9)
    ax.axhline(0.3114, color="green", ls="--", lw=1.1, label="frozen IS +0.3114R")
    ax.axhline(0, color="black", lw=0.8)
    ax.set_ylabel("E[R] per trade (IS)")
    ax.set_title("ORB-001 M15-confirmation entry — arm comparison (IS)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(_OUT / "m15_confirm.png", dpi=120)
    print(f"\nWrote outputs -> {_OUT}")

    print("\n" + "=" * 84)
    verdict = ("FILTER ADDS EDGE" if (filter_val > 0 and welch.pvalue < 0.05)
               else "FILTER NO SIGNIFICANT GAIN")
    print(f"VERDICT: {verdict} | direction_only {dirn['E_R']:+.4f}R vs baseline "
          f"{base['E_R']:+.4f}R (net {net_vs_base:+.4f}) | filter alone {filter_val:+.4f} "
          f"p={welch.pvalue:.3f}")
    print("=" * 84)


if __name__ == "__main__":
    main()
