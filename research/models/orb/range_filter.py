"""
ORB-001 task 17 — range-width edge filter (productionise + OOS).  STAGE 1: IS profile.

The `filter` component slot already has one FALSIFIED entry (trend_regime_gate,
strategy_log #8) — the edge is regime-agnostic, so "no filter" is the incumbent to
beat. This script tests a SECOND filter hypothesis: does the opening-range WIDTH
predict per-dollar profitability on the LIVE config (09:00/N5 · trail_1R · Mode-A
5% cap)?

KEY STRUCTURAL FACT (trail_oos._walk_modea, equity_sim constants):
    At min-lot, CONTRACT_OZ*MIN_LOT = 100*0.01 = 1.0, so dollar risk == range_w.
    The 5% cap SKIPS any trade with range_w > 5% of current equity. At the $50
    start that is range_w > $2.50 — so the live strategy ALREADY has a dynamic
    UPPER-width filter. The new territory for an edge filter is therefore:
      (a) the NARROW end (cap never removes narrow ranges — are they noise?), and
      (b) whether a STATIC width band beats the dynamic cap on $/t + survival.

STAGE 1 (this run) is IS-only profiling — NO rule is committed, NO DB write:
    1. IS control: unfiltered 09:00/N5 trail_1R E[R] / $/t / win  (the reference).
    2. range_w distribution sanity block (+ where the $2.50 start-cap bites).
    3. Width sweep: equal-N deciles + pre-committed fixed-$ buckets, each with
       n · win% · E[R] · SE · t · $/trade.
We READ the profile, THEN pre-commit a rule shape (cap / floor / band) in stage 2.

    python research/models/orb/range_filter.py

Outputs -> research/outputs/orb/range_filter/
    range_filter_is_deciles.csv  range_filter_is_buckets.csv  range_filter_is_summary.json
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np
import pandas as pd
from tqdm import tqdm

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
from research.models.orb.orb_core import IS_END
from research.code.session_cache import session_files
from research.models.orb.equity_sim import CONTRACT_OZ, MIN_LOT

# Live config (strategy_log get_live_config 2026-06-09).
ANCHOR_HOUR, N_MIN = 9.0, 5
SPREAD   = 2.0 * 0.10
IS_CUT   = np.datetime64(IS_END)
EOD_HOUR = 21
START    = 50.0
CAP_PCT  = 5.0
NS_H = 3_600_000_000_000
NS_M =    60_000_000_000
NS_D = 86_400_000_000_000
# range_w that breaches the 5% cap at the STARTING balance ($50): rw > 5% * 50 = $2.50.
START_CAP_RW = CAP_PCT / 100.0 * START / (CONTRACT_OZ * MIN_LOT)

# Pre-committed fixed-$ buckets (round numbers, chosen BEFORE seeing the profile;
# the $2.50 start-cap boundary is made explicit).
FIXED_EDGES = [0.0, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 8.0, np.inf]

_OUT = REPO / "research" / "outputs" / "orb" / "range_filter"


# --- trail_1R per-day sim — verbatim from anchor_dd._simulate_day -------------
def _simulate_day(ts, mid, day0, anchor_hour=ANCHOR_HOUR, n_minutes=N_MIN):
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
    return {"range_w": rw, "R": R}


def _scan(files, oos=False, desc="IS"):
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
            r = _simulate_day(ts_all[mk], mid_all[mk], int(d) * NS_D)
            if r is not None:
                rows.append(r)
    return rows


def _bin_stats(R, rw, mask, label):
    R, rw = R[mask], rw[mask]
    n = len(R)
    if n == 0:
        return {"bin": label, "n": 0, "win_pct": None, "E_R": None,
                "SE_R": None, "t": None, "dollar_per_trade": None,
                "above_start_cap": None}
    mu = float(R.mean()); sd = float(R.std(ddof=1)) if n > 1 else 0.0
    se = sd / np.sqrt(n) if n > 1 else float("nan")
    t  = mu / se if se and se == se and se > 0 else float("nan")
    return {"bin": label, "n": n,
            "win_pct": round(float((R > 0).mean()) * 100, 1),
            "E_R": round(mu, 4), "SE_R": round(se, 4),
            "t": round(t, 2) if t == t else None,
            "dollar_per_trade": round(float((R * rw).mean()), 4),
            "rw_lo": round(float(rw.min()), 2), "rw_hi": round(float(rw.max()), 2)}


def main():
    _OUT.mkdir(parents=True, exist_ok=True)
    files = session_files(None)
    if not files:
        sys.exit("No session-cache files. Build first: python research/code/session_cache.py build")

    print("=" * 96)
    print("ORB-001 TASK 17 STAGE 1 — range-width IS profile (live config 09:00/N5 · trail_1R)")
    print(f"  session-cache files: {len(files)}   |  IS = ts < {IS_END.date()}")
    print(f"  $50 start 5% cap auto-skips range_w > ${START_CAP_RW:.2f} (dynamic; rises with equity)")
    print("=" * 96)

    rows = _scan(files, oos=False, desc="IS 09:00/N5")
    R  = np.array([r["R"] for r in rows], dtype=float)
    rw = np.array([r["range_w"] for r in rows], dtype=float)
    n  = len(R)

    # --- Sanity block (protocol rule 5) -------------------------------------
    qs = np.percentile(rw, [0, 10, 25, 50, 75, 90, 99, 100])
    print(f"\n[sanity] IS trades n={n}")
    print(f"  range_w $  min={qs[0]:.2f}  p10={qs[1]:.2f}  p25={qs[2]:.2f}  "
          f"med={qs[3]:.2f}  p75={qs[4]:.2f}  p90={qs[5]:.2f}  p99={qs[6]:.2f}  max={qs[7]:.2f}")
    above = float((rw > START_CAP_RW).mean()) * 100
    print(f"  share of IS trades with range_w > ${START_CAP_RW:.2f} (skipped at $50 start): {above:.1f}%")

    # --- Unfiltered reference ----------------------------------------------
    ref = _bin_stats(R, rw, np.ones(n, dtype=bool), "ALL (unfiltered)")
    print(f"\n[reference] UNFILTERED 09:00/N5 trail_1R:")
    print(f"  E[R]={ref['E_R']:+.4f}  SE={ref['SE_R']:.4f}  t={ref['t']:+.2f}  "
          f"win={ref['win_pct']:.1f}%  $/trade={ref['dollar_per_trade']:+.4f}  n={n}")
    print("  ^ this E[R] is the STAGE-2 IS control-repro reference (halt on >0.02 drift)")

    # --- Equal-N deciles (pre-committed: deciles, not eyeballed) ------------
    print("\n[deciles] equal-N range_w deciles  (edge profile; $/t is the ranking metric):")
    edges = np.percentile(rw, np.arange(0, 101, 10))
    edges[0] -= 1e-9; edges[-1] += 1e-9
    dec_rows = []
    print(f"  {'decile':>6} {'rw range $':>14} {'n':>5} {'win%':>6} {'E[R]':>8} {'t':>6} {'$/trade':>9}")
    for k in range(10):
        m = (rw > edges[k]) & (rw <= edges[k + 1])
        s = _bin_stats(R, rw, m, f"D{k+1}")
        dec_rows.append({**s, "edge_lo": round(float(edges[k]), 2), "edge_hi": round(float(edges[k+1]), 2)})
        cap_flag = " *cap" if edges[k] >= START_CAP_RW else ""
        tstr = f"{s['t']:>+6.2f}" if s['t'] is not None else "   n/a"
        print(f"  {s['bin']:>6} {s['rw_lo']:>6.2f}-{s['rw_hi']:<6.2f} {s['n']:>5} "
              f"{s['win_pct']:>6.1f} {s['E_R']:>+8.4f} {tstr} {s['dollar_per_trade']:>+9.4f}{cap_flag}")

    # --- Fixed-$ buckets (pre-committed, MQL5-portable thresholds) -----------
    print("\n[buckets] pre-committed fixed-$ width buckets ($2.50 = start-cap boundary):")
    buck_rows = []
    print(f"  {'bucket $':>12} {'n':>5} {'win%':>6} {'E[R]':>8} {'t':>6} {'$/trade':>9}")
    for k in range(len(FIXED_EDGES) - 1):
        lo, hi = FIXED_EDGES[k], FIXED_EDGES[k + 1]
        m = (rw > lo) & (rw <= hi)
        lbl = f"{lo:.1f}-{'inf' if np.isinf(hi) else f'{hi:.1f}'}"
        s = _bin_stats(R, rw, m, lbl)
        buck_rows.append({**s, "lo": lo, "hi": (None if np.isinf(hi) else hi)})
        if s["n"] == 0:
            print(f"  {lbl:>12} {0:>5}  (empty)"); continue
        cap_flag = " *cap" if lo >= START_CAP_RW else ""
        tstr = f"{s['t']:>+6.2f}" if s['t'] is not None else "   n/a"
        print(f"  {lbl:>12} {s['n']:>5} {s['win_pct']:>6.1f} {s['E_R']:>+8.4f} "
              f"{tstr} {s['dollar_per_trade']:>+9.4f}{cap_flag}")

    print("\n  ( *cap = bucket lies entirely above the $2.50 start-cap; "
          "already auto-skipped at low equity )")
    print("=" * 96)
    print("STAGE 1 done — read the profile, THEN pre-commit the rule shape in stage 2.")
    print("No DB write, no rule committed yet (discuss-before-build).")

    # --- structured utf-8 outputs (task 7 spirit) ---------------------------
    pd.DataFrame(dec_rows).to_csv(_OUT / "range_filter_is_deciles.csv", index=False, encoding="utf-8")
    pd.DataFrame(buck_rows).to_csv(_OUT / "range_filter_is_buckets.csv", index=False, encoding="utf-8")
    (_OUT / "range_filter_is_summary.json").write_text(json.dumps({
        "model": "ORB-001", "task": 17, "stage": "1_is_profile",
        "config": {"anchor": "09:00/N5", "exit": "trail_1R", "sizing": "ModeA_minlot_5pct"},
        "is_sealed": str(IS_END.date()), "n_is_trades": n,
        "start_cap_rw": round(START_CAP_RW, 2), "share_above_start_cap_pct": round(above, 1),
        "unfiltered_reference": ref, "deciles": dec_rows, "buckets": buck_rows,
    }, indent=2, default=str), encoding="utf-8")
    print(f"Outputs -> {_OUT}")


if __name__ == "__main__":
    main()
