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
