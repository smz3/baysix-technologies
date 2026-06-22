"""
ORB-001 task 21 — fixedpip_2p0 stop vs trail_1R (exit-component contest).

STALENESS FIX: task 14 found fixedpip_2p0 ($2 stop, 3:1 target) +0.496 $/t IS vs the
THEN-frozen range_w stop +0.324 (+53%). But that frozen stop (fixed_3R/range_w, 08:00
anchor) was SUPERSEDED by trail_1R (strategy_log #9) at 09:00/N5. So fixedpip must be
re-baselined against the LIVE champion trail_1R (IS $/t +0.99, OOS $/t +7.62, p90 DD
20.1%, ruin 0%). This script runs both exits head-to-head at the live 09:00/N5 anchor.

fixedpip_2p0 = fixed $2.00 stop (1R=$2) + 3:1 target ($6) + immediate entry + EOD flat
               -> risks $2.00/trade = 4% of $50 (vs trail's range_w ~$0.64 ~1.3%).
trail_1R     = range_w trailing stop (the live exit).

Tests: (1) IS control repro (trail +1.5472 E[R]); (2) OOS $/t + fill gauntlet;
(3) Mode-A survival/DD MC at $50 (fixedpip's 4%/trade risk vs trail's ~1.3%);
(4) IS regime split 200d (is fixedpip's edge trend-beta? OOS 2024-26 is all-uptrend
    so the regime evidence MUST come from the IS cross-section -- regime_gate.py:117).

ADOPT fixedpip ONLY if vs trail_1R: OOS $/t higher AND p90 DD/ruin not worse AND edge
holds in BOTH trend and range IS regimes. Else KEEP trail_1R, log exit REJECTED.

    python research/models/orb/fixedstop_exit.py
Outputs -> research/outputs/orb/fixedstop/
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
from research.models.orb.orb001.regime_gate import compute_regime
from research.code.arctic_io import daily_bars
from research.models.orb.orb001.range_filter_stage2 import IS_REF_ER, OOS_MONTHS

ANCHOR_HOUR, N_MIN = 9.0, 5
SPREAD   = 2.0 * 0.10
IS_CUT   = np.datetime64(IS_END)
EOD_HOUR = 21
RR       = 3.0          # fixedpip reward:risk (3:1, as task 14)
FIX_D    = 2.0          # fixed $2.00 stop distance
NS_H = 3_600_000_000_000
NS_M =    60_000_000_000
NS_D = 86_400_000_000_000
_OUT = REPO / "research" / "outputs" / "orb" / "fixedstop"


def _simulate_day(ts, mid, day0, slip_extra=0.0, gap_fill=False):
    """Shared 09:00/N5 immediate-breakout entry, then BOTH exits on the same trade."""
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
    g = pdir * (emid - e)                       # signed favourable excursion

    # --- trail_1R (range_w trailing stop), R in range_w units ---
    ef_trail = emid - pdir * half * (1.0 + slip_extra)
    ef_adj   = pdir * (ef_trail - e) / rw
    peak_g   = np.maximum.accumulate(g)
    rel      = g <= peak_g - rw + half
    i_x      = int(np.argmax(rel)) if rel.any() else None
    if i_x is not None:
        i_fill  = min(i_x + 1, len(ef_adj) - 1) if gap_fill else i_x
        R_trail = float(ef_adj[i_fill])
    else:
        R_trail = float(ef_adj[-1])

    # --- fixedpip_2p0 ($2 stop / $6 target / EOD), R in D units [-1, +3] ---
    half_eff = half * (1.0 + slip_extra)
    stop_lvl = e - pdir * FIX_D
    tgt_lvl  = e + pdir * RR * FIX_D
    if pdir > 0:
        hit_t = emid >= tgt_lvl + half
        hit_s = emid <= stop_lvl + half_eff
    else:
        hit_t = emid <= tgt_lvl - half
        hit_s = emid >= stop_lvl - half_eff
    i_t = int(np.argmax(hit_t)) if hit_t.any() else None
    i_s = int(np.argmax(hit_s)) if hit_s.any() else None
    if i_t is not None and (i_s is None or i_t <= i_s):
        R_fix, fix_out = RR, "target"
    elif i_s is not None:
        R_fix, fix_out = -1.0, "stop"
    else:
        exit_fill = emid[-1] - pdir * half_eff
        R_fix, fix_out = float(pdir * (exit_fill - e) / FIX_D), "eod"

    return {"range_w": rw, "entry_px": e, "R_trail": R_trail,
            "R_fix": float(R_fix), "fix_outcome": fix_out}


def _scan(files, oos, slip_extra=0.0, gap_fill=False, desc=""):
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
            r = _simulate_day(ts_all[mk], mid_all[mk], int(d) * NS_D, slip_extra, gap_fill)
            if r is not None:
                r["date"] = pd.Timestamp(int(d) * NS_D).date()
                rows.append(r)
    return rows


def _dpt(rows, which):
    R  = np.array([r[f"R_{which}"] for r in rows], float)
    rw = np.array([(r["range_w"] if which == "trail" else FIX_D) for r in rows], float)
    n  = len(R); mu = float(R.mean()); sd = float(R.std(ddof=1))
    se = sd / np.sqrt(n); t = mu / se if sd > 0 else float("nan")
    return {"n": n, "E_R": round(mu, 4), "t": round(t, 2),
            "win_pct": round(float((R > 0).mean()) * 100, 1),
            "dollar_per_trade": round(float((R * rw).mean()), 4)}


def _mc_rows(rows, which):
    """Reshape for run_trail_mc: range_w carries the risk-unit (range_w for trail, $2 for fix)."""
    return [{"date": r["date"], "R": r[f"R_{which}"], "entry_px": r["entry_px"],
             "range_w": (r["range_w"] if which == "trail" else FIX_D)} for r in rows]


def _regime_split(is_rows):
    """IS-only trend/range split (200d SMA). OOS is all-uptrend (degenerate)."""
    close = daily_bars(columns=["close"])["close"].copy()
    close.index = pd.to_datetime(close.index)
    reg = compute_regime(close, 200)
    reg_ff = reg.reindex(reg.index.union(pd.to_datetime([r["date"] for r in is_rows]))).ffill()
    out = {}
    for r in is_rows:
        r["regime"] = reg_ff.get(pd.Timestamp(r["date"]), "flat")
    for rg in ("up", "flat", "down"):
        sub = [r for r in is_rows if r["regime"] == rg]
        if not sub:
            out[rg] = {"n": 0}; continue
        out[rg] = {"n": len(sub),
                   "trail_dpt": round(float(np.mean([r["R_trail"] * r["range_w"] for r in sub])), 4),
                   "fix_dpt":   round(float(np.mean([r["R_fix"]   * FIX_D       for r in sub])), 4),
                   "trail_ER":  round(float(np.mean([r["R_trail"] for r in sub])), 4),
                   "fix_ER":    round(float(np.mean([r["R_fix"]   for r in sub])), 4)}
    return out


def main():
    _OUT.mkdir(parents=True, exist_ok=True)
    files, files_oos = session_files(None), session_files(OOS_MONTHS)
    if not files:
        sys.exit("No session-cache files. Build first.")

    print("=" * 96)
    print("ORB-001 TASK 21 — fixedpip_2p0 ($2 stop/$6 tgt) vs trail_1R @ 09:00/N5")
    print("=" * 96)
    is_all   = _scan(files,     oos=False, desc="IS")
    oos_all  = _scan(files_oos, oos=True,  desc="OOS")
    oos_2x   = _scan(files_oos, oos=True, slip_extra=2.0, desc="OOS slip2x")
    oos_gap  = _scan(files_oos, oos=True, gap_fill=True,  desc="OOS gap")

    # [0] IS control repro (trail)
    is_tr = _dpt(is_all, "trail"); is_fx = _dpt(is_all, "fix")
    ok = abs(is_tr["E_R"] - IS_REF_ER) < 0.02
    print(f"\n[0] IS control trail E[R]={is_tr['E_R']:+.4f} vs ref {IS_REF_ER:+.4f} -> {'OK' if ok else '*** MISMATCH'}")
    if not ok:
        sys.exit("*** IS control repro failed — halting.")
    print(f"    IS  trail : $/t={is_tr['dollar_per_trade']:+.4f}  E[R]={is_tr['E_R']:+.4f}  win={is_tr['win_pct']:.1f}%  n={is_tr['n']}")
    print(f"    IS  fixed : $/t={is_fx['dollar_per_trade']:+.4f}  E[R]={is_fx['E_R']:+.4f}  win={is_fx['win_pct']:.1f}%  n={is_fx['n']}")

    # [1] OOS + fill gauntlet
    print("\n[1] OOS $/trade + fill gauntlet:")
    res = {}
    for which in ("trail", "fix"):
        s0 = _dpt(oos_all, which); s2 = _dpt(oos_2x, which); sg = _dpt(oos_gap, which)
        surv2x = round(s2["dollar_per_trade"]/s0["dollar_per_trade"]*100, 0) if s0["dollar_per_trade"] else float("nan")
        survg  = round(sg["dollar_per_trade"]/s0["dollar_per_trade"]*100, 0) if s0["dollar_per_trade"] else float("nan")
        print(f"    {which:>5}: OOS $/t={s0['dollar_per_trade']:+.4f}  E[R]={s0['E_R']:+.4f}  t={s0['t']:+.2f}  "
              f"win={s0['win_pct']:.1f}%  n={s0['n']}  | slip2x {surv2x:.0f}%  gap {survg:.0f}%")
        res[which] = {"oos": s0, "surv2x": surv2x, "survg": survg}

    # [2] survival MC
    print("\n[2] Mode-A survival/DD MC (forward_isedge central):")
    for which in ("trail", "fix"):
        mc = run_trail_mc(_mc_rows(oos_all, which), is_trail_R=[r[f"R_{which}"] for r in is_all])
        f = mc["forward_isedge"]
        print(f"    {which:>5}: median DD={f['median_dd']:.1f}%  p90 DD={f['p90_dd']:.1f}%  "
              f"ruin={f['p_blowup']:.1f}%  med terminal ${f['median_terminal']:,.0f}")
        res[which]["mc"] = {"median_dd": round(f["median_dd"],1), "p90_dd": round(f["p90_dd"],1),
                            "ruin": round(f["p_blowup"],2), "median_terminal": round(f["median_terminal"],0)}

    # [3] IS regime split
    print("\n[3] IS regime split (200d) — is fixedpip trend-beta?")
    rs = _regime_split(is_all)
    print(f"    {'regime':>5} {'n':>5} {'trail $/t':>10} {'fix $/t':>9}")
    for rg in ("up", "flat", "down"):
        d = rs[rg]
        if d["n"] == 0:
            print(f"    {rg:>5} {0:>5}  (none)"); continue
        print(f"    {rg:>5} {d['n']:>5} {d['trail_dpt']:>+10.4f} {d['fix_dpt']:>+9.4f}")

    # [4] Verdict
    tr, fx = res["trail"], res["fix"]
    better_dpt = fx["oos"]["dollar_per_trade"] > tr["oos"]["dollar_per_trade"]
    dd_ok      = fx["mc"]["p90_dd"] <= tr["mc"]["p90_dd"] + 0.5
    ruin_ok    = fx["mc"]["ruin"]   <= tr["mc"]["ruin"] + 0.1
    # trend-beta: fixedpip edge concentrates in up and dies/reverses outside it
    fix_up = rs["up"].get("fix_dpt", 0) if rs["up"]["n"] else 0
    fix_dn = rs["down"].get("fix_dpt", 0) if rs["down"]["n"] else None
    regime_ok = (fix_dn is not None and fix_dn > 0)   # holds outside uptrend
    adopt = better_dpt and dd_ok and ruin_ok and regime_ok
    print("\n" + "=" * 96)
    print("VERDICT — adopt fixedpip ONLY if vs trail_1R: $/t higher AND DD/ruin not worse AND holds in down-regime")
    print(f"  $/t: fix {fx['oos']['dollar_per_trade']:+.4f} vs trail {tr['oos']['dollar_per_trade']:+.4f} -> {'higher' if better_dpt else 'LOWER'}")
    print(f"  p90 DD: fix {fx['mc']['p90_dd']}% vs trail {tr['mc']['p90_dd']}% -> {'ok' if dd_ok else 'WORSE'}")
    print(f"  ruin: fix {fx['mc']['ruin']}% vs trail {tr['mc']['ruin']}% -> {'ok' if ruin_ok else 'WORSE'}")
    print(f"  IS down-regime fix $/t: {fix_dn} -> {'holds' if regime_ok else 'TREND-BETA (fails outside uptrend)'}")
    verdict = "ADOPT fixedpip_2p0" if adopt else "KEEP trail_1R (fixedpip_2p0 REJECTED)"
    print(f"  >>> {verdict}")
    print("=" * 96)

    summary = {"model": "ORB-001", "task": 21, "anchor": "09:00/N5",
               "is_control_ok": ok, "is_trail": is_tr, "is_fix": is_fx,
               "oos": {"trail": tr, "fix": fx}, "is_regime_200d": rs,
               "verdict": verdict, "adopt": adopt}
    (_OUT / "fixedstop_summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    pd.DataFrame([{"exit": k, **v["oos"], **v["mc"]} for k, v in res.items()]).to_csv(
        _OUT / "fixedstop_compare.csv", index=False, encoding="utf-8")
    print(f"Outputs -> {_OUT}")


if __name__ == "__main__":
    main()
