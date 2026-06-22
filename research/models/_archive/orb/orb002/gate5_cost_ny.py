"""
ORB-002 Gate 5 — "Is there a tradeable NY ORB signal with positive NET edge?"

Primary test: N=5, trail_1R exit (ORB-001 live config), NET @ 2-pip JM spread.
Sweeps N={5,15,30} for colour. Sweeps spread {raw/2pip/3pip} for sensitivity.

Kill-line: net E[R] > 0 AND t >= 3.0 @ 2-pip, N=5, trail_1R (full IS).

Spread model: B-book/swap-free = win-rate drag, not payoff deduction.
See orb_backtest.py header for full notarisation.

    python research/models/orb/gate5_cost_ny.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from research.models.orb.orb002.orb002_backtest import run_backtest_multi_trail, edge_stats

N_SWEEP = [5, 15, 30]
PRIMARY_N = 5
PIP_PRICE = 0.10
SPREADS_PIPS = [0.0, 2.0, 3.0]
ACCOUNT_USD = 50.0
T_FLOOR = 3.0


def main() -> None:
    print("=" * 80)
    print("ORB-002 GATE 5 — NET edge (trail_1R, spread as win-rate drag) | full IS")
    print("anchor = NYSE 09:30 ET (DST-aware) | kill-line: E[R]>0 & t>=3 @ 2-pip N=5")
    print("=" * 80)

    # One pass per spread (barriers shift -> cannot post-process spread)
    runs = {}
    for sp in SPREADS_PIPS:
        runs[sp] = run_backtest_multi_trail(
            None, n_list=N_SWEEP, is_only=True,
            spread_price=sp * PIP_PRICE,
        )

    headline = []
    for N in N_SWEEP:
        flag = "[PRIMARY]" if N == PRIMARY_N else ""
        print(f"\n----- N = {N} min {flag} -----")
        for sp in SPREADS_PIPS:
            s = edge_stats(runs[sp][N])
            label = "raw " if sp == 0 else f"{sp:>3}pip"
            tag = ""
            if sp != 0.0:
                tag = "  PASS" if (s["E_R"] > 0 and s["t_stat"] >= T_FLOOR) else "  FAIL"
            print(f"  {label}: win {s['win_rate']:.1%}  E[R] {s['E_R']:+.4f}  "
                  f"t {s['t_stat']:+.2f}{tag}")
            if sp == 2.0:
                headline.append({"N": N, "win": s["win_rate"], "E_R": s["E_R"], "t": s["t_stat"]})

        # $50 min-lot survival on raw trades (risk = range_w per 0.01 lot on a $50 account)
        rw = runs[0.0][N]["range_w"].values
        risk = rw / ACCOUNT_USD * 100
        print(f"  $50 survival (0.01 lot): risk/trade median {np.median(risk):.1f}%  "
              f"p90 {np.percentile(risk, 90):.1f}%  max {risk.max():.1f}%  "
              f"| >10%-risk trades {100 * (risk > 10).mean():.1f}%")

    print("\n===== HEADLINE: NET @ 2-pip (JM Pro live spread) =====")
    df = pd.DataFrame(headline)
    with pd.option_context("display.width", 120):
        print(df.to_string(index=False, formatters={
            "win": "{:.1%}".format, "E_R": "{:+.4f}".format, "t": "{:+.2f}".format,
        }))

    primary = df[df["N"] == PRIMARY_N].iloc[0]
    verdict = primary["E_R"] > 0 and primary["t"] >= T_FLOOR
    print()
    if verdict:
        print(f"GATE 5 PASS: N={PRIMARY_N} trail_1R net edge holds @ 2-pip  "
              f"(E[R]={primary['E_R']:+.4f}, t={primary['t']:+.2f})")
    else:
        print(f"GATE 5 FAIL: N={PRIMARY_N} trail_1R does not clear net t>={T_FLOOR} @ 2-pip  "
              f"(E[R]={primary['E_R']:+.4f}, t={primary['t']:+.2f})")


if __name__ == "__main__":
    main()
