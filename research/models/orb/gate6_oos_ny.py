"""
ORB-002 Gate 6 — OUT-OF-SAMPLE test. ONE SHOT on the sealed 2024-05-02 -> 2026 data.

FROZEN config (pre-committed before breaking the seal):
  session=NY, anchor=09:30 ET (DST-aware), N=5,
  exit=trail_1R, stop=1R, spread=2-pip (win-rate-drag model), EOD flat=21:00 UTC.

Two pre-committed reads:
  (1) unfiltered            -> does the EDGE hold OOS?
  (2) max-range <=5 USD filter -> tradeable on $50 (<=10% risk, ~full-Kelly)?

Pass = OOS net E[R] stays clearly positive and significant, in the neighbourhood of IS.
IS reference is computed inline (full IS run) for direct comparison.

    python research/models/orb/gate6_oos_ny.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from research.models.orb.orb002_backtest import run_backtest_multi_trail, edge_stats

PRIMARY_N = 5
SPREAD = 2.0 * 0.10        # 2 pip @ $0.10/pip
MAX_RANGE_USD = 5.0        # <=10% risk on $50 account with 0.01 lot
T_FLOOR = 3.0
OOS_MONTHS = [(y, m) for y in range(2024, 2027) for m in range(1, 13)
              if (y, m) >= (2024, 5)]


def main() -> None:
    print("=" * 86)
    print("ORB-002 GATE 6 — OUT-OF-SAMPLE  |  sealed 2024-05-02 -> 2026  |  trail_1R, 2-pip net")
    print("anchor = NYSE 09:30 ET (DST-aware)  |  N=5")
    print("=" * 86)

    # IS reference (run inline so we have apples-to-apples comparison)
    print("\n[1/2] IS reference: trail_1R @ N=5, 2-pip (full IS) ...")
    is_runs = run_backtest_multi_trail(
        None, n_list=[PRIMARY_N], is_only=True, spread_price=SPREAD,
    )
    is_tr = is_runs[PRIMARY_N]
    is_s = edge_stats(is_tr)
    print(f"  IS: E[R] {is_s['E_R']:+.4f}  t {is_s['t_stat']:+.2f}  "
          f"win {is_s['win_rate']:.1%}  n={is_s['n_trades']}")

    # OOS — ONE SHOT
    print(f"\n[2/2] OOS: trail_1R @ N=5, 2-pip (sealed 2024-05-02+) ...")
    oos_runs = run_backtest_multi_trail(
        OOS_MONTHS, n_list=[PRIMARY_N], is_only=False,
        spread_price=SPREAD, oos_only=True,
    )
    oos_tr = oos_runs[PRIMARY_N]
    oos_s = edge_stats(oos_tr)

    if len(oos_tr):
        print(f"  OOS span: {oos_tr['date'].min()} -> {oos_tr['date'].max()}  "
              f"({len(oos_tr)} trading days)")

    print(f"\n  IS   : E[R] {is_s['E_R']:+.4f}  t {is_s['t_stat']:+.2f}  "
          f"win {is_s['win_rate']:.1%}  n={is_s['n_trades']}")
    print(f"  OOS  : E[R] {oos_s['E_R']:+.4f}  t {oos_s['t_stat']:+.2f}  "
          f"win {oos_s['win_rate']:.1%}  n={oos_s['n_trades']}")
    retention = oos_s["E_R"] / is_s["E_R"] if is_s["E_R"] else np.nan
    print(f"  edge retention: {retention:.0%} of IS E[R]")

    # Pre-committed read 2: $50-tradeable filter
    oos_filt = oos_tr[oos_tr["range_w"] <= MAX_RANGE_USD]
    oos_fs = edge_stats(oos_filt) if len(oos_filt) else {"E_R": np.nan, "t_stat": np.nan,
                                                          "win_rate": np.nan, "n_trades": 0}
    dropped = oos_s["n_trades"] - len(oos_filt)
    print(f"\n  OOS <=${MAX_RANGE_USD} filter: E[R] {oos_fs['E_R']:+.4f}  "
          f"t {oos_fs['t_stat']:+.2f}  win {oos_fs['win_rate']:.1%}  "
          f"n={oos_fs['n_trades']}  (dropped {dropped})")

    print("\n===== GATE 6 VERDICT =====")
    held = oos_s["E_R"] > 0 and oos_s["t_stat"] >= T_FLOOR
    print(f"OOS E[R] {oos_s['E_R']:+.4f}  t {oos_s['t_stat']:+.2f}  "
          f"(IS was {is_s['E_R']:+.4f}, retained {retention:.0%})")
    print(f"filtered: E[R] {oos_fs['E_R']:+.4f}  t {oos_fs['t_stat']:+.2f}")
    print("\n" + (
        "GATE 6 PASS — NY ORB edge holds out-of-sample. ORB-002 survives the full ladder."
        if held else
        "GATE 6 FAIL — edge does not hold OOS. NY ORB transplant is in-sample overfit."
    ))


if __name__ == "__main__":
    main()
