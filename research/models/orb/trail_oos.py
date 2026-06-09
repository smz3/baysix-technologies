"""
ORB-001 trail_1R OOS validation (backlog task 13).

IS trail_1R = +0.7910R (t=11.30). This runs OOS, stress-tests fill realism,
splits by regime, and re-runs the 50-dollar MC on the trail R-distribution.

    python research/models/orb/trail_oos.py

Outputs -> research/outputs/orb/trail_oos/
    trail_oos_main.csv  trail_oos_regime.csv  trail_oos_summary.json
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np
import pandas as pd
from tqdm import tqdm

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from research.models.orb.orb_core import _tick_files, IS_END, LONDON_ANCHOR_HOUR
from research.code.session_cache import session_files  # Layer A: read 07:00-22:00 session slice
from research.models.orb.equity_sim import MIN_LOT, CONTRACT_OZ, LEVERAGE
from research.models.orb.regime_gate import build_daily_close, compute_regime

OR_MIN       = 5
SPREAD       = 2.0 * 0.10
IS_END_TS    = IS_END
OOS_MONTHS   = [(y, m) for y in range(2024, 2027) for m in range(1, 13)
                if (y, m) >= (2024, 5)]
IS_BASE_REF  = 0.3114
IS_TRAIL_REF = 0.7910
OOS_BASE_REF = 0.8758
SLIP_SCENARIOS = [0.0, 0.5, 1.0, 2.0]
N_PATHS      = 1000
SEED         = 42
START        = 50.0
CAP_PCT      = 5.0
NS_H         = 3_600_000_000_000
NS_M         =    60_000_000_000
NS_D         = 86_400_000_000_000
_OUT         = REPO / "research" / "outputs" / "orb" / "trail_oos"

# ---------------------------------------------------------------------------
# Per-day simulation — verbatim from structures.py _exit_R (arm=trail_1R)
# ---------------------------------------------------------------------------

def _simulate_day(ts, mid, day0, slip_extra=0.0, gap_fill=False):
    """
    Simulate one day, return (base_trade, trail_trade) or (None, None).

    slip_extra: extra half-spread fractions on the trail exit fill ONLY.
      0.0 = structures.py verbatim (exit at bid/ask, continuous trail).
      k   = exit_fill uses (1+k)*half instead of half, modelling gap/slippage.
    base_3R resolves at clean level fills (+3R/-1R) so slippage is inapplicable.

    gap_fill: if True, book the trail exit at the NEXT observed tick after the
      trail level is breached (i_x+1), not at the trigger tick itself. Models the
      real-money case where a stop order is sent on observing the breach and fills
      at the next available price (latency + price gapping THROUGH the level).
      This is the task-12 fill-realism guard for the trail exit specifically.
    """
    half   = SPREAD * 0.5
    anchor = day0 + LONDON_ANCHOR_HOUR * NS_H
    or_end = anchor + OR_MIN * NS_M
    eod    = day0 + 21 * NS_H

    in_or = (ts >= anchor) & (ts < or_end)
    if not in_or.any():
        return None, None
    or_hi, or_lo = mid[in_or].max(), mid[in_or].min()
    rw = or_hi - or_lo
    if rw <= 0:
        return None, None

    post = (ts >= or_end) & (ts < eod)
    if not post.any():
        return None, None
    pmid = mid[post]

    up = pmid >= or_hi - half
    dn = pmid <= or_lo + half
    i_up = int(np.argmax(up)) if up.any() else None
    i_dn = int(np.argmax(dn)) if dn.any() else None
    if i_up is None and i_dn is None:
        return None, None
    if i_dn is None or (i_up is not None and i_up <= i_dn):
        pdir, e, i_b = 1.0, or_hi, i_up
    else:
        pdir, e, i_b = -1.0, or_lo, i_dn

    emid = pmid[i_b:]
    if len(emid) < 2:
        return None, None

    g = pdir * (emid - e)

    # structures.py line 155-156: bid for long, ask for short
    ef_base      = emid - pdir * half
    ef_adj_base  = pdir * (ef_base - e) / rw

    # trail fill: extra slippage factor
    ef_trail     = emid - pdir * half * (1.0 + slip_extra)
    ef_adj_trail = pdir * (ef_trail - e) / rw

    def first(mask):
        return int(np.argmax(mask)) if mask.any() else None

    # base_3R (structures.py verbatim lines 66-68, 104-109)
    i_stop = first(g <= -rw + half)
    i_tgt  = first(g >= 3 * rw + half)
    cands  = [(i, r) for i, r in [(i_tgt, 3.0), (i_stop, -1.0)] if i is not None]
    if not cands:
        R_base = float(ef_adj_base[-1])
    else:
        i_b2, r_b = min(cands, key=lambda c: c[0])
        R_base = r_b

    # trail_1R (structures.py verbatim lines 78-85)
    peak_g = np.maximum.accumulate(g)
    rel    = g <= peak_g - rw + half
    i_x    = first(rel)
    if i_x is not None:
        i_fill  = min(i_x + 1, len(ef_adj_trail) - 1) if gap_fill else i_x
        R_trail = float(ef_adj_trail[i_fill])
    else:
        R_trail = float(ef_adj_trail[-1])

    direction = "long" if pdir > 0 else "short"
    meta = {"direction": direction, "range_w": rw, "entry_px": e}
    return ({**meta, "R": R_base}, {**meta, "R": R_trail})


def _run_slice(files, is_slice, oos_slice, slip_extra=0.0, gap_fill=False, desc=""):
    is_cut = np.datetime64(IS_END_TS)
    base_rows, trail_rows = [], []
    for f in tqdm(files, desc=desc or "scan"):
        df = pd.read_parquet(f, columns=["ts_utc", "bid", "ask"])
        if is_slice:
            df = df[df["ts_utc"].values < is_cut]
        elif oos_slice:
            df = df[df["ts_utc"].values >= is_cut]
        if df.empty:
            continue
        ts_all  = df["ts_utc"].values.astype("datetime64[ns]").astype(np.int64)
        mid_all = (df["bid"].values + df["ask"].values) * 0.5
        day_key = ts_all // NS_D
        for d in np.unique(day_key):
            mk  = day_key == d
            b, t = _simulate_day(ts_all[mk], mid_all[mk], int(d) * NS_D, slip_extra, gap_fill)
            date = pd.Timestamp(int(d) * NS_D).date()
            if b is not None:
                b["date"] = date; base_rows.append(b)
            if t is not None:
                t["date"] = date; trail_rows.append(t)
    return base_rows, trail_rows


def _stats(rows, label):
    if not rows:
        return {"label": label, "n": 0}
    R  = np.array([r["R"] for r in rows], dtype=float)
    rw = np.array([r["range_w"] for r in rows], dtype=float)
    n  = len(R)
    mu = float(R.mean())
    sd = float(R.std(ddof=1))
    t  = mu / (sd / np.sqrt(n)) if sd > 0 and n > 1 else float("nan")
    return {"label": label, "n": n,
            "E_R":            round(mu, 4),
            "sd_R":           round(sd, 4),
            "SE_R":           round(sd / np.sqrt(n), 4),
            "t_stat":         round(t,  2),
            "win_rate":       round(float((R > 0).mean()), 4),
            "dollar_per_trade": round(float((R * rw).mean()), 4)}

# ---------------------------------------------------------------------------
# Regime split
# ---------------------------------------------------------------------------

def _add_regimes(rows):
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    close = build_daily_close()
    regime_df = pd.DataFrame(index=close.index)
    regime_df["regime_200d"] = compute_regime(close, 200)
    regime_df["regime_50d"]  = compute_regime(close, 50)
    for col in regime_df.columns:
        all_idx = regime_df[col].index.union(df["date"])
        reg_ff  = regime_df[col].reindex(all_idx).ffill()
        df[col] = reg_ff.reindex(df["date"]).values
    return df


def _regime_table(df, sma_col, period, arm):
    rows = []
    for regime in ("up", "flat", "down"):
        g = df[df[sma_col] == regime]
        n = len(g)
        if n == 0:
            rows.append({"period": period, "sma": sma_col, "regime": regime, "arm": arm,
                         "n": 0, "E_R": None, "SE_R": None,
                         "t_stat": None, "win_rate": None, "low_power": True})
            continue
        R  = g["R"].values
        mu = float(R.mean())
        sd = float(R.std(ddof=1)) if n > 1 else None
        se = sd / np.sqrt(n) if sd else None
        t  = mu / se if (se and se > 0) else None
        rows.append({"period": period, "sma": sma_col, "regime": regime, "arm": arm,
                     "n": n, "E_R": round(mu, 4),
                     "SE_R":     round(se, 4) if se else None,
                     "t_stat":   round(t,  2) if t  else None,
                     "win_rate": round(float((R > 0).mean()), 4),
                     "low_power": n < 30})
    return rows


# ---------------------------------------------------------------------------
# MC survival / DD
# ---------------------------------------------------------------------------

def _walk_modea(R, rw, entry, start, cap):
    eq = peak = start
    max_dd = 0.0; blew = False
    for i in range(len(R)):
        risk   = rw[i] * CONTRACT_OZ * MIN_LOT
        margin = entry[i] * CONTRACT_OZ * MIN_LOT / LEVERAGE
        if eq <= 0 or eq < margin:
            blew = True; break
        if cap is not None and (risk / eq) * 100.0 > cap:
            continue
        eq += R[i] * rw[i]
        if eq > peak: peak = eq
        dd = (peak - eq) / peak if peak > 0 else 0.0
        if dd > max_dd: max_dd = dd
        if eq <= 0: blew = True; break
    return eq, max_dd * 100.0, blew


def run_trail_mc(trail_rows, is_trail_R=None, n_paths=N_PATHS, seed=SEED, start=START, cap=CAP_PCT):
    """
    Bootstrap MC on the trail_1R R-distribution. Three scenarios bracket forward DD:

      realized      : OOS R as-is (E[R]=+1.73). ROSY upper bound — assumes the
                      inflated 2024-26 trend regime repeats. DD too low.
      derated_floor : OOS R additively shifted to E[R]=+0.79 (IS edge), but each
                      loss FLOORED at -1R (the trail's structural stop). Fixes the
                      old harsh derate that manufactured impossible <-1R losses.
      forward_isedge: *** CENTRAL ESTIMATE *** sizing (range_w/entry) bootstrapped
                      from OOS trades = current ~$3300 price regime / $50 sizing,
                      but each trade's R drawn from the IS trail distribution =
                      conservative +0.79 edge with its REAL shape and natural -1R
                      floor. No artificial shifting. Decouples 'what edge' (IS,
                      conservative) from 'what sizing' (OOS, current prices).
                      Caveat: R drawn independently of range_w (weak correlation).

    All preserve the Mode-A min-lot / 5%-cap walk.
    """
    df    = pd.DataFrame(trail_rows).sort_values("date").reset_index(drop=True)
    R0    = df["R"].to_numpy(dtype=float)
    rw0   = np.abs(df["range_w"].to_numpy(dtype=float))
    ent0  = df["entry_px"].to_numpy(dtype=float)
    n     = len(R0)
    realized_er = float(R0.mean())
    shift       = realized_er - IS_TRAIL_REF
    R0_derated  = np.maximum(R0 - shift, -1.0)        # FLOOR at structural -1R stop
    print(f"  n={n}  realized OOS E[R]={realized_er:+.4f}  IS ref={IS_TRAIL_REF:+.4f}  shift={shift:+.4f}")
    print(f"  derated_floor E[R]={float(R0_derated.mean()):+.4f} (floored at -1R)")
    if is_trail_R is not None:
        is_pool = np.asarray(is_trail_R, dtype=float)
        print(f"  IS trail pool: n={len(is_pool)}  E[R]={float(is_pool.mean()):+.4f}")
    print(f"  paths={n_paths}  cap={cap}%  start=${start:.0f}")

    child = np.random.SeedSequence(seed).spawn(n_paths)

    def _run(R_src, label, R_pool=None):
        terms, dds, blows = [], [], []
        for i in tqdm(range(n_paths), desc=label, leave=False):
            rng_i = np.random.default_rng(child[i])
            idx   = rng_i.choice(n, size=n, replace=True)
            R_used = rng_i.choice(R_pool, size=n, replace=True) if R_pool is not None else R_src[idx]
            term, dd, blew = _walk_modea(R_used, rw0[idx], ent0[idx], start, cap)
            terms.append(term); dds.append(dd); blows.append(blew)
        T, D, B = np.array(terms), np.array(dds), np.array(blows)
        return {"label":          label,
                "median_terminal": float(np.median(T)),
                "p5_terminal":     float(np.percentile(T, 5)),
                "p90_terminal":    float(np.percentile(T, 90)),
                "p95_terminal":    float(np.percentile(T, 95)),
                "median_dd":       float(np.median(D)),
                "p90_dd":          float(np.percentile(D, 90)),
                "p_blowup":        float(np.mean(B)) * 100.0}

    out = {"n_trades":         n,
           "realized_OOS_ER": realized_er,
           "IS_trail_ref_ER": IS_TRAIL_REF,
           "shift":           shift,
           "realized":        _run(R0,         "MC realized"),
           "derated_floor":   _run(R0_derated, "MC derated-floor")}
    if is_trail_R is not None:
        out["forward_isedge"] = _run(None, "MC forward IS-edge", R_pool=is_pool)
    return out


# ---------------------------------------------------------------------------
# Main + helpers
# ---------------------------------------------------------------------------

def _fmt(v, fmt):
    if v is None:
        return "  n/a"
    return format(v, fmt)


def _get(rows, arm, period, sma, regime):
    for r in rows:
        if (r["arm"] == arm and r["period"] == period
                and r["sma"] == sma and r["regime"] == regime):
            return r.get("E_R")
    return None


def main():
    _OUT.mkdir(parents=True, exist_ok=True)
    print("=" * 88)
    print("ORB-001 trail_1R OOS VALIDATION (task 13)")
    print("=" * 88)
    files_all = session_files(None)
    files_oos = session_files(OOS_MONTHS)
    if not files_all:
        sys.exit("No session-cache files. Build first: python research/code/session_cache.py build")

    # 1 IS control repro
    print("\n[1/5] IS control repro (base_3R + trail_1R) ...")
    is_base_rows, is_trail_rows = _run_slice(
        files_all, is_slice=True, oos_slice=False, slip_extra=0.0, desc="IS slip=0x")
    is_base_st  = _stats(is_base_rows,  "IS base_3R")
    is_trail_st = _stats(is_trail_rows, "IS trail_1R")
    er_b = is_base_st["E_R"];  t_b = is_base_st["t_stat"]
    w_b  = is_base_st["win_rate"]; n_b = is_base_st["n"]
    er_t = is_trail_st["E_R"]; t_t = is_trail_st["t_stat"]
    w_t  = is_trail_st["win_rate"]; n_t = is_trail_st["n"]
    print(f"  IS base_3R : E[R] {er_b:+.4f}  t {t_b:+.2f}  win {w_b:.1%}  n={n_b}")
    print(f"  IS trail_1R: E[R] {er_t:+.4f}  t {t_t:+.2f}  win {w_t:.1%}  n={n_t}")
    base_ok  = abs(er_b - IS_BASE_REF)  < 0.01
    trail_ok = abs(er_t - IS_TRAIL_REF) < 0.02
    lbl_b = "OK" if base_ok  else "*** MISMATCH"
    lbl_t = "OK" if trail_ok else "*** MISMATCH"
    print(f"  base_3R  repro vs {IS_BASE_REF:+.4f}: {lbl_b}")
    print(f"  trail_1R repro vs {IS_TRAIL_REF:+.4f}: {lbl_t}")
    if not base_ok or not trail_ok:
        import sys; sys.exit(1)

    # 2 OOS controls
    print("\n[2/5] OOS base_3R + OOS trail_1R (slip=0) ...")
    oos_base_rows, oos_trail_rows = _run_slice(
        files_oos, is_slice=False, oos_slice=True, slip_extra=0.0, desc="OOS slip=0x")
    oos_base_st  = _stats(oos_base_rows,  "OOS base_3R")
    oos_trail_st = _stats(oos_trail_rows, "OOS trail_1R slip=0x")
    er_ob = oos_base_st["E_R"]; t_ob = oos_base_st["t_stat"]
    w_ob  = oos_base_st["win_rate"]; n_ob = oos_base_st["n"]
    print(f"  OOS base_3R: E[R] {er_ob:+.4f}  t {t_ob:+.2f}  win {w_ob:.1%}  n={n_ob}")
    oos_ok = abs(er_ob - OOS_BASE_REF) < 0.02
    lbl_o  = "OK" if oos_ok else "*** MISMATCH"
    print(f"  OOS base repro vs {OOS_BASE_REF:+.4f}: {lbl_o}")
    if not oos_ok:
        import sys; sys.exit(1)
    er_ot = oos_trail_st["E_R"]; t_ot = oos_trail_st["t_stat"]
    w_ot  = oos_trail_st["win_rate"]; n_ot = oos_trail_st["n"]
    dp_ot = oos_trail_st["dollar_per_trade"]
    print(f"  OOS trail_1R: E[R] {er_ot:+.4f}  t {t_ot:+.2f}  win {w_ot:.1%}  n={n_ot}  dp {dp_ot:+.4f}")
    print(f"  vs IS trail ref {IS_TRAIL_REF:+.4f}  vs OOS base {OOS_BASE_REF:+.4f}")

    # 3 Fill stress
    print("\n[3/5] Fill-realism stress (trail exit slippage) ...")
    slip_stats = [oos_trail_st]
    for slip in SLIP_SCENARIOS[1:]:
        _, trail_sl = _run_slice(
            files_oos, is_slice=False, oos_slice=True,
            slip_extra=slip, desc=f"OOS slip={slip}x")
        st = _stats(trail_sl, f"OOS trail_1R slip={slip}x")
        slip_stats.append(st)
        se = st["E_R"]; st2 = st["t_stat"]; sw = st["win_rate"]; sd2 = st["dollar_per_trade"]
        print(f"  slip={slip}x: E[R] {se:+.4f}  t {st2:+.2f}  win {sw:.1%}  dp {sd2:+.4f}")
    inc_0 = oos_trail_st["E_R"] - oos_base_st["E_R"]
    inc_w = slip_stats[-1]["E_R"] - oos_base_st["E_R"]
    pct_s = inc_w / inc_0 * 100.0 if inc_0 != 0 else float("nan")
    print(f"  Trail increment (slip=0x): {inc_0:+.4f}R")
    print(f"  Trail increment (slip=2x): {inc_w:+.4f}R")
    print(f"  => {pct_s:.0f}% of trail increment survives worst-case fill")
    print("  base_3R resolves at level fills -- comparison is conservative.")

    # 3b GAP-THROUGH fill test (task-12 guard): book trail exit at NEXT tick
    print("\n[3b/5] Gap-through fill test (trail exit at next tick after breach) ...")
    _, gap_trail = _run_slice(
        files_oos, is_slice=False, oos_slice=True,
        slip_extra=0.0, gap_fill=True, desc="OOS gap-fill")
    gap_st = _stats(gap_trail, "OOS trail_1R gap-fill")
    er_g = gap_st["E_R"]; t_g = gap_st["t_stat"]; w_g = gap_st["win_rate"]; dp_g = gap_st["dollar_per_trade"]
    inc_gap = gap_st["E_R"] - oos_base_st["E_R"]
    pct_gap = inc_gap / inc_0 * 100.0 if inc_0 != 0 else float("nan")
    print(f"  gap-fill : E[R] {er_g:+.4f}  t {t_g:+.2f}  win {w_g:.1%}  dp {dp_g:+.4f}")
    print(f"  ideal-fill increment: {inc_0:+.4f}R   gap-fill increment: {inc_gap:+.4f}R")
    print(f"  => {pct_gap:.0f}% of trail increment survives realistic next-tick fill")

    # 4 Regime split
    print("\n[4/5] Regime split (200d+50d SMA, IS+OOS) ...")
    print("  Building daily close (~30s) ...")
    is_trail_df  = _add_regimes(is_trail_rows)
    oos_trail_df = _add_regimes(oos_trail_rows)
    is_base_df   = _add_regimes(is_base_rows)
    oos_base_df  = _add_regimes(oos_base_rows)
    all_regime_rows = []
    for window in (200, 50):
        col = f"regime_{window}d"
        for period, t_df, b_df in [("IS",  is_trail_df, is_base_df),
                                    ("OOS", oos_trail_df, oos_base_df)]:
            all_regime_rows += _regime_table(t_df, col, period, "trail_1R")
            all_regime_rows += _regime_table(b_df, col, period, "base_3R")
    print("\nPeriod  SMA    Regime   n      E[R]     t_stat   win%    arm")
    print("  " + "-" * 68)
    for w in (200, 50):
        col = f"regime_{w}d"
        for period in ("IS", "OOS"):
            for arm in ("trail_1R", "base_3R"):
                for r in all_regime_rows:
                    if r["period"]==period and r["sma"]==col and r["arm"]==arm:
                        flag = "  **low-n" if r.get("low_power") else ""
                        er_s = _fmt(r["E_R"],      "+.4f")
                        ts_s = _fmt(r["t_stat"],   "+.2f")
                        wr_s = _fmt(r["win_rate"], ".1%")
                        rn = r["n"]; rr = r["regime"]
                        print(f"  {period:<5} {w:>4}d  {rr:<6}  {rn:>5}  {er_s:<9} {ts_s:<8} {wr_s:<7} {arm}{flag}")
    print("\nTrail INCREMENT over base_3R (IS 200d):")
    for regime in ("up", "flat", "down"):
        t_er = _get(all_regime_rows, "trail_1R", "IS", "regime_200d", regime)
        b_er = _get(all_regime_rows, "base_3R",  "IS", "regime_200d", regime)
        if t_er is not None and b_er is not None:
            print(f"    {regime:<5}: trail={t_er:+.4f}  base={b_er:+.4f}  delta={t_er-b_er:+.4f}")
    is_up_d = (_get(all_regime_rows, "trail_1R","IS","regime_200d","up") or 0) - (
              _get(all_regime_rows, "base_3R", "IS","regime_200d","up") or 0)
    is_dn_d = (_get(all_regime_rows, "trail_1R","IS","regime_200d","down") or 0) - (
              _get(all_regime_rows, "base_3R", "IS","regime_200d","down") or 0)
    tb = is_up_d > 0.05 and is_dn_d < -0.05
    print(f"  IS 200d increment: up={is_up_d:+.4f}  down={is_dn_d:+.4f}")
    print(f"  Trend-beta on trail INCREMENT (up>+0.05 AND down<-0.05): {tb}")

    # 5 MC — three scenarios bracket forward DD; forward_isedge is the central estimate
    print("\n[5/5] Survival/DD MC (Mode-A 5% cap, three scenarios) ...")
    is_trail_R = [r["R"] for r in is_trail_rows]
    mc = run_trail_mc(oos_trail_rows, is_trail_R=is_trail_R)
    rmc = mc["realized_OOS_ER"]
    def _show(d, header):
        print(f"\n{header}:")
        print(f"    med terminal ${d['median_terminal']:>8,.2f}  p5 ${d['p5_terminal']:>7,.2f}  p90 ${d['p90_terminal']:>8,.2f}")
        print(f"    median DD {d['median_dd']:>5.1f}%  p90 DD {d['p90_dd']:>5.1f}%  ruin {d['p_blowup']:.1f}%")
    _show(mc["realized"],       f"Realized OOS E[R]={rmc:+.4f} (ROSY upper bound)")
    _show(mc["derated_floor"],  "Derated-to-IS-edge, losses floored at -1R (conservative)")
    fwd = mc["forward_isedge"]
    _show(fwd,                  ">>> FORWARD IS-edge + current-price sizing (CENTRAL ESTIMATE)")
    print("\nBase_3R frozen ref: median DD~6%  p90 DD~33%  ruin~0%  (dd_sizing_study)")

    # Outputs
    pd.DataFrame([is_base_st, is_trail_st, oos_base_st, oos_trail_st]
                 + slip_stats[1:]).to_csv(_OUT / "trail_oos_main.csv", index=False)
    pd.DataFrame(all_regime_rows).to_csv(_OUT / "trail_oos_regime.csv", index=False)
    summary = {
        "model": "ORB-001", "analysis": "trail_oos_task13",
        "IS_base_3R":  is_base_st,  "IS_trail_1R":    is_trail_st,
        "OOS_base_3R": oos_base_st, "OOS_trail_base": oos_trail_st,
        "slip_scenarios":  slip_stats,
        "trail_inc_slip0": inc_0,  "trail_inc_worst": inc_w,
        "pct_survived":    pct_s,
        "OOS_trail_gapfill": gap_st,
        "trail_inc_gapfill": inc_gap, "pct_survived_gapfill": pct_gap,
        "regime":          all_regime_rows,
        "mc":              mc,
        "trend_beta_increment": tb,
        "is_up_delta":     is_up_d, "is_dn_delta": is_dn_d,
    }
    (_OUT / "trail_oos_summary.json").write_text(
        json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print("\n" + "=" * 88)
    print("VERDICT SUMMARY")
    print(f"  OOS trail_1R  : E[R]={er_ot:+.4f}  t={t_ot:+.2f}  win={w_ot:.1%}  n={n_ot}")
    ws_e = slip_stats[-1]["E_R"]; ws_t = slip_stats[-1]["t_stat"]
    print(f"  Worst-slip 2x : E[R]={ws_e:+.4f}  t={ws_t:+.2f}  ({pct_s:.0f}% of increment survived)")
    print(f"  Gap-fill      : E[R]={er_g:+.4f}  t={t_g:+.2f}  ({pct_gap:.0f}% of increment survived)")
    print(f"  Trend-beta on trail increment: {tb}  (IS 200d up={is_up_d:+.4f} dn={is_dn_d:+.4f})")
    print(f"  Trail MC FORWARD (central): median DD={fwd['median_dd']:.1f}%  p90 DD={fwd['p90_dd']:.1f}%  ruin={fwd['p_blowup']:.1f}%  vs base p90 ~33%")
    print(f"  Outputs -> {_OUT}")
    print("=" * 88)


if __name__ == "__main__":
    main()