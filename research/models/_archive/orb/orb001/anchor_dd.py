"""
ORB-001 task 22 follow-on — DD/survival MC for the anchor candidates.

Task 22 (anchor_oos.py) showed later anchors beat incumbent 08:00/N=5 on OOS
$/trade by ~27-32% with ~95% fill survival. Adoption is GATED on the Mode-A
min-lot / 5%-cap DD/survival/ruin MC (er_denominator_illusion + orb_dd_structural
_floor rules) — you never switch a risk-unit on $/trade alone. THIS runs that gate.

Reuses trail_oos.run_trail_mc (the exact MC that governed trail_1R adoption),
parametrized per cell. Central estimate = forward_isedge: OOS-price sizing +
R drawn from the cell's OWN IS trail pool (conservative edge, real -1R floor).
Incumbent 08:00/N=5 included as a CONTROL — must reproduce ~p90 DD 25.5%.

    python research/models/orb/anchor_dd.py

Bar to clear: candidate forward p90 DD <= incumbent's (25.5%), ruin ~0%.
Outputs -> research/outputs/orb/anchor_dd/
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np
import pandas as pd
from research.code.arctic_io import read_tick_month
from tqdm import tqdm

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
from research.models.orb.orb001.orb_core import IS_END
from research.code.session_cache import session_files
from research.models.orb.orb001.trail_oos import run_trail_mc

SPREAD   = 2.0 * 0.10
IS_CUT   = np.datetime64(IS_END)
EOD_HOUR = 21
OOS_MONTHS = [(y, m) for y in range(2024, 2027) for m in range(1, 13) if (y, m) >= (2024, 5)]
NS_H = 3_600_000_000_000
NS_M =    60_000_000_000
NS_D = 86_400_000_000_000

INCUMBENT  = (8.0, 5)
CANDIDATES = [(9.0, 5), (8.5, 3)]      # winner + IS rank-1
CELLS      = [INCUMBENT] + CANDIDATES
INC_P90_REF = 25.5                      # incumbent trail_1R forward p90 DD (task 13)
_OUT = REPO / "research" / "outputs" / "orb" / "anchor_dd"


def _simulate_day(ts, mid, day0, anchor_hour, n_minutes):
    """Trail_1R per-day sim — returns full row for the MC (date set by caller)."""
    half   = SPREAD * 0.5
    anchor = day0 + int(anchor_hour * NS_H)
    or_end = anchor + n_minutes * NS_M
    eod    = day0 + EOD_HOUR * NS_H

    in_or = (ts >= anchor) & (ts < or_end)
    if not in_or.any():
        return None
    or_hi, or_lo = mid[in_or].max(), mid[in_or].min()
    rw = or_hi - or_lo
    if rw <= 0:
        return None
    post = (ts >= or_end) & (ts < eod)
    if not post.any():
        return None
    pmid = mid[post]
    up = pmid >= or_hi - half
    dn = pmid <= or_lo + half
    i_up = int(np.argmax(up)) if up.any() else None
    i_dn = int(np.argmax(dn)) if dn.any() else None
    if i_up is None and i_dn is None:
        return None
    if i_dn is None or (i_up is not None and i_up <= i_dn):
        pdir, e, i_b = 1.0, or_hi, i_up
    else:
        pdir, e, i_b = -1.0, or_lo, i_dn
    emid = pmid[i_b:]
    if len(emid) < 2:
        return None
    g = pdir * (emid - e)
    ef_trail = emid - pdir * half
    ef_adj   = pdir * (ef_trail - e) / rw
    peak_g = np.maximum.accumulate(g)
    rel    = g <= peak_g - rw + half
    i_x    = int(np.argmax(rel)) if rel.any() else None
    R = float(ef_adj[i_x]) if i_x is not None else float(ef_adj[-1])
    return {"direction": "long" if pdir > 0 else "short",
            "range_w": rw, "entry_px": e, "R": R}


def _scan(files, anchor_hour, n_minutes, oos, desc=""):
    rows = []
    for f in tqdm(files, desc=desc, leave=False):
        df = read_tick_month(f, columns=["ts_utc", "bid", "ask"])
        tsv = df["ts_utc"].values
        df = df[tsv >= IS_CUT] if oos else df[tsv < IS_CUT]
        if df.empty:
            continue
        ts_all  = df["ts_utc"].values.astype("datetime64[ns]").astype(np.int64)
        mid_all = (df["bid"].values + df["ask"].values) * 0.5
        day_key = ts_all // NS_D
        for d in np.unique(day_key):
            mk = day_key == d
            r = _simulate_day(ts_all[mk], mid_all[mk], int(d) * NS_D, anchor_hour, n_minutes)
            if r is not None:
                r["date"] = pd.Timestamp(int(d) * NS_D).date()
                rows.append(r)
    return rows


def _ah(ah):
    h, m = divmod(int(round(ah * 60)), 60)
    return f"{h:02d}:{m:02d}"


def main():
    _OUT.mkdir(parents=True, exist_ok=True)
    files     = session_files(None)
    files_oos = session_files(OOS_MONTHS)
    if not files:
        sys.exit("No session-cache files. Build first: python research/code/session_cache.py build")

    print("=" * 92)
    print("ORB-001 TASK 22 DD GATE — Mode-A survival/DD MC for anchor candidates")
    print(f"  cells: " + ", ".join(f"{_ah(a)}/N={n}" for a, n in CELLS))
    print(f"  incumbent forward p90 DD ref = {INC_P90_REF}%  (bar to beat)")
    print("=" * 92)

    out = []
    for a, n in CELLS:
        tag = f"{_ah(a)}/N={n}"
        is_inc = (a, n) == INCUMBENT
        print(f"\n[cell] {tag}{'  <- incumbent (control)' if is_inc else ''}")
        oos_rows = _scan(files_oos, a, n, oos=True,  desc=f"{tag} OOS")
        is_rows  = _scan(files,     a, n, oos=False, desc=f"{tag} IS")
        is_R = [r["R"] for r in is_rows]
        print(f"    OOS n={len(oos_rows)}  IS n={len(is_rows)}  (running MC ...)")
        mc = run_trail_mc(oos_rows, is_trail_R=is_R)
        fwd = mc["forward_isedge"]
        rea = mc["realized"]
        print(f"    FORWARD IS-edge (central): median DD={fwd['median_dd']:.1f}%  "
              f"p90 DD={fwd['p90_dd']:.1f}%  ruin={fwd['p_blowup']:.1f}%  "
              f"med terminal ${fwd['median_terminal']:,.0f}")
        print(f"    realized (rosy)          : median DD={rea['median_dd']:.1f}%  "
              f"p90 DD={rea['p90_dd']:.1f}%  ruin={rea['p_blowup']:.1f}%")
        verdict = "—" if is_inc else ("PASS" if (fwd['p90_dd'] <= INC_P90_REF and fwd['p_blowup'] < 1.0) else "FAIL")
        if not is_inc:
            print(f"    vs incumbent p90 {INC_P90_REF}%: {verdict}")
        out.append({"cell": tag, "anchor_hour": a, "n_minutes": n, "incumbent": is_inc,
                    "oos_n": len(oos_rows), "is_n": len(is_rows),
                    "fwd_median_dd": round(fwd['median_dd'], 1), "fwd_p90_dd": round(fwd['p90_dd'], 1),
                    "fwd_ruin": round(fwd['p_blowup'], 2), "fwd_median_terminal": round(fwd['median_terminal'], 0),
                    "realized_p90_dd": round(rea['p90_dd'], 1), "verdict": verdict})

    print("\n" + "=" * 92)
    print("VERDICT — adopt new anchor only if forward p90 DD <= incumbent 25.5% AND ruin ~0%")
    inc = next(r for r in out if r["incumbent"])
    print(f"  incumbent {inc['cell']}: forward p90 DD={inc['fwd_p90_dd']}%  ruin={inc['fwd_ruin']}%  (control)")
    switch = None
    for r in out:
        if r["incumbent"]:
            continue
        print(f"  {r['cell']:>9}: forward p90 DD={r['fwd_p90_dd']}%  median DD={r['fwd_median_dd']}%  "
              f"ruin={r['fwd_ruin']}%  med terminal ${r['fwd_median_terminal']:,.0f}  -> {r['verdict']}")
        if r["verdict"] == "PASS" and switch is None:
            switch = r["cell"]
    print("  " + "-" * 88)
    print(f"  >>> {'SWITCH anchor to ' + switch if switch else 'KEEP incumbent 08:00/N=5'} "
          f"(DD gate {'cleared' if switch else 'not cleared'})")
    print("=" * 92)

    pd.DataFrame(out).to_csv(_OUT / "anchor_dd_cells.csv", index=False, encoding="utf-8")
    (_OUT / "anchor_dd_summary.json").write_text(
        json.dumps({"model": "ORB-001", "analysis": "anchor_dd_task22",
                    "incumbent_p90_ref": INC_P90_REF, "cells": out,
                    "switch": switch}, indent=2, default=str), encoding="utf-8")
    print(f"Outputs -> {_OUT}")


if __name__ == "__main__":
    main()
