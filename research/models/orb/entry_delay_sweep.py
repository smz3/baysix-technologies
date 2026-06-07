"""
ORB-001 entry-delay sweep + sealed OOS (backlog task 12).

Lead (from M15 task-8 control): delaying the M5-breakout entry from 08:05 to 08:15
lifted IS E[R] +0.31 -> +0.45R. BUT that control used IDEALISED fills (entered at
or_hi even on days price had already broken before 08:15 — unfillable). This script
re-tests the delay HONESTLY:

  realistic delayed entry: arm at 08:00+D. If price is ALREADY beyond the level at
  the arm time, the move is missed -> NO trade. Otherwise take the first genuine
  cross of or_hi/or_lo after the arm time, filled at the level (legit stop order).
  -> waiting forgoes the early-breakout days; that is the true cost of delay.

Protocol (single sealed holdout):
  1. IS sweep over arm-delays {10,15,20,30} min (realistic), frozen 08:05 baseline ref.
  2. Pick the best IS delay (by E[R]).  n_trials = 4 (the searched delays).
  3. ONE sealed-OOS confirmation on that single winner + baseline. OOS is the verdict;
     IS winner level is selection-biased, so we trust OOS, not IS.

Config: M5 range, target 3R / stop 1R, 2-pip spread (win-rate-drag), EOD 21:00 UTC.

Outputs -> research/outputs/orb/entry_delay/
  delay_is_sweep.csv, delay_summary.json, entry_delay.png

    python research/models/orb/entry_delay_sweep.py
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

OR_MIN = 5
TARGET_R = 3.0
SPREAD = 2.0 * 0.10
EOD_HOUR = 21
SWEEP_DELAYS = [10, 15, 20, 30]     # realistic delayed entries (minutes from 08:00)
BASELINE_DELAY = 5                  # frozen 08:05 entry (reference, no skip)

_OUT = Path(__file__).resolve().parents[3] / "research" / "outputs" / "orb" / "entry_delay"

NS_H = 3_600_000_000_000
NS_M = 60_000_000_000
NS_D = 86_400_000_000_000


def _simulate_day(ts, mid, day0, delay_min, realistic):
    """One ORB trade. realistic=False -> frozen baseline (entry from 08:05, no skip).
    realistic=True -> arm at 08:00+delay; skip if already broken at arm; else first
    fresh cross of the level after arm."""
    half = SPREAD * 0.5
    anchor = day0 + LONDON_ANCHOR_HOUR * NS_H
    or_end = anchor + OR_MIN * NS_M
    arm = anchor + delay_min * NS_M
    eod = day0 + EOD_HOUR * NS_H

    in_or = (ts >= anchor) & (ts < or_end)
    if not in_or.any():
        return None
    or_hi, or_lo = mid[in_or].max(), mid[in_or].min()
    range_w = or_hi - or_lo
    if range_w <= 0:
        return None

    post = (ts >= arm) & (ts < eod)
    if not post.any():
        return None
    pmid = mid[post]

    if realistic:
        # already beyond the level at the arm tick -> missed the move, no trade.
        if pmid[0] >= or_hi - half or pmid[0] <= or_lo + half:
            return None

    up = pmid >= or_hi - half
    dn = pmid <= or_lo + half
    i_up = int(np.argmax(up)) if up.any() else None
    i_dn = int(np.argmax(dn)) if dn.any() else None
    if i_up is None and i_dn is None:
        return None
    if i_dn is None or (i_up is not None and i_up <= i_dn):
        direction, i_entry, entry = "long", i_up, or_hi
        stop, target = or_lo, or_hi + TARGET_R * range_w
    else:
        direction, i_entry, entry = "short", i_dn, or_lo
        stop, target = or_hi, or_lo - TARGET_R * range_w

    emid = pmid[i_entry:]
    if direction == "long":
        hit_t, hit_s = emid >= target + half, emid <= stop + half
    else:
        hit_t, hit_s = emid <= target - half, emid >= stop - half
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
    return {"direction": direction, "range_w": range_w, "outcome": outcome, "R": float(R)}


def _run(arms, oos):
    """arms: list of (label, delay_min, realistic). oos: False=IS (<seal), True=OOS(>=seal)."""
    from tqdm import tqdm
    files = _tick_files(None)
    is_cut = np.datetime64(IS_END)
    trades = {lbl: [] for lbl, _, _ in arms}
    tag = "OOS" if oos else "IS"
    for f in tqdm(files, desc=f"delay {tag}"):
        df = pd.read_parquet(f, columns=["ts_utc", "bid", "ask"])
        v = df["ts_utc"].values
        df = df[v >= is_cut] if oos else df[v < is_cut]
        if df.empty:
            continue
        ts_all = df["ts_utc"].values.astype("datetime64[ns]").astype(np.int64)
        mid_all = (df["bid"].values + df["ask"].values) * 0.5
        day_key = ts_all // NS_D
        for d in np.unique(day_key):
            m = day_key == d
            tsd, midd, day0 = ts_all[m], mid_all[m], int(d) * NS_D
            for lbl, dl, rl in arms:
                tr = _simulate_day(tsd, midd, day0, dl, rl)
                if tr is not None:
                    trades[lbl].append(tr)
    return {lbl: pd.DataFrame(rows) for lbl, rows in trades.items()}


def _stat_row(lbl, tr):
    s = edge_stats(tr)
    se = s["sd_R"] / np.sqrt(s["n_trades"]) if s["n_trades"] else np.nan
    return {"arm": lbl, "delay_min": None, "n": s["n_trades"], "E_R": s["E_R"],
            "se_R": se, "t_stat": s["t_stat"], "win_rate": s["win_rate"]}


def main():
    print("=" * 84)
    print("ORB-001 ENTRY-DELAY SWEEP (realistic fills) + sealed OOS  |  M5, 3R, 2-pip")
    print("=" * 84)
    _OUT.mkdir(parents=True, exist_ok=True)

    # ---- IS sweep ---------------------------------------------------------
    is_arms = [("base_08:05", BASELINE_DELAY, False)] + \
              [(f"delay_{d}m", d, True) for d in SWEEP_DELAYS]
    is_runs = _run(is_arms, oos=False)

    print("\n----- IS SWEEP -----")
    rows = []
    for lbl, dl, _ in is_arms:
        r = _stat_row(lbl, is_runs[lbl]); r["delay_min"] = dl
        rows.append(r)
        print(f"  {lbl:12s}: E[R] {r['E_R']:+.4f} +/- {r['se_R']:.4f}  t {r['t_stat']:+.2f}  "
              f"win {r['win_rate']:.1%}  (n={r['n']})")
    is_df = pd.DataFrame(rows).set_index("arm")

    base_is = is_df.loc["base_08:05", "E_R"]
    sweep_only = is_df.loc[[f"delay_{d}m" for d in SWEEP_DELAYS]]
    best_lbl = sweep_only["E_R"].idxmax()
    best_delay = int(is_df.loc[best_lbl, "delay_min"])
    n_trials = len(SWEEP_DELAYS)
    print(f"\n  baseline IS E[R] {base_is:+.4f} | best delayed = {best_lbl} "
          f"({best_delay}m) IS E[R] {is_df.loc[best_lbl,'E_R']:+.4f} | n_trials={n_trials}")
    repro = abs(base_is - 0.3114) < 0.01
    print(f"  baseline repro of +0.3114R: {'OK' if repro else 'MISMATCH'} ({base_is:+.4f})")

    # ---- sealed OOS: ONE shot on the IS winner + baseline -----------------
    print(f"\n----- SEALED OOS (one shot: baseline + {best_lbl}) -----")
    oos_arms = [("base_08:05", BASELINE_DELAY, False), (best_lbl, best_delay, True)]
    oos_runs = _run(oos_arms, oos=True)
    oos_base = _stat_row("base_08:05", oos_runs["base_08:05"])
    oos_best = _stat_row(best_lbl, oos_runs[best_lbl])
    for r in (oos_base, oos_best):
        print(f"  {r['arm']:12s}: E[R] {r['E_R']:+.4f} +/- {r['se_R']:.4f}  "
              f"t {r['t_stat']:+.2f}  win {r['win_rate']:.1%}  (n={r['n']})")

    # OOS verdict: does the delayed arm beat baseline OOS, and is it significant?
    from scipy import stats
    welch = stats.ttest_ind(oos_runs[best_lbl]["R"].values,
                            oos_runs["base_08:05"]["R"].values, equal_var=False)
    oos_gain = oos_best["E_R"] - oos_base["E_R"]
    holds = (oos_best["E_R"] > 0 and oos_best["t_stat"] >= 3.0 and oos_gain > 0)
    print(f"\n  OOS gain (delay - base): {oos_gain:+.4f} R  (Welch t {welch.statistic:+.2f}, "
          f"p {welch.pvalue:.4f})")

    # ---- write ------------------------------------------------------------
    is_df.to_csv(_OUT / "delay_is_sweep.csv")
    summary = {
        "config": {"OR_MIN": OR_MIN, "target_R": TARGET_R, "spread_price": SPREAD},
        "n_trials": n_trials,
        "is_baseline_E_R": float(base_is),
        "is_sweep": is_df.reset_index().to_dict(orient="records"),
        "best_delay_min": best_delay, "best_is_E_R": float(is_df.loc[best_lbl, "E_R"]),
        "oos_base_E_R": oos_base["E_R"], "oos_base_t": oos_base["t_stat"],
        "oos_best_E_R": oos_best["E_R"], "oos_best_t": oos_best["t_stat"],
        "oos_gain_R": oos_gain, "oos_welch_t": welch.statistic, "oos_welch_p": welch.pvalue,
        "verdict_holds": bool(holds), "baseline_repro_ok": bool(repro),
    }
    (_OUT / "delay_summary.json").write_text(json.dumps(summary, indent=2))

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(9, 5))
    delays = [BASELINE_DELAY] + SWEEP_DELAYS
    er = [is_df.loc["base_08:05", "E_R"]] + [is_df.loc[f"delay_{d}m", "E_R"] for d in SWEEP_DELAYS]
    se = [is_df.loc["base_08:05", "se_R"]] + [is_df.loc[f"delay_{d}m", "se_R"] for d in SWEEP_DELAYS]
    ax.errorbar(delays, er, yerr=se, marker="o", capsize=4, color="#3b7dd8", label="IS E[R]")
    ax.scatter([best_delay], [oos_best["E_R"]], color="red", zorder=5, s=70,
               label=f"OOS best ({best_delay}m) {oos_best['E_R']:+.3f}")
    ax.scatter([BASELINE_DELAY], [oos_base["E_R"]], color="black", zorder=5, s=70,
               label=f"OOS baseline {oos_base['E_R']:+.3f}")
    ax.axhline(0.3114, color="green", ls="--", lw=1.1, label="frozen IS +0.3114R")
    ax.set_xlabel("entry-arm delay (min from 08:00)")
    ax.set_ylabel("E[R] per trade")
    ax.set_title("ORB-001 entry-delay sweep (IS) + sealed-OOS verdict")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(_OUT / "entry_delay.png", dpi=120)
    print(f"\nWrote outputs -> {_OUT}")

    print("\n" + "=" * 84)
    v = "DELAY HOLDS OOS — upgrade entry timing" if holds else \
        "DELAY DOES NOT BEAT BASELINE OOS — keep frozen 08:05"
    print(f"VERDICT: {v} | OOS base {oos_base['E_R']:+.4f} vs {best_lbl} "
          f"{oos_best['E_R']:+.4f} (gain {oos_gain:+.4f}, p={welch.pvalue:.3f})")
    print("=" * 84)


if __name__ == "__main__":
    main()
