"""
ORB-001 Gate 5 — "Is there a tradeable signal with positive NET edge?"

NET edge after JM spread + $50 min-lot survival, on the full IS.

NOTARIZATION (2026-06-06) — this file was REWRITTEN. The original applied spread
as a flat payoff deduction (net_R = raw_R - spread/range_w), which wrongly shrank
the 2:1 payoff. Corrected per Syafiq: on a B-book/swap-free account spread does
not debit on entry and does not change the 2:1 payoff — it is embedded in fills
(buy-stop on ASK, exits on BID), so it is a WIN-RATE drag, modelled inside
orb_backtest._simulate_day via spread_price. Spread is the ONLY cost (swap $0,
commission $0, leverage irrelevant). See orb_backtest.py header for the full note.

    python research/models/orb/gate5_cost.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from research.models.orb.orb_backtest import run_backtest_multi, edge_stats

N_SWEEP = [5, 15, 30]
PIP_PRICE = 0.10
SPREADS_PIPS = [0.0, 2.0, 3.0]   # raw / JM-Pro live / news-widen sensitivity
ACCOUNT_USD = 50.0
T_FLOOR = 3.0


def main() -> None:
    print("=" * 80)
    print("ORB-001 GATE 5 — NET edge (spread as win-rate drag) + $50 survival | full IS")
    print("=" * 80)

    # one full backtest pass per spread (barriers shift -> cannot post-process)
    runs = {}
    for sp in SPREADS_PIPS:
        runs[sp] = run_backtest_multi(None, n_list=N_SWEEP, is_only=True,
                                      spread_price=sp * PIP_PRICE)

    headline = []
    for N in N_SWEEP:
        print(f"\n----- N = {N} min -----")
        for sp in SPREADS_PIPS:
            s = edge_stats(runs[sp][N])
            label = "raw " if sp == 0 else f"{sp:>3}pip"
            tag = "" if sp == 0 else ("  PASS" if (s["E_R"] > 0 and s["t_stat"] >= T_FLOOR) else "  FAIL")
            print(f"  {label}: win {s['win_rate']:.1%}  E[R] {s['E_R']:+.4f}  "
                  f"t {s['t_stat']:+.2f}{tag}")
            if sp == 2.0:
                headline.append({"N": N, "win": s["win_rate"], "E_R": s["E_R"], "t": s["t_stat"]})
        # survival on $50 (range_w from the raw run; 0.01 lot risks range_w USD)
        rw = runs[0.0][N]["range_w"].values
        risk = rw / ACCOUNT_USD * 100
        print(f"  $50 survival (0.01 lot): risk/trade median {np.median(risk):.1f}%  "
              f"p90 {np.percentile(risk,90):.1f}%  max {risk.max():.1f}%  "
              f"| >10%-risk trades {100*(risk>10).mean():.1f}%")

    print("\n===== HEADLINE: NET @ 2-pip (your live JM Pro spread) =====")
    df = pd.DataFrame(headline)
    with pd.option_context("display.width", 120):
        print(df.to_string(index=False, formatters={
            "win": "{:.1%}".format, "E_R": "{:+.4f}".format, "t": "{:+.2f}".format}))
    ok = df[(df["E_R"] > 0) & (df["t"] >= T_FLOOR)]
    print("\n" + (f"GATE 5 net edge holds at 2-pip for N={ok['N'].tolist()} "
                  f"(t>={T_FLOOR})." if len(ok) else
                  "GATE 5: no N clears net t>=3 at 2-pip."))


if __name__ == "__main__":
    main()
