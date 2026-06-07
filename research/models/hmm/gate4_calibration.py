"""
HMM-001 Gate 4 — Is the regime-change PROBABILITY actually accurate?

Stays at Gate 4. Tests the one thing we never validated: does the HMM's
time-varying P(regime change tomorrow) mean what it says, and does it beat
simpler forecasters?

Regime definition (FIXED, choice A): asymmetric threshold rule on cum20 from
Gate 4 attempt 3 (result_id=10): Bull >= +2.92%, Bear <= -1.11%, else Sideways.
Ground-truth event o_t = 1 if the label changes from day t to t+1 (an observable
function of realised price). Threshold generalisation is Gate 6's job.

THREE forecasters race, each producing p_t = P(change at t+1 | data <= t),
scored ONLY on a held-out test window (no leakage):
  - Climatology   : expanding base rate of changes (the floor)
  - Discrete MC   : 1 - A_jj, transition matrix rebuilt from labels <= t (strong baseline)
  - HMM filtered  : 1 - sum_k P(S_t=k|data<=t) A_kk  (the time-varying contender)
                    HMM params frozen on train; forward-filtering is causal.

Accuracy = calibration (reliability diagram, Brier reliability term, Spiegelhalter Z)
         + discrimination (ROC-AUC, Brier Skill Score vs climatology, log-loss)
         + timeliness (early-warning: P(change) before vs away from true shifts).
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from scipy.stats import rankdata, ttest_ind
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parents[2] / "code"))
from pipeline import log_result
from markov_baseline import load_and_label, S2I
from gate4_hmm import fit_best, forward_filter, get_sigma, K

# regime definition (fixed) + no-leakage layout:
#   HMM params fit on [start .. HMM_TRAIN_END]
#   scored on [TEST_START .. end]                              <- held out from HMM
# Two recalibrations compared, both causal:
#   fixed    : isotonic fit once on (HMM_TRAIN_END .. TEST_START]  (the 2021 fold)
#   adaptive : isotonic refit each test day on the trailing CALIB_W days (rolling)
THR_BULL       = 0.0292
THR_BEAR       = -0.0111
HMM_TRAIN_END  = "2020-12-31"
TEST_START     = "2022-01-01"
CALIB_W        = 252            # rolling calibration window (~1 trading year)
EPS            = 1e-6


# ── scoring metrics ───────────────────────────────────────────────────────────
def brier(p, o):
    return np.mean((p - o) ** 2)


def logloss(p, o):
    p = np.clip(p, EPS, 1 - EPS)
    return -np.mean(o * np.log(p) + (1 - o) * np.log(1 - p))


def auc(p, o):
    """Mann-Whitney ROC-AUC = P(p|change > p|no-change)."""
    o = o.astype(bool)
    n1, n0 = o.sum(), (~o).sum()
    if n1 == 0 or n0 == 0:
        return np.nan
    r = rankdata(p)
    return (r[o].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


def spiegelhalter_z(p, o):
    """Calibration test. |Z|<1.96 => not significantly miscalibrated."""
    num = np.sum((o - p) * (1 - 2 * p))
    den = np.sqrt(np.sum((1 - 2 * p) ** 2 * p * (1 - p)))
    return num / den if den > 0 else np.nan


def brier_decomp(p, o, n_bins=10):
    """Murphy decomposition via quantile bins: Brier = REL - RES + UNC."""
    edges = np.unique(np.quantile(p, np.linspace(0, 1, n_bins + 1)))
    obar  = o.mean()
    N     = len(o)
    rel = res = 0.0
    table = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (p >= lo) & (p <= hi) if hi == edges[-1] else (p >= lo) & (p < hi)
        nb = m.sum()
        if nb == 0:
            continue
        pbar, ofreq = p[m].mean(), o[m].mean()
        rel += nb * (pbar - ofreq) ** 2
        res += nb * (ofreq - obar) ** 2
        table.append((pbar, ofreq, int(nb)))
    return rel / N, res / N, obar * (1 - obar), table


# ── isotonic recalibration (monotonic map, fit on TRAIN only) ─────────────────
def isotonic_fit(x, y):
    """Pool-adjacent-violators. Returns (ux, ufit): monotone map for np.interp."""
    order = np.argsort(x, kind="mergesort")
    xs, ys = x[order], y[order].astype(float)
    vals, ws, ns = [], [], []
    for yi in ys:
        v, w, n = yi, 1.0, 1
        while vals and vals[-1] >= v:
            pv, pw, pn = vals.pop(), ws.pop(), ns.pop()
            v = (pv * pw + v * w) / (pw + w); w += pw; n += pn
        vals.append(v); ws.append(w); ns.append(n)
    fitted = np.empty(len(ys)); pos = 0
    for v, n in zip(vals, ns):
        fitted[pos:pos + n] = v; pos += n
    ux, inv = np.unique(xs, return_inverse=True)        # collapse ties for interp
    ufit = np.zeros(len(ux)); cnt = np.zeros(len(ux))
    np.add.at(ufit, inv, fitted); np.add.at(cnt, inv, 1)
    return ux, ufit / cnt


def isotonic_predict(ux, ufit, xnew):
    return np.interp(xnew, ux, ufit)                    # clips at endpoints


def rolling_isotonic(p_full, o, test_idx, window):
    """Adaptive recalibration: for each test day t, refit isotonic on the trailing
    `window` days [t-window, t-1] (outcomes known by day t — causal)."""
    out = np.full(len(test_idx), np.nan)
    for j, t in enumerate(test_idx):
        lo = max(0, t - window)
        xs, ys = p_full[lo:t], o[lo:t]                  # strictly before t
        ux, ufit = isotonic_fit(xs, ys)
        out[j] = isotonic_predict(ux, ufit, p_full[t])
    return out


def platt_fit(x, y):
    """2-param logistic calibration sigmoid(a*x+b). Low variance — safe on small windows."""
    from scipy.optimize import minimize

    def nll(params):
        z = params[0] * x + params[1]
        return -np.mean(y * (-np.logaddexp(0, -z)) + (1 - y) * (-np.logaddexp(0, z)))

    res = minimize(nll, np.array([1.0, -2.0]), method="Nelder-Mead",
                   options={"xatol": 1e-4, "fatol": 1e-6, "maxiter": 2000})
    return res.x


def rolling_platt(p_full, o, test_idx, window):
    """Adaptive Platt: refit the 2-param logistic on the trailing window per test day."""
    out = np.full(len(test_idx), np.nan)
    for j, t in enumerate(test_idx):
        lo = max(0, t - window)
        a, b = platt_fit(p_full[lo:t], o[lo:t])
        z = a * p_full[t] + b
        out[j] = 1.0 / (1.0 + np.exp(-z))
    return out


def score(name, p, o, brier_ref=None):
    b   = brier(p, o)
    bss = (1 - b / brier_ref) if brier_ref else np.nan
    rel, res, unc, table = brier_decomp(p, o)
    return {"name": name, "brier": b, "bss": bss, "logloss": logloss(p, o),
            "auc": auc(p, o), "z": spiegelhalter_z(p, o),
            "rel": rel, "res": res, "unc": unc, "table": table}


# ── forecasters (walk-forward) ────────────────────────────────────────────────
def main():
    close, cum20, _ = load_and_label()
    labels = pd.Series(np.where(cum20 >= THR_BULL, "Bull",
                       np.where(cum20 <= THR_BEAR, "Bear", "Sideways")),
                       index=cum20.index)
    s = labels.map(S2I).values
    N = len(s)
    o = (s[1:] != s[:-1]).astype(float)               # o[t] = change t -> t+1, t in 0..N-2

    hmm_i  = int(np.searchsorted(cum20.index.values, np.datetime64(HMM_TRAIN_END))) + 1
    test_i = int(np.searchsorted(cum20.index.values, np.datetime64(TEST_START))) + 1
    print("\n--- Setup (rolling calibration) ---")
    print(f"n_obs={N}  thresholds: Bull>={THR_BULL:+.2%} Bear<={THR_BEAR:+.2%}")
    print(f"HMM train  : {cum20.index[0].date()} -> {HMM_TRAIN_END}  ({hmm_i} obs)")
    print(f"fixed calib: {cum20.index[hmm_i].date()} -> {TEST_START}  ({test_i-hmm_i} obs)")
    print(f"adaptive   : rolling isotonic, trailing {CALIB_W}d per test day")
    print(f"test (OOS) : {cum20.index[test_i].date()} -> {cum20.index[-1].date()}  "
          f"({N-1-test_i} obs, {int(o[test_i:].sum())} changes, rate {o[test_i:].mean():.1%})")

    # 1. HMM: fit on HMM-train slice only, freeze, causal filter over full series
    Xtr = cum20.values[:hmm_i].reshape(-1, 1)
    model, _ = fit_best(Xtr)
    alpha = forward_filter(model, cum20.values.reshape(-1, 1))
    Akk = np.diag(model.transmat_)
    p_hmm_full = 1 - alpha @ Akk                        # time-varying P(change), causal

    # 2. discrete MC + 3. climatology, expanding walk-forward
    p_mc_full   = np.full(N, np.nan)
    p_clim_full = np.full(N, np.nan)
    counts = np.zeros((3, 3))
    for t in tqdm(range(1, N - 1), desc="walk-forward MC/clim"):
        counts[s[t - 1], s[t]] += 1                     # transitions <= t
        row = counts[s[t]]
        p_mc_full[t]   = 1 - row[s[t]] / row.sum() if row.sum() > 0 else np.nan
        p_clim_full[t] = o[:t].mean()                   # changes strictly before t

    # fixed recalibration: isotonic fit once on the 2021 fold
    idx_cal  = np.arange(hmm_i, test_i)
    ux, ufit = isotonic_fit(p_hmm_full[idx_cal], o[idx_cal])

    # 3. score on the held-out test window (drop final index — no o for last day)
    idx = np.arange(test_i, N - 1)
    o_te    = o[idx]
    p_clim  = p_clim_full[idx]
    p_mc    = p_mc_full[idx]
    p_hmm   = p_hmm_full[idx]
    p_fixed = isotonic_predict(ux, ufit, p_hmm)              # fixed-fold isotonic
    p_iso   = rolling_isotonic(p_hmm_full, o, idx, CALIB_W)  # adaptive isotonic
    p_platt = rolling_platt(p_hmm_full, o, idx, CALIB_W)     # adaptive Platt (low variance)
    brier_ref = brier(p_clim, o_te)

    results = [score("Climatology",     p_clim,  o_te, brier_ref),
               score("DiscreteMC",      p_mc,    o_te, brier_ref),
               score("HMMfiltered",     p_hmm,   o_te, brier_ref),
               score("HMM+iso fixed",   p_fixed, o_te, brier_ref),
               score("HMM+iso adapt",   p_iso,   o_te, brier_ref),
               score("HMM+Platt adapt", p_platt, o_te, brier_ref)]

    print(f"\n--- Probabilistic accuracy (test n={len(o_te)}) ---")
    print(f"{'forecaster':14s}{'Brier':>9s}{'BSS':>8s}{'logloss':>9s}{'AUC':>7s}"
          f"{'Z(calib)':>10s}{'REL':>9s}{'RES':>9s}")
    for r in results:
        print(f"{r['name']:14s}{r['brier']:>9.4f}{r['bss']:>8.3f}{r['logloss']:>9.4f}"
              f"{r['auc']:>7.3f}{r['z']:>10.2f}{r['rel']:>9.5f}{r['res']:>9.5f}")
    print("  BSS>0 beats climatology | AUC>0.5 has skill | |Z|<1.96 calibrated"
          " | low REL=calibrated, high RES=informative")

    # reliability diagram — raw HMM vs adaptive Platt
    for r in (results[2], results[5]):
        print(f"\n--- Reliability ({r['name']}, quantile bins) ---")
        print(f"  {'pred_p':>8s}{'obs_freq':>10s}{'n':>7s}")
        for pbar, ofreq, nb in r["table"]:
            print(f"  {pbar:>8.3f}{ofreq:>10.3f}{nb:>7d}")

    # early-warning: HMM P(change) when a change is imminent vs not
    chg, nochg = p_hmm[o_te == 1], p_hmm[o_te == 0]
    tstat, pval = ttest_ind(chg, nochg, equal_var=False)
    print("\n--- Early warning (HMM filtered) ---")
    print(f"  mean P(change) | change next day  = {chg.mean():.3f}")
    print(f"  mean P(change) | quiet  next day  = {nochg.mean():.3f}")
    print(f"  Welch t={tstat:.2f} (p={pval:.1e})  -> "
          f"{'rises ahead of shifts' if (tstat>0 and pval<0.05) else 'no lead signal'}")

    plot(close, idx, cum20, results)

    # ── DB logging ────────────────────────────────────────────────────────────
    git_sha = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).decode().strip()
    raw, iso, cal = results[2], results[4], results[5]   # cal = adaptive Platt (best)
    params = json.dumps({"thr_bull": THR_BULL, "thr_bear": THR_BEAR,
                         "hmm_train_end": HMM_TRAIN_END, "test_start": TEST_START,
                         "calib_window": CALIB_W, "recalibration": "rolling_platt",
                         "forecasters": ["clim", "mc", "hmm", "iso_fixed", "iso_adapt", "platt_adapt"],
                         "test_n": len(o_te)})
    notes = (f"raw Z={raw['z']:.2f} | iso_adapt bss={iso['bss']:.3f} Z={iso['z']:.2f} | "
             f"platt_adapt bss={cal['bss']:.3f} Z={cal['z']:.2f} auc={cal['auc']:.3f} | "
             f"earlywarn t={tstat:.2f}")
    common_kw = dict(idea_id="HMM-001", gate_number=4, stage="walkforward", period="daily",
                     n_obs=len(o_te), data_start=str(cum20.index[idx[0]].date()),
                     data_end=str(cum20.index[idx[-1]].date()), git_sha=git_sha,
                     code_path="research/models/hmm/gate4_calibration.py", parameters=params)
    rid_a = log_result(**common_kw, metric_key="regime_change_brier_skill_platt",
                       metric_value=float(cal["bss"]), cost_adjusted=0, notes=notes)
    rid_b = log_result(**common_kw, metric_key="regime_change_calib_z_platt",
                       metric_value=float(cal["z"]), cost_adjusted=0, notes=notes)
    print(f"\nLogged: platt bss result_id={rid_a}, platt Z result_id={rid_b}")
    print("Done.")


def plot(close, idx, cum20, results):
    fig = go.Figure()
    for r, c in [(results[2], "#E74C3C"), (results[4], "#3498DB"),
                 (results[5], "#2ECC71"), (results[1], "#F39C12")]:
        pts = sorted(r["table"])
        fig.add_trace(go.Scatter(x=[t[0] for t in pts], y=[t[1] for t in pts],
                                 mode="lines+markers", name=r["name"], line=dict(color=c)))
    fig.add_trace(go.Scatter(x=[0, 0.3], y=[0, 0.3], mode="lines", name="perfect",
                             line=dict(color="#888888", dash="dash")))
    fig.update_layout(title="HMM-001 Gate 4 — Regime-change forecast reliability (test)",
                      xaxis_title="Predicted P(change)", yaxis_title="Observed frequency",
                      template="plotly_dark", height=550)
    out = "research/outputs/hmm/hmm_gate4_reliability.html"
    fig.write_html(out)
    print(f"Chart saved: {out}")


if __name__ == "__main__":
    main()
