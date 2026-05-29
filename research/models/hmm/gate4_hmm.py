"""
HMM-001 Gate 4 — Does the unsupervised HMM confirm or improve on the 5% baseline?

Gate 1 goal statement is the bar (NOT signal edge / Sharpe):
  "probabilistic regime intelligence ... accurately detects the current regime
   and quantifies P(regime change) ... strategy-agnostic filter."

So Gate 4 measures:
  1. Sane regimes      — Gate 0 expectations: converge, no degenerate state,
                          vol separation sigma_max/sigma_min > 2.0, restart stability
  2. Accuracy vs base  — agreement % + Cohen's kappa between FILTERED HMM regimes
                          (real-time, failure-mode F5) and the 5%/20d labels.
                          Above chance but not identical = the HMM adds information.
  3. Calibration       — one-step-ahead FORECAST pseudo-residuals Z_t. If the model's
                          regime probabilities are honest, Z_t ~ iid N(0,1)
                          (Jarque-Bera normality + Ljung-Box independence).
                          A hard fail here means P(regime change) is miscalibrated
                          under Gaussian -> escalate to NIG (Gate 0 fat-tail delta).

Self-contained: opens Gate 4, logs result, passes/blocks in research.db.
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from hmmlearn.hmm import GaussianHMM
from scipy.stats import norm, jarque_bera
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parents[2] / "code"))
from pipeline import get_gates, log_result, open_gate, pass_gate, block_gate
from markov_baseline import load_and_label

IS_END     = "2024-05-02"
K          = 3
N_RESTARTS = 15
FEATURE    = sys.argv[1] if len(sys.argv) > 1 else "logret"   # "logret" | "cum20"
NAMES      = ["Bull", "Neutral", "Bear"]          # by descending mean return
COLOURS    = {"Bull": "#2ECC71", "Neutral": "#F39C12", "Bear": "#E74C3C"}

THRESH = {
    "occ_min":      0.05,
    "vol_ratio":    2.0,
    "logL_spread":  0.02,    # F4: relative logL spread across restarts
    "kappa_min":    0.10,    # agrees above chance
    "kappa_max":    0.95,    # but not identical (adds info)
}


# ── Load ──────────────────────────────────────────────────────────────────────
def load():
    df = pd.read_parquet("data/parquet/daily/xauusd_daily.parquet")
    df = df[df.index <= IS_END]
    logret = np.log(df["close"] / df["close"].shift(1)).dropna()
    bclose, cum20, labels = load_and_label()       # 5%/20d baseline (Sideways = Neutral)

    if FEATURE == "cum20":
        # HMM sees the SAME directional observable the baseline thresholds.
        feat  = cum20
        close = bclose
    else:                                          # "logret": raw daily return (vol regimes)
        feat  = logret
        close = df.loc[logret.index, "close"]

    X = feat.values.reshape(-1, 1)
    return close, feat, X, labels


# ── Fit ─────────────────────────────────────────────────────────────────────
MIN_COVAR = 1e-8        # variance floor (F1) — sigma >= 1e-4, sane vs ret_std~0.0076


def get_sigma(model):
    """State std devs, robust to diag/full covars_ shape."""
    cov = np.asarray(model.covars_)
    var = cov.reshape(cov.shape[0], -1)[:, 0]
    return np.sqrt(var)


def fit_best(X):
    """Robust restarts: variance floor (F1), skip degenerate/non-finite fits (F2)."""
    best, best_score, scores, n_bad = None, -np.inf, [], 0
    for seed in tqdm(range(N_RESTARTS), desc=f"K={K} restarts"):
        try:
            m = GaussianHMM(n_components=K, covariance_type="diag",
                            n_iter=1000, tol=1e-6, min_covar=MIN_COVAR, random_state=seed)
            m.fit(X)
            s = m.score(X)
        except Exception as e:
            n_bad += 1
            tqdm.write(f"  restart {seed+1:2d}/{N_RESTARTS}  SKIPPED ({type(e).__name__})")
            continue
        sig = get_sigma(m)
        if not np.isfinite(s) or not np.isfinite(m.means_).all() or not np.isfinite(sig).all():
            n_bad += 1
            tqdm.write(f"  restart {seed+1:2d}/{N_RESTARTS}  SKIPPED (non-finite)")
            continue
        scores.append(s)
        tqdm.write(f"  restart {seed+1:2d}/{N_RESTARTS}  logL={s:.2f}  conv={m.monitor_.converged}")
        if s > best_score:
            best_score, best = s, m
    if best is None:
        raise RuntimeError("All restarts failed — model degenerate on this feature.")
    spread = (max(scores) - min(scores)) / abs(np.mean(scores))
    print(f"  ({len(scores)}/{N_RESTARTS} valid restarts, {n_bad} skipped)")
    return best, spread


def order_by_mean(model):
    """Map raw state idx -> name, highest mean return = Bull."""
    mus   = model.means_[:, 0]
    order = np.argsort(mus)[::-1]                   # descending
    return {order[i]: NAMES[i] for i in range(K)}


# ── Manual forward filtering (real-time, F5) + forecast pseudo-residuals ───────
def emission_logprob(model, X):
    mu  = model.means_[:, 0]
    sig = get_sigma(model)
    return np.column_stack([norm.logpdf(X[:, 0], mu[k], sig[k]) for k in range(K)]), mu, sig


def forward_filter(model, X):
    """Return alpha[t,k] = P(S_t=k | r_1..t), normalised (filtered, not smoothed)."""
    logB, _, _ = emission_logprob(model, X)
    B = np.exp(logB - logB.max(axis=1, keepdims=True))    # scaled emissions
    T = len(X)
    alpha = np.zeros((T, K))
    a = model.startprob_ * B[0]
    alpha[0] = a / a.sum()
    for t in range(1, T):
        a = (alpha[t - 1] @ model.transmat_) * B[t]
        alpha[t] = a / a.sum()
    return alpha


def forecast_pseudo_residuals(model, X, alpha):
    """One-step-ahead PIT residuals. Predict S_{t} from r_1..t-1, then PIT r_t."""
    mu  = model.means_[:, 0]
    sig = get_sigma(model)
    T   = len(X)
    pred = np.zeros((T, K))
    pred[0] = model.startprob_
    pred[1:] = alpha[:-1] @ model.transmat_              # P(S_t | r_1..t-1)
    U = np.zeros(T)
    for k in range(K):
        U += pred[:, k] * norm.cdf(X[:, 0], mu[k], sig[k])
    U = np.clip(U, 1e-6, 1 - 1e-6)
    return norm.ppf(U)


def ljung_box(z, m=10):
    """Manual Ljung-Box Q on z. Returns (Q, dof). Large Q => autocorrelation."""
    z = z - z.mean()
    n = len(z)
    denom = np.sum(z ** 2)
    Q = 0.0
    for k in range(1, m + 1):
        rho = np.sum(z[k:] * z[:-k]) / denom
        Q += rho ** 2 / (n - k)
    return n * (n + 2) * Q, m


# ── Accuracy vs baseline ──────────────────────────────────────────────────────
def cohens_kappa(conf):
    N  = conf.sum()
    po = np.trace(conf) / N
    pe = (conf.sum(0) * conf.sum(1)).sum() / N ** 2
    return (po - pe) / (1 - pe) if pe < 1 else 0.0


def compare_to_baseline(close, alpha, state_names, labels):
    """Filtered most-likely HMM regime vs 5%/20d label, on common dates."""
    filt = pd.Series([state_names[k] for k in alpha.argmax(1)], index=close.index)
    base = labels.replace({"Sideways": "Neutral"})
    common = filt.index.intersection(base.index)
    h, b = filt.loc[common], base.loc[common]

    cats = NAMES
    conf = np.zeros((3, 3))
    for i, bi in enumerate(cats):
        for j, hj in enumerate(cats):
            conf[i, j] = ((b == bi) & (h == hj)).sum()
    agree = np.trace(conf) / conf.sum()
    return filt, conf, agree, cohens_kappa(conf), common


def plot(close, alpha, state_names):
    states = alpha.argmax(1)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=close.index, y=close.values, mode="lines",
                             line=dict(color="#aaaaaa", width=1), showlegend=False))
    for k, name in state_names.items():
        mask = states == k
        fig.add_trace(go.Scatter(x=close.index[mask], y=close.values[mask], mode="markers",
                                 marker=dict(color=COLOURS[name], size=4), name=name))
    fig.update_layout(title="HMM-001 Gate 4 — Gaussian HMM K=3, Filtered Regimes (IS)",
                      xaxis_title="Date", yaxis_title="Price (USD)",
                      template="plotly_dark", height=600)
    out = "research/outputs/hmm_gate4_regimes.html"
    fig.write_html(out)
    print(f"\nChart saved: {out}")


def main():
    close, feat, X, labels = load()
    n_obs = len(X)

    print("\n--- Sanity block ---")
    print(f"n_obs       : {n_obs}   IS: {feat.index[0].date()} -> {feat.index[-1].date()}")
    print(f"feat_std    : {feat.std():.5f}   K={K}  restarts={N_RESTARTS}")
    print(f"feature     : {FEATURE}  ({'20d cumulative return (directional)' if FEATURE=='cum20' else 'D1 log return (vol)'})\n")

    model, logL_spread = fit_best(X)
    state_names = order_by_mean(model)
    alpha = forward_filter(model, X)

    print("\n--- Fitted regimes (sorted by mean return) ---")
    mu, sig = model.means_[:, 0], get_sigma(model)
    states_seq = alpha.argmax(1)
    for k in range(K):
        occ = (states_seq == k).mean() * 100
        dur = 1 / (1 - model.transmat_[k, k])
        print(f"  {state_names[k]:8s} mu={mu[k]:+.5f}  sigma={sig[k]:.5f}  "
              f"occ={occ:4.1f}%  A_jj={model.transmat_[k,k]:.3f}  dur={dur:4.1f}d  "
              f"P(change)={1-model.transmat_[k,k]:.3f}")

    if FEATURE == "cum20":   # data-driven buckets vs the human +/-5% cut
        print("\n  Data-driven cum20 range per state (vs human +/-5% threshold):")
        for k in range(K):
            vals = feat.values[states_seq == k]
            if len(vals):
                print(f"    {state_names[k]:8s} cum20 in [{vals.min():+.1%}, {vals.max():+.1%}]  "
                      f"mean={vals.mean():+.1%}")

    # accuracy vs baseline
    filt, conf, agree, kappa, common = compare_to_baseline(close, alpha, state_names, labels)
    print(f"\n--- Accuracy vs 5%/20d baseline ({len(common)} common days) ---")
    print(f"  confusion (rows=baseline, cols=HMM)  order={NAMES}")
    for i, name in enumerate(NAMES):
        print(f"  {name:8s} " + " ".join(f"{int(conf[i,j]):5d}" for j in range(3)))
    print(f"  agreement = {agree:.1%}   Cohen's kappa = {kappa:.3f}")

    # calibration
    Z = forecast_pseudo_residuals(model, X, alpha)
    jb_stat, jb_p = jarque_bera(Z)
    lb_q, lb_m = ljung_box(Z, m=10)
    print(f"\n--- Calibration (one-step forecast pseudo-residuals Z_t) ---")
    print(f"  Z mean={Z.mean():+.3f} std={Z.std():.3f}  (target ~ N(0,1))")
    print(f"  Jarque-Bera = {jb_stat:.1f} (p={jb_p:.2e})  -> {'NORMAL' if jb_p>0.05 else 'NON-NORMAL'}")
    print(f"  Ljung-Box Q({lb_m}) = {lb_q:.1f}  (chi2_0.05={18.31})  -> "
          f"{'INDEP' if lb_q<18.31 else 'AUTOCORR'}")

    # ── checks ────────────────────────────────────────────────────────────────
    occ_vals = [(alpha.argmax(1) == k).mean() for k in range(K)]
    checks = {
        "converged":   (bool(model.monitor_.converged), str(model.monitor_.converged), "True"),
        "occupancy":   (min(occ_vals) >= THRESH["occ_min"],
                        f"min={min(occ_vals):.3f}", f">= {THRESH['occ_min']}"),
        "vol_ratio":   (sig.max()/sig.min() >= THRESH["vol_ratio"],
                        f"{sig.max()/sig.min():.2f}", f">= {THRESH['vol_ratio']}"),
        "restart_stab":(logL_spread < THRESH["logL_spread"],
                        f"spread={logL_spread:.4f}", f"< {THRESH['logL_spread']}"),
        "adds_info":   (THRESH["kappa_min"] < kappa < THRESH["kappa_max"],
                        f"kappa={kappa:.3f}", f"in ({THRESH['kappa_min']},{THRESH['kappa_max']})"),
    }
    calibrated = jb_p > 0.05 and lb_q < 18.31

    print("\n--- Gate 4 checks ---")
    for name, (passed, val, crit) in checks.items():
        print(f"  [{'PASS' if passed else 'FAIL'}] {name:13s} {val}  (need: {crit})")
    print(f"  [{'PASS' if calibrated else 'WARN'}] calibration   JB_p={jb_p:.2e} LB_Q={lb_q:.1f}  "
          f"(diagnostic -> NIG if fail)")

    model_sane = all(c[0] for c in checks.values())

    plot(close, alpha, state_names)

    # ── DB logging ────────────────────────────────────────────────────────────
    git_sha = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).decode().strip()
    params = json.dumps({"K": K, "restarts": N_RESTARTS, "emission": "gaussian",
                         "feature": FEATURE, "states": "filtered",
                         "covariance_type": "diag", "min_covar": MIN_COVAR})
    check_notes = " | ".join(f"{n}={'P' if p else 'F'}({v})" for n, (p, v, _) in checks.items())
    calib_notes = f"JB={jb_stat:.0f}(p={jb_p:.1e}) LB_Q={lb_q:.1f} calibrated={calibrated}"

    g4 = [g for g in get_gates("HMM-001") if g["gate_number"] == 4]
    attempt = max((g["attempt"] for g in g4), default=0) + 1
    open_gate("HMM-001", 4,
              pass_criteria="HMM sane (converge+occ+vol+stability) AND 0.1<kappa<0.95 (confirms+adds info)",
              attempt=attempt)

    common_kw = dict(idea_id="HMM-001", gate_number=4, stage="IS", period="daily",
                     n_obs=n_obs, n_trials=N_RESTARTS, data_start=str(feat.index[0].date()),
                     data_end=str(feat.index[-1].date()), git_sha=git_sha,
                     code_path="research/models/hmm/gate4_hmm.py", parameters=params)
    rid_k = log_result(**common_kw, metric_key="regime_agreement_kappa",
                       metric_value=float(kappa), cost_adjusted=0,
                       notes=f"agree={agree:.3f} | {check_notes}")
    rid_c = log_result(**common_kw, metric_key="forecast_calibration_jb_p",
                       metric_value=float(jb_p), cost_adjusted=0, notes=calib_notes)

    answer = (f"HMM K=3 | agree={agree:.1%} kappa={kappa:.3f} | "
              f"vol_ratio={sig.max()/sig.min():.2f} | {calib_notes}")
    if model_sane and THRESH["kappa_min"] < kappa < THRESH["kappa_max"]:
        pass_gate("HMM-001", 4, gate_answer=answer, answered_by="agent", attempt=attempt)
        print(f"\n>>> GATE 4: PASS (attempt {attempt}) — kappa {rid_k} / calib {rid_c}")
    else:
        block_gate("HMM-001", 4, gate_answer=answer, answered_by="agent", attempt=attempt)
        print(f"\n>>> GATE 4: BLOCKED (attempt {attempt}) — kappa {rid_k} / calib {rid_c}")

    if not calibrated:
        print("    NOTE: Gaussian pseudo-residuals fail -> P(regime change) miscalibrated. "
              "Escalate to NIG emissions (Gate 0 fat-tail delta).")
    print("Done.")


if __name__ == "__main__":
    main()
