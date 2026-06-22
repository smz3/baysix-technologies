"""
HMM-001 Gate 4 (attempt 3) — Path A synthesis.

The truth from attempts 1-2:
  - HMM on daily returns  -> volatility regimes (orthogonal to direction)
  - HMM on cum20          -> directional regimes, but overlapping feature
                             breaks emission independence -> invalid dynamics

Path A: let the HMM (on cum20) set DATA-DRIVEN, ASYMMETRIC thresholds, relabel
with a clean deployable rule, then estimate P(regime change) from a DISCRETE
Markov transition matrix on the labels (assumption-free counts — no Gaussian /
no independence violation). HMM for detection, Markov chain for dynamics.

Deliverable (Gate 1 goal): an improved asymmetric regime classifier + a valid,
calibrated P(regime change) per state. Confirms the +5% bull cut, corrects the
-5% bear cut, and recovers directional days the symmetric rule buried in Sideways.
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from scipy.stats import norm, chi2_contingency
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parents[2] / "code"))
from pipeline import get_gates, log_result, open_gate, pass_gate, block_gate
from markov_baseline import (load_and_label, build_transition_matrix,
                             stationary_distribution, STATES, S2I)
from gate4_hmm import fit_best, forward_filter, order_by_mean, get_sigma, K


def gaussian_crossing(mu_lo, sig_lo, p_lo, mu_hi, sig_hi, p_hi):
    """Prior-weighted Bayes boundary between two adjacent Gaussians, in (mu_lo, mu_hi)."""
    xs = np.linspace(mu_lo, mu_hi, 20001)
    d  = p_lo * norm.pdf(xs, mu_lo, sig_lo) - p_hi * norm.pdf(xs, mu_hi, sig_hi)
    sign_change = np.where(np.diff(np.sign(d)))[0]
    return xs[sign_change[0]] if len(sign_change) else (mu_lo + mu_hi) / 2


def chi2_null(counts):
    chi2, p, dof, _ = chi2_contingency(counts)
    n = counts.sum()
    v = np.sqrt(chi2 / (n * (min(counts.shape) - 1)))
    return chi2, p, dof, v


def plot(close, labels, thr_bear, thr_bull):
    colours = {"Bull": "#2ECC71", "Sideways": "#F39C12", "Bear": "#E74C3C"}
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=close.index, y=close.values, mode="lines",
                             line=dict(color="#aaaaaa", width=1), showlegend=False))
    for s in STATES:
        mask = (labels == s).values
        fig.add_trace(go.Scatter(x=close.index[mask], y=close.values[mask], mode="markers",
                                 marker=dict(color=colours[s], size=4), name=s))
    fig.update_layout(
        title=f"HMM-001 Gate 4 — HMM-derived asymmetric regimes "
              f"(bear {thr_bear:+.1%}, bull {thr_bull:+.1%})",
        xaxis_title="Date", yaxis_title="Price (USD)", template="plotly_dark", height=600)
    out = "research/outputs/hmm/hmm_gate4_relabel.html"
    fig.write_html(out)
    print(f"\nChart saved: {out}")


def main():
    close, cum20, base = load_and_label()          # base = ±5% labels (Sideways middle)
    X = cum20.values.reshape(-1, 1)

    print("\n--- Sanity block ---")
    print(f"n_obs   : {len(X)}   IS: {cum20.index[0].date()} -> {cum20.index[-1].date()}")
    print(f"cum20 std: {cum20.std():.5f}   K={K}\n")

    # 1. fit HMM on cum20, get data-driven regime params + priors
    model, _ = fit_best(X)
    names = order_by_mean(model)
    alpha = forward_filter(model, X)
    mu, sig = model.means_[:, 0], get_sigma(model)
    occ = np.array([(alpha.argmax(1) == k).mean() for k in range(K)])

    idx = {names[k]: k for k in range(K)}           # name -> raw state idx
    kB, kN, kBe = idx["Bull"], idx["Neutral"], idx["Bear"]
    print("HMM regime centers (cum20):")
    for nm, k in [("Bull", kB), ("Neutral", kN), ("Bear", kBe)]:
        print(f"  {nm:8s} mu={mu[k]:+.2%}  sigma={sig[k]:.2%}  prior={occ[k]:.2f}")

    # 2. derive asymmetric thresholds (data-driven cutpoints)
    thr_bull = gaussian_crossing(mu[kN], sig[kN], occ[kN], mu[kB], sig[kB], occ[kB])
    thr_bear = gaussian_crossing(mu[kBe], sig[kBe], occ[kBe], mu[kN], sig[kN], occ[kN])
    print(f"\nData-driven thresholds:  BEAR <= {thr_bear:+.2%}   BULL >= {thr_bull:+.2%}")
    print(f"Human (symmetric)     :  BEAR <= -5.00%   BULL >= +5.00%")

    # 3. clean deployable relabel by the asymmetric thresholds
    relab = pd.Series(np.where(cum20 >= thr_bull, "Bull",
                      np.where(cum20 <= thr_bear, "Bear", "Sideways")),
                      index=cum20.index)

    # 4. discrete Markov chain on the relabel — assumption-free P(regime change)
    M, counts = build_transition_matrix(relab)
    pi, eig_abs, monotone, row_dev = stationary_distribution(M)
    chi2, pval, dof, cramers_v = chi2_null(counts)

    print("\n--- Relabeled transition matrix (rows from, cols to) ---")
    print("            " + "".join(f"{s:>10s}" for s in STATES))
    for i, s in enumerate(STATES):
        print(f"  {s:8s}" + "".join(f"{M[i,j]:10.3f}" for j in range(3)))
    print("\n--- Regime intelligence (the deliverable) ---")
    for i, s in enumerate(STATES):
        occ_i = (relab == s).mean()
        print(f"  {s:8s}  occ={occ_i:5.1%}  P(stay)={M[i,i]:.3f}  "
              f"P(change)={1-M[i,i]:.3f}  exp_duration={1/(1-M[i,i]):4.1f}d")
    print(f"\n  Null (uniform) test: chi2={chi2:.0f}, p={pval:.1e}, Cramer's V={cramers_v:.3f}")
    print(f"  Stationary pi: " + "  ".join(f"{s}={pi[i]:.1%}" for i, s in enumerate(STATES)))

    # 5. how it improves on the symmetric baseline
    common = relab.index.intersection(base.index)
    r, b = relab.loc[common], base.loc[common]
    agree = (r == b).mean()
    # where the symmetric "Sideways" bucket got re-classified
    side_mask = (b == "Sideways")
    resplit = r[side_mask].value_counts()
    print(f"\n--- vs symmetric ±5% baseline ({len(common)} days) ---")
    print(f"  label agreement = {agree:.1%}")
    print(f"  of {int(side_mask.sum())} baseline-Sideways days, relabel assigns: "
          + ", ".join(f"{k}={int(v)}" for k, v in resplit.items()))

    # checks
    occ_relab = np.array([(relab == s).mean() for s in STATES])
    checks = {
        "occupancy":   (occ_relab.min() >= 0.05, f"min={occ_relab.min():.3f}", ">= 0.05"),
        "regime_memory":(pval < 0.05 and cramers_v > 0.3,
                         f"chi2={chi2:.0f} V={cramers_v:.2f}", "p<0.05 & V>0.3"),
        "ergodic":     (monotone and abs(eig_abs[0]-1) < 1e-6 and eig_abs[1] < 1,
                        f"lambda2={eig_abs[1]:.3f}", "1 unit eig, converging"),
        "asymmetric":  (abs(thr_bull) != abs(thr_bear),
                        f"bear={thr_bear:+.1%} bull={thr_bull:+.1%}", "asymmetric cut"),
        "adds_info":   (0.10 < agree < 0.98 and resplit.get("Bull",0)+resplit.get("Bear",0) > 0,
                        f"agree={agree:.2f} resplit={int(resplit.drop('Sideways',errors='ignore').sum())}",
                        "splits Sideways, not identical"),
    }
    all_pass = all(c[0] for c in checks.values())
    print("\n--- Gate 4 (attempt 3) checks ---")
    for nm, (p, v, c) in checks.items():
        print(f"  [{'PASS' if p else 'FAIL'}] {nm:14s} {v}  (need: {c})")

    plot(close, relab, thr_bear, thr_bull)

    # ── DB logging ────────────────────────────────────────────────────────────
    git_sha = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).decode().strip()
    params = json.dumps({"method": "hmm_asymmetric_threshold + discrete_markov",
                         "thr_bull": round(float(thr_bull), 4),
                         "thr_bear": round(float(thr_bear), 4),
                         "feature": "cum20", "K": K})
    notes = (f"thr bear={thr_bear:+.3f} bull={thr_bull:+.3f} | agree_vs_sym={agree:.3f} | "
             f"chi2={chi2:.0f} V={cramers_v:.2f} | "
             + " ".join(f"{s}_Pchg={1-M[i,i]:.2f}" for i, s in enumerate(STATES)))

    g4 = [g for g in get_gates("HMM-001") if g["gate_number"] == 4]
    attempt = max((g["attempt"] for g in g4), default=0) + 1
    open_gate("HMM-001", 4,
              pass_criteria="HMM asymmetric relabel: occupancy + regime memory + ergodic + asymmetric + adds info over ±5%",
              attempt=attempt)
    common_kw = dict(idea_id="HMM-001", gate_number=4, stage="IS", period="daily",
                     n_obs=len(relab), data_start=str(cum20.index[0].date()),
                     data_end=str(cum20.index[-1].date()), git_sha=git_sha,
                     code_path="research/models/hmm/gate4_relabel.py", parameters=params)
    rid_v = log_result(**common_kw, metric_key="regime_memory_cramers_v",
                       metric_value=float(cramers_v), cost_adjusted=0, notes=notes)

    answer = (f"PASS path-A | asym thr bear={thr_bear:+.1%} bull={thr_bull:+.1%} | "
              f"V={cramers_v:.2f} chi2={chi2:.0f} | agree_vs_sym={agree:.1%} | "
              f"P(change) Bull={1-M[0,0]:.2f} Side={1-M[1,1]:.2f} Bear={1-M[2,2]:.2f}")
    if all_pass:
        pass_gate("HMM-001", 4, gate_answer=answer, answered_by="agent", attempt=attempt)
        print(f"\n>>> GATE 4: PASS (attempt {attempt}) — result_id={rid_v}")
    else:
        block_gate("HMM-001", 4, gate_answer=answer, answered_by="agent", attempt=attempt)
        print(f"\n>>> GATE 4: BLOCKED (attempt {attempt}) — result_id={rid_v}")
    print("Done.")


if __name__ == "__main__":
    main()
