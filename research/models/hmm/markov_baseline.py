"""
HMM-001 Gate 2 — Rule-based 5%/20-day Markov chain on XAUUSD D1.

This is the SIMPLEST implementation (Steps 1-7 of the Hedge Fund Method):
label states by a fixed 5% threshold on the 20-day cumulative return,
count transitions into a 3x3 matrix, verify the chain is sane.

The 5% threshold is FIXED here by design — Gate 4's HMM is what
cross-examines it (Step 10). No HMM in this file.

4 objective sanity checks (rule-based, see braindump/research_protocol.md Gate 2):
  1. State occupancy   — every state >= 30 observations (estimability floor)
  2. Stochastic matrix — every populated row of M sums to 1.0
  3. Ergodicity        — one eigenvalue ~1, all others |lambda|<1, row_dev monotone down
  4. Persistence       — A_jj > pi_j for every state (inertia beats chance)

Self-contained: opens Gate 2 (attempt 2), logs result, passes/blocks in research.db.
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from research.code.arctic_io import daily_bars
import plotly.graph_objects as go
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parents[2] / "code"))
from pipeline import get_gates, log_result, open_gate, pass_gate, block_gate

# ── Config ───────────────────────────────────────────────────────────────────
IS_END     = "2024-05-02"
LOOKBACK   = 20           # Step 1: 20-day window
THRESHOLD  = 0.05         # Step 1: +/-5% cumulative return
FORECAST_N = 28           # Step 7: stationary distribution horizon

STATES   = ["Bull", "Sideways", "Bear"]     # matrix row/col order (Step 4)
S2I      = {s: i for i, s in enumerate(STATES)}
COLOURS  = {"Bull": "#2ECC71", "Sideways": "#F39C12", "Bear": "#E74C3C"}

THRESHOLDS = {
    "min_obs":     30,        # estimability floor per state
    "row_tol":     1e-9,
    "eig_tol":     1e-6,      # |lambda - 1| tolerance for the unit eigenvalue
}


# ── Steps 1-2: load, return, label ────────────────────────────────────────────
def load_and_label():
    df = daily_bars()
    df = df[df.index <= IS_END]

    daily_ret = df["close"].pct_change()                 # R_i, daily % return
    cum20     = daily_ret.rolling(LOOKBACK).sum()         # Step 1: sum of last 20 R_i
    cum20     = cum20.dropna()                            # valid from day 20 (Step 2)

    labels = pd.Series(
        np.where(cum20 >= THRESHOLD, "Bull",
        np.where(cum20 <= -THRESHOLD, "Bear", "Sideways")),
        index=cum20.index,
    )
    close = df.loc[labels.index, "close"]
    return close, cum20, labels


# ── Step 4: transition matrix ─────────────────────────────────────────────────
def build_transition_matrix(labels: pd.Series) -> np.ndarray:
    """Count consecutive-day transitions into a row-normalised 3x3 matrix."""
    counts = np.zeros((3, 3))
    seq = labels.values
    for a, b in tqdm(zip(seq[:-1], seq[1:]), total=len(seq) - 1,
                     desc="counting transitions"):
        counts[S2I[a], S2I[b]] += 1
    row_sums = counts.sum(axis=1, keepdims=True)
    M = np.divide(counts, row_sums, out=np.zeros_like(counts),
                  where=row_sums != 0)
    return M, counts


# ── Step 7: stationary distribution + convergence ─────────────────────────────
def stationary_distribution(M: np.ndarray):
    """Return (pi, eigvals_abs_sorted, row_dev_monotone, row_dev_final).

    pi from the left eigenvector with eigenvalue 1. Ergodicity is judged by
    the eigenvalue spectrum (one unit eigenvalue, rest inside the unit circle)
    and by M^n row-deviation from pi decreasing monotonically.
    """
    vals, vecs = np.linalg.eig(M.T)
    idx = np.argmin(np.abs(vals - 1.0))
    pi  = np.real(vecs[:, idx])
    pi  = pi / pi.sum()

    eig_abs = np.sort(np.abs(vals))[::-1]          # descending |lambda|

    Mn       = M.copy()
    prev_dev = np.abs(Mn - pi).max()
    monotone = True
    for _ in range(2, FORECAST_N + 1):
        Mn  = Mn @ M
        dev = np.abs(Mn - pi).max()
        if dev > prev_dev + 1e-12:                 # allow float noise
            monotone = False
        prev_dev = dev

    return pi, eig_abs, monotone, prev_dev


# ── Sanity checks ──────────────────────────────────────────────────────────────
def run_checks(labels, M, pi, eig_abs, monotone) -> dict:
    """Returns dict check_name -> (passed, value_str, criterion_str)."""
    checks = {}

    counts    = labels.value_counts()
    obs_vals  = {s: int(counts.get(s, 0)) for s in STATES}
    obs_min   = min(obs_vals.values())
    occ_pass  = obs_min >= THRESHOLDS["min_obs"]
    checks["occupancy"] = (
        occ_pass,
        " ".join(f"{s[:4]}={obs_vals[s]}" for s in STATES),
        f"all >= {THRESHOLDS['min_obs']} obs",
    )

    populated  = np.array([obs_vals[s] > 0 for s in STATES])
    row_sums   = M.sum(axis=1)
    row_err    = np.abs(row_sums[populated] - 1.0).max()
    row_pass   = row_err <= THRESHOLDS["row_tol"]
    checks["stochastic_matrix"] = (
        bool(row_pass), f"max_row_err={row_err:.2e}",
        f"<= {THRESHOLDS['row_tol']:.0e}",
    )

    # Ergodicity: exactly one unit eigenvalue, all others strictly inside circle
    n_unit     = int(np.sum(np.abs(eig_abs - 1.0) <= THRESHOLDS["eig_tol"]))
    lambda2    = eig_abs[1] if len(eig_abs) > 1 else 0.0
    ergo_pass  = (n_unit == 1) and (lambda2 < 1.0 - THRESHOLDS["eig_tol"]) and monotone
    checks["ergodicity"] = (
        bool(ergo_pass),
        f"n_unit_eig={n_unit}  lambda2={lambda2:.3f}  row_dev_monotone={monotone}",
        "1 unit eig, |lambda2|<1, M^n converging",
    )

    diag       = np.array([M[i, i] for i in range(3)])
    ratios     = {s: diag[i] / pi[i] for i, s in enumerate(STATES) if populated[i]}
    inertia_ok = all(diag[i] > pi[i] for i in range(3) if populated[i])
    checks["persistence"] = (
        bool(inertia_ok),
        " ".join(f"{s[:4]}={ratios[s]:.1f}x" for s in ratios),
        "A_jj > pi_j for all (inertia > chance)",
    )

    return checks


# ── Plot ────────────────────────────────────────────────────────────────────
def plot(close: pd.Series, labels: pd.Series):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=close.index, y=close.values, mode="lines",
                             line=dict(color="#aaaaaa", width=1),
                             name="Close", showlegend=False))
    for s in STATES:
        mask = (labels == s).values
        fig.add_trace(go.Scatter(x=close.index[mask], y=close.values[mask],
                                 mode="markers", marker=dict(color=COLOURS[s], size=4),
                                 name=s))
    fig.update_layout(
        title="XAUUSD D1 — 5%/20-day Rule-Based Markov States (IS)",
        xaxis_title="Date", yaxis_title="Price (USD)",
        template="plotly_dark", height=600)
    out = "research/outputs/hmm/hmm_gate2_markov_baseline.html"
    fig.write_html(out)
    print(f"\nChart saved: {out}")


# ── Main ────────────────────────────────────────────────────────────────────
def main():
    close, cum20, labels = load_and_label()
    n_obs = len(labels)

    print("\n--- Sanity block ---")
    print(f"n_obs        : {n_obs}")
    print(f"IS window    : {labels.index[0].date()} -> {labels.index[-1].date()}")
    print(f"lookback     : {LOOKBACK}d   threshold: +/-{THRESHOLD:.0%}")
    occ = labels.value_counts()
    print(f"raw counts   : " + "  ".join(f"{s}={occ.get(s,0)}" for s in STATES))

    M, counts = build_transition_matrix(labels)
    pi, eig_abs, monotone, row_dev = stationary_distribution(M)

    print("\n--- Transition matrix M (rows: from, cols: to) ---")
    print("              " + "".join(f"{s:>10s}" for s in STATES))
    for i, s in enumerate(STATES):
        print(f"  {s:10s}" + "".join(f"{M[i,j]:10.3f}" for j in range(3)))
    print(f"\nStationary pi : " + "  ".join(f"{s}={pi[i]:.3f}" for i, s in enumerate(STATES)))
    print(f"|eigenvalues| : " + "  ".join(f"{v:.3f}" for v in eig_abs))
    print(f"M^n row_dev at n={FORECAST_N}: {row_dev:.2e}  (monotone decreasing: {monotone})")

    checks   = run_checks(labels, M, pi, eig_abs, monotone)
    all_pass = all(c[0] for c in checks.values())

    print("\n--- Gate 2 objective checks (rule-based) ---")
    for name, (passed, value, criterion) in checks.items():
        flag = "PASS" if passed else "FAIL"
        print(f"  [{flag}] {name:18s}  {value}  (need: {criterion})")

    plot(close, labels)

    # ── DB logging ────────────────────────────────────────────────────────────
    git_sha = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).decode().strip()
    params_json = json.dumps({
        "lookback": LOOKBACK, "threshold": THRESHOLD,
        "states": STATES, "feature": "20d_cumulative_return",
        "implementation": "rule_based_markov_chain",
    })
    check_notes = " | ".join(
        f"{n}={'PASS' if p else 'FAIL'}({v})" for n, (p, v, _) in checks.items()
    )

    gate2_rows = [g for g in get_gates("HMM-001") if g["gate_number"] == 2]
    attempt = max((g["attempt"] for g in gate2_rows), default=0) + 1

    open_gate("HMM-001", 2,
              pass_criteria="occupancy>=5% + rows sum to 1 + M^n converges by n<=28 + all A_jj>0.85",
              attempt=attempt)

    result_id = log_result(
        idea_id="HMM-001", gate_number=2, stage="IS",
        metric_key="foundation_check",
        metric_value=1.0 if all_pass else 0.0,
        cost_adjusted=0, period="daily", n_obs=n_obs,
        data_start=str(labels.index[0].date()),
        data_end=str(labels.index[-1].date()),
        git_sha=git_sha,
        code_path="research/models/hmm/markov_baseline.py",
        parameters=params_json,
        notes=check_notes,
    )

    gate_answer = f"{'PASS' if all_pass else 'FAIL'} | rule-based 5%/20d Markov | {check_notes}"
    if all_pass:
        pass_gate("HMM-001", 2, gate_answer=gate_answer, answered_by="agent", attempt=attempt)
        print(f"\n>>> GATE 2: PASS (attempt {attempt}) — logged (result_id={result_id})")
    else:
        block_gate("HMM-001", 2, gate_answer=gate_answer, answered_by="agent", attempt=attempt)
        print(f"\n>>> GATE 2: BLOCKED (attempt {attempt}) — logged (result_id={result_id})")
        print("    Fix whichever checks failed, increment attempt, re-run.")

    print("Done.")


if __name__ == "__main__":
    main()
