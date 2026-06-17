"""
dataset.py — BRC-001 per-zone Gate-3 dataset assembler (task 108).

Ties the four BRC modules into ONE per-zone table — the input to the Gate-3 edge
test (task 110):
    zones.py        confirmed 5-pointer geometry (L1/L2/mid, break_kind)
    lifecycle.py    invalidation = death boundary (close beyond L2)   [task 116]
    retest.py       wick touch ladder T1→T2→T3, deepest_T             [task 108]
    continuation.py Option-A forward return from each touch bar       [task 108]

One row per confirmed zone. The columns let task 110 test:
    H_base  vs H_alt-1 : sign of cont_* (continuation vs fade-the-level)
    H_alt-2            : break_kind (same_bar vs sequential — is the 2nd break
                         load-bearing?)
and condition any of it on deepest_T / invalidation.

D1 only, single-TF atom. Writes CSV to research/outputs/brc001/.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from zones import BrcZone        # import first: runs _struct_on_path
from structures import SignalDirection
import lifecycle as lc
import retest as rt
import continuation as cont


def build_dataset(tf: str = "D1", swing_window: int = 3, horizon: int = 10) -> "pd.DataFrame":
    """Assemble the per-zone dataset (one row per confirmed zone)."""
    import rawbreakout as rb
    import zones as zmod

    df, _, _ = rb.raw_breakouts(tf, swing_window=swing_window)
    zs = zmod.detect_zones(tf, swing_window=swing_window)
    lives = {id(L.zone): L for L in lc.label_lifecycles(df, zs)}

    rows = []
    for zid, z in enumerate(zs):          # zs already sorted by p4_time
        life = lives[id(z)]
        lad = rt.find_retest_ladder(df, z, life)
        row = {
            "zone_id": zid,
            "direction": "SELL" if z.direction == SignalDirection.BEARISH else "BUY",
            "break_kind": z.break_kind,
            "p4_time": pd.Timestamp(z.p4_time),
            "l1": z.l1_price, "mid": z.mid, "l2": z.l2_price, "p5": z.p5_price,
            "invalidated": life.invalidated,
            "invalidation_time": life.invalidation_time,
            "bars_alive": life.bars_alive,
            "deepest_T": lad.deepest_T,
        }
        for lvl in (1, 2, 3):
            t = lad.touches.get(lvl)
            row[f"touched_T{lvl}"] = t is not None
            row[f"t{lvl}_time"] = t.time if t else pd.NaT
            row[f"t{lvl}_bars_after_p4"] = t.bars_after_p4 if t else pd.NA
            if t is not None:
                c = cont.label_continuation(df, z, t, life, horizon=horizon)
                row[f"contH_T{lvl}"] = c.cont_H
                row[f"cont_inval_T{lvl}"] = c.cont_inval
            else:
                row[f"contH_T{lvl}"] = float("nan")
                row[f"cont_inval_T{lvl}"] = float("nan")
        rows.append(row)

    return pd.DataFrame(rows)


def _main(argv: list[str]) -> None:
    import sys as _sys
    here = Path(__file__).resolve().parent
    if str(here) not in _sys.path:
        _sys.path.insert(0, str(here))

    tf = argv[argv.index("--tf") + 1].upper() if "--tf" in argv else "D1"
    window = int(argv[argv.index("--window") + 1]) if "--window" in argv else 3
    H = int(argv[argv.index("--H") + 1]) if "--H" in argv else 10

    data = build_dataset(tf, swing_window=window, horizon=H)
    out = Path(__file__).resolve().parents[4] / "research" / "outputs" / "brc001"
    out.mkdir(parents=True, exist_ok=True)
    csv = out / f"brc001_gate3_dataset_{tf}_H{H}.csv"
    data.to_csv(csv, index=False)

    n = len(data)
    print(f"{tf} window={window} H={H}  zones={n}  ->  {csv}")
    print(f"  invalidated={data.invalidated.sum()}  alive={(~data.invalidated).sum()}")
    print("  deepest-T:", {k: int((data.deepest_T == k).sum()) for k in (0, 1, 2, 3)})
    print("  break_kind:", dict(data.break_kind.value_counts()))
    for lvl in (1, 2, 3):
        sub = data[data[f"touched_T{lvl}"]]
        if len(sub):
            print(f"  T{lvl}: n={len(sub):4d}  "
                  f"meanContH={sub[f'contH_T{lvl}'].mean():+7.3f}  "
                  f"meanContInval={sub[f'cont_inval_T{lvl}'].mean():+7.3f}")


if __name__ == "__main__":
    import sys as _sys
    _main(_sys.argv[1:])
