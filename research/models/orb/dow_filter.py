"""
ORB-001 task 18 — day-of-week / seasonality filter.

Third filter hypothesis (after trend_regime_gate #8 and range_width_floor #12, both
FALSIFIED). Does any WEEKDAY (or season) bleed money on the live config (09:00/N5 ·
trail_1R · Mode-A 5% cap)? Unlike the width floor — which dropped POSITIVE-EV trades
and so cost terminal — removing a genuinely loss-making weekday should LIFT terminal
(fewer losers = better compounding). So a toxic day, if real, can clear the bar.

Pre-committed screen (before any MC): a weekday is a DROP candidate only if its
$/trade is NEGATIVE in BOTH IS and OOS (replicates out of sample). Seasonality (month)
is profiled too but treated as exploratory only — too few years per bucket to act on.

If candidate(s) found: drop them -> OOS $/t + survival MC vs no-filter, same adopt
rule as task 17 ($/t higher AND p90 DD / ruin / terminal not worse). Else FALSIFIED.

    python research/models/orb/dow_filter.py

Outputs -> research/outputs/orb/dow_filter/
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
from research.models.orb.orb_core import IS_END
from research.code.session_cache import session_files
from research.models.orb.trail_oos import run_trail_mc
from research.models.orb.range_filter_stage2 import _scan, _stats, IS_REF_ER, OOS_MONTHS

WD_NAME = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
_OUT = REPO / "research" / "outputs" / "orb" / "dow_filter"


def _wd(rows):
    for r in rows:
        r["wd"] = pd.Timestamp(r["date"]).weekday()
        r["mo"] = pd.Timestamp(r["date"]).month
    return rows


def _profile(rows, key, names):
    """Per-bucket stats table; returns dict bucket->stats."""
    out = {}
    keys = sorted({r[key] for r in rows})
    for k in keys:
        sub = [r for r in rows if r[key] == k]
        out[k] = _stats(sub)
    return out


def main():
    _OUT.mkdir(parents=True, exist_ok=True)
    files     = session_files(None)
    files_oos = session_files(OOS_MONTHS)
    if not files:
        sys.exit("No session-cache files. Build first: python research/code/session_cache.py build")

    print("=" * 92)
    print("ORB-001 TASK 18 — day-of-week / seasonality filter (live 09:00/N5 · trail_1R)")
    print("=" * 92)

    is_all  = _wd(_scan(files,     oos=False, desc="IS slip0"))
    oos_all = _wd(_scan(files_oos, oos=True,  desc="OOS slip0"))

    # [0] IS control repro
    is_ref = _stats(is_all)
    ok = abs(is_ref["E_R"] - IS_REF_ER) < 0.02
    print(f"\n[0] IS control (no-filter): E[R]={is_ref['E_R']:+.4f} vs ref {IS_REF_ER:+.4f} "
          f"-> {'OK' if ok else '*** MISMATCH'}  n={is_ref['n']}")
    if not ok:
        sys.exit("*** IS control repro failed — halting.")

    # [1] Weekday profile (IS + OOS) — the committed axis
    is_wd, oos_wd = _profile(is_all, "wd", WD_NAME), _profile(oos_all, "wd", WD_NAME)
    print("\n[weekday]  $/trade by day  (DROP candidate = negative in BOTH IS and OOS):")
    print(f"  {'day':>4} | {'IS n':>5} {'IS $/t':>8} {'IS E[R]':>8} | {'OOS n':>5} {'OOS $/t':>8} {'flag':>5}")
    candidates = []
    wd_rows = []
    for k in sorted(is_wd):
        i, o = is_wd[k], oos_wd.get(k)
        odpt = o["dollar_per_trade"] if o else None
        toxic = (i["dollar_per_trade"] < 0) and (odpt is not None and odpt < 0)
        flag = "DROP?" if toxic else ""
        if toxic:
            candidates.append(k)
        print(f"  {WD_NAME[k]:>4} | {i['n']:>5} {i['dollar_per_trade']:>+8.4f} {i['E_R']:>+8.4f} | "
              f"{(o['n'] if o else 0):>5} {(odpt if odpt is not None else float('nan')):>+8.4f} {flag:>5}")
        wd_rows.append({"weekday": WD_NAME[k], "is_n": i["n"], "is_dpt": i["dollar_per_trade"],
                        "is_ER": i["E_R"], "oos_n": (o["n"] if o else 0),
                        "oos_dpt": odpt, "drop_candidate": toxic})

    # [2] Seasonality (month) — exploratory only
    is_mo = _profile(is_all, "mo", None)
    print("\n[month] IS $/trade by month (EXPLORATORY — too few years/bucket to act on):")
    print("  " + "  ".join(f"{m:02d}:{is_mo[m]['dollar_per_trade']:+.2f}" for m in sorted(is_mo)))

    # [3] Verdict
    print("\n" + "=" * 92)
    no_filter_oos = _stats(oos_all)
    mc0 = run_trail_mc(oos_all, is_trail_R=[r["R"] for r in is_all])
    f0 = mc0["forward_isedge"]
    print(f"  no_filter (incumbent): OOS $/t={no_filter_oos['dollar_per_trade']:+.4f}  "
          f"p90 DD={f0['p90_dd']:.1f}%  ruin={f0['p_blowup']:.1f}%  terminal ${f0['median_terminal']:,.0f}")

    verdict, winner, drop_rows = None, None, []
    if not candidates:
        verdict = "KEEP no_filter (DoW filter FALSIFIED — no weekday toxic in both IS and OOS)"
        print(f"  no DROP candidates — every weekday positive $/t in IS or OOS.")
    else:
        days = ",".join(WD_NAME[k] for k in candidates)
        print(f"  DROP candidate(s): {days} — testing removal vs no-filter ...")
        keep_is  = [r for r in is_all  if r["wd"] not in candidates]
        keep_oos = [r for r in oos_all if r["wd"] not in candidates]
        s = _stats(keep_oos)
        mc = run_trail_mc(keep_oos, is_trail_R=[r["R"] for r in keep_is])
        f = mc["forward_isedge"]
        retain = round(len(keep_oos) / len(oos_all) * 100, 1)
        better = s["dollar_per_trade"] > no_filter_oos["dollar_per_trade"]
        dd_ok  = f["p90_dd"]      <= f0["p90_dd"] + 0.5
        ruin_ok= f["p_blowup"]    <= f0["p_blowup"] + 0.1
        term_ok= f["median_terminal"] >= f0["median_terminal"]
        adopt  = better and dd_ok and ruin_ok and term_ok
        print(f"  drop_{days}: OOS $/t={s['dollar_per_trade']:+.4f}({'>' if better else '<='}null)  "
              f"p90 DD={f['p90_dd']:.1f}%({'ok' if dd_ok else 'WORSE'})  "
              f"ruin={f['p_blowup']:.1f}%({'ok' if ruin_ok else 'WORSE'})  "
              f"term ${f['median_terminal']:,.0f}({'ok' if term_ok else 'WORSE'})  retain={retain}%  "
              f"-> {'ADOPT' if adopt else 'no'}")
        winner = f"drop_{days}" if adopt else None
        verdict = f"ADOPT {winner}" if adopt else f"KEEP no_filter (drop {days} fails bar — DoW filter FALSIFIED)"
        drop_rows = [{"drop_days": days, "retain_pct": retain, "oos_dpt": s["dollar_per_trade"],
                      "fwd_p90_dd": round(f["p90_dd"], 1), "fwd_ruin": round(f["p_blowup"], 2),
                      "fwd_median_terminal": round(f["median_terminal"], 0), "adopt": adopt}]
    print(f"  >>> {verdict}")
    print("=" * 92)

    pd.DataFrame(wd_rows).to_csv(_OUT / "dow_weekday.csv", index=False, encoding="utf-8")
    (_OUT / "dow_summary.json").write_text(json.dumps(
        {"model": "ORB-001", "task": 18, "config": "09:00/N5 trail_1R ModeA_5pct",
         "is_control_ok": ok, "weekday": wd_rows,
         "month_is_dpt": {int(m): is_mo[m]["dollar_per_trade"] for m in is_mo},
         "no_filter": {"oos_dpt": no_filter_oos["dollar_per_trade"], "fwd_p90_dd": round(f0["p90_dd"], 1),
                       "fwd_ruin": round(f0["p_blowup"], 2), "fwd_median_terminal": round(f0["median_terminal"], 0)},
         "drop_test": drop_rows, "verdict": verdict, "winner": winner}, indent=2, default=str),
        encoding="utf-8")
    print(f"Outputs -> {_OUT}")


if __name__ == "__main__":
    main()
