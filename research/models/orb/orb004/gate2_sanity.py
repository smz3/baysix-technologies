"""
ORB-004 Gate 2 — "Does the simplest implementation produce sane output?"

NOT an edge test (that's Gate 3). This just proves the multi-session feature layer
(first-M15 range + session VWAP + daily ATR + alignment flag) builds without
look-ahead and yields numbers in plausible ranges. Runs on a small IS slice so it's
fast; scale up at Gate 3.

Run (rule 12 — long tick load, visible window):
    python research/models/orb/orb004/gate2_sanity.py
"""
from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pandas as pd

_HERE = Path(__file__).resolve()
sys.path.insert(0, str(_HERE.parents[4]))
from research.models.orb.orb004.orb004_core import (
    load_minute_bars, daily_atr, build_session_signals, SESSIONS, session_anchor, M15,
)

SLICE = [(2023, 1), (2023, 2), (2023, 3)]      # 3 IS months — sanity, not edge


def _hdr(t): print(f"\n{'='*64}\n  {t}\n{'='*64}")


def main():
    _hdr("1. LOAD 1-MIN BARS + VOLUME")
    bars = load_minute_bars(SLICE, is_only=True)
    assert bars.index.is_monotonic_increasing, "bars not sorted"
    vol_pos = (bars["volume"] > 0).mean()
    print(f"  bars       : {len(bars):,}  [{bars.index.min()} .. {bars.index.max()}]")
    print(f"  monotonic  : {bars.index.is_monotonic_increasing}")
    print(f"  volume>0   : {vol_pos:.1%} of minutes   (mean vol/min {bars['volume'].mean():.1f})")

    _hdr("2. DAILY ATR(14)")
    atr = daily_atr(14)
    atr_slice = atr[(atr.index >= bars.index.min().normalize()) &
                    (atr.index <= bars.index.max().normalize())]
    print(f"  atr rows   : {len(atr):,}  (full daily series, shifted +1d)")
    print(f"  slice ATR  : mean {atr_slice.mean():.2f}  min {atr_slice.min():.2f}  max {atr_slice.max():.2f}")
    assert (atr_slice.dropna() > 0).all(), "non-positive ATR"

    _hdr("3. SESSION ANCHORS (DST check on NY)")
    for d in ["2023-01-15", "2023-07-15"]:        # winter EST vs summer EDT
        day = pd.Timestamp(d)
        print(f"  {d}: " + "  ".join(
            f"{s}={session_anchor(day, s).strftime('%H:%M')}UTC" for s in SESSIONS))

    _hdr("4. BUILD SESSION SIGNALS")
    sig = build_session_signals(bars, atr)
    print(f"  total signal rows : {len(sig):,}")

    # sanity invariants — fail loud if the feature layer is wrong
    assert (sig["or_high"] >= sig["or_low"]).all(), "or_high < or_low"
    assert (sig["range_w"] >= 0).all(), "negative range width"
    assert sig[["or_high", "or_low"]].notna().all().all(), "NaN in range bounds"

    _hdr("5. PER-SESSION SUMMARY")
    for s in SESSIONS:
        sub = sig.xs(s, level="session")
        broke = sub["direction"] != "none"
        aligned = sub.loc[broke, "vwap_aligned"]
        print(f"  {s:<7}: n={len(sub):>3}  broke={broke.mean():.0%}  "
              f"vwap_aligned(of broke)={aligned.mean():.0%}  "
              f"range_w[med]={sub['range_w'].median():.2f}  "
              f"r_regime[med]={sub['range_w_regime'].median():.2f}")
    al = sig.loc[sig['direction'] != 'none', 'vwap_aligned'].mean()
    print(f"\n  VWAP-aligned overall: {al:.0%}  "
          f"(<100% confirms the prior-24h filter now discriminates; "
          f"session-anchored VWAP was 100% = no-op)")

    _hdr("6. SAMPLE ROWS (first 8 breakouts)")
    cols = ["or_high", "or_low", "range_w", "direction", "break_time",
            "entry_px", "vwap_at_break", "range_w_regime", "vwap_aligned"]
    with pd.option_context("display.width", 200, "display.max_columns", 20):
        print(sig[sig["direction"] != "none"][cols].head(8).to_string())

    # entry price must equal the breached range level (realistic stop fill)
    longs = sig[sig["direction"] == "long"]
    shorts = sig[sig["direction"] == "short"]
    assert np.allclose(longs["entry_px"], longs["or_high"]), "long entry != or_high"
    assert np.allclose(shorts["entry_px"], shorts["or_low"]), "short entry != or_low"

    _hdr("GATE 2 SANITY: PASS — feature layer builds clean, all invariants hold")


if __name__ == "__main__":
    main()
