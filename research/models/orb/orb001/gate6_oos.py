"""
ORB-001 Gate 6 — OUT-OF-SAMPLE test. ONE SHOT on the sealed 2024-05-02 -> 2026 data.

FROZEN config (locked before breaking the seal, step5 call_id=13 + this run):
  session=London, anchor=08:00 UTC, N=5 (primary; 15/30 = secondary colour),
  target=3R, stop=1R, spread=2 pip (win-rate-drag model), EOD flat=21:00 UTC.
Two pre-committed reads:
  (1) unfiltered            -> does the EDGE hold OOS?
  (2) max-range <= $5 filter -> tradeable on $50 (<=10% risk, ~full-Kelly)?

Pass = OOS net E[R] stays clearly positive and significant, in the neighbourhood
of IS. ~15 IS configs were explored -> OOS is the guard against that.

    python research/models/orb/gate6_oos.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from research.models.orb.orb001.orb_backtest import run_backtest_multi, edge_stats

N_SWEEP = [5, 15, 30]
PRIMARY_N = 5
TARGET_R = 3.0
SPREAD = 2.0 * 0.10
MAX_RANGE_USD = 5.0     # skip days risking >$5 on 0.01 lot (=10% of $50)
OOS_MONTHS = [(y, m) for y in range(2024, 2027) for m in range(1, 13) if (y, m) >= (2024, 5)]

# IS reference at the frozen 3R config (from exit_study, full IS) for comparison.
IS_REF = {5: dict(E_R=0.3114, t=7.65, win=0.342),
          15: dict(E_R=0.2407, t=6.08, win=0.334),
          30: dict(E_R=0.2068, t=5.35, win=0.337)}


def stats(tr: pd.DataFrame) -> dict:
    s = edge_stats(tr)
    return s


def main() -> None:
    print("=" * 84)
    print("ORB-001 GATE 6 — OUT-OF-SAMPLE  |  sealed 2024-05-02 -> 2026  |  3R, 2-pip net")
    print("=" * 84)

    runs = run_backtest_multi(OOS_MONTHS, n_list=N_SWEEP, is_only=False,
                              spread_price=SPREAD, target_R=TARGET_R, oos_only=True)

    if len(runs[PRIMARY_N]):
        d0 = runs[PRIMARY_N]
        print(f"OOS span: {d0['date'].min()} -> {d0['date'].max()}   "
              f"({len(d0)} trading days, N={PRIMARY_N})\n")

    rows = []
    for N in N_SWEEP:
        tr = runs[N]
        s = stats(tr)
        # filtered to tradeable-on-$50
        trf = tr[tr["range_w"] <= MAX_RANGE_USD]
        sf = stats(trf)
        ref = IS_REF[N]
        flag = "PRIMARY" if N == PRIMARY_N else "color  "
        print(f"----- N={N} ({flag}) -----")
        print(f"  IS ref            : E[R] {ref['E_R']:+.4f}  t {ref['t']:+.2f}  win {ref['win']:.1%}")
        print(f"  OOS unfiltered    : E[R] {s['E_R']:+.4f}  t {s['t_stat']:+.2f}  "
              f"win {s['win_rate']:.1%}  (n={s['n_trades']})")
        print(f"  OOS <=$5 filter   : E[R] {sf['E_R']:+.4f}  t {sf['t_stat']:+.2f}  "
              f"win {sf['win_rate']:.1%}  (n={sf['n_trades']}, dropped {s['n_trades']-sf['n_trades']})")
        retention = s['E_R'] / ref['E_R'] if ref['E_R'] else np.nan
        print(f"  edge retention    : {retention:.0%} of IS E[R]\n")
        rows.append({"N": N, "IS_E_R": ref["E_R"], "OOS_E_R": s["E_R"], "OOS_t": s["t_stat"],
                     "OOS_E_R_filt": sf["E_R"], "OOS_t_filt": sf["t_stat"], "retain": retention})

    df = pd.DataFrame(rows)
    print("===== VERDICT (primary N=5, unfiltered) =====")
    p = df[df["N"] == PRIMARY_N].iloc[0]
    held = p["OOS_E_R"] > 0 and p["OOS_t"] >= 3.0
    print(f"OOS E[R] {p['OOS_E_R']:+.4f}  t {p['OOS_t']:+.2f}  (IS was {p['IS_E_R']:+.4f}, "
          f"retained {p['retain']:.0%})")
    print(f"filtered: E[R] {p['OOS_E_R_filt']:+.4f}  t {p['OOS_t_filt']:+.2f}")
    print("\n" + ("GATE 6 PASS — edge holds out-of-sample. ORB-001 survives the full ladder."
                  if held else
                  "GATE 6 FAIL — edge does not hold OOS. ORB-001 was in-sample overfit."))


if __name__ == "__main__":
    main()
