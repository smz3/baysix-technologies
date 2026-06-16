"""
gate2_benchmark_postmortem.py — does the SEPARABLE straddle ladder ITSELF predict
H4 on XAUUSD? (Post-mortem to the MSM-001 Gate-2 interaction kill.)

The Gate-2 test asked whether the cross-scale INTERACTION adds value OVER the
separable benchmark. It didn't (t=-0.28). This asks the prior question: does ANY
multi-scale momentum live at H4 — i.e. is the benchmark B itself predictive? That
tells us whether the horizon is dead or only the interaction is.

Reuses the exact leak-free features from gate2_interaction (sorted M5, causal-z,
non-overlap H4 label, IS-sealed). Logs ONLY the benchmark's own HAC t-stat — does
not touch the interaction verdict or strategy_log.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import statsmodels.api as sm

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "research" / "code"))
import pipeline                                    # noqa: E402
import gate2_interaction as g2                     # noqa: E402   (build fns + config)


def main():
    cache = REPO / "research" / "outputs" / "msm_g2_features.pkl"
    if cache.exists():
        import pandas as pd
        feat = pd.read_pickle(cache)
        print(f"[postmortem] loaded cached features ({len(feat):,} H4 obs)")
    else:
        feat = g2.build_features(g2.build_m5_closes())
        feat.to_pickle(cache)

    y = feat["fwd"].values
    Xb = sm.add_constant(feat[["B"]])
    mb = sm.OLS(y, Xb).fit(cov_type="HAC", cov_kwds={"maxlags": g2.HAC_LAGS})
    t_B, coef_B, r2 = mb.tvalues["B"], mb.params["B"], mb.rsquared
    n = len(feat)

    # directional Sharpe of the benchmark sign, net of spread (same convention as G2)
    d = np.sign(feat["B"].values)
    pnl = d * y - (g2.SPREAD_USD / feat["price"].values)
    sh = pnl.mean() / pnl.std() if pnl.std() else 0.0

    print("\n=== benchmark-only (separable straddle ladder), H4 IS ===")
    print(f"n                 : {n:,}")
    print(f"B own HAC t-stat  : {t_B:+.3f}")
    print(f"B coef            : {coef_B:+.6f}")
    print(f"R^2               : {r2:.5f}")
    print(f"dir Sharpe NET    : {sh:+.4f}")
    verdict = "separable momentum HAS H4 sign" if abs(t_B) >= 2 else "NO separable H4 sign either — horizon is flat"
    print(f"\n--> {verdict}")

    sha = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).decode().strip()
    pipeline.log_result(
        idea_id="MSM-001", gate_number=2, stage="IS",
        trial_family_id="MSM-001-gate2-benchmark-postmortem",
        metric_key="h4_benchmark_own_t", metric_value=float(t_B),
        cost_adjusted=0, period="per_trade", n_obs=int(n),
        data_start=str(feat.index[0]), data_end=str(feat.index[-1]),
        git_sha=sha, code_path="research/models/msm/gate2_benchmark_postmortem.py",
        n_trials=4, instrument="XAUUSD",
        parameters="benchmark-only sum(2Phi(z)-1) on 9-rung ladder; causal-z; H4 non-overlap",
        notes=(f"Post-mortem to interaction kill: does separable multi-scale momentum predict "
               f"H4 at all? coef_B={coef_B:+.6f} R2={r2:.5f} dirSharpeNet={sh:+.4f}. {verdict}."))
    print("logged h4_benchmark_own_t")


if __name__ == "__main__":
    main()
