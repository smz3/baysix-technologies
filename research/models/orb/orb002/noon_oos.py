"""
Noon-anchor variant — Gate 6 OUT-OF-SAMPLE. ONE SHOT on sealed 2024-05-02 -> 2026.

Mirrors gate6_oos_ny.py exactly, but anchors on 12:00 ET (DST-aware) instead of
NYSE 09:30 ET. Reuses the verified trail sim from noon_anchor_scan (_sim_trail),
which is a faithful copy of orb002_backtest._simulate_day_trail.

FROZEN config (pre-committed before breaking the seal):
  session=NY, anchor=12:00 ET (DST-aware: 16:00 UTC EDT / 17:00 UTC EST), N=5,
  exit=trail_1R, stop=1R, spread=2-pip (win-rate-drag model), EOD flat=21:00 UTC.

Two pre-committed reads:
  (1) unfiltered            -> does the noon EDGE hold OOS?
  (2) max-range <=5 USD filter -> tradeable on $50 (<=10% risk, ~full-Kelly)?

Pass = OOS net E[R] stays clearly positive and significant, near IS.
IS reference computed inline (full IS run) for direct comparison.

WATCH: noon net edge is fragile (IS net +0.18R, 55% spread drag vs 11% for the
09:30 anchor). Tight noon ranges -> spread sensitivity is the main OOS risk.

    python research/models/orb/orb002/noon_oos.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from research.models.orb.orb002.orb002_core import _tick_files, IS_END
from research.models.orb.orb002.orb002_backtest import edge_stats
from research.models.orb.orb002.noon_anchor_scan import _sim_trail

NS_D = 86_400_000_000_000

PRIMARY_N = 5
SPREAD = 2.0 * 0.10        # 2 pip @ $0.10/pip
MAX_RANGE_USD = 5.0        # <=10% risk on $50 account with 0.01 lot
T_FLOOR = 3.0


def run_trail(n_minutes: int, spread_price: float, *, oos_only: bool) -> pd.DataFrame:
    """Single pass over tick parquet; trail_1R noon sim per day. Tags each trade's date.

    oos_only=False -> IS only (ts < IS_END); oos_only=True -> OOS only (ts >= IS_END).
    """
    files = _tick_files(None)
    if not files:
        raise FileNotFoundError("No tick parquet found")
    is_cut = np.datetime64(IS_END)

    rows = []
    desc = "OOS" if oos_only else "IS "
    for f in tqdm(files, desc=f"noon {desc} trail N={n_minutes}"):
        df = pd.read_parquet(f, columns=["ts_utc", "bid", "ask"])
        if oos_only:
            df = df[df["ts_utc"].values >= is_cut]
        else:
            df = df[df["ts_utc"].values < is_cut]
        if df.empty:
            continue
        ts_all = df["ts_utc"].values.astype("datetime64[ns]").astype(np.int64)
        mid_all = (df["bid"].values + df["ask"].values) * 0.5
        day_key = ts_all // NS_D
        for d in np.unique(day_key):
            m = day_key == d
            tsd, midd, day0 = ts_all[m], mid_all[m], int(d) * NS_D
            tr = _sim_trail(tsd, midd, day0, n_minutes, spread_price=spread_price)
            if tr is not None:
                tr["date"] = pd.Timestamp(day0).date()
                rows.append(tr)
    return pd.DataFrame(rows)


def main() -> None:
    print("=" * 88)
    print("NOON Gate 6 — OUT-OF-SAMPLE  |  sealed 2024-05-02 -> 2026  |  trail_1R, 2-pip net")
    print("anchor = 12:00 ET (DST-aware: 16:00 UTC EDT / 17:00 UTC EST)  |  N=5")
    print("=" * 88)

    # IS reference (apples-to-apples)
    print("\n[1/2] IS reference: noon trail_1R @ N=5, 2-pip (full IS) ...")
    is_tr = run_trail(PRIMARY_N, SPREAD, oos_only=False)
    is_s = edge_stats(is_tr)
    print(f"  IS: E[R] {is_s['E_R']:+.4f}  t {is_s['t_stat']:+.2f}  "
          f"win {is_s['win_rate']:.1%}  n={is_s['n_trades']}")

    # OOS — ONE SHOT
    print(f"\n[2/2] OOS: noon trail_1R @ N=5, 2-pip (sealed 2024-05-02+) ...")
    oos_tr = run_trail(PRIMARY_N, SPREAD, oos_only=True)
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

    print("\n===== NOON GATE 6 VERDICT =====")
    held = oos_s["E_R"] > 0 and oos_s["t_stat"] >= T_FLOOR
    print(f"OOS E[R] {oos_s['E_R']:+.4f}  t {oos_s['t_stat']:+.2f}  "
          f"(IS was {is_s['E_R']:+.4f}, retained {retention:.0%})")
    print(f"filtered: E[R] {oos_fs['E_R']:+.4f}  t {oos_fs['t_stat']:+.2f}")
    print("\n" + (
        "NOON GATE 6 PASS — noon ORB edge holds OOS. Candidate for ORB-003."
        if held else
        "NOON GATE 6 FAIL — noon edge does not hold OOS. Native noon hypothesis is IS overfit."
    ))

    # structured artifact for logging (task 7 protocol)
    out = {
        "is":  {k: is_s[k]  for k in ("E_R", "t_stat", "win_rate", "n_trades")},
        "oos": {k: oos_s[k] for k in ("E_R", "t_stat", "win_rate", "n_trades")},
        "oos_filtered": {k: oos_fs[k] for k in ("E_R", "t_stat", "win_rate", "n_trades")},
        "retention": retention, "held": bool(held),
        "config": {"anchor": "12:00 ET DST-aware", "N": PRIMARY_N,
                   "exit": "trail_1R", "spread_pip": 2.0, "eod_utc": 21},
    }
    res_dir = Path(__file__).resolve().parents[4] / "research" / "outputs"
    res_dir.mkdir(parents=True, exist_ok=True)
    res_path = res_dir / "noon_oos_results.json"
    res_path.write_text(json.dumps(out, indent=2, default=float), encoding="utf-8")
    print(f"\n[results] wrote {res_path}")


if __name__ == "__main__":
    main()
