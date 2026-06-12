"""
Task 29 — complete Gate 6 for ORB-002 (NY 09:30) and ORB-003 (noon 12:00).

WHY: Gate 6 (protocol L204-226) = walk-forward AND Monte Carlo AND OOS. Both ideas
were marked passed on the OOS leg ONLY (walkforward=0, montecarlo=0 rows). This
backfills the two missing legs for both anchors in ONE parquet sweep.

Both anchors use the FROZEN trail_1R / N=5 / 2-pip config. NY trail sim is
orb002_backtest._simulate_day_trail (full fields incl entry_px); noon trail sim is
noon_anchor_scan._sim_trail (verified faithful copy, entry_px added for task 29).

LEG 1 — WALK-FORWARD (faithful port of orb001/walk_forward.py, anchor-agnostic):
  full-history (2016->2026) per-year / per-quarter / decay-regression / IS-vs-OOS
  Welch split-half. Pure stability scan, config already frozen (no re-fit).

LEG 2 — MONTE CARLO (honest-edge $50 survival, trail-compatible):
  ORB-001's MC flipped discrete +3R winners to de-rate the inflated OOS edge to the
  honest IS edge. trail_1R has CONTINUOUS R -> no discrete winners to flip. The
  faithful generalization: BOOTSTRAP-FROM-IS. Resample the IS trail trades (which
  embody the honest forward edge, NOT the bull-regime OOS) into OOS-length $50 paths
  under the 5% survival cap. Reports median/p5/p95 terminal, P(blow-up), median DD.
  Honest by construction, correct for continuous R. (Alternatives rejected: block-
  bootstrap the OOS sequence = bakes in the inflated edge; scale-OOS-to-IS = hacky
  level-shift that distorts the trade-size/R joint distribution.)

Writes research/outputs/orb/gate6_completion/gate6_completion_results.json for logging.

Run in a new window (~12-15 min, full-history tick replay x 2 anchors):
    python research/models/orb/orb002/gate6_completion.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from research.code.arctic_io import read_tick_month
from scipy import stats
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from research.models.orb.orb002.orb002_core import _tick_files, IS_END
from research.models.orb.orb002.orb002_backtest import _simulate_day_trail, edge_stats
from research.models.orb.orb002.noon_anchor_scan import _sim_trail as _sim_trail_noon
from research.models.orb.orb001.equity_sim import simulate_equity

NS_D = 86_400_000_000_000
N = 5
SPREAD = 2.0 * 0.10        # 2-pip JM
CAP = 5.0                  # Mode-A 5% survival cap
START = 50.0
N_PATHS = 1000
SEED = 42

# IS reference E[R] per anchor (from each idea's Gate-6 answer / step4_results)
ANCHORS = {
    "ORB-002": {"label": "NY 09:30 ET",  "sim": _simulate_day_trail, "is_ref_E_R": 0.7477},
    "ORB-003": {"label": "noon 12:00 ET", "sim": _sim_trail_noon,     "is_ref_E_R": 0.1802},
}

_OUT = Path(__file__).resolve().parents[4] / "research" / "outputs" / "orb" / "gate6_completion"


# ── one full-history sweep, both anchors ──────────────────────────────────────
def build_trades() -> dict[str, pd.DataFrame]:
    files = _tick_files(None)
    if not files:
        raise FileNotFoundError("No tick parquet found")
    out = {k: [] for k in ANCHORS}
    for f in tqdm(files, desc="gate6 full-history sweep (2 anchors)"):
        df = read_tick_month(f, columns=["ts_utc", "bid", "ask"])
        if df.empty:
            continue
        ts = df["ts_utc"].values.astype("datetime64[ns]").astype(np.int64)
        mid = (df["bid"].values + df["ask"].values) * 0.5
        dk = ts // NS_D
        for d in np.unique(dk):
            m = dk == d
            tsd, midd, day0 = ts[m], mid[m], int(d) * NS_D
            for key, cfg in ANCHORS.items():
                tr = cfg["sim"](tsd, midd, day0, N, spread_price=SPREAD)
                if tr is not None:
                    tr["date"] = pd.Timestamp(day0).date()
                    out[key].append(tr)
    res = {}
    for k, rows in out.items():
        d = pd.DataFrame(rows)
        d["date"] = pd.to_datetime(d["date"])
        res[k] = d.sort_values("date").reset_index(drop=True)
    return res


# ── LEG 1: walk-forward stability ─────────────────────────────────────────────
def walk_forward(tr: pd.DataFrame, is_ref_E_R: float, label: str) -> dict:
    tr = tr.copy()
    tr["year"] = tr["date"].dt.year
    overall = edge_stats(tr)

    yr = []
    for y, g in tr.groupby("year"):
        s = edge_stats(g)
        yr.append({"year": int(y), "n": s["n_trades"], "E_R": s["E_R"], "t": s["t_stat"]})
    by_year = pd.DataFrame(yr)

    # decay regression: per-trade R ~ time
    x = tr["date"].map(pd.Timestamp.toordinal).values.astype(float)
    yv = tr["R"].values
    lr = stats.linregress(x, yv)
    slope_per_year = lr.slope * 365.25
    decaying = (slope_per_year < 0) and (lr.pvalue < 0.05)

    # IS vs OOS Welch split-half
    is_R = tr.loc[tr["date"] < IS_END, "R"].values
    oos_R = tr.loc[tr["date"] >= IS_END, "R"].values
    welch = stats.ttest_ind(oos_R, is_R, equal_var=False)

    print(f"\n--- WALK-FORWARD {label} ---")
    print(f"  pooled E[R] {overall['E_R']:+.4f}  t {overall['t_stat']:+.2f}  n={overall['n_trades']}")
    for r in yr:
        print(f"  {r['year']}: E[R] {r['E_R']:+.4f}  t {r['t']:+.2f}  (n={r['n']})")
    print(f"  decay {slope_per_year:+.4f} R/yr (p={lr.pvalue:.3f}) -> "
          f"{'DECAYING' if decaying else 'no sig decay'}")
    print(f"  IS E[R] {is_R.mean():+.4f} (n={len(is_R)}) | OOS E[R] {oos_R.mean():+.4f} "
          f"(n={len(oos_R)}) | Welch t {welch.statistic:+.2f} p {welch.pvalue:.4f}")

    n_pos = int((by_year["E_R"] > 0).sum())
    n_tot = int(len(by_year))
    return {
        "pooled_E_R": overall["E_R"], "pooled_t": overall["t_stat"],
        "n_trades": int(overall["n_trades"]),
        "decay_slope_R_per_year": float(slope_per_year), "decay_p": float(lr.pvalue),
        "decaying": bool(decaying),
        "min_year_E_R": float(by_year["E_R"].min()), "max_year_E_R": float(by_year["E_R"].max()),
        "n_years_positive": n_pos, "n_years_total": n_tot,
        "IS_E_R": float(is_R.mean()), "OOS_E_R": float(oos_R.mean()),
        "welch_t": float(welch.statistic), "welch_p": float(welch.pvalue),
        "is_ref_E_R": is_ref_E_R,
        "by_year": by_year.to_dict("records"),
    }


# ── LEG 2: honest-edge Monte Carlo ($50 survival, bootstrap-from-IS) ──────────
def monte_carlo(tr: pd.DataFrame, label: str) -> dict:
    is_tr = tr[tr["date"] < IS_END].reset_index(drop=True)
    n_oos = int((tr["date"] >= IS_END).sum())          # path length = real OOS horizon
    rng = np.random.default_rng(SEED)

    print(f"\n--- MONTE CARLO {label} (bootstrap-from-IS, {N_PATHS} paths) ---")
    print(f"  IS source trades={len(is_tr)}  IS E[R]={is_tr['R'].mean():+.4f}  "
          f"path length=n_oos={n_oos}  start=${START:.0f}  cap={CAP}%")

    terms, dds, blows = [], [], []
    for _ in tqdm(range(N_PATHS), desc=f"honest MC {label}"):
        idx = rng.integers(0, len(is_tr), size=n_oos)
        samp = is_tr.iloc[idx].copy().reset_index(drop=True)
        samp["date"] = pd.date_range("2024-05-02", periods=n_oos, freq="D")
        s = simulate_equity(samp, start=START, risk_cap_pct=CAP)["summary"]
        terms.append(s["terminal_equity"]); dds.append(s["max_drawdown_pct"])
        blows.append(s["blew_up"])
    terms = np.array(terms); dds = np.array(dds)
    p5, p50, p95 = np.percentile(terms, [5, 50, 95])
    p_blow = float(np.mean(blows)) * 100.0
    med_dd = float(np.median(dds))

    print(f"  terminal median ${p50:,.2f}  p5 ${p5:,.2f}  p95 ${p95:,.2f}")
    print(f"  P(blow-up) {p_blow:.1f}%   median max DD {med_dd:.1f}%")
    verdict = "SURVIVES" if p_blow < 5 else "FRAGILE" if p_blow < 25 else "FAILS"
    print(f"  -> $50 {verdict}")
    return {
        "is_E_R": float(is_tr["R"].mean()), "n_is": int(len(is_tr)), "n_oos_pathlen": n_oos,
        "terminal_median": float(p50), "terminal_p5": float(p5), "terminal_p95": float(p95),
        "p_blowup_pct": p_blow, "median_max_dd_pct": med_dd, "verdict": verdict,
    }


def main() -> None:
    _OUT.mkdir(parents=True, exist_ok=True)
    print("=" * 88)
    print("TASK 29 — GATE 6 COMPLETION (walk-forward + Monte Carlo) | ORB-002 + ORB-003")
    print("=" * 88)

    trades = build_trades()
    results = {}
    for key, cfg in ANCHORS.items():
        tr = trades[key]
        print(f"\n{'#'*88}\n# {key} — {cfg['label']}  | full-history n={len(tr)}  "
              f"span {tr['date'].min().date()}->{tr['date'].max().date()}\n{'#'*88}")
        wf = walk_forward(tr, cfg["is_ref_E_R"], cfg["label"])
        mc = monte_carlo(tr, cfg["label"])
        results[key] = {"label": cfg["label"], "walkforward": wf, "montecarlo": mc}

    res_path = _OUT / "gate6_completion_results.json"
    res_path.write_text(json.dumps(results, indent=2, default=float), encoding="utf-8")
    print(f"\n[results] wrote {res_path}")


if __name__ == "__main__":
    main()
