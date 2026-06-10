"""
ORB-001 exit-design study (Gate 6 prep, still IN-SAMPLE).

Question (Syafiq): is the 2R target right? Does letting winners run to EOD beat it?
Tests target in {1R, 1.5R, 2R, 3R, EOD-close} x N in {5,15,30}, NET @ 2-pip.

Purpose is robustness, not max-chasing: if the edge is positive across most exits
the strategy is healthy; if only 2R works, that is an overfit warning. Every cell
here is a trial -> counts toward N_trials before we freeze the OOS config.

    python research/models/orb/exit_study.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from research.models.orb.orb001.orb_backtest import run_backtest_multi

N_SWEEP = [5, 15, 30]
TARGETS = [1.0, 1.5, 2.0, 3.0, None]   # None = EOD-close (1R stop, no target)
SPREAD = 2.0 * 0.10                     # live JM Pro, price units
T_FLOOR = 3.0


def label(t):
    return "EOD" if t is None else f"{t:g}R"


def main() -> None:
    print("=" * 88)
    print("ORB-001 EXIT STUDY  |  full IS  |  NET @ 2-pip  |  target in {1,1.5,2,3R, EOD-close}")
    print("=" * 88)

    rows = []
    for tR in TARGETS:
        runs = run_backtest_multi(None, n_list=N_SWEEP, is_only=True,
                                  spread_price=SPREAD, target_R=tR)
        for N in N_SWEEP:
            tr = runs[N]
            R = tr["R"].values
            n = len(R)
            mean, sd = R.mean(), R.std(ddof=1)
            t = mean / (sd / np.sqrt(n)) if sd > 0 else np.nan
            oc = tr["outcome"].value_counts()
            wins = tr["R"] > 0
            rows.append({
                "exit": label(tR), "N": N, "n": n,
                "win%": wins.mean(), "E[R]": mean, "t": t,
                "totalR": R.sum(),
                "avgWin": R[wins.values].mean() if wins.any() else 0.0,
                "avgLoss": R[~wins.values].mean() if (~wins).any() else 0.0,
                "stop%": oc.get("stop", 0) / n, "eod%": oc.get("eod", 0) / n,
            })

    df = pd.DataFrame(rows)
    for N in N_SWEEP:
        sub = df[df["N"] == N].drop(columns="N")
        print(f"\n----- N = {N} min -----")
        with pd.option_context("display.width", 140):
            print(sub.to_string(index=False, formatters={
                "win%": "{:.1%}".format, "E[R]": "{:+.4f}".format, "t": "{:+.2f}".format,
                "totalR": "{:+.1f}".format, "avgWin": "{:+.3f}".format,
                "avgLoss": "{:+.3f}".format, "stop%": "{:.1%}".format, "eod%": "{:.1%}".format}))

    # best by E[R] and by total R, robustness flag
    print("\n===== READOUT =====")
    pos = (df["E[R]"] > 0) & (df["t"] >= T_FLOOR)
    print(f"cells with net E[R]>0 & t>=3 : {pos.sum()}/{len(df)}  "
          f"({'robust across exits' if pos.mean() > 0.6 else 'exit-sensitive — overfit risk'})")
    best_er = df.loc[df["E[R]"].idxmax()]
    best_tot = df.loc[df["totalR"].idxmax()]
    print(f"best per-trade E[R] : {best_er['exit']} N={int(best_er['N'])}  "
          f"E[R] {best_er['E[R]']:+.4f}  t {best_er['t']:+.2f}")
    print(f"best total R (sum)  : {best_tot['exit']} N={int(best_tot['N'])}  "
          f"totalR {best_tot['totalR']:+.1f}  (n={int(best_tot['n'])})")


if __name__ == "__main__":
    main()
