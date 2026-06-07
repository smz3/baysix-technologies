"""
HMM-001 Gate 4 — LOOKBACK WINDOW SWEEP (the one unexamined assumption).

Every gate so far used a 20-day cumulative return — same arbitrary origin as the
±5% we spent four gates dismantling. This file cross-examines the window itself:
{10, 20, 40, 60} days, picking by OUT-OF-FOLD Brier / AUC on the held-out test.

Per window W (faithful to the existing Gate-4 pipeline, just parameterised):
  1. cumW = rolling W-day sum of daily returns (IS only, <= 2024-05-02).
  2. Derive ASYMMETRIC cuts the same way gate4_relabel did on 20d: fit a 3-state
     Gaussian HMM on cumW, take prior-weighted Bayes crossings (Neutral<->Bull =
     thr_bull, Bear<->Neutral = thr_bear). Report in sigma_W units so the window
     <-> threshold coupling is visible (collapses the 2-D grid to one knob).
  3. Relabel -> ground-truth event o_t = label changes from t to t+1.
  4. Race the same forecasters as gate4_calibration (climatology / discrete MC /
     HMM-filtered + adaptive Platt & isotonic recalibration), HMM fit on TRAIN only,
     causal forward-filter, scored ONLY on the held-out test window.

Fixed across windows for a fair comparison: HMM_TRAIN_END / TEST_START dates and
CALIB_W. Different W just shifts how many obs precede each date (larger W = fewer).

Run:  python research/models/hmm/gate4_window_sweep.py            # default 10,20
      python research/models/hmm/gate4_window_sweep.py 10,20,40,60
Stays at Gate 4. Logs one out-of-fold (Brier, AUC) result per window — every
window tested is a trial (deflation bookkeeping for the one-shot OOS).
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from scipy.stats import ttest_ind
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parents[2] / "code"))
from pipeline import log_result
from gate4_hmm import fit_best, forward_filter, order_by_mean, get_sigma, K
from gate4_relabel import gaussian_crossing
from gate4_calibration import (brier, logloss, auc, spiegelhalter_z, score,
                               isotonic_fit, isotonic_predict, rolling_isotonic,
                               rolling_platt)

IS_END        = "2024-05-02"
HMM_TRAIN_END = "2020-12-31"     # fixed across windows  -> fair comparison
TEST_START    = "2022-01-01"
CALIB_W       = 252              # rolling recalibration window (~1 trading year)
S2I           = {"Bull": 0, "Sideways": 1, "Bear": 2}


# ── load cumW (IS only) — mirrors markov_baseline.load_and_label but parameterised ──
def load_cumW(W):
    df  = pd.read_parquet("data/parquet/daily/xauusd_daily.parquet")
    df  = df[df.index <= IS_END]
    ret = df["close"].pct_change()
    cumW = ret.rolling(W).sum().dropna()
    return df.loc[cumW.index, "close"], cumW


# ── derive asymmetric cuts on full IS (defines the regime; same rule as gate4_relabel) ──
def derive_cuts(cumW):
    X = cumW.values.reshape(-1, 1)
    model, _ = fit_best(X)
    names = order_by_mean(model)
    alpha = forward_filter(model, X)
    mu, sig = model.means_[:, 0], get_sigma(model)
    occ = np.array([(alpha.argmax(1) == k).mean() for k in range(K)])
    idx = {names[k]: k for k in range(K)}
    kB, kN, kBe = idx["Bull"], idx["Neutral"], idx["Bear"]
    thr_bull = gaussian_crossing(mu[kN], sig[kN], occ[kN], mu[kB], sig[kB], occ[kB])
    thr_bear = gaussian_crossing(mu[kBe], sig[kBe], occ[kBe], mu[kN], sig[kN], occ[kN])
    return thr_bull, thr_bear, mu, sig, occ, (kB, kN, kBe)


# ── score one window: returns the forecaster table + headline diagnostics ─────────
def sweep_window(W):
    close, cumW = load_cumW(W)
    sigW = cumW.std()

    thr_bull, thr_bear, mu, sig, occ, (kB, kN, kBe) = derive_cuts(cumW)
    labels = pd.Series(np.where(cumW.values >= thr_bull, "Bull",
                       np.where(cumW.values <= thr_bear, "Bear", "Sideways")),
                       index=cumW.index)
    s = labels.map(S2I).values
    N = len(s)
    o = (s[1:] != s[:-1]).astype(float)            # o[t] = change t -> t+1

    hmm_i  = int(np.searchsorted(cumW.index.values, np.datetime64(HMM_TRAIN_END))) + 1
    test_i = int(np.searchsorted(cumW.index.values, np.datetime64(TEST_START))) + 1

    print(f"\n{'='*72}\n  WINDOW W = {W}d\n{'='*72}")
    print("--- Sanity block ---")
    print(f"  n_obs={N}  sigma_W={sigW:.4f}  IS {cumW.index[0].date()} -> {cumW.index[-1].date()}")
    print(f"  HMM centers (cum{W}): Bull mu={mu[kB]:+.2%} Neutral mu={mu[kN]:+.2%} Bear mu={mu[kBe]:+.2%}")
    print(f"  derived cuts: BULL >= {thr_bull:+.2%} ({thr_bull/sigW:+.2f}sigma) | "
          f"BEAR <= {thr_bear:+.2%} ({thr_bear/sigW:+.2f}sigma)")
    occ_lab = labels.value_counts(normalize=True)
    print(f"  label occ: " + " ".join(f"{k}={occ_lab.get(k,0):.1%}" for k in ['Bull','Sideways','Bear']))
    print(f"  splits: train {hmm_i} | calib {test_i-hmm_i} | test {N-1-test_i} "
          f"({int(o[test_i:].sum())} changes, rate {o[test_i:].mean():.1%})")
    if min(hmm_i, test_i - hmm_i, N - 1 - test_i) < 30:
        print("  !! WARNING: a split has < 30 obs — scores unreliable for this window")

    # forecaster HMM: fit on TRAIN slice only, freeze, causal filter over full series
    Xtr = cumW.values[:hmm_i].reshape(-1, 1)
    model, _ = fit_best(Xtr)
    alpha = forward_filter(model, cumW.values.reshape(-1, 1))
    Akk = np.diag(model.transmat_)
    p_hmm_full = 1 - alpha @ Akk                   # time-varying P(change), causal

    # discrete MC + climatology, expanding walk-forward
    p_mc_full   = np.full(N, np.nan)
    p_clim_full = np.full(N, np.nan)
    counts = np.zeros((3, 3))
    for t in tqdm(range(1, N - 1), desc=f"W={W} walk-forward MC/clim"):
        counts[s[t - 1], s[t]] += 1
        row = counts[s[t]]
        p_mc_full[t]   = 1 - row[s[t]] / row.sum() if row.sum() > 0 else np.nan
        p_clim_full[t] = o[:t].mean()

    idx_cal  = np.arange(hmm_i, test_i)
    ux, ufit = isotonic_fit(p_hmm_full[idx_cal], o[idx_cal])

    idx = np.arange(test_i, N - 1)
    o_te    = o[idx]
    p_clim  = p_clim_full[idx]
    p_mc    = p_mc_full[idx]
    p_hmm   = p_hmm_full[idx]
    p_fixed = isotonic_predict(ux, ufit, p_hmm)
    p_iso   = rolling_isotonic(p_hmm_full, o, idx, CALIB_W)
    p_platt = rolling_platt(p_hmm_full, o, idx, CALIB_W)
    brier_ref = brier(p_clim, o_te)

    results = [score("Climatology",     p_clim,  o_te, brier_ref),
               score("DiscreteMC",      p_mc,    o_te, brier_ref),
               score("HMMfiltered",     p_hmm,   o_te, brier_ref),
               score("HMM+iso fixed",   p_fixed, o_te, brier_ref),
               score("HMM+iso adapt",   p_iso,   o_te, brier_ref),
               score("HMM+Platt adapt", p_platt, o_te, brier_ref)]

    print(f"\n  --- Out-of-fold accuracy (test n={len(o_te)}) ---")
    print(f"  {'forecaster':16s}{'Brier':>9s}{'BSS':>8s}{'AUC':>7s}{'Z(calib)':>10s}")
    for r in results:
        print(f"  {r['name']:16s}{r['brier']:>9.4f}{r['bss']:>8.3f}{r['auc']:>7.3f}{r['z']:>10.2f}")

    # early warning (raw HMM)
    chg, nochg = p_hmm[o_te == 1], p_hmm[o_te == 0]
    tstat, _ = ttest_ind(chg, nochg, equal_var=False)

    raw, platt = results[2], results[5]
    return {"W": W, "sigW": float(sigW), "n_test": int(len(o_te)),
            "thr_bull": float(thr_bull), "thr_bear": float(thr_bear),
            "sig_bull": float(thr_bull / sigW), "sig_bear": float(thr_bear / sigW),
            "change_rate": float(o[test_i:].mean()),
            "hmm_auc": float(raw["auc"]), "hmm_brier": float(raw["brier"]),
            "platt_brier": float(platt["brier"]), "platt_bss": float(platt["bss"]),
            "platt_z": float(platt["z"]), "platt_auc": float(platt["auc"]),
            "earlywarn_t": float(tstat),
            "data_start": str(cumW.index[idx[0]].date()),
            "data_end": str(cumW.index[idx[-1]].date())}


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else "10,20"
    windows = [int(w) for w in arg.split(",")]
    print(f"\nLOOKBACK WINDOW SWEEP — windows={windows}  (20 = reference / known result)")

    rows = [sweep_window(W) for W in windows]

    # ── cross-window comparison ───────────────────────────────────────────────
    print(f"\n{'='*78}\n  CROSS-WINDOW COMPARISON (out-of-fold)\n{'='*78}")
    print(f"  {'W':>4s}{'sigma_W':>9s}{'bull(sig)':>14s}{'bear(sig)':>14s}"
          f"{'HMM_AUC':>9s}{'Platt_Br':>10s}{'Platt_BSS':>10s}{'Platt_Z':>9s}{'EW_t':>7s}")
    for r in rows:
        bull = f"{r['thr_bull']:+.1%}({r['sig_bull']:+.2f}s)"
        bear = f"{r['thr_bear']:+.1%}({r['sig_bear']:+.2f}s)"
        print(f"  {r['W']:>4d}{r['sigW']:>9.4f}{bull:>14s}{bear:>14s}"
              f"{r['hmm_auc']:>9.3f}{r['platt_brier']:>10.4f}"
              f"{r['platt_bss']:>10.3f}{r['platt_z']:>9.2f}{r['earlywarn_t']:>7.2f}")
    best_auc = max(rows, key=lambda r: r["hmm_auc"])
    best_bri = min(rows, key=lambda r: r["platt_brier"])
    print(f"\n  best discrimination (HMM AUC): W={best_auc['W']} (AUC={best_auc['hmm_auc']:.3f})")
    print(f"  best calibration  (Platt Brier): W={best_bri['W']} (Brier={best_bri['platt_brier']:.4f})")
    print("  NOTE: window NOT frozen yet — inspect, then decide. AUC = window's timing skill;"
          " Brier/Z fixable by recalibration layer.")

    plot(rows)

    # ── DB logging — one Brier + one AUC result per window (each = a trial) ────
    git_sha = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).decode().strip()
    for r in rows:
        params = json.dumps({"window": r["W"], "sigma_W": round(r["sigW"], 5),
                             "thr_bull": round(r["thr_bull"], 4), "thr_bear": round(r["thr_bear"], 4),
                             "thr_bull_sigma": round(r["sig_bull"], 3),
                             "thr_bear_sigma": round(r["sig_bear"], 3),
                             "hmm_train_end": HMM_TRAIN_END, "test_start": TEST_START,
                             "calib_window": CALIB_W, "cut_method": "gaussian_crossing",
                             "recalibration": "rolling_platt", "test_n": r["n_test"]})
        notes = (f"W={r['W']}d cut +{r['sig_bull']:.2f}s/{r['sig_bear']:.2f}s | "
                 f"HMM_AUC={r['hmm_auc']:.3f} | platt Brier={r['platt_brier']:.4f} "
                 f"BSS={r['platt_bss']:.3f} Z={r['platt_z']:.2f} | EW_t={r['earlywarn_t']:.2f}")
        common_kw = dict(idea_id="HMM-001", gate_number=4, stage="walkforward", period="daily",
                         n_obs=r["n_test"], data_start=r["data_start"], data_end=r["data_end"],
                         git_sha=git_sha, code_path="research/models/hmm/gate4_window_sweep.py",
                         parameters=params)
        ra = log_result(**common_kw, metric_key=f"window_sweep_hmm_auc_W{r['W']}",
                        metric_value=r["hmm_auc"], cost_adjusted=0, notes=notes)
        rb = log_result(**common_kw, metric_key=f"window_sweep_platt_brier_W{r['W']}",
                        metric_value=r["platt_brier"], cost_adjusted=0, notes=notes)
        print(f"  Logged W={r['W']}: AUC result_id={ra}, Brier result_id={rb}")
    print("\nDone. (window NOT frozen — Gate 4 stays open; OOS untouched)")


def plot(rows):
    ws = [r["W"] for r in rows]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=ws, y=[r["hmm_auc"] for r in rows], mode="lines+markers",
                             name="HMM AUC (discrimination)", line=dict(color="#E74C3C")))
    fig.add_trace(go.Scatter(x=ws, y=[r["platt_bss"] for r in rows], mode="lines+markers",
                             name="Platt BSS (skill vs clim)", line=dict(color="#2ECC71")))
    fig.add_hline(y=0.5, line=dict(color="#888888", dash="dash"),
                  annotation_text="AUC=0.5 (no skill)")
    fig.update_layout(title="HMM-001 Gate 4 — Lookback window sweep (out-of-fold)",
                      xaxis_title="Lookback window (days)", yaxis_title="metric",
                      template="plotly_dark", height=520)
    out = "research/outputs/hmm/hmm_gate4_window_sweep.html"
    fig.write_html(out)
    print(f"\n  Chart saved: {out}")


if __name__ == "__main__":
    main()
