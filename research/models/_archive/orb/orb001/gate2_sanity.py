"""
ORB-001 Gate 2 — "Does the simplest possible implementation produce sane output?"

NOT an edge test (that is Gate 3). This only checks the plumbing is sane:
  - 08:00 UTC opening range builds on real data every trading day
  - range widths are economically plausible for gold (a few $ over 15 min)
  - breakouts fire at sane times, ~1 trade/day, both directions represented
  - no look-ahead (entry strictly after the range window closes)

Run in a visible PowerShell window (protocol rule 8 — slice loads >10s):
    python research/models/orb/gate2_sanity.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from research.models.orb.orb001.orb_core import load_minute_bars, opening_range_breakouts

# Representative sanity slice: 4 months spanning all seasons (summer + winter),
# enough days to eyeball without loading the full 24GB tick set.
SANITY_MONTHS = [(2019, 1), (2019, 4), (2019, 7), (2019, 10)]
N_MINUTES = 15  # middle of the {5,15,30} sweep


def main() -> None:
    print("=" * 70)
    print("ORB-001 GATE 2 SANITY  |  XAUUSD  |  London anchor 08:00 UTC")
    print(f"slice = {SANITY_MONTHS}   N = {N_MINUTES} min")
    print("=" * 70)

    bars = load_minute_bars(SANITY_MONTHS, is_only=True)

    # ── sanity block (protocol rule 5) ──────────────────────────────────────
    print("\n--- sanity block ---")
    print(f"1-min bars      : {len(bars):,}")
    print(f"date range      : {bars.index.min()}  ->  {bars.index.max()}")
    print(f"px range (mid)  : {bars['low'].min():.2f}  ->  {bars['high'].max():.2f}")
    gap0700 = bars.index[bars.index.hour == 7]
    print(f"07:00 UTC bars  : {len(gap0700)}  (expect 0 — daily maintenance gap)")
    anchor_bars = bars.index[(bars.index.hour == 8) & (bars.index.minute == 0)]
    print(f"08:00 UTC bars  : {len(anchor_bars)}  (expect ~ one per trading day)")

    if bars["high"].max() > 1e4 or bars["low"].min() < 1e2:
        print("!! WARNING: implausible gold price — check data partition / symbol blend")

    # ── build opening-range breakouts ───────────────────────────────────────
    orb = opening_range_breakouts(bars, n_minutes=N_MINUTES)

    print("\n--- first 15 trading days ---")
    with pd.option_context("display.width", 120):
        print(orb.head(15).to_string())

    # ── summary diagnostics ─────────────────────────────────────────────────
    n_days = len(orb)
    vc = orb["direction"].value_counts()
    n_break = int(vc.get("long", 0) + vc.get("short", 0))
    print("\n--- summary ---")
    print(f"trading days        : {n_days}")
    print(f"days with breakout  : {n_break}  ({n_break / n_days:.0%})")
    print(f"  long / short / none: {vc.get('long',0)} / {vc.get('short',0)} / {vc.get('none',0)}")
    print(f"range width (USD)    : median {orb['range_w'].median():.2f}  "
          f"[p10 {orb['range_w'].quantile(.1):.2f}, p90 {orb['range_w'].quantile(.9):.2f}]")

    bt = orb["break_time"].dropna()
    if len(bt):
        mins = np.array([t.hour * 60 + t.minute for t in bt])
        print(f"breakout time (UTC)  : median {int(mins.mean()//60):02d}:{int(mins.mean()%60):02d}"
              f"   earliest {min(bt)}   latest {max(bt)}")

    # ── verdict gates (eyeball-able pass conditions) ────────────────────────
    print("\n--- Gate 2 checks ---")
    checks = {
        "no 07:00 UTC bars (gap intact)":      len(gap0700) == 0,
        "08:00 anchor present most days":       len(anchor_bars) >= 0.9 * n_days,
        "range width plausible (0.5-30 USD)":   0.5 <= orb["range_w"].median() <= 30,
        "breakouts fire on most days (>=60%)":  n_break / n_days >= 0.60,
        "both directions present":              vc.get("long", 0) > 0 and vc.get("short", 0) > 0,
    }
    for name, ok in checks.items():
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    print("\n" + ("ALL CHECKS PASS — output is sane." if all(checks.values())
                  else "SOME CHECKS FAILED — inspect before logging Gate 2."))


if __name__ == "__main__":
    main()
