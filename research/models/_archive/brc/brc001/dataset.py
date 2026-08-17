"""
dataset.py — BRC-001 per-zone Gate-3 dataset assembler (task 108).

Ties the four BRC modules into ONE per-zone table — the input to the Gate-3 edge
test (task 110):
    zones.py        confirmed 5-pointer geometry (L1/L2/mid, break_kind)
    lifecycle.py    invalidation = death boundary (close beyond L2)   [task 116]
    retest.py       wick touch ladder T1→T2→T3, deepest_T             [task 108]
    continuation.py EVENT-BASED outcomes from the L1 retest entry     [task 108]

One row per confirmed zone. BRC is event-based — entry on the retest TOUCH, exit on
a zone EVENT (zone death = close beyond L2, or the +1R first-passage). NO fixed-bar
horizon (the dead fixed-H `cont_H` was removed 2026-06-17). The columns let task 110
test:
    payoff edge : let_run_r (unmanaged hold to invalidation) + race_outcome (+1R/-L2)
    H_alt-2     : break_kind (same_bar vs sequential — is the 2nd break load-bearing?)
and condition any of it on deepest_T / invalidation.

Single-TF atom (TF passed by the caller). Writes CSV to research/outputs/brc001/.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from zones import BrcZone        # import first: runs _struct_on_path
from structures import SignalDirection
import lifecycle as lc
import retest as rt
import continuation as cont


def build_dataset(tf: str = "D1", swing_window: int = 3) -> "pd.DataFrame":
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

        # event-based outcomes from the L1 retest entry (the trade trigger)
        t1 = lad.touches.get(1)
        if t1 is not None:
            lr = cont.let_run(df, z, t1, life)
            ex = cont.excursion(df, z, t1, life)
            rc = cont.barrier_race(df, z, t1, life, target_R=1.0)
            row["let_run_r"] = lr.realized_r
            row["mfe_r"] = ex.mfe_r
            row["mae_r"] = ex.mae_r
            row["race_outcome"] = rc.outcome
            row["race_bars"] = rc.bars_to_resolve
        else:
            row["let_run_r"] = float("nan")
            row["mfe_r"] = float("nan")
            row["mae_r"] = float("nan")
            row["race_outcome"] = None
            row["race_bars"] = pd.NA
        rows.append(row)

    return pd.DataFrame(rows)


def _main(argv: list[str]) -> None:
    import sys as _sys
    here = Path(__file__).resolve().parent
    if str(here) not in _sys.path:
        _sys.path.insert(0, str(here))

    tf = argv[argv.index("--tf") + 1].upper() if "--tf" in argv else "D1"
    window = int(argv[argv.index("--window") + 1]) if "--window" in argv else 3

    data = build_dataset(tf, swing_window=window)
    out = Path(__file__).resolve().parents[4] / "research" / "outputs" / "brc001"
    out.mkdir(parents=True, exist_ok=True)
    csv = out / f"brc001_gate3_dataset_{tf}.csv"
    data.to_csv(csv, index=False)

    n = len(data)
    print(f"{tf} window={window}  zones={n}  ->  {csv}")
    print(f"  invalidated={data.invalidated.sum()}  alive={(~data.invalidated).sum()}")
    print("  deepest-T:", {k: int((data.deepest_T == k).sum()) for k in (0, 1, 2, 3)})
    print("  break_kind:", dict(data.break_kind.value_counts()))
    ret = data[data.touched_T1]
    if len(ret):
        rc = ret.race_outcome.value_counts().to_dict()
        print(f"  L1-retest entries: n={len(ret)}  letRun E[R]={ret.let_run_r.mean():+7.3f} "
              f"med={ret.let_run_r.median():+6.3f}  MFE med={ret.mfe_r.median():.2f}R  "
              f"1R-race={rc}")


if __name__ == "__main__":
    import sys as _sys
    _main(_sys.argv[1:])
