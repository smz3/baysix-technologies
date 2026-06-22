"""
ORB-001 Walk-Forward Edge Stability (backlog task 10).

Question: is the honest +0.31R IS edge a STABLE baseline through time, or is it
drifting / regime-dependent? The single sealed OOS came back inflated (+0.88R),
which we attributed to a benign regime (gold doubling + trend). A single holdout
split can be lucky; this is the per-year / per-quarter lie-detector that a single
split cannot give.

Method (no re-fitting — the config is already FROZEN from Gate 6, so this is a
pure stability scan, not a re-optimisation):
  config = London, anchor 08:00 UTC, N=5, target 3R, stop 1R, spread 2 pip,
           EOD flat 21:00 UTC  (= the +0.31R IS / +0.88R OOS config)
  data   = FULL history 2016 -> 2026 (IS + OOS together; we WANT every regime)

Reads:
  1. Per-year   E[R] +/- 1 SE, t-stat, win rate, n.
  2. Per-quarter E[R] +/- 1 SE  (finer grain for the rolling picture).
  3. Rolling-100-trade E[R] line.
  4. Decay regression: OLS of per-trade R on date-ordinal -> slope (R/year) + t.
     Negative + significant => edge decaying.
  5. Split-half: IS (pre 2024-05-02) vs OOS Welch t-test -> is OOS a real outlier?

Outputs -> research/outputs/orb/walk_forward/
  walk_forward_by_year.csv, walk_forward_by_quarter.csv,
  walk_forward_summary.json, walk_forward.png

    python research/models/orb/walk_forward.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from research.models.orb.orb001.orb_backtest import run_backtest_multi, edge_stats
from research.models.orb.orb001.orb_core import IS_END

# ---- FROZEN config (Gate 6, step5 call_id=13) -----------------------------
N = 5
TARGET_R = 3.0
SPREAD = 2.0 * 0.10          # 2-pip round trip in price units
ROLL = 100                   # rolling-trade window for the smooth E[R] line
IS_REF_E_R = 0.3114          # IS reference at this config (gate6 IS_REF[5])

_OUT = Path(__file__).resolve().parents[4] / "research" / "outputs" / "orb" / "walk_forward"


def _bucket_stats(tr: pd.DataFrame, label: str) -> dict:
    """edge_stats for a bucket, plus the +/-1 SE band on E[R]."""
    s = edge_stats(tr)
    se = s["sd_R"] / np.sqrt(s["n_trades"]) if s["n_trades"] > 0 else np.nan
    return {"bucket": label, "n": s["n_trades"], "E_R": s["E_R"], "sd_R": s["sd_R"],
            "se_R": se, "t_stat": s["t_stat"], "win_rate": s["win_rate"]}


def main() -> None:
    print("=" * 84)
    print("ORB-001 WALK-FORWARD EDGE STABILITY  |  N=5 3R 2-pip  |  FULL 2016->2026")
    print("=" * 84)
    _OUT.mkdir(parents=True, exist_ok=True)

    # FULL history: is_only=False AND oos_only=False => no date filter at all.
    runs = run_backtest_multi(None, n_list=[N], is_only=False,
                              spread_price=SPREAD, target_R=TARGET_R, oos_only=False)
    tr = runs[N].copy()
    tr["date"] = pd.to_datetime(tr["date"])
    tr = tr.sort_values("date").reset_index(drop=True)
    tr["year"] = tr["date"].dt.year
    tr["quarter"] = tr["date"].dt.to_period("Q").astype(str)

    print(f"\nTotal trades: {len(tr)}   span {tr['date'].min().date()} -> {tr['date'].max().date()}")
    overall = edge_stats(tr)
    print(f"Pooled E[R] {overall['E_R']:+.4f}  t {overall['t_stat']:+.2f}  "
          f"win {overall['win_rate']:.1%}\n")

    # ---- (1) per-year -----------------------------------------------------
    print("----- PER-YEAR -----")
    yr_rows = []
    for y, g in tr.groupby("year"):
        r = _bucket_stats(g, str(y))
        yr_rows.append(r)
        print(f"  {y}: E[R] {r['E_R']:+.4f} +/- {r['se_R']:.4f}  "
              f"t {r['t_stat']:+.2f}  win {r['win_rate']:.1%}  (n={r['n']})")
    by_year = pd.DataFrame(yr_rows)

    # ---- (2) per-quarter --------------------------------------------------
    q_rows = [_bucket_stats(g, q) for q, g in tr.groupby("quarter")]
    by_quarter = pd.DataFrame(q_rows)

    # ---- (4) decay regression: R ~ date_ordinal ---------------------------
    from scipy import stats
    x = tr["date"].map(pd.Timestamp.toordinal).values.astype(float)
    y = tr["R"].values
    lr = stats.linregress(x, y)
    slope_per_year = lr.slope * 365.25
    print("\n----- DECAY REGRESSION (per-trade R ~ time) -----")
    print(f"  slope {slope_per_year:+.4f} R/year   t {lr.slope/lr.stderr:+.2f}   "
          f"p {lr.pvalue:.3f}")
    decaying = (slope_per_year < 0) and (lr.pvalue < 0.05)
    print(f"  -> {'DECAYING (sig. negative)' if decaying else 'no significant decay'}")

    # ---- (5) IS vs OOS split-half (Welch) ---------------------------------
    is_R = tr.loc[tr["date"] < IS_END, "R"].values
    oos_R = tr.loc[tr["date"] >= IS_END, "R"].values
    welch = stats.ttest_ind(oos_R, is_R, equal_var=False)
    print("\n----- IS vs OOS SPLIT-HALF (Welch) -----")
    print(f"  IS  E[R] {is_R.mean():+.4f}  (n={len(is_R)})")
    print(f"  OOS E[R] {oos_R.mean():+.4f}  (n={len(oos_R)})")
    print(f"  Welch t {welch.statistic:+.2f}  p {welch.pvalue:.4f}  "
          f"-> OOS {'IS a real outlier' if welch.pvalue < 0.05 else 'within IS noise'}")

    # ---- rolling E[R] -----------------------------------------------------
    tr["roll_E_R"] = tr["R"].rolling(ROLL).mean()

    # ---- write structured outputs ----------------------------------------
    by_year.to_csv(_OUT / "walk_forward_by_year.csv", index=False)
    by_quarter.to_csv(_OUT / "walk_forward_by_quarter.csv", index=False)
    summary = {
        "config": {"N": N, "target_R": TARGET_R, "spread_price": SPREAD},
        "span": [str(tr["date"].min().date()), str(tr["date"].max().date())],
        "n_trades": int(len(tr)),
        "pooled_E_R": overall["E_R"], "pooled_t": overall["t_stat"],
        "IS_ref_E_R": IS_REF_E_R,
        "decay_slope_per_year": slope_per_year,
        "decay_t": lr.slope / lr.stderr, "decay_p": lr.pvalue, "decaying": bool(decaying),
        "IS_E_R": float(is_R.mean()), "OOS_E_R": float(oos_R.mean()),
        "welch_t": welch.statistic, "welch_p": welch.pvalue,
        "min_year_E_R": float(by_year["E_R"].min()),
        "max_year_E_R": float(by_year["E_R"].max()),
        "n_years_positive": int((by_year["E_R"] > 0).sum()),
        "n_years_total": int(len(by_year)),
    }
    (_OUT / "walk_forward_summary.json").write_text(json.dumps(summary, indent=2))

    # ---- plot -------------------------------------------------------------
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 9))
    # top: per-year E[R] with +/-1 SE, IS baseline, zero line
    ax1.bar(by_year["bucket"], by_year["E_R"], yerr=by_year["se_R"],
            capsize=4, color="#3b7dd8", alpha=0.85)
    ax1.axhline(IS_REF_E_R, color="green", ls="--", lw=1.2, label=f"IS ref {IS_REF_E_R:+.3f}R")
    ax1.axhline(0, color="black", lw=0.8)
    ax1.axvline(x=str(IS_END.year), color="red", ls=":", lw=1.2, label="IS/OOS seal 2024")
    ax1.set_title("ORB-001 per-year E[R] (+/-1 SE) — N=5 3R 2-pip, full history")
    ax1.set_ylabel("E[R] per trade")
    ax1.legend(fontsize=8)
    # bottom: rolling E[R] through time
    ax2.plot(tr["date"], tr["roll_E_R"], color="#d8633b", lw=1.0)
    ax2.axhline(IS_REF_E_R, color="green", ls="--", lw=1.2)
    ax2.axhline(0, color="black", lw=0.8)
    ax2.axvline(IS_END, color="red", ls=":", lw=1.2)
    ax2.set_title(f"Rolling-{ROLL}-trade E[R]")
    ax2.set_ylabel("E[R] per trade")
    fig.tight_layout()
    fig.savefig(_OUT / "walk_forward.png", dpi=120)
    print(f"\nWrote outputs -> {_OUT}")

    # ---- verdict ----------------------------------------------------------
    print("\n" + "=" * 84)
    pos = summary["n_years_positive"]; tot = summary["n_years_total"]
    print(f"VERDICT: {pos}/{tot} years positive | year E[R] range "
          f"[{summary['min_year_E_R']:+.3f}, {summary['max_year_E_R']:+.3f}] | "
          f"decay {slope_per_year:+.3f}R/yr (p={lr.pvalue:.3f})")
    print("=" * 84)


if __name__ == "__main__":
    main()
