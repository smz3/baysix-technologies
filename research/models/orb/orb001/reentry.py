"""
ORB-001 re-entry / second-breakout study (backlog task 19).

ORB-001 takes ONE signal/day (first breakout). HYPOTHESIS: on days where that first
trade loses, is there a SECOND breakout with its own positive edge, or does re-entering
just bleed equity on already-bad days?

SPEC (confirmed 2026-06-09):
  * Geometry  = direction-agnostic restart. After trade-1 exits, re-run the SAME
                first-breakout detector on the ORIGINAL or_hi/or_low from the exit tick
                onward; take whichever side breaks first. (long/short split = diagnostic.)
  * Trigger   = primary arm conditions on a LOSING first trade (R1 <= 0). The
                'after_any' arm (re-enter after any non-EOD exit) is the robustness null.
  * Depth     = ONE re-entry only (no 3rd/4th).
  * Mechanics = IDENTICAL to live: trail_1R exit, Mode-A min-lot 5% cap, 2-pip spread.
  * Fills     = honest stop-entry at the breached level (half-spread drag on EXIT only,
                = win-rate drag); trade-2 entry index STRICTLY after trade-1 exit index.
                The reverse signal coincides with the stop, so idealised fills would
                fabricate edge here exactly like task 12 — guarded against.

LIVE CONFIG: anchor 09:00 UTC / N=5 / trail_1R / Mode-A 5% cap (NOT orb_core's legacy
08:00 — task 22 switched the anchor to 09:00). Hardcoded below to match live.

IS-ONLY (config selection keeps OOS sealed). OOS is a gated follow-up if IS passes the
two bars: (1) trade-2 own $/trade > 0 with a real t-stat, AND (2) the combined daily
stream does not worsen $50 survival/DD vs trade-1-alone.

    python research/models/orb/reentry.py

Outputs -> research/outputs/orb/reentry/
    reentry_arms.csv  reentry_daily.csv  reentry_summary.json  reentry.png
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from tqdm import tqdm

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))

from research.models.orb.orb001.orb_core import IS_END
from research.code.session_cache import session_files
from research.models.orb.orb001.equity_sim import MIN_LOT, CONTRACT_OZ, LEVERAGE

ANCHOR_HOUR = 9          # LIVE anchor 09:00 UTC (task 22) — NOT orb_core's legacy 08:00
OR_MIN      = 5
SPREAD      = 2.0 * 0.10
EOD_HOUR    = 21
N_PATHS     = 1000
SEED        = 42
START       = 50.0
CAP_PCT     = 5.0
NS_H = 3_600_000_000_000
NS_M =    60_000_000_000
NS_D = 86_400_000_000_000
_OUT = REPO / "research" / "outputs" / "orb" / "reentry"


# ---------------------------------------------------------------------------
# trail_1R exit — verbatim semantics from structures.py _exit_R(arm='trail_1R')
# ---------------------------------------------------------------------------
def _trail_exit(emid, e, pdir, rw, half):
    """trail_1R from entry tick. Returns (R, exit_idx_in_emid, hit) where hit=True if
    the trailing/initial stop fired (non-EOD). Exit fills on the opposite quote."""
    g = pdir * (emid - e)
    exit_fill_adj = pdir * ((emid - pdir * half) - e) / rw   # long sells bid, short buys ask
    peak = np.maximum.accumulate(g)
    rel = g <= peak - rw + half                              # 1R below running peak
    i_x = int(np.argmax(rel)) if rel.any() else None
    if i_x is not None:
        return float(exit_fill_adj[i_x]), i_x, True
    return float(exit_fill_adj[-1]), len(emid) - 1, False    # EOD flat


def _simulate_day(ts, mid, day0):
    """Return per-day dict with trade-1 (always) and trade-2 (direction-agnostic restart
    after trade-1's non-EOD exit), or None if no first breakout. trade-2 is recorded
    UNCONDITIONALLY on a non-EOD trade-1 exit; the loss-condition is applied downstream
    so both 'after_loss' and 'after_any' arms come from one pass."""
    half = SPREAD * 0.5
    anchor = day0 + ANCHOR_HOUR * NS_H
    or_end = anchor + OR_MIN * NS_M
    eod = day0 + EOD_HOUR * NS_H

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

    def find_break(start_idx):
        """First breakout of the ORIGINAL OR levels at/after start_idx (in pmid)."""
        seg = pmid[start_idx:]
        up = seg >= or_hi - half
        dn = seg <= or_lo + half
        i_up = int(np.argmax(up)) if up.any() else None
        i_dn = int(np.argmax(dn)) if dn.any() else None
        if i_up is None and i_dn is None:
            return None
        if i_dn is None or (i_up is not None and i_up <= i_dn):
            return 1.0, or_hi, start_idx + i_up
        return -1.0, or_lo, start_idx + i_dn

    # ---- trade 1: first breakout from window close ----
    b1 = find_break(0)
    if b1 is None:
        return None
    pdir1, e1, i_entry1 = b1
    emid1 = pmid[i_entry1:]
    if len(emid1) < 2:
        return None
    R1, i_x1, hit1 = _trail_exit(emid1, e1, pdir1, rw, half)
    exit_idx1 = i_entry1 + i_x1

    rec = {"date": pd.Timestamp(day0).date(), "rw": float(rw),
           "dir1": "long" if pdir1 > 0 else "short", "entry1": float(e1),
           "R1": R1, "hit1": bool(hit1),
           "dir2": None, "entry2": np.nan, "R2": np.nan}

    # ---- trade 2: direction-agnostic restart, strictly after trade-1 exit ----
    if hit1 and (exit_idx1 + 1) < len(pmid):
        b2 = find_break(exit_idx1 + 1)
        if b2 is not None:
            pdir2, e2, i_entry2 = b2
            emid2 = pmid[i_entry2:]
            if len(emid2) >= 2:
                R2, _, _ = _trail_exit(emid2, e2, pdir2, rw, half)
                rec["dir2"] = "long" if pdir2 > 0 else "short"
                rec["entry2"] = float(e2)
                rec["R2"] = R2
    return rec


def run_is():
    files = session_files(None)
    is_cut = np.datetime64(IS_END)
    rows = []
    for f in tqdm(files, desc="reentry IS"):
        df = pd.read_parquet(f, columns=["ts_utc", "bid", "ask"])
        df = df[df["ts_utc"].values < is_cut]
        if df.empty:
            continue
        ts_all = df["ts_utc"].values.astype("datetime64[ns]").astype(np.int64)
        mid_all = (df["bid"].values + df["ask"].values) * 0.5
        day_key = ts_all // NS_D
        for d in np.unique(day_key):
            m = day_key == d
            r = _simulate_day(ts_all[m], mid_all[m], int(d) * NS_D)
            if r is not None:
                rows.append(r)
    return pd.DataFrame(rows).sort_values("date").reset_index(drop=True)


# ---------------------------------------------------------------------------
# stats
# ---------------------------------------------------------------------------
def _r_stat(R, label):
    R = np.asarray(R, dtype=float)
    n = len(R)
    if n == 0:
        return {"arm": label, "n": 0}
    mean, sd = float(R.mean()), float(R.std(ddof=1)) if n > 1 else 0.0
    t = mean / (sd / np.sqrt(n)) if sd > 0 else np.nan
    return {"arm": label, "n": n, "E_R": mean, "se_R": (sd / np.sqrt(n)) if n > 1 else np.nan,
            "t_stat": t, "win_rate": float((R > 0).mean())}


def _dollar_per_trade(R, rw):
    """$ P&L per trade at min lot (CONTRACT_OZ*MIN_LOT = 1 oz): R * range_w."""
    R, rw = np.asarray(R, float), np.asarray(rw, float)
    return float((R * rw * CONTRACT_OZ * MIN_LOT).mean()) if len(R) else np.nan


# ---------------------------------------------------------------------------
# combined-daily survival: day-block bootstrap (preserves within-day t1/t2 pairing)
# ---------------------------------------------------------------------------
def _walk_modea(R, rw, entry, start=START, cap=CAP_PCT):
    eq = peak = start
    max_dd = 0.0
    blew = False
    for i in range(len(R)):
        risk = rw[i] * CONTRACT_OZ * MIN_LOT
        margin = entry[i] * CONTRACT_OZ * MIN_LOT / LEVERAGE
        if eq <= 0 or eq < margin:
            blew = True
            break
        if cap is not None and (risk / eq) * 100.0 > cap:
            continue
        eq += R[i] * rw[i] * CONTRACT_OZ * MIN_LOT
        if eq > peak:
            peak = eq
        dd = (peak - eq) / peak if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd
        if eq <= 0:
            blew = True
            break
    return eq, max_dd * 100.0, blew


def _day_blocks(df, include_t2):
    """Per-day list of (R, rw, entry) trades. include_t2(row)->bool decides trade-2."""
    blocks = []
    for _, r in df.iterrows():
        day = [(r["R1"], r["rw"], r["entry1"])]
        if include_t2(r) and not pd.isna(r["R2"]):
            day.append((r["R2"], r["rw"], r["entry2"]))
        blocks.append(day)
    return blocks


def run_mc(blocks, label, n_paths=N_PATHS, seed=SEED):
    nb = len(blocks)
    child = np.random.SeedSequence(seed).spawn(n_paths)
    terms, dds, blows = [], [], []
    for i in tqdm(range(n_paths), desc=label, leave=False):
        rng = np.random.default_rng(child[i])
        idx = rng.choice(nb, size=nb, replace=True)
        flat = [t for j in idx for t in blocks[j]]
        R = np.array([t[0] for t in flat]); rw = np.array([t[1] for t in flat])
        ent = np.array([t[2] for t in flat])
        term, dd, blew = _walk_modea(R, rw, ent)
        terms.append(term); dds.append(dd); blows.append(blew)
    T, D, B = np.array(terms), np.array(dds), np.array(blows)
    total_trades = sum(len(b) for b in blocks)
    return {"label": label, "n_days": nb, "total_trades": total_trades,
            "median_terminal": float(np.median(T)), "p5_terminal": float(np.percentile(T, 5)),
            "p90_terminal": float(np.percentile(T, 90)),
            "median_dd": float(np.median(D)), "p90_dd": float(np.percentile(D, 90)),
            "p_blowup": float(np.mean(B)) * 100.0}


# ---------------------------------------------------------------------------
def main():
    _OUT.mkdir(parents=True, exist_ok=True)
    print("=" * 90)
    print("ORB-001 RE-ENTRY / SECOND-BREAKOUT (task 19) | IS 2016->2024-05 | trail_1R | "
          "anchor 09:00/N5 | NET @ 2-pip")
    print("=" * 90)

    df = run_is()
    df.to_csv(_OUT / "reentry_daily.csv", index=False)
    n_days = len(df)
    n_loss = int((df["R1"] <= 0).sum())
    has_t2 = ~df["R2"].isna()
    print(f"\n  days with a 1st trade: {n_days}")
    print(f"  1st-trade losers (R1<=0): {n_loss} ({n_loss / n_days:.1%})")
    print(f"  days with any 2nd breakout (non-EOD exit): {int(has_t2.sum())}")

    # ---- per-trade edge ----
    s_t1 = _r_stat(df["R1"], "trade1")
    after_loss = df[(df["R1"] <= 0) & has_t2]
    after_any = df[has_t2]
    s_loss = _r_stat(after_loss["R2"], "trade2_after_loss")
    s_any = _r_stat(after_any["R2"], "trade2_after_any")
    s_t1["dollar_per_trade"] = _dollar_per_trade(df["R1"], df["rw"])
    s_loss["dollar_per_trade"] = _dollar_per_trade(after_loss["R2"], after_loss["rw"])
    s_any["dollar_per_trade"] = _dollar_per_trade(after_any["R2"], after_any["rw"])

    print("\n----- PER-TRADE EDGE (IS) -----")
    for s in (s_t1, s_loss, s_any):
        if s["n"] == 0:
            print(f"  {s['arm']:20s}: (none)"); continue
        print(f"  {s['arm']:20s}: n={s['n']:>4}  E[R] {s['E_R']:+.4f}  t {s['t_stat']:+.2f}  "
              f"win {s['win_rate']:.1%}  $/trade {s['dollar_per_trade']:+.4f}")

    # ---- curve-fit diagnostics ----
    paired = df[(df["R1"] <= 0) & has_t2]
    corr = float(np.corrcoef(paired["R1"], paired["R2"])[0, 1]) if len(paired) > 2 else np.nan
    same_dir = float((after_loss["dir1"] == after_loss["dir2"]).mean()) if len(after_loss) else np.nan
    print("\n----- CURVE-FIT GUARD -----")
    print(f"  corr(R1, R2) on loss+reentry days: {corr:+.3f}  (near 0 = trade-2 is its own signal)")
    print(f"  trade-2 SAME direction as failed trade-1: {same_dir:.1%}  "
          f"(high = continuation/re-break; low = reversal/fade)")

    # ---- combined-daily survival vs trade-1-alone ----
    print("\n----- $50 SURVIVAL: combined daily stream vs trade-1-alone (day-block MC) -----")
    blk_t1 = _day_blocks(df, lambda r: False)
    blk_loss = _day_blocks(df, lambda r: r["R1"] <= 0)
    blk_any = _day_blocks(df, lambda r: True)
    mc_t1 = run_mc(blk_t1, "MC trade1-only")
    mc_loss = run_mc(blk_loss, "MC +reentry-after-loss")
    mc_any = run_mc(blk_any, "MC +reentry-after-any")
    for mc in (mc_t1, mc_loss, mc_any):
        print(f"  {mc['label']:26s}: median ${mc['median_terminal']:>7.0f}  "
              f"p5 ${mc['p5_terminal']:>6.0f}  p90DD {mc['p90_dd']:>5.1f}%  "
              f"blowup {mc['p_blowup']:>4.1f}%")

    # ---- outputs ----
    arms_df = pd.DataFrame([s_t1, s_loss, s_any])
    arms_df.to_csv(_OUT / "reentry_arms.csv", index=False)
    summary = {
        "model": "ORB-001", "analysis": "reentry_second_breakout_task19",
        "config": {"anchor_hour": ANCHOR_HOUR, "or_min": OR_MIN, "exit": "trail_1R",
                   "spread_price": SPREAD, "sizing": "ModeA_minlot_5pct"},
        "n_days": n_days, "n_loss1": n_loss, "n_reentry": int(has_t2.sum()),
        "per_trade": {"trade1": s_t1, "trade2_after_loss": s_loss, "trade2_after_any": s_any},
        "curvefit": {"corr_R1_R2": corr, "trade2_same_dir_frac": same_dir},
        "survival": {"trade1_only": mc_t1, "reentry_after_loss": mc_loss,
                     "reentry_after_any": mc_any},
        "note": "IS-only (config selection; OOS sealed). $/trade is the deploy metric "
                "(E[R] is a denominator illusion). VERDICT bar: trade-2 own $/trade>0 with "
                "real t AND combined survival not worse than trade-1-alone. OOS only if both pass.",
    }
    (_OUT / "reentry_summary.json").write_text(json.dumps(summary, indent=2, default=str))

    # ---- plot ----
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
    labels = ["trade1", "t2_after_loss", "t2_after_any"]
    ervals = [s_t1.get("E_R", 0), s_loss.get("E_R", 0), s_any.get("E_R", 0)]
    sevals = [s_t1.get("se_R", 0), s_loss.get("se_R", 0), s_any.get("se_R", 0)]
    ax1.bar(labels, ervals, yerr=sevals, capsize=4, color=["#888", "#d8743b", "#3b7dd8"])
    ax1.axhline(0, color="black", lw=0.8)
    ax1.set_ylabel("E[R] per trade (IS)")
    ax1.set_title("Re-entry per-trade edge")
    ax1.tick_params(axis="x", rotation=20)
    mcs = [mc_t1, mc_loss, mc_any]
    mlabels = ["t1-only", "+reentry/loss", "+reentry/any"]
    ax2.bar(mlabels, [m["median_terminal"] for m in mcs], color=["#888", "#d8743b", "#3b7dd8"])
    ax2.set_ylabel("median $50 terminal (MC)")
    ax2.set_title("Combined survival")
    ax2.tick_params(axis="x", rotation=20)
    fig.tight_layout()
    fig.savefig(_OUT / "reentry.png", dpi=120)
    print(f"\nWrote outputs -> {_OUT}")

    # ---- verdict ----
    print("\n" + "=" * 90)
    edge_ok = s_loss["n"] > 0 and s_loss["dollar_per_trade"] > 0 and (s_loss["t_stat"] or 0) > 2
    surv_ok = (mc_loss["median_terminal"] >= mc_t1["median_terminal"] and
               mc_loss["p90_dd"] <= mc_t1["p90_dd"] + 1.0 and
               mc_loss["p_blowup"] <= mc_t1["p_blowup"] + 0.5)
    print(f"VERDICT (after-loss arm): edge {'PASS' if edge_ok else 'FAIL'} "
          f"($/t {s_loss.get('dollar_per_trade', float('nan')):+.4f}, t {s_loss.get('t_stat', float('nan')):+.2f}) | "
          f"survival {'PASS' if surv_ok else 'FAIL'} "
          f"(median ${mc_loss['median_terminal']:.0f} vs ${mc_t1['median_terminal']:.0f}, "
          f"p90DD {mc_loss['p90_dd']:.1f}% vs {mc_t1['p90_dd']:.1f}%). "
          f"{'-> OOS warranted' if edge_ok and surv_ok else '-> stop at IS (no OOS)'}")
    print("=" * 90)


if __name__ == "__main__":
    main()
