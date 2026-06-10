"""
ORB-002 Gate 3 — "Does the NY 09:30 ORB have raw edge?"

Pre-registered kill-line (same as ORB-001 Gate 3):
    raw E[R]_gross >= 0.10R per trade  AND  t-stat >= 3  (in-sample)
N swept {5,15,30} using a FIXED 3R target (raw edge test, no spread cost).
Each N is a separate trial; t>=3 pre-pays for the multiple comparison.

Primary config for the transplant is N=5 (ORB-001 live). N=15/30 are colour.

Usage:
    python research/models/orb/gate3_edge_ny.py slice    # 4-month dev slice (fast)
    python research/models/orb/gate3_edge_ny.py full     # full IS 2016 -> 2024-05-02
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from research.models.orb.orb002_backtest import run_backtest_multi_fixed, edge_stats

N_SWEEP = [5, 15, 30]
PRIMARY_N = 5
SLICE_MONTHS = [(2019, 1), (2019, 4), (2019, 7), (2019, 10)]
TARGET_R = 3.0      # raw gate uses fixed 3R (consistent with ORB-001 Gate 3)
E_R_FLOOR = 0.10
T_FLOOR = 3.0


def main(mode: str) -> None:
    year_months = SLICE_MONTHS if mode == "slice" else None
    print("=" * 72)
    print(f"ORB-002 GATE 3 EDGE  |  mode={mode}  |  XAUUSD  |  RAW (no cost)")
    print(f"anchor = NYSE 09:30 ET (DST-aware)  |  fixed {TARGET_R}R target")
    print(f"kill-line: E[R] >= {E_R_FLOOR}  AND  t >= {T_FLOOR}   (in-sample)")
    print("=" * 72)

    all_trades = run_backtest_multi_fixed(
        year_months, n_list=N_SWEEP, is_only=True,
        spread_price=0.0, target_R=TARGET_R,
    )

    summary = []
    for N in N_SWEEP:
        print(f"\n----- N = {N} min {'[PRIMARY]' if N == PRIMARY_N else ''} -----")
        s = edge_stats(all_trades[N])
        s["N"] = N
        summary.append(s)
        print(f"  trades   : {s['n_trades']:,}")
        print(f"  win rate : {s['win_rate']:.1%}")
        print(f"  E[R]     : {s['E_R']:+.4f}   sd {s['sd_R']:.3f}")
        print(f"  t-stat   : {s['t_stat']:+.2f}")
        verdict = "PASS" if (s["E_R"] >= E_R_FLOOR and s["t_stat"] >= T_FLOOR) else "FAIL"
        print(f"  -> {verdict} vs kill-line")

    df = pd.DataFrame(summary)[["N", "n_trades", "win_rate", "E_R", "sd_R", "t_stat"]]
    print("\n===== SWEEP SUMMARY =====")
    with pd.option_context("display.width", 120):
        print(df.to_string(index=False,
              formatters={"win_rate": "{:.1%}".format, "E_R": "{:+.4f}".format,
                          "sd_R": "{:.3f}".format, "t_stat": "{:+.2f}".format}))

    passers = df[(df["E_R"] >= E_R_FLOOR) & (df["t_stat"] >= T_FLOOR)]
    primary_pass = df[df["N"] == PRIMARY_N].iloc[0]
    primary_ok = primary_pass["E_R"] >= E_R_FLOOR and primary_pass["t_stat"] >= T_FLOOR

    print()
    if primary_ok:
        print(f"PRIMARY N={PRIMARY_N}: PASS (E[R]={primary_pass['E_R']:+.4f}, "
              f"t={primary_pass['t_stat']:+.2f})")
    else:
        print(f"PRIMARY N={PRIMARY_N}: FAIL -> investigate before Gate 5.")
    if len(passers) > 1:
        print(f"Also passing: N={[n for n in passers['N'].tolist() if n != PRIMARY_N]}")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "slice"
    if mode not in ("slice", "full"):
        sys.exit("usage: gate3_edge_ny.py [slice|full]")
    main(mode)
