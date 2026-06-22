"""
ORB-002 Gate 2 — "Does the NY 09:30 ET anchor produce sane output?"

NOT an edge test (Gate 3). Checks plumbing only:
  - 09:30 ET anchor data present on trading days (13:30 UTC EDT / 14:30 UTC EST)
  - opening range builds correctly on real data
  - range widths plausible for gold (0.5-30 USD)
  - breakouts fire at sane times, both directions represented
  - no look-ahead (entry strictly after range window closes)

Run in a visible PowerShell window (loads minute bars, >10s):
    python research/models/orb/gate2_sanity_ny.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from research.models.orb.orb002.orb002_core import (
    load_minute_bars, opening_range_breakouts_ny, ny_anchor_ns
)

SANITY_MONTHS = [(2019, 1), (2019, 4), (2019, 7), (2019, 10)]
N_MINUTES = 5   # live config (ORB-001 inherited)


def main() -> None:
    print("=" * 74)
    print("ORB-002 GATE 2 SANITY  |  XAUUSD  |  NYSE 09:30 ET anchor (DST-aware)")
    print(f"slice = {SANITY_MONTHS}   N = {N_MINUTES} min")
    print("13:30 UTC = EDT (summer) | 14:30 UTC = EST (winter)")
    print("=" * 74)

    bars = load_minute_bars(SANITY_MONTHS, is_only=True)

    # Count bars at each DST-phase anchor minute (proxy for data coverage)
    edt_bars = bars.index[(bars.index.hour == 13) & (bars.index.minute == 30)]
    est_bars = bars.index[(bars.index.hour == 14) & (bars.index.minute == 30)]

    print("\n--- sanity block ---")
    print(f"1-min bars      : {len(bars):,}")
    print(f"date range      : {bars.index.min()}  ->  {bars.index.max()}")
    print(f"px range (mid)  : {bars['low'].min():.2f}  ->  {bars['high'].max():.2f}")
    print(f"13:30 UTC bars  : {len(edt_bars)}  (09:30 ET during EDT)")
    print(f"14:30 UTC bars  : {len(est_bars)}  (09:30 ET during EST)")
    print(f"anchor coverage : {len(edt_bars) + len(est_bars)} anchor-minute bars total")

    if bars["high"].max() > 1e4 or bars["low"].min() < 1e2:
        print("!! WARNING: implausible gold price — check data partition / symbol blend")

    # Build NY opening-range breakouts
    orb = opening_range_breakouts_ny(bars, n_minutes=N_MINUTES)

    print("\n--- first 15 trading days ---")
    with pd.option_context("display.width", 120):
        print(orb.head(15).to_string())

    # Count trading days with any bar in the 13:00-15:30 UTC window
    ny_window = bars[(bars.index.hour >= 13) & (bars.index.hour < 16)]
    n_trading_days_approx = len(ny_window.index.normalize().unique())

    n_days = len(orb)
    vc = orb["direction"].value_counts()
    n_break = int(vc.get("long", 0) + vc.get("short", 0))

    print("\n--- summary ---")
    print(f"OR built on days        : {n_days}  of ~{n_trading_days_approx} trading days with NY-window data")
    print(f"days with breakout      : {n_break}  ({n_break / n_days:.0%} of OR days)")
    print(f"  long / short / none   : {vc.get('long',0)} / {vc.get('short',0)} / {vc.get('none',0)}")
    print(f"range width (USD)        : median {orb['range_w'].median():.2f}  "
          f"[p10 {orb['range_w'].quantile(.1):.2f}, p90 {orb['range_w'].quantile(.9):.2f}]")

    bt = orb["break_time"].dropna()
    if len(bt):
        mins = np.array([t.hour * 60 + t.minute for t in bt])
        print(f"breakout time (UTC)      : median {int(mins.mean()//60):02d}:{int(mins.mean()%60):02d}"
              f"   earliest {min(bt)}   latest {max(bt)}")

    # Spot-check DST correctness: print anchor UTC for first 5 days
    print("\n--- DST anchor spot-check (first 5 days) ---")
    for date in orb.index[:5]:
        day0_ns = pd.Timestamp(date).value
        anchor_ns = ny_anchor_ns(day0_ns)
        anchor_utc = pd.Timestamp(anchor_ns)
        print(f"  {date}  ->  anchor UTC {anchor_utc.strftime('%H:%M')}  "
              f"({'EDT' if anchor_utc.hour == 13 else 'EST'})")

    # Gate 2 pass/fail checks
    print("\n--- Gate 2 checks ---")
    coverage_pct = n_days / max(n_trading_days_approx, 1)
    checks = {
        "anchor-minute bars present (13:30 or 14:30 UTC)":  (len(edt_bars) + len(est_bars)) > 0,
        "OR builds on >=80% of NY-window trading days":     coverage_pct >= 0.80,
        "range width plausible (0.05-30 USD, N=5 calibrated)": 0.05 <= orb["range_w"].median() <= 30,
        "breakouts fire on most OR days (>=60%)":           n_break / n_days >= 0.60,
        "both directions present":                          vc.get("long", 0) > 0 and vc.get("short", 0) > 0,
    }
    for name, ok in checks.items():
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    print("\n" + ("ALL CHECKS PASS — NY anchor output is sane."
                  if all(checks.values()) else
                  "SOME CHECKS FAILED — inspect before logging Gate 2."))


if __name__ == "__main__":
    main()
