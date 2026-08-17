"""
lifecycle.py — BRC-001 post-confirmation zone invalidation (task 116).

A confirmed BrcZone is born at P4 (the 2nd-break bar). zones.py only enforces the
PRE-confirmation gap gate (_passes_gap, L2 not closed-through before P4); once a
zone exists, nothing there kills it. This module supplies the POST-confirmation
death boundary that every later measurement (retest ladder, continuation horizon —
task 108) must respect: a zone is DEAD on the first bar whose CLOSE breaks beyond
L2 in the anti-break direction.

Mirrors the live EA exactly (B2BZoneStatus.mqh:169-197, UpdateZoneStatus):
    SELL (BEARISH): invalidation_level = MAX(L1, L2) ; dead when close > level
    BUY  (BULLISH): invalidation_level = MIN(L1, L2) ; dead when close < level
Under the restored P3<P1 gate L2 == P1 and L2 is already the extreme, so the
MAX/MIN collapses to L2 — but we keep the EA's MAX/MIN form so the rule stays
correct even if the geometry ever changes.

CLOSE-only, by design (EA uses current_close). Note the deliberate asymmetry the
handover flags: T3 = a WICK poke of L2 leaves the zone ALIVE (a touch, task 108);
invalidation needs a CLOSE beyond L2 to kill it. Same level, two rules. The
forward walk starts on the bar STRICTLY AFTER P4 (P4 itself closes beyond P5, which
is more extreme than L1 but inside L2, so it can never self-invalidate).

D1 only, single-TF atom (no multi-TF russian-doll).

Reference: mt5/Include/Sigma_System/V5.0/Detection/B2BZoneStatus.mqh:169-197
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from zones import BrcZone        # import first: runs _struct_on_path (puts struct/ on sys.path)
from structures import SignalDirection


@dataclass(frozen=True)
class ZoneLife:
    """The lived span of a confirmed zone, from birth (P4) to death (first close
    beyond L2) or to the end of available data (still alive)."""
    zone: "BrcZone"
    invalidation_level: float        # = MAX(L1,L2) SELL / MIN(L1,L2) BUY
    invalidated: bool                # False => still alive at end of data
    invalidation_time: object        # bar time of the killing close (None if alive)
    invalidation_price: float | None # the close that killed it (None if alive)
    bars_alive: int                  # P4-exclusive bar count until death (or data end)


def _invalidation_level(zone: "BrcZone", sell: bool) -> float:
    return max(zone.l1_price, zone.l2_price) if sell else min(zone.l1_price, zone.l2_price)


def zone_life(df, zone: "BrcZone") -> "ZoneLife":
    """Forward-walk `df` from the bar AFTER P4 and return the zone's lived span.

    Death = first bar CLOSING beyond L2 (close > level SELL / close < level BUY).
    If no such bar exists, the zone is still alive at the end of the data.
    """
    sell = zone.direction == SignalDirection.BEARISH
    level = _invalidation_level(zone, sell)

    times = pd.DatetimeIndex(pd.to_datetime(df["time"].values))
    closes = df["close"].values

    # bars strictly after P4 (P4 confirms the zone; it cannot self-invalidate).
    post = times > pd.Timestamp(zone.p4_time)
    idx = post.nonzero()[0]

    for k, j in enumerate(idx):
        c = closes[j]
        dead = (c > level) if sell else (c < level)
        if dead:
            return ZoneLife(
                zone=zone, invalidation_level=level, invalidated=True,
                invalidation_time=times[j], invalidation_price=float(c),
                bars_alive=k,
            )

    return ZoneLife(
        zone=zone, invalidation_level=level, invalidated=False,
        invalidation_time=None, invalidation_price=None,
        bars_alive=len(idx),
    )


def label_lifecycles(df, zones: list["BrcZone"]) -> list["ZoneLife"]:
    """Map zone_life over a list of confirmed zones (death boundary for task 108)."""
    return [zone_life(df, z) for z in zones]


def _main(argv: list[str]) -> None:
    import sys as _sys
    from pathlib import Path

    here = Path(__file__).resolve().parent
    if str(here) not in _sys.path:
        _sys.path.insert(0, str(here))
    import rawbreakout as rb
    import zones as zmod

    tf = argv[argv.index("--tf") + 1].upper() if "--tf" in argv else "D1"
    window = int(argv[argv.index("--window") + 1]) if "--window" in argv else 3

    df, _, _ = rb.raw_breakouts(tf, swing_window=window)
    zs = zmod.detect_zones(tf, swing_window=window)
    lives = label_lifecycles(df, zs)

    dead = sum(1 for L in lives if L.invalidated)
    alive = len(lives) - dead
    spans = [L.bars_alive for L in lives if L.invalidated]
    med = sorted(spans)[len(spans) // 2] if spans else float("nan")
    print(f"{tf} window={window}  zones={len(lives)}  "
          f"invalidated={dead}  still_alive={alive}  "
          f"median_bars_to_death={med}")
    for L in lives[:5]:
        z = L.zone
        d = "SELL" if z.direction == SignalDirection.BEARISH else "BUY"
        tag = (f"DEAD @ {str(L.invalidation_time)[:10]} ({L.bars_alive}b)"
               if L.invalidated else f"ALIVE ({L.bars_alive}b)")
        print(f"  {d}  P4={str(z.p4_time)[:10]}  L2={z.l2_price:.2f}  {tag}")


if __name__ == "__main__":
    import sys as _sys
    _main(_sys.argv[1:])
