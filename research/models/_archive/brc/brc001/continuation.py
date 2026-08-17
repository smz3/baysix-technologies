"""
continuation.py — BRC-001 continuation labelling (task 108).

BRC is EVENT-BASED: the only clocks are the retest TOUCH (price re-touches a zone
level after confirmation, retest.py) and zone DEATH (close beyond L2, lifecycle.py).
There is NO fixed-bar horizon — a calendar window would measure price after the zone
is already dead (~48% of retests die before +10 bars). Removed 2026-06-17 (the
fixed-H `label_continuation` was a dead label that fed nothing; Syafiq flagged it).

All measures here anchor on the retest touch (Option A, DECIDED 2026-06-17 — from the
touch bar, not P4) and resolve on zone events:
  let_run     : unmanaged hold, stop=L2, no TP — exit on the invalidation event.
  barrier_race: first-passage between a +target_R close and the L2 invalidation close.
  excursion   : MFE/MAE in R over the alive window [touch -> death].

Returns favour the BREAK direction (SELL: price falls; BUY: price rises). R = |L1-L2|.
Single-TF atom (D1/H4/...), TF passed by the caller.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from zones import BrcZone        # import first: runs _struct_on_path
from structures import SignalDirection
from lifecycle import ZoneLife
from retest import Touch


@dataclass(frozen=True)
class Excursion:
    """Path-aware continuation, measured ONLY while the zone is alive (task 108b —
    fixed-H is deprecated: ~48% of retests die before +10 bars, so a calendar window
    measures price after the zone is dead). Entry = the L1 retest fill; risk unit
    R = |L1 - L2| (the zone height = distance to invalidation). Excursions use the
    bar extremes (intrabar high/low), normalized to R."""
    R: float                 # |L1 - L2| zone height (price points)
    mfe_r: float             # max FAVOURABLE excursion (break dir) / R, from entry
    mae_r: float             # max ADVERSE excursion / R, from entry
    bars_to_mfe: int         # bars from the retest entry to the favourable extreme
    n_bars: int              # bars in the alive window (entry -> death/data-end)


@dataclass(frozen=True)
class LetRun:
    """Unmanaged 'let winners run to invalidation' hold from the L1 retest entry.
    Stop = L2 (-1R, the lifecycle invalidation boundary); NO profit cap. The trade
    exits on the first CLOSE beyond L2 (loss, ~ -1R or worse — the close overshoots)
    or, if the zone never dies, at the last close (an alive RUNNER, possibly many R).
    This is the only thread the symmetric 1R race left open: winners' MFE ~2R vs the
    1R stop. realized_r = signed(entry -> exit close) / R, R = |L1 - L2|."""
    realized_r: float
    invalidated: bool
    bars_held: int


def let_run(df, zone: "BrcZone", touch: "Touch", life: "ZoneLife") -> "LetRun":
    """Close-based unmanaged hold: stop at L2, no take-profit, exit at death or end."""
    sell = zone.direction == SignalDirection.BEARISH
    times = pd.DatetimeIndex(pd.to_datetime(df["time"].values))
    closes = df["close"].values
    n = len(closes)

    entry = zone.l1_price
    R = abs(zone.l1_price - zone.l2_price)
    stop = zone.l2_price

    start = int((times >= pd.Timestamp(touch.time)).argmax())
    for j in range(start, n):
        c = closes[j]
        dead = (c > stop) if sell else (c < stop)
        if dead:
            r = (entry - c) / R if sell else (c - entry) / R
            return LetRun(realized_r=float(r), invalidated=True, bars_held=j - start)
    c = closes[n - 1]
    r = (entry - c) / R if sell else (c - entry) / R
    return LetRun(realized_r=float(r), invalidated=False, bars_held=n - 1 - start)


@dataclass(frozen=True)
class Race:
    """First-passage (Ruler B) outcome from the retest entry, both barriers
    CLOSE-based so daily bars need no intrabar order assumption:
        WIN  = a bar CLOSES >= target_R*R in the break direction first
        LOSS = a bar CLOSES beyond L2 first (= invalidation, lifecycle.py)
        OPEN = neither before data end (still alive)
    R = |L1 - L2| (the zone's own height = the stop distance). Entry = L1."""
    outcome: str             # 'win' | 'loss' | 'open'
    bars_to_resolve: int     # bars from entry to the deciding close (data-end if open)
    target_R: float


def barrier_race(df, zone: "BrcZone", touch: "Touch", life: "ZoneLife",
                 target_R: float = 1.0) -> "Race":
    """Close-based race between a +target_R profit barrier and the L2 stop."""
    sell = zone.direction == SignalDirection.BEARISH
    times = pd.DatetimeIndex(pd.to_datetime(df["time"].values))
    closes = df["close"].values
    n = len(closes)

    entry = zone.l1_price
    R = abs(zone.l1_price - zone.l2_price)
    stop = zone.l2_price
    target = (entry - target_R * R) if sell else (entry + target_R * R)

    start = int((times >= pd.Timestamp(touch.time)).argmax())
    for j in range(start, n):
        c = closes[j]
        win = (c <= target) if sell else (c >= target)
        loss = (c > stop) if sell else (c < stop)
        if win:
            return Race("win", j - start, target_R)
        if loss:
            return Race("loss", j - start, target_R)
    return Race("open", n - 1 - start, target_R)


def excursion(df, zone: "BrcZone", touch: "Touch", life: "ZoneLife") -> "Excursion":
    """MFE/MAE in R units over the alive window [retest touch -> invalidation bar
    inclusive] (or -> data end if the zone never dies). Favourable = the break
    direction; R = the L1->L2 distance the stop sits at."""
    sell = zone.direction == SignalDirection.BEARISH
    times = pd.DatetimeIndex(pd.to_datetime(df["time"].values))
    highs = df["high"].values
    lows = df["low"].values

    entry = zone.l1_price
    R = abs(zone.l1_price - zone.l2_price)

    win = times >= pd.Timestamp(touch.time)
    if life.invalidated:                       # include the death bar (the stop hit)
        win = win & (times <= pd.Timestamp(life.invalidation_time))
    idx = win.nonzero()[0]

    # favourable extreme = lowest low (SELL) / highest high (BUY); adverse = mirror
    fav = lows[idx].min() if sell else highs[idx].max()
    adv = highs[idx].max() if sell else lows[idx].min()
    mfe = (entry - fav) if sell else (fav - entry)
    mae = (adv - entry) if sell else (entry - adv)

    fav_pos = lows[idx].argmin() if sell else highs[idx].argmax()
    return Excursion(
        R=float(R), mfe_r=float(mfe / R), mae_r=float(mae / R),
        bars_to_mfe=int(fav_pos), n_bars=int(len(idx)),
    )


def _main(argv: list[str]) -> None:
    import sys as _sys
    from pathlib import Path
    here = Path(__file__).resolve().parent
    if str(here) not in _sys.path:
        _sys.path.insert(0, str(here))
    import rawbreakout as rb
    import zones as zmod
    import lifecycle as lc
    import retest as rt

    tf = argv[argv.index("--tf") + 1].upper() if "--tf" in argv else "D1"
    window = int(argv[argv.index("--window") + 1]) if "--window" in argv else 3
    df, _, _ = rb.raw_breakouts(tf, swing_window=window)
    zs = zmod.detect_zones(tf, swing_window=window)
    lives = {id(L.zone): L for L in lc.label_lifecycles(df, zs)}

    import numpy as np
    # event-based summary: entry on the retest touch of each ladder level, exit on
    # the zone-death event (let_run) or the +1R/-L2 first-passage (barrier_race).
    for lvl in (1, 2, 3):
        lr, mfe, race = [], [], {"win": 0, "loss": 0, "open": 0}
        for z in zs:
            life = lives[id(z)]
            t = rt.find_retest_ladder(df, z, life).touches.get(lvl)
            if t is None:
                continue
            lr.append(let_run(df, z, t, life).realized_r)
            mfe.append(excursion(df, z, t, life).mfe_r)
            race[barrier_race(df, z, t, life).outcome] += 1
        n = len(lr)
        if not n:
            continue
        lr = np.array(lr); mfe = np.array(mfe)
        print(f"T{lvl}: n={n:4d}  letRun E[R]={lr.mean():+7.3f} med={np.median(lr):+6.3f}  "
              f"MFE med={np.median(mfe):.2f}R  1R-race win/loss/open="
              f"{race['win']}/{race['loss']}/{race['open']}")


if __name__ == "__main__":
    import sys as _sys
    _main(_sys.argv[1:])
