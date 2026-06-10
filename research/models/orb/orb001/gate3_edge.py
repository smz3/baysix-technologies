"""
ORB-001 Gate 3 — "Does the dumb rule have any edge, raw?"

Pre-registered kill-line (Gate 1, step5 call_id=9):
    raw E[R]_gross >= 0.10R per trade  AND  t-stat >= 3,  in-sample.
Costs deferred to Gate 5 (TCM-001 + min-lot). N swept {5,15,30} one-by-one,
each a separate trial -> t>=3 pre-pays for the multiple comparison.

Usage:
    python research/models/orb/gate3_edge.py slice     # 2019 4-month dev slice (fast)
    python research/models/orb/gate3_edge.py full       # full IS 2016 -> 2024-05-02
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from research.models.orb.orb001.orb_backtest import run_backtest_multi, edge_stats

N_SWEEP = [5, 15, 30]
SLICE_MONTHS = [(2019, 1), (2019, 4), (2019, 7), (2019, 10)]

E_R_FLOOR = 0.10
T_FLOOR = 3.0


def main(mode: str) -> None:
    year_months = SLICE_MONTHS if mode == "slice" else None
    print("=" * 72)
    print(f"ORB-001 GATE 3 EDGE TEST  |  mode={mode}  |  XAUUSD  |  RAW (no cost)")
    print(f"kill-line: E[R] >= {E_R_FLOOR}  AND  t >= {T_FLOOR}   (in-sample)")
    print("=" * 72)

    all_trades = run_backtest_multi(year_months, n_list=N_SWEEP, is_only=True)

    summary = []
    for N in N_SWEEP:
        print(f"\n----- N = {N} min -----")
        s = edge_stats(all_trades[N])
        s["N"] = N
        summary.append(s)
        print(f"  trades   : {s['n_trades']:,}   "
              f"(target {s['n_target']} / stop {s['n_stop']} / eod {s['n_eod']})")
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
    print()
    if len(passers):
        print(f"GATE 3 PASS candidates (N): {passers['N'].tolist()}  "
              f"-> proceed to full IS / Gate 4." if mode == "slice"
              else f"GATE 3 PASSED for N={passers['N'].tolist()} on full IS.")
    else:
        print("NO N clears the kill-line"
              + (" on the dev slice — debug or expect Gate 3 KILL on full IS."
                 if mode == "slice" else " on full IS -> ORB-001 KILLED at Gate 3."))


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "slice"
    if mode not in ("slice", "full"):
        sys.exit("usage: gate3_edge.py [slice|full]")
    main(mode)
