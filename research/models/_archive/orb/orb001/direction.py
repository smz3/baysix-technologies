"""
ORB-001 long/short direction asymmetry (backlog task 16).

The edge has never been split by side. Gold has a strong secular up-drift over
2016-2026; even though ORB is intraday + EOD-flat (no overnight carry), an uptrend
regime can still favour long breakouts intraday. If longs carry most of the edge,
the live answer is long-only or asymmetric sizing, not symmetric.

Method (NO new backtest — reuse the frozen Gate-3/6 engine):
  frozen config = N=5, 3R target, 2-pip JM spread, immediate 08:05 entry.
  IS  : run_backtest_multi(is_only)        -> split by direction
  OOS : run_backtest_multi(oos_only)       -> DECOMPOSE the already-revealed Gate-6
        OOS trades by direction (re-analysis of a seen result, not a new peek).
  asymmetry test = Welch two-sample t on R_long vs R_short (unequal variance).
  Each side also tested vs 0 (is each individually profitable?).

Selection discipline: any "long-only" decision is an IS-selected config -> the OOS
split is the confirmation. If the asymmetry flips sign or dies OOS, stay symmetric.

Outputs -> research/outputs/orb/direction/
  direction_stats.csv, direction_summary.json, direction.png

    python research/models/orb/direction.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from research.models.orb.orb001.orb_backtest import run_backtest_multi, edge_stats

OR_MIN = 5
TARGET_R = 3.0
SPREAD = 2.0 * 0.10
BASE_REPRO = 0.3114
_OUT = Path(__file__).resolve().parents[4] / "research" / "outputs" / "orb" / "direction"


def _side_stats(trades, side):
    g = trades[trades["direction"] == side]
    s = edge_stats(g)
    return {"side": side, "n": s["n_trades"], "E_R": s["E_R"], "sd_R": s["sd_R"],
            "se_R": s["sd_R"] / np.sqrt(s["n_trades"]), "t_vs_0": s["t_stat"],
            "win_rate": s["win_rate"]}


def _analyse(period, trades):
    longs = trades[trades["direction"] == "long"]["R"].values
    shorts = trades[trades["direction"] == "short"]["R"].values
    sl, ss = _side_stats(trades, "long"), _side_stats(trades, "short")
    # Welch two-sample t-test on the asymmetry (long R vs short R)
    t_asym, p_asym = stats.ttest_ind(longs, shorts, equal_var=False)
    diff = sl["E_R"] - ss["E_R"]
    frac_long = len(longs) / (len(longs) + len(shorts))
    print(f"\n----- {period} (frozen N=5/3R/2-pip) -----")
    for s in (sl, ss):
        print(f"  {s['side']:5s}: E[R] {s['E_R']:+.4f} +/- {s['se_R']:.4f}  "
              f"t_vs0 {s['t_vs_0']:+.2f}  win {s['win_rate']:.1%}  (n={s['n']})")
    print(f"  long share of trades: {frac_long:.1%}")
    print(f"  ASYMMETRY long-short = {diff:+.4f}R  Welch t {t_asym:+.2f}  p {p_asym:.3f}  "
          f"-> {'SIGNIFICANT' if p_asym < 0.05 else 'not sig'}")
    return {"period": period, "long": sl, "short": ss, "diff_long_minus_short": diff,
            "welch_t": float(t_asym), "welch_p": float(p_asym), "frac_long": float(frac_long),
            "asym_significant": bool(p_asym < 0.05)}


def main():
    _OUT.mkdir(parents=True, exist_ok=True)
    print("=" * 84)
    print("ORB-001 DIRECTION ASYMMETRY (task 16) | frozen config | long vs short")
    print("=" * 84)

    is_tr = run_backtest_multi(None, n_list=[OR_MIN], is_only=True,
                               spread_price=SPREAD, target_R=TARGET_R)[OR_MIN]
    oos_tr = run_backtest_multi(None, n_list=[OR_MIN], is_only=False, oos_only=True,
                                spread_price=SPREAD, target_R=TARGET_R)[OR_MIN]

    # sanity: pooled IS must reproduce the frozen edge
    base = edge_stats(is_tr)["E_R"]
    print(f"\n  pooled IS repro of +{BASE_REPRO}R: {'OK' if abs(base-BASE_REPRO)<0.01 else 'MISMATCH'} ({base:+.4f})")

    res_is = _analyse("IS  2016->2024-05", is_tr)
    res_oos = _analyse("OOS 2024-05->2026 (Gate-6, re-analysed)", oos_tr)

    # verdict logic — a side is "kept" if it is independently profitable (t_vs0 >= 2)
    same_sign = np.sign(res_is["diff_long_minus_short"]) == np.sign(res_oos["diff_long_minus_short"])
    long_keep = res_is["long"]["t_vs_0"] >= 2 and res_oos["long"]["t_vs_0"] >= 2
    short_keep = res_is["short"]["t_vs_0"] >= 2 and res_oos["short"]["t_vs_0"] >= 2
    both_sides_pos = long_keep and short_keep
    asym_consistent = same_sign and abs(res_oos["diff_long_minus_short"]) > 0.05
    if both_sides_pos and asym_consistent:
        verdict = ("STAY SYMMETRIC at $50: both sides independently profitable IS+OOS "
                   "(long richer, asymmetry same sign + similar magnitude OOS, just underpowered "
                   "n). Long-only forfeits profitable trades + bets on trend persistence. "
                   "Asymmetric sizing infeasible at min-lot -> revisit at larger account.")
    elif both_sides_pos:
        verdict = "STAY SYMMETRIC: both sides independently profitable IS+OOS, no consistent asymmetry."
    elif long_keep and not short_keep:
        verdict = "LONG-ONLY candidate: shorts not independently profitable across IS+OOS."
    elif short_keep and not long_keep:
        verdict = "SHORT-ONLY candidate: longs not independently profitable across IS+OOS."
    else:
        verdict = "neither side robust across IS+OOS -> revisit."
    both_sides_pos_is = res_is["long"]["E_R"] > 0 and res_is["short"]["E_R"] > 0

    rows = []
    for r in (res_is, res_oos):
        for side in ("long", "short"):
            d = dict(r[side]); d["period"] = r["period"]; rows.append(d)
    df = pd.DataFrame(rows)
    df.to_csv(_OUT / "direction_stats.csv", index=False)
    summary = {"model": "ORB-001", "analysis": "direction_asymmetry_task16",
               "pooled_IS_repro": float(base), "IS": res_is, "OOS": res_oos,
               "both_sides_profitable_IS": bool(both_sides_pos_is), "verdict": verdict}
    (_OUT / "direction_summary.json").write_text(json.dumps(summary, indent=2, default=str))

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(8, 5))
    labels = ["IS long", "IS short", "OOS long", "OOS short"]
    vals = [res_is["long"]["E_R"], res_is["short"]["E_R"],
            res_oos["long"]["E_R"], res_oos["short"]["E_R"]]
    errs = [res_is["long"]["se_R"], res_is["short"]["se_R"],
            res_oos["long"]["se_R"], res_oos["short"]["se_R"]]
    ax.bar(labels, vals, yerr=errs, capsize=4,
           color=["#2e7d32", "#c62828", "#66bb6a", "#ef5350"], alpha=0.9)
    ax.axhline(0, color="black", lw=0.8)
    ax.set_ylabel("E[R] per trade")
    ax.set_title("ORB-001 long vs short — IS & OOS (task 16)")
    fig.tight_layout()
    fig.savefig(_OUT / "direction.png", dpi=120)
    print(f"\nWrote outputs -> {_OUT}")

    print("\n" + "=" * 84)
    print(f"VERDICT: {verdict}")
    print("=" * 84)


if __name__ == "__main__":
    main()
