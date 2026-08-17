"""
retest.py — BRC-001 retest ladder (task 108).

After a zone confirms at P4, price may pull back INTO the zone and re-touch its
levels. The touch ladder is ordered by depth (T1 shallowest → T3 deepest), using
the CONFIRMED touch model (handover 2026-06-17, EA-matched):
    T1 = L1  = P2          (zone edge nearest the break — first touched)
    T2 = mid = (L1+L2)/2
    T3 = L2  = P1          (far edge — deepest; a CLOSE beyond it = invalidation)

WICK-BASED (deliberate, departs from the close-only STRUCT break rule): a retest is
a touch, and a touch is an intrabar event, so we use the bar's high/low — NOT the
close. SELL break is downward, so the pullback comes UP: a level is touched when
bar.high >= level. BUY mirrors: pullback DOWN, touched when bar.low <= level.
(Contrast invalidation in lifecycle.py, which IS close-only: a wick poke of L2 is a
T3 touch and leaves the zone alive; only a close beyond L2 kills it.)

Scan window = the zone's lived span (P4-exclusive → invalidation bar inclusive, or
data end if still alive); a wick T3 on the very bar that then closes through L2 is a
legitimate T3 touch. Levels are nested, so a T3 touch implies T1/T2 were touched on
or before it — but each level records its OWN first-touch bar (T1 is generally hit
earlier than T3), which is what continuation.py measures forward return FROM.

D1 only, single-TF atom.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from zones import BrcZone        # import first: runs _struct_on_path
from structures import SignalDirection
from lifecycle import ZoneLife


@dataclass(frozen=True)
class Touch:
    """First re-touch of one ladder level after P4 (wick-based)."""
    level: int               # 1=L1, 2=mid, 3=L2
    level_price: float
    time: object
    bar_index: int           # absolute position in df
    bars_after_p4: int       # 0-based bars elapsed since the P4 bar


@dataclass(frozen=True)
class RetestLadder:
    """Per-zone retest summary: the first touch of each level reached, and the
    deepest level the pullback penetrated (T0 = never re-entered the zone)."""
    zone: "BrcZone"
    touches: dict             # {level:int -> Touch} for levels actually touched
    deepest_T: int           # 0..3


def level_prices(zone: "BrcZone") -> dict:
    """Ladder level → price. T1=L1, T2=mid, T3=L2 (independent of direction)."""
    return {1: zone.l1_price, 2: zone.mid, 3: zone.l2_price}


def find_retest_ladder(df, zone: "BrcZone", life: "ZoneLife") -> "RetestLadder":
    """Scan the zone's lived span and record the first wick touch of each ladder
    level. SELL: touched when bar.high >= level; BUY: when bar.low <= level."""
    sell = zone.direction == SignalDirection.BEARISH
    levels = level_prices(zone)

    times = pd.DatetimeIndex(pd.to_datetime(df["time"].values))
    highs = df["high"].values
    lows = df["low"].values

    # lived span: bars strictly after P4 and strictly BEFORE the invalidation bar
    # (or all remaining bars if the zone is still alive). The death bar is EXCLUDED:
    # its close goes beyond L2, which would mechanically register a T3 wick touch on
    # every invalidated zone and conflate "retest reached the far edge" with "zone
    # died". A genuine T3 = a wick poke of L2 on a bar that closes back inside (alive).
    after_p4 = times > pd.Timestamp(zone.p4_time)
    if life.invalidated:
        within = after_p4 & (times < pd.Timestamp(life.invalidation_time))
    else:
        within = after_p4
    idx = within.nonzero()[0]
    p4_pos = int((~after_p4).sum())   # first post-P4 absolute index = count of bars <= P4

    touches: dict = {}
    for j in idx:
        probe = highs[j] if sell else lows[j]
        for lvl, price in levels.items():
            if lvl in touches:
                continue
            hit = (probe >= price) if sell else (probe <= price)
            if hit:
                touches[lvl] = Touch(
                    level=lvl, level_price=float(price), time=times[j],
                    bar_index=int(j), bars_after_p4=int(j - p4_pos),
                )
        if len(touches) == 3:
            break

    deepest = max(touches) if touches else 0
    return RetestLadder(zone=zone, touches=touches, deepest_T=deepest)


def _main(argv: list[str]) -> None:
    import sys as _sys
    from pathlib import Path
    here = Path(__file__).resolve().parent
    if str(here) not in _sys.path:
        _sys.path.insert(0, str(here))
    import rawbreakout as rb
    import zones as zmod
    import lifecycle as lc

    tf = argv[argv.index("--tf") + 1].upper() if "--tf" in argv else "D1"
    window = int(argv[argv.index("--window") + 1]) if "--window" in argv else 3
    df, _, _ = rb.raw_breakouts(tf, swing_window=window)
    zs = zmod.detect_zones(tf, swing_window=window)
    lives = {id(L.zone): L for L in lc.label_lifecycles(df, zs)}

    dist = {0: 0, 1: 0, 2: 0, 3: 0}
    for z in zs:
        lad = find_retest_ladder(df, z, lives[id(z)])
        dist[lad.deepest_T] += 1
    n = len(zs)
    print(f"{tf} window={window}  zones={n}  deepest-T distribution:")
    for k in (0, 1, 2, 3):
        print(f"  T{k}: {dist[k]:4d}  ({100*dist[k]/n:5.1f}%)")


if __name__ == "__main__":
    import sys as _sys
    _main(_sys.argv[1:])
