"""
ORB-001 drawdown / sizing study (backlog tasks 1 + 2).

Resolves two coupled questions on the honest-edge $50 account (median $721 / 33% DD
at Mode-A min-lot + 5% cap). Both run on ONE OOS data load + the same de-rate-to-
+0.31R Monte Carlo as equity_sim_honest (winners flipped to stops to hit honest E[R]).

TASK 2 — survival filter (DD lever):
  A. %-of-equity cap sweep {3,4,5,6,8,10,None} -> DD/growth frontier.
  B. ATR-relative filter: skip days whose opening-range width range_w exceeds
     m x its rolling-median (an opening-range ATR proxy, self-contained, no extra
     data pass). Sweep m {1.5,2,2.5,3}. Equity-INDEPENDENT structural filter, vs the
     equity-dependent %-cap. Reported standalone and stacked with the 5% cap.

TASK 1 — Mode B fixed-fractional / compounding (growth lever):
  Risk f% of CURRENT equity, lot = floor(f%*eq / (range_w*100) / step)*step, min 0.01.
  Compare Mode A (flat min-lot) vs Mode B {f=2,3,5%} on terminal / DD / blow-up.
  At $50 the min-lot floor binds (f% < min-lot risk on wide days); Mode B only scales
  once equity grows -> expect higher terminal AND higher sustained %DD than Mode A.

Outputs -> research/outputs/orb/dd_sizing/
  cap_sweep.csv, atr_filter.csv, mode_b.csv, dd_sizing_summary.json, dd_frontier.png

    python research/models/orb/dd_sizing_study.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from research.models.orb.orb001.equity_sim import (
    load_oos_trades, MIN_LOT, CONTRACT_OZ, LEVERAGE,
)
from research.models.orb.orb001.equity_sim_honest import (
    n_flips_to_target, TARGET_ER, WIN_R, START, N_PATHS, SEED,
)

_OUT = Path(__file__).resolve().parents[4] / "research" / "outputs" / "orb" / "dd_sizing"
ATR_WINDOW = 20
LOT_STEP = 0.01

# ---- fast numpy equity walks (sequential dependency -> tight scalar loop) ----
# Both mirror equity_sim exactly: min-lot pnl = R*range_w, margin = entry*100*lot/lev.


def _walk_modea(R, rw, entry, start, cap, leverage=LEVERAGE):
    """Mode A min-lot walk. cap = %-equity skip-filter (None = take all)."""
    eq = peak = start
    max_dd = 0.0
    blew = False
    for i in range(R.shape[0]):
        risk = rw[i] * CONTRACT_OZ * MIN_LOT          # = rw[i]
        margin = entry[i] * CONTRACT_OZ * MIN_LOT / leverage
        if eq <= 0 or eq < margin:
            blew = True
            break
        if cap is not None and (risk / eq) * 100.0 > cap:
            continue
        eq += R[i] * rw[i]                            # min-lot dollar pnl
        if eq > peak:
            peak = eq
        dd = (peak - eq) / peak if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd
        if eq <= 0:
            blew = True
            break
    return eq, max_dd * 100.0, blew


def _walk_modeb(R, rw, entry, start, risk_frac_pct, leverage=LEVERAGE):
    """Mode B fixed-fractional: risk ~f% of current equity, lot floored to step/min."""
    eq = peak = start
    max_dd = 0.0
    blew = False
    for i in range(R.shape[0]):
        raw_lot = (risk_frac_pct / 100.0 * eq) / (rw[i] * CONTRACT_OZ)
        lot = raw_lot - (raw_lot % LOT_STEP)          # floor to step
        if lot < MIN_LOT:
            lot = MIN_LOT
        margin = entry[i] * CONTRACT_OZ * lot / leverage
        if eq <= 0 or eq < margin:
            blew = True
            break
        eq += R[i] * rw[i] * CONTRACT_OZ * lot
        if eq > peak:
            peak = eq
        dd = (peak - eq) / peak if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd
        if eq <= 0:
            blew = True
            break
    return eq, max_dd * 100.0, blew


def atr_keep_mask(rw: np.ndarray, mult: float, window: int = ATR_WINDOW) -> np.ndarray:
    """Boolean keep-mask: drop days whose range_w > mult x rolling-median (PRIOR days)."""
    s = pd.Series(rw)
    atr = s.rolling(window, min_periods=5).median().shift(1)
    keep = (s <= mult * atr).fillna(True)            # warm-up days: keep
    return keep.to_numpy()


def run_mc(trades: pd.DataFrame, walk, n_paths: int = N_PATHS, seed: int = SEED,
           desc: str = "MC", **walk_kw) -> dict:
    """N de-rated (+0.31R) paths through `walk`; numpy arrays, tqdm per protocol."""
    from tqdm import tqdm
    df = trades.sort_values("date").reset_index(drop=True)
    R0 = df["R"].to_numpy(dtype=float)
    rw = np.abs(df["range_w"].to_numpy(dtype=float))
    entry = df["entry_px"].to_numpy(dtype=float)
    win_pos = np.flatnonzero(R0 == WIN_R)
    k = n_flips_to_target(df, TARGET_ER)
    k = min(k, len(win_pos))

    term = np.empty(n_paths); dd = np.empty(n_paths); blow = np.empty(n_paths, bool)
    child = np.random.SeedSequence(seed).spawn(n_paths)
    for i in tqdm(range(n_paths), desc=desc, leave=False):
        rng = np.random.default_rng(child[i])
        R = R0.copy()
        if k > 0:
            R[rng.choice(win_pos, size=k, replace=False)] = -1.0
        term[i], dd[i], blow[i] = walk(R, rw, entry, START, **walk_kw)
    return {"median_terminal": float(np.median(term)),
            "p5_terminal": float(np.percentile(term, 5)),
            "p95_terminal": float(np.percentile(term, 95)),
            "median_dd": float(np.median(dd)),
            "p_blowup": float(np.mean(blow)) * 100.0}


def main() -> None:
    _OUT.mkdir(parents=True, exist_ok=True)
    print("=" * 84)
    print("ORB-001 DRAWDOWN / SIZING STUDY  (tasks 1+2)  — honest +0.31R, $50, OOS seq")
    print("=" * 84)
    trades = load_oos_trades().reset_index(drop=True)
    n = len(trades)
    print(f"OOS trades: {n}  ({trades['date'].min()} -> {trades['date'].max()})")
    print(f"SANITY  realized E[R]={trades['R'].mean():+.4f} -> de-rate target {TARGET_ER:+.4f}  "
          f"k={n_flips_to_target(trades, TARGET_ER)} flips  paths={N_PATHS}\n")

    # ---- TASK 2A: %-equity cap sweep -------------------------------------
    print("----- TASK 2A: %-of-equity cap sweep (Mode A min-lot) -----")
    cap_rows = []
    for cap in [3.0, 4.0, 5.0, 6.0, 8.0, 10.0, None]:
        r = run_mc(trades, _walk_modea, cap=cap, desc=f"capA {cap}")
        r["cap_pct"] = cap if cap is not None else "none"
        cap_rows.append(r)
        print(f"  cap {str(r['cap_pct']):>4}: med ${r['median_terminal']:>7,.0f}  "
              f"DD {r['median_dd']:>4.1f}%  blow {r['p_blowup']:.1f}%  "
              f"(p5 ${r['p5_terminal']:,.0f} p95 ${r['p95_terminal']:,.0f})")
    cap_df = pd.DataFrame(cap_rows)

    # ---- TASK 2B: ATR-relative filter ------------------------------------
    print("\n----- TASK 2B: ATR-relative range filter (skip range_w > m x rolling-median) -----")
    atr_rows = []
    trades_sorted = trades.sort_values("date").reset_index(drop=True)
    rw_all = np.abs(trades_sorted["range_w"].to_numpy(dtype=float))
    for m in [1.5, 2.0, 2.5, 3.0]:
        mask = atr_keep_mask(rw_all, m)
        tf = trades_sorted[mask].reset_index(drop=True)
        kept = len(tf)
        for cap in [None, 5.0]:
            r = run_mc(tf, _walk_modea, cap=cap, desc=f"ATR m{m} cap{cap}")
            r.update({"atr_mult": m, "cap_pct": cap if cap else "none",
                      "n_kept": kept, "n_dropped": n - kept})
            atr_rows.append(r)
            print(f"  m={m} cap={str(r['cap_pct']):>4}: med ${r['median_terminal']:>7,.0f}  "
                  f"DD {r['median_dd']:>4.1f}%  blow {r['p_blowup']:.1f}%  "
                  f"kept {kept}/{n} (dropped {n-kept})")
    atr_df = pd.DataFrame(atr_rows)

    # ---- TASK 1: Mode B fixed-fractional ---------------------------------
    print("\n----- TASK 1: Mode B fixed-fractional / compounding vs Mode A -----")
    mb_rows = []
    # Mode A reference (min-lot, 5% cap) = the honest baseline
    ra = run_mc(trades, _walk_modea, cap=5.0, desc="ModeA"); ra["mode"] = "A_minlot_cap5"
    mb_rows.append(ra)
    print(f"  Mode A (min-lot, 5% cap): med ${ra['median_terminal']:>7,.0f}  "
          f"DD {ra['median_dd']:.1f}%  blow {ra['p_blowup']:.1f}%")
    for f in [2.0, 3.0, 5.0]:
        r = run_mc(trades, _walk_modeb, risk_frac_pct=f, desc=f"ModeB {f}"); r["mode"] = f"B_fixfrac_{f:g}pct"
        mb_rows.append(r)
        print(f"  Mode B (risk {f:g}%/eq):       med ${r['median_terminal']:>7,.0f}  "
              f"DD {r['median_dd']:.1f}%  blow {r['p_blowup']:.1f}%  "
              f"(p95 ${r['p95_terminal']:,.0f})")
    mb_df = pd.DataFrame(mb_rows)

    # ---- write -----------------------------------------------------------
    cap_df.to_csv(_OUT / "cap_sweep.csv", index=False)
    atr_df.to_csv(_OUT / "atr_filter.csv", index=False)
    mb_df.to_csv(_OUT / "mode_b.csv", index=False)
    summary = {
        "model": "ORB-001", "analysis": "dd_sizing_study", "n_trades": n,
        "target_ER": TARGET_ER, "n_paths": N_PATHS, "start_usd": START,
        "cap_sweep": cap_rows, "atr_filter": atr_rows, "mode_b": mb_rows,
    }
    (_OUT / "dd_sizing_summary.json").write_text(json.dumps(summary, indent=2))

    # ---- frontier plot: DD vs terminal -----------------------------------
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.scatter(cap_df["median_dd"], cap_df["median_terminal"], c="#3b7dd8", s=60, label="%-equity cap")
    for _, r in cap_df.iterrows():
        ax.annotate(f"cap {r['cap_pct']}", (r["median_dd"], r["median_terminal"]), fontsize=7)
    ax.scatter(atr_df["median_dd"], atr_df["median_terminal"], c="#2e9e5b", s=40,
               marker="^", label="ATR filter")
    ax.scatter(mb_df["median_dd"], mb_df["median_terminal"], c="#d8633b", s=50,
               marker="s", label="Mode A/B sizing")
    ax.set_xlabel("median max drawdown (%)")
    ax.set_ylabel("median terminal equity ($)")
    ax.set_title("ORB-001 DD vs growth frontier — honest +0.31R, $50 (lower-right = better)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(_OUT / "dd_frontier.png", dpi=120)
    print(f"\nWrote outputs -> {_OUT}")

    # ---- verdict: lowest-DD config that still grows & 0% blow-up ---------
    safe = cap_df[(cap_df["p_blowup"] == 0) & (cap_df["median_terminal"] > START)]
    best_dd = safe.sort_values("median_dd").iloc[0] if len(safe) else None
    print("\n" + "=" * 84)
    if best_dd is not None:
        print(f"LOWEST-DD surviving cap: {best_dd['cap_pct']} -> DD {best_dd['median_dd']:.1f}%, "
              f"med ${best_dd['median_terminal']:,.0f} (vs 5%-cap baseline ${ra['median_terminal']:,.0f}/"
              f"{ra['median_dd']:.1f}%DD)")
    print("=" * 84)


if __name__ == "__main__":
    main()
