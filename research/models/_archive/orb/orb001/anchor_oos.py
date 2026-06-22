"""
ORB-001 backlog task 22 — anchor candidate OOS + fill re-validation.

Task 15 (IS-only sweep, anchor_sweep.py) found incumbent 08:00/N=5 was NOT
IS-optimal on $/trade (ranked 13/20). Three cells looked better on IS:
    08:30/N=3 (+53%), 08:30/N=5 (+41%), 09:00/N=5 (+38%).
We did not switch — IS-only 20-cell grid is overfit-prone + narrow-N fills
unvalidated. THIS script is the validation: run each candidate through the
trail_1R fill gauntlet OOS (post-2024-05-02) + fill realism, vs the incumbent.

Parametrizes trail_oos.py's verbatim trail_1R per-day sim on (anchor_hour,
n_minutes). Reads the session-slice cache (Layer A). Runs fast.

    python research/models/orb/anchor_oos.py

DECISION RULE (printed in VERDICT): switch the anchor ONLY if a candidate's OOS
$/trade beats incumbent 08:00/N=5 by more than 1 SE AND it retains a comparable
share of edge post-fill (slip-2x + gap-through). Otherwise KEEP incumbent.

Outputs -> research/outputs/orb/anchor_oos/
    anchor_oos_cells.csv  anchor_oos_summary.json
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

# Cells: (anchor_hour, n_minutes). First is the incumbent.
INCUMBENT   = (8.0, 5)
CANDIDATES  = [(8.5, 3), (8.5, 5), (9.0, 5)]
CELLS       = [INCUMBENT] + CANDIDATES

SPREAD       = 2.0 * 0.10
IS_CUT       = np.datetime64(IS_END)
IS_TRAIL_REF = 0.7910          # incumbent IS trail_1R control (trail_oos.py)
SLIP_SCENARIOS = [0.0, 0.5, 1.0, 2.0]
OOS_MONTHS   = [(y, m) for y in range(2024, 2027) for m in range(1, 13) if (y, m) >= (2024, 5)]
EOD_HOUR     = 21
NS_H = 3_600_000_000_000
NS_M =    60_000_000_000
NS_D = 86_400_000_000_000
_OUT = REPO / "research" / "outputs" / "orb" / "anchor_oos"


# ---------------------------------------------------------------------------
# Per-day trail_1R sim — verbatim trail logic from trail_oos.py, parametrized
# on (anchor_hour, n_minutes). slip_extra/gap_fill as in trail_oos.
# ---------------------------------------------------------------------------

def _simulate_day(ts, mid, day0, anchor_hour, n_minutes, slip_extra=0.0, gap_fill=False):
    # DEPRECATED / RETIRED (task 49, 2026-06-13): idealized mid+tolerance fill path.
    # Superseded by research/code/fills.py (realistic bid/ask, MT5-faithful). Kept
    # only because the abandoned ORB-001 tree imports it; do NOT use in new work and
    # do NOT delete (the handover forbids retrofitting the dead ORB scripts).
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
    ef_trail     = emid - pdir * half * (1.0 + slip_extra)
    ef_adj_trail = pdir * (ef_trail - e) / rw

    def first(mask):
        return int(np.argmax(mask)) if mask.any() else None

    peak_g = np.maximum.accumulate(g)
    rel    = g <= peak_g - rw + half
    i_x    = first(rel)
    if i_x is not None:
        i_fill  = min(i_x + 1, len(ef_adj_trail) - 1) if gap_fill else i_x
        R_trail = float(ef_adj_trail[i_fill])
    else:
        R_trail = float(ef_adj_trail[-1])

    return {"range_w": rw, "R": R_trail}


def _scan(files, anchor_hour, n_minutes, oos=True, slip_extra=0.0, gap_fill=False, desc=""):
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
            r = _simulate_day(ts_all[mk], mid_all[mk], int(d) * NS_D,
                              anchor_hour, n_minutes, slip_extra, gap_fill)
            if r is not None:
                rows.append(r)
    return rows


def _stats(rows):
    if not rows:
        return {"n": 0, "E_R": None, "SE_R": None, "t_stat": None,
                "win_pct": None, "dollar_per_trade": None}
    R  = np.array([r["R"] for r in rows], dtype=float)
    rw = np.array([r["range_w"] for r in rows], dtype=float)
    n  = len(R); mu = float(R.mean()); sd = float(R.std(ddof=1))
    se = sd / np.sqrt(n)
    t  = mu / se if sd > 0 and n > 1 else float("nan")
    return {"n": n, "E_R": round(mu, 4), "SE_R": round(se, 4),
            "t_stat": round(t, 2), "win_pct": round(float((R > 0).mean()) * 100, 1),
            "dollar_per_trade": round(float((R * rw).mean()), 4)}


def _ah(ah):
    h, m = divmod(int(round(ah * 60)), 60)
    return f"{h:02d}:{m:02d}"


def main():
    _OUT.mkdir(parents=True, exist_ok=True)
    files = session_files(None)
    files_oos = session_files(OOS_MONTHS)
    if not files:
        sys.exit("No session-cache files. Build first: python research/code/session_cache.py build")

    print("=" * 92)
    print("ORB-001 TASK 22 — anchor candidate OOS + fill re-validation (trail_1R)")
    print(f"  OOS = ts >= {IS_END.date()}  |  cells: " +
          ", ".join(f"{_ah(a)}/N={n}" for a, n in CELLS))
    print(f"  session-cache files: {len(files)}")
    print("=" * 92)

    # 0) IS control repro — incumbent must reproduce +0.7910R or halt
    print("[0] IS control repro: incumbent 08:00/N=5 trail_1R ...")
    is_inc = _stats(_scan(files, *INCUMBENT, oos=False, desc="IS 08:00/N=5"))
    er = is_inc["E_R"]
    ok = er is not None and abs(er - IS_TRAIL_REF) < 0.02
    print(f"    IS trail_1R E[R]={er:+.4f}  vs ref {IS_TRAIL_REF:+.4f}: "
          f"{'OK' if ok else '*** MISMATCH'}  n={is_inc['n']}")
    if not ok:
        sys.exit("*** IS control repro failed — halting (cache or logic drift).")

    # 1) Per-cell OOS + fill gauntlet
    cell_out = []
    for a, n in CELLS:
        tag = f"{_ah(a)}/N={n}"
        is_inc_cell = (a, n) == INCUMBENT
        print(f"\n[cell] {tag}{'  <- incumbent' if is_inc_cell else ''}")
        base = _stats(_scan(files_oos, a, n, oos=True, slip_extra=0.0, desc=f"{tag} slip0"))
        print(f"    OOS slip0 : E[R]={base['E_R']:+.4f}  t={base['t_stat']:+.2f}  "
              f"win={base['win_pct']:.1f}%  $/t={base['dollar_per_trade']:+.4f}  n={base['n']}")
        if base["n"] < 200:
            print(f"    **LOW-N ({base['n']}) — fills sparse, treat with caution")

        slips = {0.0: base}
        for s in SLIP_SCENARIOS[1:]:
            st = _stats(_scan(files_oos, a, n, oos=True, slip_extra=s, desc=f"{tag} slip{s}"))
            slips[s] = st
            print(f"    OOS slip{s}x: E[R]={st['E_R']:+.4f}  $/t={st['dollar_per_trade']:+.4f}")
        gap = _stats(_scan(files_oos, a, n, oos=True, slip_extra=0.0, gap_fill=True, desc=f"{tag} gap"))
        print(f"    OOS gap   : E[R]={gap['E_R']:+.4f}  $/t={gap['dollar_per_trade']:+.4f}")

        er0 = base["E_R"]
        surv_2x  = (slips[2.0]["E_R"] / er0 * 100.0) if er0 else float("nan")
        surv_gap = (gap["E_R"]       / er0 * 100.0) if er0 else float("nan")
        print(f"    edge surviving fill: slip2x={surv_2x:.0f}%  gap={surv_gap:.0f}%")
        cell_out.append({"cell": tag, "anchor_hour": a, "n_minutes": n,
                         "incumbent": is_inc_cell, **base,
                         "ER_slip2x": slips[2.0]["E_R"], "ER_gap": gap["E_R"],
                         "surv_2x_pct": round(surv_2x, 1), "surv_gap_pct": round(surv_gap, 1)})

    # 2) Verdict
    df = pd.DataFrame(cell_out)
    inc = df[df["incumbent"]].iloc[0]
    inc_dp = float(inc["dollar_per_trade"]); inc_se = float(inc["SE_R"])
    inc_surv2x = float(inc["surv_2x_pct"]); inc_survgap = float(inc["surv_gap_pct"])

    print("\n" + "=" * 92)
    print("VERDICT — switch only if a candidate beats incumbent $/trade by >1 SE AND holds fill")
    print(f"  incumbent {inc['cell']}: $/t={inc_dp:+.4f}  SE_R={inc_se:.4f}  "
          f"surv slip2x={inc_surv2x:.0f}%  gap={inc_survgap:.0f}%  n={int(inc['n'])}")
    print("  " + "-" * 88)
    decision = "KEEP_INCUMBENT"; winner = inc["cell"]; best_gap = 0.0
    for _, r in df[~df["incumbent"]].sort_values("dollar_per_trade", ascending=False).iterrows():
        gap_dp = float(r["dollar_per_trade"]) - inc_dp
        beats = gap_dp > inc_se                                  # >1 SE on incumbent
        holds = (float(r["surv_2x_pct"]) >= inc_surv2x - 10 and  # within 10pp fill retention
                 float(r["surv_gap_pct"]) >= inc_survgap - 10)
        enough_n = int(r["n"]) >= 200
        nflag = "  **LOW-N" if not enough_n else ""
        is_switch = beats and holds and enough_n
        verdict = "SWITCH-CANDIDATE" if is_switch else "no"
        print(f"  {r['cell']:>9}: $/t={float(r['dollar_per_trade']):+.4f}  "
              f"gap={gap_dp:+.4f} ({'>' if beats else '<='}SE)  "
              f"surv2x={float(r['surv_2x_pct']):.0f}% gap={float(r['surv_gap_pct']):.0f}%  "
              f"n={int(r['n'])}{nflag}  -> {verdict}")
        if is_switch and gap_dp > best_gap:
            decision = "SWITCH"; winner = r["cell"]; best_gap = gap_dp
    print("  " + "-" * 88)
    if decision == "SWITCH":
        print(f"  >>> SWITCH anchor to {winner} — beats incumbent OOS + holds fill.")
    else:
        print(f"  >>> KEEP incumbent 08:00/N=5 — no candidate clears OOS + fill bar.")
    print("=" * 92)

    df.to_csv(_OUT / "anchor_oos_cells.csv", index=False, encoding="utf-8")
    summary = {"model": "ORB-001", "analysis": "anchor_oos_task22",
               "is_sealed": str(IS_END.date()), "cells": cell_out,
               "is_control_repro": {"E_R": er, "ref": IS_TRAIL_REF, "ok": ok},
               "incumbent_dpt": inc_dp, "incumbent_SE_R": inc_se,
               "decision": decision, "winner": winner}
    (_OUT / "anchor_oos_summary.json").write_text(json.dumps(summary, indent=2, default=str),
                                                  encoding="utf-8")
    print(f"Outputs -> {_OUT}")


if __name__ == "__main__":
    main()
