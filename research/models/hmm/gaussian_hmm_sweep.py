"""
HMM Gate 2 — Rolling vol window sweep: [3, 5, 7, 10, 14, 20] days.
Features: [r_t, rolling_std(window)]. K=3, 10 restarts per window.
Exploratory only — no DB writes. Use gaussian_hmm.py for the formal run.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from hmmlearn.hmm import GaussianHMM
from tqdm import tqdm

IS_END     = "2024-05-02"
K          = 3
N_RESTARTS = 10
WINDOWS    = [3, 5, 7, 10, 14, 20]

THRESHOLDS = {
    "occ_min":     0.05,
    "occ_max":     0.90,
    "persistence": 0.85,
    "vol_ratio":   2.0,
}


def load_returns():
    df      = pd.read_parquet("data/parquet/daily/xauusd_daily.parquet")
    df      = df[df.index <= IS_END]
    log_ret = np.log(df["close"] / df["close"].shift(1)).dropna()
    return log_ret


def build_features(log_ret: pd.Series, window: int):
    rolling_vol = log_ret.rolling(window).std()
    df = pd.DataFrame({"r": log_ret, "vol": rolling_vol}).dropna()
    return np.column_stack([df["r"].values, df["vol"].values]), len(df)


def fit_best(features: np.ndarray, window: int) -> GaussianHMM:
    best, best_score = None, -np.inf
    for seed in tqdm(range(N_RESTARTS), desc=f"  w={window:2d}d restarts", leave=False):
        m = GaussianHMM(n_components=K, covariance_type="diag",
                        n_iter=1000, tol=1e-5, random_state=seed)
        m.fit(features)
        score = m.score(features)
        tqdm.write(f"    restart {seed+1:2d}/{N_RESTARTS}  logL={score:.2f}  "
                   f"converged={m.monitor_.converged}")
        if score > best_score:
            best_score, best = score, m
    return best


def run_checks(model: GaussianHMM, states: np.ndarray) -> dict:
    checks = {}

    converged = bool(model.monitor_.converged)
    checks["converged"] = (converged, str(converged))

    occ_vals  = [(states == k).mean() for k in range(K)]
    occ_min_v = min(occ_vals)
    occ_max_v = max(occ_vals)
    occ_pass  = occ_min_v >= THRESHOLDS["occ_min"] and occ_max_v <= THRESHOLDS["occ_max"]
    checks["occupancy"] = (occ_pass, f"min={occ_min_v:.3f}/max={occ_max_v:.3f}")

    diag_min  = min(model.transmat_[k, k] for k in range(K))
    pers_pass = diag_min >= THRESHOLDS["persistence"]
    checks["persistence"] = (pers_pass, f"min_Ajj={diag_min:.3f}")

    mu_vols   = model.means_[:, 1]
    vol_ratio = mu_vols.max() / mu_vols.min()
    vol_pass  = vol_ratio >= THRESHOLDS["vol_ratio"]
    checks["vol_ratio"] = (vol_pass, f"ratio={vol_ratio:.2f}")

    return checks


def label_states(model: GaussianHMM) -> dict:
    mus   = np.array([model.means_[k, 0] for k in range(K)])
    order = np.argsort(mus)[::-1]
    return {order[i]: n for i, n in enumerate(["Bull", "Neutral", "Bear"])}


def main():
    log_ret = load_returns()

    print("\n--- Sanity block ---")
    print(f"IS window : {log_ret.index[0].date()} -> {log_ret.index[-1].date()}")
    print(f"K         : {K}  |  N_RESTARTS: {N_RESTARTS}")
    print(f"Sweep     : rolling_vol windows = {WINDOWS}")
    print(f"Features  : [r_t, rolling_std(window)]\n")

    results = []

    for w in WINDOWS:
        print(f"\n{'='*60}")
        print(f"Window = {w}d")
        print(f"{'='*60}")

        features, n_obs = build_features(log_ret, w)
        print(f"  n_obs={n_obs}")

        model       = fit_best(features, w)
        states      = model.predict(features)
        state_names = label_states(model)
        checks      = run_checks(model, states)
        all_pass    = all(c[0] for c in checks.values())

        for k in range(K):
            occ = (states == k).mean() * 100
            print(f"  {state_names[k]:8s}  mu_ret={model.means_[k,0]:.5f}  "
                  f"mu_vol={model.means_[k,1]:.5f}  occ={occ:.1f}%  "
                  f"A_jj={model.transmat_[k,k]:.3f}")

        results.append({"window": w, "n_obs": n_obs,
                        "all_pass": all_pass, "checks": checks})

    # ── Summary table ───────────────────────────────────────────────────────────
    print("\n\n" + "=" * 76)
    print("SWEEP SUMMARY  —  K=3  |  features: [r_t, rolling_std(window)]")
    print("=" * 76)
    header = f"{'W':>4}  {'Conv':>5}  {'Occupancy':>22}  {'Persistence':>16}  {'VolRatio':>12}  {'Result':>10}"
    print(header)
    print("-" * 76)

    for r in results:
        c      = r["checks"]
        conv   = "PASS" if c["converged"][0]   else "FAIL"
        occ    = ("PASS" if c["occupancy"][0]   else "FAIL") + f" {c['occupancy'][1]}"
        pers   = ("PASS" if c["persistence"][0] else "FAIL") + f" {c['persistence'][1]}"
        vol    = ("PASS" if c["vol_ratio"][0]   else "FAIL") + f" {c['vol_ratio'][1]}"
        result = ">>> PASS <<<"  if r["all_pass"] else "BLOCKED"
        print(f"  {r['window']:2d}  {conv:>5}  {occ:>22}  {pers:>16}  {vol:>12}  {result:>10}")

    print("=" * 76)

    passing = [r["window"] for r in results if r["all_pass"]]
    if passing:
        print(f"\nWindows that PASS all checks: {passing}")
        print(f"Recommended: w={passing[0]} (shortest passing window = least smoothing)")
    else:
        print("\nNo window passed all checks. Review persistence values above.")


if __name__ == "__main__":
    main()
