"""
continuation.py — BRC-001 continuation labelling (task 108, Option A).

After a retest touch, measure the forward return in the BREAK direction. Anchor =
Option A (DECIDED 2026-06-17): measure FROM the retest touch bar, not from P4. This
is the dependent variable for the Gate-3 edge test (task 110):
  H_base : continuation > 0 (price resumes in the break direction — "memory")
  H_alt-1: continuation <= 0 (the retest reverts — fade-the-level / no memory)

Returns are SIGNED by direction so positive always means "continued in the break
direction":
  BEARISH (SELL): favourable = price falls → return = close[from] - close[to]
  BULLISH (BUY) : favourable = price rises → return = close[to]  - close[from]

Two horizons per touch (both in PRICE POINTS; $/trade + cost deduction live in the
Gate-3 harness, NOT here):
  cont_H     : fixed H bars forward from the touch bar (NaN if data runs out).
  cont_inval : touch bar → zone death (or data end) — the unmanaged hold, bounded by
               the lifecycle.py invalidation boundary. This is the natural stop side:
               invalidation is always a close beyond L2 AGAINST the break.

D1 only, single-TF atom.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from zones import BrcZone        # import first: runs _struct_on_path
from structures import SignalDirection
from lifecycle import ZoneLife
from retest import Touch


@dataclass(frozen=True)
class Continuation:
    level: int               # which ladder level the touch was (1/2/3)
    cont_H: float            # signed break-dir points over H bars (NaN if insufficient)
    cont_inval: float        # signed break-dir points to zone death / data end


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


def _signed(closes, frm: int, to: int, sell: bool) -> float:
    """Break-direction price move (points) between two absolute df positions."""
    return float(closes[frm] - closes[to]) if sell else float(closes[to] - closes[frm])


def label_continuation(df, zone: "BrcZone", touch: "Touch",
                       life: "ZoneLife", horizon: int = 10) -> "Continuation":
    """Signed forward return in the break direction from `touch`'s bar."""
    sell = zone.direction == SignalDirection.BEARISH
    closes = df["close"].values
    times = pd.DatetimeIndex(pd.to_datetime(df["time"].values))
    n = len(closes)
    frm = touch.bar_index

    # fixed horizon
    to_h = frm + horizon
    cont_h = _signed(closes, frm, to_h, sell) if to_h < n else float("nan")

    # to-invalidation (or data end) — terminal absolute index
    if life.invalidated:
        term = int((times == pd.Timestamp(life.invalidation_time)).argmax())
    else:
        term = n - 1
    if term < frm:          # touch on/after the death bar → degenerate hold
        term = frm
    cont_inval = _signed(closes, frm, term, sell)

    return Continuation(level=touch.level, cont_H=cont_h, cont_inval=cont_inval)


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
    H = int(argv[argv.index("--H") + 1]) if "--H" in argv else 10
    df, _, _ = rb.raw_breakouts(tf, swing_window=window)
    zs = zmod.detect_zones(tf, swing_window=window)
    lives = {id(L.zone): L for L in lc.label_lifecycles(df, zs)}

    import numpy as np
    for lvl in (1, 2, 3):
        ch, ci = [], []
        for z in zs:
            lad = rt.find_retest_ladder(df, z, lives[id(z)])
            t = lad.touches.get(lvl)
            if t is None:
                continue
            c = label_continuation(df, z, t, lives[id(z)], horizon=H)
            ch.append(c.cont_H); ci.append(c.cont_inval)
        ch = np.array([x for x in ch if x == x]); ci = np.array(ci)
        print(f"T{lvl}: n={len(ci):4d}  meanContH(${H}b)={np.nanmean(ch):+8.3f}  "
              f"meanContInval={np.mean(ci) if len(ci) else float('nan'):+8.3f}")


if __name__ == "__main__":
    import sys as _sys
    _main(_sys.argv[1:])
