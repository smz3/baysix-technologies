"""
HMM Gate 2 — Foundation check on XAUUSD D1.
4 objective sanity checks replace visual confirmation.
Self-contained: opens Gate 2, logs result, passes/blocks in research.db.
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from hmmlearn.hmm import GaussianHMM
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parents[2] / "code"))
from pipeline import get_gates, log_result, open_gate, pass_gate, block_gate

IS_END      = "2024-05-02"
K           = 3
N_RESTARTS  = 10

THRESHOLDS = {
    "occ_min":     0.05,
    "occ_max":     0.90,
    "persistence": 0.85,
    "vol_ratio":   2.0,
}

COLOURS = {"Bull": "#2ECC71", "Neutral": "#F39C12", "Bear": "#E74C3C"}

KNOWN_EVENTS = {
    "GFC crisis":     ("2008-09-01", "2009-03-31"),
    "COVID crash":    ("2020-02-15", "2020-04-30"),
    "Russia-Ukraine": ("2022-02-20", "2022-04-30"),
}


def load_returns():
    df      = pd.read_parquet("data/parquet/daily/xauusd_daily.parquet")
    df      = df[df.index <= IS_END]
    log_ret = np.log(df["close"] / df["close"].shift(1)).dropna()
    features = np.column_stack([log_ret.values, np.abs(log_ret.values)])
    return df.loc[log_ret.index, "close"], log_ret, features


def fit_best(features: np.ndarray) -> GaussianHMM:
    best, best_score = None, -np.inf
    for seed in tqdm(range(N_RESTARTS), desc=f"K={K} restarts"):
        m = GaussianHMM(n_components=K, covariance_type="full",
                        n_iter=1000, tol=1e-5, random_state=seed)
        m.fit(features)
        score = m.score(features)
        tqdm.write(f"  restart {seed+1:2d}/{N_RESTARTS}  logL={score:.2f}  converged={m.monitor_.converged}")
        if score > best_score:
            best_score, best = score, m
    return best


def label_states(model: GaussianHMM) -> dict:
    mus   = np.array([model.means_[k, 0] for k in range(K)])
    order = np.argsort(mus)[::-1]
    names = ["Bull", "Neutral", "Bear"]
    return {order[i]: names[i] for i in range(K)}


def run_checks(model: GaussianHMM, states: np.ndarray) -> dict:
    """Returns dict of check_name → (passed: bool, value: str, criterion: str)."""
    checks = {}

    converged = bool(model.monitor_.converged)
    checks["converged"] = (converged, str(converged), "True")

    occ_vals  = [(states == k).mean() for k in range(K)]
    occ_min_v = min(occ_vals)
    occ_max_v = max(occ_vals)
    occ_pass  = occ_min_v >= THRESHOLDS["occ_min"] and occ_max_v <= THRESHOLDS["occ_max"]
    checks["occupancy"] = (occ_pass,
                           f"min={occ_min_v:.3f} max={occ_max_v:.3f}",
                           f"all in [{THRESHOLDS['occ_min']},{THRESHOLDS['occ_max']}]")

    diag_min  = min(model.transmat_[k, k] for k in range(K))
    pers_pass = diag_min >= THRESHOLDS["persistence"]
    checks["persistence"] = (pers_pass,
                              f"min_Ajj={diag_min:.3f}",
                              f"> {THRESHOLDS['persistence']}")

    mu_vols   = model.means_[:, 1]
    vol_ratio = mu_vols.max() / mu_vols.min()
    vol_pass  = vol_ratio >= THRESHOLDS["vol_ratio"]
    checks["vol_ratio"] = (vol_pass,
                           f"ratio={vol_ratio:.2f}",
                           f"> {THRESHOLDS['vol_ratio']}")

    return checks


def event_anchoring(close: pd.Series, states: np.ndarray, state_names: dict):
    print("\n--- Event anchoring (informational) ---")
    volatile_ids = {k for k, v in state_names.items() if v in ("Bear", "Neutral")}
    for name, (start, end) in KNOWN_EVENTS.items():
        mask = (close.index >= start) & (close.index <= end)
        if mask.sum() == 0:
            print(f"  {name:20s}: no data in window")
            continue
        frac = np.isin(states[mask], list(volatile_ids)).mean()
        print(f"  {name:20s}: {frac*100:.0f}% obs in Bear/Neutral states")


def plot(close: pd.Series, states: np.ndarray, state_names: dict):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=close.index, y=close.values, mode="lines",
                             line=dict(color="#aaaaaa", width=1),
                             name="Close", showlegend=False))
    for state_id, name in state_names.items():
        mask = states == state_id
        fig.add_trace(go.Scatter(x=close.index[mask], y=close.values[mask],
                                 mode="markers", marker=dict(color=COLOURS[name], size=4),
                                 name=name))
    fig.update_layout(title="XAUUSD D1 — HMM K=3 Gaussian Regimes (IS)",
                      xaxis_title="Date", yaxis_title="Price (USD)",
                      template="plotly_dark", height=600)
    out = "research/outputs/hmm/hmm_gate2_regimes.html"
    fig.write_html(out)
    print(f"\nChart saved: {out}")


def main():
    close, log_ret, features = load_returns()
    n_obs = len(features)

    print("\n--- Sanity block ---")
    print(f"n_obs     : {n_obs}")
    print(f"return_std: {log_ret.std():.5f}")
    print(f"IS window : {log_ret.index[0].date()} → {log_ret.index[-1].date()}")
    print(f"K         : {K}  |  N_RESTARTS: {N_RESTARTS}")
    print(f"features  : [r_t, |r_t|]  shape={features.shape}\n")

    model       = fit_best(features)
    states      = model.predict(features)
    state_names = label_states(model)

    print("\n--- Model params ---")
    for k in range(K):
        occ = (states == k).mean() * 100
        print(f"  {state_names[k]:8s} (state {k})  "
              f"mu_ret={model.means_[k,0]:.5f}  mu_vol={model.means_[k,1]:.5f}  "
              f"occ={occ:.1f}%  A_jj={model.transmat_[k,k]:.3f}")

    checks   = run_checks(model, states)
    all_pass = all(c[0] for c in checks.values())

    print("\n--- Gate 2 objective checks ---")
    for name, (passed, value, criterion) in checks.items():
        flag = "PASS" if passed else "FAIL"
        print(f"  [{flag}] {name:12s}  {value}  (need: {criterion})")

    event_anchoring(close, states, state_names)
    plot(close, states, state_names)

    # ── DB logging ──────────────────────────────────────────────────────────────
    git_sha     = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).decode().strip()
    params_json = json.dumps({"K": K, "N_RESTARTS": N_RESTARTS,
                               "covariance_type": "full",
                               "features": ["r_t", "abs_r_t"]})
    check_notes = " | ".join(
        f"{n}={'PASS' if p else 'FAIL'}({v})" for n, (p, v, _) in checks.items()
    )

    gate2_rows = [g for g in get_gates("HMM-001") if g["gate_number"] == 2]
    if not gate2_rows:
        open_gate("HMM-001", 2,
                  pass_criteria="converged=True + occ [5%,90%] + all A_jj>0.85 + vol_ratio>2.0",
                  attempt=1)
        attempt = 1
    else:
        attempt = max(g["attempt"] for g in gate2_rows)

    result_id = log_result(
        idea_id="HMM-001", gate_number=2, stage="IS",
        metric_key="foundation_check",
        metric_value=1.0 if all_pass else 0.0,
        cost_adjusted=0, period="daily", n_obs=n_obs,
        data_start=str(log_ret.index[0].date()),
        data_end=str(log_ret.index[-1].date()),
        git_sha=git_sha,
        code_path="research/models/hmm/gaussian_hmm.py",
        parameters=params_json,
        notes=check_notes,
    )

    gate_answer = f"{'PASS' if all_pass else 'FAIL'} | K={K} | {check_notes}"
    if all_pass:
        pass_gate("HMM-001", 2, gate_answer=gate_answer, answered_by="agent", attempt=attempt)
        print(f"\n>>> GATE 2: PASS — logged (result_id={result_id})")
    else:
        block_gate("HMM-001", 2, gate_answer=gate_answer, answered_by="agent", attempt=attempt)
        print(f"\n>>> GATE 2: BLOCKED — logged (result_id={result_id})")
        print("    Fix whichever checks failed, increment attempt, re-run.")

    print("Done.")


if __name__ == "__main__":
    main()
