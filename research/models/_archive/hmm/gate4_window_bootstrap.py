"""
HMM-001 Gate 4 — Bootstrap tiebreak: is W=40's AUC edge over W=20 real or noise?

The sweep gave raw-HMM regime-change AUC 0.606 (W=20) vs 0.659 (W=40). But W=40
has fewer regime-change events in the test window, so its AUC has wider error bars.
Before freezing a window for the one-shot OOS, test the difference properly.

Method — PAIRED bootstrap on the common test days:
  - For W in {20, 40}: rebuild the regime (same gaussian_crossing cuts as the sweep),
    fit the forecaster HMM on TRAIN only, causal-filter, take raw P(change) on test.
  - Align both on common calendar test dates (same days for both -> paired).
  - B resamples of day indices (with replacement); each draw recompute AUC_20, AUC_40
    on the SAME resampled days; record dAUC = AUC_40 - AUC_20.
  - Report observed dAUC, 95% percentile CI, and one-sided p = P(dAUC <= 0).

Stays at Gate 4. Logs the dAUC point estimate + CI to research.db.
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parents[2] / "code"))
from pipeline import log_result
from gate4_hmm import fit_best, forward_filter
from gate4_calibration import auc
from gate4_window_sweep import (load_cumW, derive_cuts, S2I,
                                HMM_TRAIN_END, TEST_START)

B    = 10000
SEED = 0


def get_test_arrays(W):
    """Return (test_dates, p_hmm, o_te): raw HMM P(change) + change indicator on test."""
    close, cumW = load_cumW(W)
    thr_bull, thr_bear, *_ = derive_cuts(cumW)
    labels = pd.Series(np.where(cumW.values >= thr_bull, "Bull",
                       np.where(cumW.values <= thr_bear, "Bear", "Sideways")),
                       index=cumW.index)
    s = labels.map(S2I).values
    N = len(s)
    o = (s[1:] != s[:-1]).astype(float)

    hmm_i  = int(np.searchsorted(cumW.index.values, np.datetime64(HMM_TRAIN_END))) + 1
    test_i = int(np.searchsorted(cumW.index.values, np.datetime64(TEST_START))) + 1

    model, _ = fit_best(cumW.values[:hmm_i].reshape(-1, 1))
    alpha = forward_filter(model, cumW.values.reshape(-1, 1))
    p_hmm_full = 1 - alpha @ np.diag(model.transmat_)

    idx = np.arange(test_i, N - 1)
    dates = cumW.index[idx]
    return pd.Series(p_hmm_full[idx], index=dates), pd.Series(o[idx], index=dates)


def main():
    print(f"\nBootstrap tiebreak — W=20 vs W=40 regime-change AUC  (B={B})")
    print("=" * 64)

    p20, o20 = get_test_arrays(20)
    p40, o40 = get_test_arrays(40)

    common = p20.index.intersection(p40.index)
    p20, o20 = p20.loc[common].values, o20.loc[common].values
    p40, o40 = p40.loc[common].values, o40.loc[common].values
    n = len(common)

    auc20, auc40 = auc(p20, o20), auc(p40, o40)
    print(f"\nCommon test days: {n}  ({common[0].date()} -> {common[-1].date()})")
    print(f"changes: W20={int(o20.sum())} ({o20.mean():.1%})  W40={int(o40.sum())} ({o40.mean():.1%})")
    print(f"observed AUC: W20={auc20:.4f}  W40={auc40:.4f}  dAUC(40-20)={auc40-auc20:+.4f}")
    print("  (should match sweep: 0.606 / 0.659)")

    rng = np.random.default_rng(SEED)
    diffs = np.full(B, np.nan)
    n_skip = 0
    for b in tqdm(range(B), desc="bootstrap dAUC"):
        idx = rng.integers(0, n, n)                       # paired resample of days
        a20, a40 = auc(p20[idx], o20[idx]), auc(p40[idx], o40[idx])
        if np.isnan(a20) or np.isnan(a40):                # degenerate resample (one class)
            n_skip += 1
            continue
        diffs[b] = a40 - a20
    diffs = diffs[~np.isnan(diffs)]

    obs   = auc40 - auc20
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    p_one = np.mean(diffs <= 0)                            # H0: W40 no better than W20
    se    = diffs.std()

    print(f"\n--- Bootstrap dAUC (W40 - W20), {len(diffs)} valid draws, {n_skip} skipped ---")
    print(f"  observed       : {obs:+.4f}")
    print(f"  bootstrap mean : {diffs.mean():+.4f}   SE={se:.4f}")
    print(f"  95% CI         : [{lo:+.4f}, {hi:+.4f}]")
    print(f"  one-sided p    : P(dAUC <= 0) = {p_one:.4f}")
    verdict = ("W40 AUC edge is REAL (CI excludes 0, p<0.05)" if lo > 0
               else "W40 edge NOT significant — CI includes 0; treat 20 and 40 as tied")
    print(f"  >>> {verdict}")

    # ── DB logging ────────────────────────────────────────────────────────────
    git_sha = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).decode().strip()
    params = json.dumps({"compare": "W40_vs_W20", "metric": "raw_hmm_change_auc",
                         "B": B, "seed": SEED, "n_common_test": n,
                         "auc_w20": round(auc20, 4), "auc_w40": round(auc40, 4),
                         "ci_lo": round(lo, 4), "ci_hi": round(hi, 4),
                         "test_start": TEST_START})
    notes = (f"dAUC={obs:+.4f} 95%CI[{lo:+.4f},{hi:+.4f}] p(<=0)={p_one:.4f} | "
             f"W20={auc20:.3f} W40={auc40:.3f} | {verdict}")
    rid = log_result(idea_id="HMM-001", gate_number=4, stage="walkforward", period="daily",
                     n_obs=n, n_trials=B, data_start=str(common[0].date()),
                     data_end=str(common[-1].date()), git_sha=git_sha,
                     code_path="research/models/hmm/gate4_window_bootstrap.py",
                     metric_key="window_bootstrap_dauc_w40_w20", metric_value=float(obs),
                     cost_adjusted=0, parameters=params, notes=notes)
    print(f"\nLogged: dAUC result_id={rid}")
    print("Done. (window still NOT frozen — decide from the CI; OOS untouched)")


if __name__ == "__main__":
    main()
