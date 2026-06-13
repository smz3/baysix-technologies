"""
gate_hypC_magnitude.py — MSM-001 hypothesis C (task 66): magnitude-conditional
HTF -> LTF dictation.

WHY (post-mortem of the dead symmetric test): the Gate-2 interaction pooled ALL
HTF magnitudes and came back flat (t=-0.28). Hypothesis: a HTF move only DICTATES
the next LTF leg when it is LARGE — small HTF moves are noise and diluted the pool.

PRE-REGISTERED DESIGN (one HTF rung, fixed bands — no data-snooped cuts):
  HTF      = rung r8 (L=256 M5 bars ~ 21h, ~D1 trailing move). direction d=sign(r8).
  LTF leg  = fwd (next H4 return, 48 M5 bars forward, non-overlapping label).
  dictation return s = d * fwd  (the return from FOLLOWING the HTF direction).
  magnitude= |z8| (causal expanding-z of the HTF rung), banded by FIXED thresholds:
             small |z|<0.67 · mid 0.67-1.5 · large >1.5   (~tercile of a normal; not fit)

METRIC-LAST WORKFLOW (CLAUDE.md rule 8b sibling; [[enforcement_code_not_prose]]):
  1. mechanism must make sense   (above)
  2. does the cell table SEPARATE — mean s, hit-rate, n per band, monotone in |z|?  <- FRONT
  3. HAC t-stat on the magnitude x direction interaction = CONFIRMATION, last.

H0: dictation does NOT strengthen with HTF magnitude (interaction coef t < 2,
    large-band net mean <= 0). Reject only if large band is positive net-of-spread
    AND the |z|-interaction carries a positive HAC t.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "research" / "code"))
sys.path.insert(0, str(REPO / "research" / "models" / "msm"))
import features as msm_features    # noqa: E402
import pipeline                    # noqa: E402
import strategy_log                # noqa: E402

HTF_RUNG   = 8                      # r8/z8 ~ D1 trailing move
SPREAD_USD = 0.20                   # JM Pro round-trip (TCM-001)
BANDS      = [(0.0, 0.67, "small"), (0.67, 1.5, "mid"), (1.5, np.inf, "large")]
HAC_LAGS   = 5
CODE_PATH  = "research/models/msm/gate_hypC_magnitude.py"


def _git_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).decode().strip()


def _stats(s, price):
    """Directional dictation return s=d*fwd: raw & net-of-spread mean, hit-rate, t."""
    s = np.asarray(s); price = np.asarray(price)
    cost = SPREAD_USD / price
    s_net = s - cost
    n = len(s)
    hit = float((s > 0).mean())
    t_net = s_net.mean() / s_net.std() * np.sqrt(n) if s_net.std() > 0 else 0.0
    return dict(n=n, mean_raw=s.mean(), mean_net=s_net.mean(), hit=hit, t_net=t_net)


def run():
    import statsmodels.api as sm

    feat = msm_features.load()
    r = feat[f"r{HTF_RUNG}"].values
    z = feat[f"z{HTF_RUNG}"].values
    fwd = feat["fwd"].values
    price = feat["price"].values

    d = np.sign(r)
    s = d * fwd                          # dictation return (follow HTF direction)
    absz = np.abs(z)
    n = len(feat)

    # ---- sanity block (protocol rule 5) ----
    print("\n=== MSM-001 hyp C — sanity ===")
    print(f"H4 obs: {n:,}   span {feat.index[0]} -> {feat.index[-1]}")
    print(f"HTF rung r{HTF_RUNG}: |z| mean {absz.mean():.2f}  p90 {np.quantile(absz,0.9):.2f}")
    print(f"unconditional dictation s=d*fwd: mean {s.mean():+.6f}  hit {(s>0).mean():.3f}")
    if n < 500:
        print("ABORT: n<500"); return

    # ---- STEP 2: cell separation (the FRONT gate — eyeball before any t) ----
    print("\n=== STEP 2 — magnitude cell separation (net of $0.20 spread) ===")
    print(f"{'band':6} {'|z|':>10} {'n':>6} {'mean_raw':>11} {'mean_net':>11} {'hit%':>7} {'t_net':>7}")
    band_rows = {}
    for lo, hi, name in BANDS:
        m = (absz >= lo) & (absz < hi)
        st = _stats(s[m], price[m])
        band_rows[name] = st
        rng = f"{lo:.2f}-{'inf' if hi==np.inf else f'{hi:.2f}'}"
        print(f"{name:6} {rng:>10} {st['n']:>6} {st['mean_raw']:>+11.6f} "
              f"{st['mean_net']:>+11.6f} {100*st['hit']:>6.1f} {st['t_net']:>+7.2f}")
    mono = band_rows['large']['mean_net'] > band_rows['mid']['mean_net'] > band_rows['small']['mean_net']
    print(f"monotone increasing dictation with |z|? {mono}   "
          f"(large-small net spread = {band_rows['large']['mean_net']-band_rows['small']['mean_net']:+.6f})")

    # ---- STEP 3: CONFIRMATION (HAC) — does dictation strengthen with magnitude? ----
    # fwd ~ const + d + d*|z| ; the interaction coef tests magnitude-conditioning.
    X = sm.add_constant(pd.DataFrame({"d": d, "d_absz": d * absz}, index=feat.index))
    mdl = sm.OLS(fwd, X).fit(cov_type="HAC", cov_kwds={"maxlags": HAC_LAGS})
    t_inter = mdl.tvalues["d_absz"]; coef_inter = mdl.params["d_absz"]
    t_d = mdl.tvalues["d"]
    large = band_rows['large']
    print("\n=== STEP 3 — confirmation (HAC, last) ===")
    print(f"base direction d coef t : {t_d:+.3f}  (unconditional HTF dictation)")
    print(f"magnitude interaction   : coef={coef_inter:+.8f}  HAC t={t_inter:+.3f}  <-- PRIMARY")
    reject = (large['mean_net'] > 0) and (t_inter >= 2.0)
    verdict = "REJECT H0 (magnitude-conditional dictation)" if reject else "FAIL TO REJECT H0"
    print(f"large-band net mean     : {large['mean_net']:+.6f}  (t_net {large['t_net']:+.2f}, n {large['n']})")
    print(f"\nVERDICT: {verdict}")

    # ---- log (after sanity; metric is the interaction t) ----
    sha = _git_sha()
    ds, de = str(feat.index[0]), str(feat.index[-1])
    params = (f"HTF=r{HTF_RUNG}(~D1); LTF=fwd H4(48 M5); s=sign(r{HTF_RUNG})*fwd; "
              f"bands |z| {BANDS[0][1]}/{BANDS[1][1]} fixed; HAC={HAC_LAGS}; spread${SPREAD_USD}rt")
    rid = pipeline.log_result(
        idea_id="MSM-001", gate_number=2, stage="IS",
        metric_key="hypC_magnitude_interaction_t", metric_value=float(t_inter),
        cost_adjusted=0, period="per_trade", n_obs=int(n),
        data_start=ds, data_end=de, git_sha=sha, code_path=CODE_PATH,
        n_trials=4, instrument="XAUUSD", parameters=params,
        notes=(f"hyp C magnitude-conditional dictation. interaction coef={coef_inter:+.8f}. "
               f"bands net: small={band_rows['small']['mean_net']:+.6f} "
               f"mid={band_rows['mid']['mean_net']:+.6f} large={large['mean_net']:+.6f} "
               f"(t_net {large['t_net']:+.2f}, n {large['n']}). monotone={mono}. {verdict}. "
               f"Guards: sorted M5, causal-z, non-overlap H4, IS-sealed."))
    pipeline.log_result(
        idea_id="MSM-001", gate_number=2, stage="IS",
        metric_key="hypC_large_band_net_mean", metric_value=float(large['mean_net']),
        cost_adjusted=1, period="per_trade", n_obs=int(large['n']),
        data_start=ds, data_end=de, git_sha=sha, code_path=CODE_PATH,
        n_trials=4, instrument="XAUUSD", parameters=params,
        notes=f"large |z|>1.5 band net dictation mean; t_net={large['t_net']:+.2f}; paired with interaction-t.")

    verdict_log = "VALIDATED" if reject else "FALSIFIED"
    strategy_log.log_change(
        "MSM-001", event="hypC_magnitude_conditional", verdict=verdict_log, component="entry",
        from_value="symmetric alignment (FALSIFIED, pooled magnitudes)",
        to_value=f"magnitude-conditional dictation: interaction t={t_inter:+.2f}, large-band net={large['mean_net']:+.6f}",
        rationale=(f"hyp C (task 66): does large HTF move dictate next H4? interaction HAC t={t_inter:+.3f}, "
                   f"large-band net mean={large['mean_net']:+.6f} (t_net {large['t_net']:+.2f}, n {large['n']}), "
                   f"monotone={mono}. {verdict}."),
        result_id=rid, git_sha=sha)
    print(f"\nlogged result_id={rid}; strategy_log updated ({verdict_log}).")


if __name__ == "__main__":
    run()
