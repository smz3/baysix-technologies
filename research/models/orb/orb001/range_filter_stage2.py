"""
ORB-001 task 17 STAGE 2 — width-floor sweep: OOS + fill gauntlet + survival MC.

Stage 1 (range_filter.py) showed: ranges are tight (median $0.64), the $2.50 cap
barely bites (2.9%), and there is NO toxic band — every width decile is positive in
$/trade. E[R] FALLS with width while $/trade RISES (denominator illusion). The only
economically honest filter is therefore a WIDTH FLOOR (drop the lowest-$/trade tight
ranges and favour wider ones), tested against the "no filter" incumbent.

Floors pre-committed from the stage-1 deciles:
    0.00  -> no filter (NULL / incumbent champion — must beat this)
    0.33  -> drop D1-D2 (tightest ~20%)
    0.52  -> drop D1-D4 (tightest ~40%)

For each: IS control repro -> OOS $/trade + fill gauntlet (slip 0/2x + gap) ->
Mode-A survival MC (forward_isedge central estimate, same path as anchor_dd).

ADOPT a floor ONLY if, vs no-filter: OOS $/trade is higher AND forward p90 DD is not
worse AND ruin not worse AND median terminal not worse (rule: $/t + survival, never
E[R]; er_denominator_illusion). Else KEEP no-filter and log the filter FALSIFIED.

    python research/models/orb/range_filter_stage2.py

Outputs -> research/outputs/orb/range_filter/  (stage2_*.csv / .json)
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np
import pandas as pd
from tqdm import tqdm

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
from research.models.orb.orb001.orb_core import IS_END
from research.code.session_cache import session_files
from research.models.orb.orb001.trail_oos import run_trail_mc

ANCHOR_HOUR, N_MIN = 9.0, 5
SPREAD   = 2.0 * 0.10
IS_CUT   = np.datetime64(IS_END)
EOD_HOUR = 21
NS_H = 3_600_000_000_000
NS_M =    60_000_000_000
NS_D = 86_400_000_000_000
OOS_MONTHS = [(y, m) for y in range(2024, 2027) for m in range(1, 13) if (y, m) >= (2024, 5)]

IS_REF_ER = 1.5472          # stage-1 unfiltered 09:00/N5 IS E[R] (control-repro anchor)
FLOORS    = [0.0, 0.33, 0.52]
_OUT = REPO / "research" / "outputs" / "orb" / "range_filter"


def _simulate_day(ts, mid, day0, slip_extra=0.0, gap_fill=False):
    """trail_1R per-day sim (verbatim anchor_oos logic) + entry_px/date for the MC."""
    half   = SPREAD * 0.5
    anchor = day0 + int(ANCHOR_HOUR * NS_H)
    or_end = anchor + N_MIN * NS_M
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
    ef_adj       = pdir * (ef_trail - e) / rw
    peak_g = np.maximum.accumulate(g)
    rel    = g <= peak_g - rw + half
    i_x    = int(np.argmax(rel)) if rel.any() else None
    if i_x is not None:
        i_fill  = min(i_x + 1, len(ef_adj) - 1) if gap_fill else i_x
        R = float(ef_adj[i_fill])
    else:
        R = float(ef_adj[-1])
    return {"range_w": rw, "R": R, "entry_px": e}


def _scan(files, oos, slip_extra=0.0, gap_fill=False, desc=""):
    rows = []
    for f in tqdm(files, desc=desc, leave=False):
        df = pd.read_parquet(f, columns=["ts_utc", "bid", "ask"])
        tsv = df["ts_utc"].values
        df = df[tsv >= IS_CUT] if oos else df[tsv < IS_CUT]
        if df.empty:
            continue
        ts_all  = df["ts_utc"].values.astype("datetime64[ns]").astype(np.int64)
        mid_all = (df["bid"].values + df["ask"].values) * 0.5
        day_key = ts_all // NS_D
        for d in np.unique(day_key):
            mk = day_key == d
            r = _simulate_day(ts_all[mk], mid_all[mk], int(d) * NS_D, slip_extra, gap_fill)
            if r is not None:
                r["date"] = pd.Timestamp(int(d) * NS_D).date()
                rows.append(r)
    return rows


def _stats(rows):
    R  = np.array([r["R"] for r in rows], float)
    rw = np.array([r["range_w"] for r in rows], float)
    n  = len(R); mu = float(R.mean()); sd = float(R.std(ddof=1))
    se = sd / np.sqrt(n); t = mu / se if sd > 0 else float("nan")
    return {"n": n, "E_R": round(mu, 4), "t": round(t, 2),
            "win_pct": round(float((R > 0).mean()) * 100, 1),
            "dollar_per_trade": round(float((R * rw).mean()), 4)}


def _apply_floor(rows, floor):
    return [r for r in rows if r["range_w"] >= floor]


def main():
    _OUT.mkdir(parents=True, exist_ok=True)
    files     = session_files(None)
    files_oos = session_files(OOS_MONTHS)
    if not files:
        sys.exit("No session-cache files. Build first: python research/code/session_cache.py build")

    print("=" * 96)
    print("ORB-001 TASK 17 STAGE 2 — width-floor sweep (OOS + fill + survival MC)")
    print(f"  config 09:00/N5 trail_1R | floors {FLOORS} | OOS ts>= {IS_END.date()}")
    print("=" * 96)

    # Full unfiltered scans (filter is applied in-memory per floor)
    print("[scan] IS + OOS (slip0) ...")
    is_all   = _scan(files,     oos=False, desc="IS slip0")
    oos_all  = _scan(files_oos, oos=True,  desc="OOS slip0")
    oos_2x   = _scan(files_oos, oos=True, slip_extra=2.0, desc="OOS slip2x")
    oos_gap  = _scan(files_oos, oos=True, gap_fill=True,  desc="OOS gap")

    # [0] IS control repro on no-filter
    is_ref = _stats(is_all)
    ok = abs(is_ref["E_R"] - IS_REF_ER) < 0.02
    print(f"\n[0] IS control (no-filter): E[R]={is_ref['E_R']:+.4f} vs ref {IS_REF_ER:+.4f} "
          f"-> {'OK' if ok else '*** MISMATCH'}  n={is_ref['n']}")
    if not ok:
        sys.exit("*** IS control repro failed — halting (cache/logic drift).")

    rows_out = []
    for floor in FLOORS:
        tag = "no_filter" if floor == 0.0 else f"floor_{floor:.2f}"
        isf, oof  = _apply_floor(is_all, floor), _apply_floor(oos_all, floor)
        oof2, oofg = _apply_floor(oos_2x, floor), _apply_floor(oos_gap, floor)
        s0, s2, sg = _stats(oof), _stats(oof2), _stats(oofg)
        retain = round(len(oof) / len(oos_all) * 100, 1)
        surv2x = round(s2["dollar_per_trade"] / s0["dollar_per_trade"] * 100, 0) if s0["dollar_per_trade"] else float("nan")
        survg  = round(sg["dollar_per_trade"] / s0["dollar_per_trade"] * 100, 0) if s0["dollar_per_trade"] else float("nan")
        print(f"\n[{tag}]  floor>={floor:.2f}  retain={retain}% of OOS trades")
        print(f"    OOS slip0 : $/t={s0['dollar_per_trade']:+.4f}  E[R]={s0['E_R']:+.4f}  "
              f"t={s0['t']:+.2f}  win={s0['win_pct']:.1f}%  n={s0['n']}")
        print(f"    fill      : slip2x $/t={s2['dollar_per_trade']:+.4f} ({surv2x:.0f}%)  "
              f"gap $/t={sg['dollar_per_trade']:+.4f} ({survg:.0f}%)")
        # survival MC (central forward_isedge)
        print(f"    survival MC (forward_isedge central) ...")
        mc = run_trail_mc(oof, is_trail_R=[r["R"] for r in isf])
        fwd = mc["forward_isedge"]
        print(f"    -> median DD={fwd['median_dd']:.1f}%  p90 DD={fwd['p90_dd']:.1f}%  "
              f"ruin={fwd['p_blowup']:.1f}%  med terminal ${fwd['median_terminal']:,.0f}")
        rows_out.append({"tag": tag, "floor": floor, "retain_pct": retain,
                         "oos_dpt": s0["dollar_per_trade"], "oos_ER": s0["E_R"],
                         "oos_t": s0["t"], "oos_win": s0["win_pct"], "oos_n": s0["n"],
                         "surv_2x_pct": surv2x, "surv_gap_pct": survg,
                         "fwd_median_dd": round(fwd["median_dd"], 1),
                         "fwd_p90_dd": round(fwd["p90_dd"], 1),
                         "fwd_ruin": round(fwd["p_blowup"], 2),
                         "fwd_median_terminal": round(fwd["median_terminal"], 0)})

    # Verdict
    df  = pd.DataFrame(rows_out)
    nul = df[df["floor"] == 0.0].iloc[0]
    print("\n" + "=" * 96)
    print("VERDICT — adopt a floor ONLY if vs no-filter: $/t higher AND p90 DD not worse "
          "AND ruin not worse AND terminal not worse")
    print(f"  no_filter (incumbent): $/t={nul['oos_dpt']:+.4f}  p90 DD={nul['fwd_p90_dd']}%  "
          f"ruin={nul['fwd_ruin']}%  terminal ${nul['fwd_median_terminal']:,.0f}  n={int(nul['oos_n'])}")
    winner, best_dpt = None, float(nul["oos_dpt"])
    for _, r in df[df["floor"] > 0].iterrows():
        better_dpt  = float(r["oos_dpt"]) > float(nul["oos_dpt"])
        dd_ok       = float(r["fwd_p90_dd"]) <= float(nul["fwd_p90_dd"]) + 0.5
        ruin_ok     = float(r["fwd_ruin"]) <= float(nul["fwd_ruin"]) + 0.1
        term_ok     = float(r["fwd_median_terminal"]) >= float(nul["fwd_median_terminal"])
        adopt = better_dpt and dd_ok and ruin_ok and term_ok
        print(f"  {r['tag']:>11}: $/t={float(r['oos_dpt']):+.4f}({'>' if better_dpt else '<='}null)  "
              f"p90 DD={r['fwd_p90_dd']}%({'ok' if dd_ok else 'WORSE'})  "
              f"ruin={r['fwd_ruin']}%({'ok' if ruin_ok else 'WORSE'})  "
              f"term ${r['fwd_median_terminal']:,.0f}({'ok' if term_ok else 'WORSE'})  "
              f"retain={r['retain_pct']}%  -> {'ADOPT' if adopt else 'no'}")
        if adopt and float(r["oos_dpt"]) > best_dpt:
            winner, best_dpt = r["tag"], float(r["oos_dpt"])
    print("  " + "-" * 92)
    verdict = f"ADOPT {winner}" if winner else "KEEP no_filter (filter FALSIFIED — edge robust across width)"
    print(f"  >>> {verdict}")
    print("=" * 96)

    df.to_csv(_OUT / "stage2_floor_sweep.csv", index=False, encoding="utf-8")
    (_OUT / "stage2_summary.json").write_text(json.dumps(
        {"model": "ORB-001", "task": 17, "stage": "2_floor_sweep_oos_mc",
         "config": "09:00/N5 trail_1R ModeA_5pct", "is_control_ok": ok,
         "floors": rows_out, "winner": winner, "verdict": verdict}, indent=2, default=str),
        encoding="utf-8")
    print(f"Outputs -> {_OUT}")


if __name__ == "__main__":
    main()
