"""
gate2_confluence_2tf.py — MSM-001 Gate 2: the DUMB pairwise confluence test.

THE POINT (drift correction, Afternoon4 [[orb_unsorted_tick_lookahead]] sibling):
the ORIGINAL MSM thesis is "does HTF/LTF momentum ALIGNMENT carry an edge". We
violated simple-before-complex (rule 7): jumped to a 9-rung straddle-ladder
interaction, found it flat, then sprayed unrelated mechanisms. This script runs the
2-timeframe test that was NEVER run — strategy_log #41 (PROPOSED), human call_id 51.

PRE-REGISTERED DESIGN (one HTF rung, one LTF rung, wide gap — no data-snooped cuts):
  HTF = rung r8 (L=256 M5 ~ 21h, ~D1 trailing move).  dir D = sign(r8)
  LTF = rung r4 (L=16  M5 ~ 80m, ~H1 trailing move).  dir L = sign(r4)
  16x scale gap chosen so AGREE/CONFLICT is informative, not mechanically collinear.
  LABEL = fwd (next H4 return, 48 M5 forward, non-overlapping).

  2x2 confluence cells by (sign r8, sign r4): ++ +- -+ --.
  AGREE  = same sign -> trade the common direction d.  dictation s = d * fwd
  CONFLICT (control) = opposite sign -> follow HTF.     s = D * fwd

METRIC-LAST (rule 8b):
  1. mechanism makes sense (above).
  2. does the cell table SEPARATE — mean fwd, hit, n per cell; AGREE vs CONFLICT?  <- FRONT
  3. HAC t-stat on AGREE dictation return (+ AGREE-CONFLICT) = CONFIRMATION, last.

H0: alignment confers NO edge — AGREE net dictation mean <= 0, AND AGREE not
    distinguishable from CONFLICT. Reject ONLY if AGREE net-of-spread > 0 with HAC
    t >= 2 AND AGREE net > CONFLICT net. Flat + null here = 3rd FALSIFIED -> kill-eligible.
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

HTF_RUNG   = 8                     # r8 ~ D1
LTF_RUNG   = 4                     # r4 ~ H1
SPREAD_USD = 0.20                  # JM Pro round-trip (TCM-001)
HAC_LAGS   = 5
CODE_PATH  = "research/models/msm/gate2_confluence_2tf.py"


def _git_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).decode().strip()


def _net(s, price):
    """net-of-spread dictation return + hit-rate."""
    s = np.asarray(s, float); price = np.asarray(price, float)
    s_net = s - SPREAD_USD / price
    return s_net, float((s > 0).mean())


def _hac_t_mean(s_net, index):
    """HAC t of the mean of s_net (regress on constant only)."""
    import statsmodels.api as sm
    X = np.ones((len(s_net), 1))
    mdl = sm.OLS(np.asarray(s_net, float), X).fit(cov_type="HAC", cov_kwds={"maxlags": HAC_LAGS})
    return float(mdl.tvalues[0]), float(mdl.params[0])


def run():
    feat = msm_features.load()
    rH = feat[f"r{HTF_RUNG}"].values
    rL = feat[f"r{LTF_RUNG}"].values
    fwd = feat["fwd"].values
    price = feat["price"].values
    D = np.sign(rH); L = np.sign(rL)
    n = len(feat)

    # ---- sanity (rule 5) ----
    print("\n=== MSM-001 Gate 2 — DUMB 2-TF confluence (D1 x H1) — sanity ===")
    print(f"H4 obs: {n:,}   span {feat.index[0]} -> {feat.index[-1]}")
    print(f"HTF r{HTF_RUNG}(~D1) up-rate {(D>0).mean():.3f}   LTF r{LTF_RUNG}(~H1) up-rate {(L>0).mean():.3f}")
    agree_rate = float((D == L).mean())
    print(f"AGREE rate (signs match): {agree_rate:.3f}   (collinearity check: ~0.5 = independent, ->1 = redundant)")
    print(f"unconditional fwd H4: mean {fwd.mean():+.6f}  hit {(fwd>0).mean():.3f}")
    if n < 500:
        print("ABORT: n<500"); return

    # ---- STEP 2: 2x2 cell separation (FRONT gate — eyeball before any t) ----
    print("\n=== STEP 2 — 2x2 confluence cells (fwd H4, net of $0.20 spread) ===")
    print(f"{'cell':6} {'n':>6} {'mean_fwd':>11} {'net_dict':>11} {'hit%':>7}")
    cells = {("+", "+"): None, ("+", "-"): None, ("-", "+"): None, ("-", "-"): None}
    for (sh, sl) in list(cells):
        m = (D == (1 if sh == "+" else -1)) & (L == (1 if sl == "+" else -1))
        if m.sum() == 0:
            continue
        d_common = 1 if sh == "+" else -1            # AGREE cells trade common dir; CONFLICT follow HTF (=D)
        s = d_common * fwd[m] if sh == sl else (1 if sh == "+" else -1) * fwd[m]
        s_net, hit = _net(s, price[m])
        cells[(sh, sl)] = dict(n=int(m.sum()), mean_fwd=float(fwd[m].mean()),
                               net_dict=float(s_net.mean()), hit=hit)
        print(f"{sh}{sl:5} {m.sum():>6} {fwd[m].mean():>+11.6f} {s_net.mean():>+11.6f} {100*hit:>6.1f}")

    # ---- aggregate AGREE vs CONFLICT ----
    agree = (D == L)
    s_agree = D[agree] * fwd[agree]                  # follow the common direction
    s_conf  = D[~agree] * fwd[~agree]                # control: follow HTF when they disagree
    sa_net, sa_hit = _net(s_agree, price[agree])
    sc_net, sc_hit = _net(s_conf, price[~agree])
    ta, ma = _hac_t_mean(sa_net, feat.index[agree])
    tc, mc = _hac_t_mean(sc_net, feat.index[~agree])
    print("\n=== STEP 2b — AGREE vs CONFLICT aggregate (net dictation return) ===")
    print(f"{'set':10} {'n':>6} {'net_mean':>11} {'hit%':>7} {'HAC_t':>7}")
    print(f"{'AGREE':10} {len(s_agree):>6} {sa_net.mean():>+11.6f} {100*sa_hit:>6.1f} {ta:>+7.2f}")
    print(f"{'CONFLICT':10} {len(s_conf):>6} {sc_net.mean():>+11.6f} {100*sc_hit:>6.1f} {tc:>+7.2f}")
    spread_ac = sa_net.mean() - sc_net.mean()
    print(f"AGREE - CONFLICT net mean = {spread_ac:+.6f}")

    # ---- STEP 3: confirmation (HAC) — last ----
    reject = (sa_net.mean() > 0) and (ta >= 2.0) and (spread_ac > 0)
    verdict = "REJECT H0 (alignment carries an edge)" if reject else "FAIL TO REJECT H0"
    print("\n=== STEP 3 — confirmation (HAC, last) ===")
    print(f"AGREE net dictation HAC t = {ta:+.3f}   (PRIMARY; need >=2)")
    print(f"AGREE net > 0 : {sa_net.mean() > 0}   AGREE > CONFLICT : {spread_ac > 0}")
    print(f"\nVERDICT: {verdict}")

    # ---- log (after sanity) ----
    sha = _git_sha()
    ds, de = str(feat.index[0]), str(feat.index[-1])
    params = (f"HTF=r{HTF_RUNG}(~D1) dir=sign; LTF=r{LTF_RUNG}(~H1) dir=sign; label=fwd H4(48 M5); "
              f"AGREE=signs match->common dir; CONFLICT control=follow HTF; HAC={HAC_LAGS}; spread${SPREAD_USD}rt")
    note = (f"DUMB 2-TF confluence D1xH1. agree_rate={agree_rate:.3f}. "
            f"AGREE net={sa_net.mean():+.6f} (t {ta:+.2f}, n {len(s_agree)}, hit {sa_hit:.3f}); "
            f"CONFLICT net={sc_net.mean():+.6f} (t {tc:+.2f}, n {len(s_conf)}); A-C={spread_ac:+.6f}. "
            f"{verdict}. Guards: sorted M5, causal-z, non-overlap H4, IS-sealed.")
    rid = pipeline.log_result(
        idea_id="MSM-001", gate_number=2, stage="IS",
        trial_family_id="MSM-001-gate2-confluence-2tf",
        metric_key="confluence_2tf_agree_t", metric_value=float(ta),
        cost_adjusted=1, period="per_trade", n_obs=int(len(s_agree)),
        data_start=ds, data_end=de, git_sha=sha, code_path=CODE_PATH,
        n_trials=1, instrument="XAUUSD", parameters=params, notes=note)
    pipeline.log_result(
        idea_id="MSM-001", gate_number=2, stage="IS",
        trial_family_id="MSM-001-gate2-confluence-2tf",
        metric_key="confluence_2tf_agree_net_mean", metric_value=float(sa_net.mean()),
        cost_adjusted=1, period="per_trade", n_obs=int(len(s_agree)),
        data_start=ds, data_end=de, git_sha=sha, code_path=CODE_PATH,
        n_trials=1, instrument="XAUUSD", parameters=params,
        notes=f"AGREE net dictation mean; A-C={spread_ac:+.6f}; paired with agree_t.")

    verdict_log = "VALIDATED" if reject else "FALSIFIED"
    strategy_log.log_change(
        "MSM-001", event="confluence_2tf_dumb", verdict=verdict_log, component="anchor",
        from_value="PROPOSED dumb pairwise alignment (log_id 41)",
        to_value=f"D1xH1 alignment: AGREE net={sa_net.mean():+.6f} (t {ta:+.2f}), A-C={spread_ac:+.6f}",
        rationale=(f"Gate 2 dumb 2-TF confluence (the never-run original thesis). AGREE net dictation "
                   f"{sa_net.mean():+.6f} HAC t={ta:+.3f} (n {len(s_agree)}), CONFLICT {sc_net.mean():+.6f}, "
                   f"A-C={spread_ac:+.6f}, agree_rate={agree_rate:.3f}. {verdict}."),
        result_id=rid, git_sha=sha)
    print(f"\nlogged result_id={rid}; strategy_log updated ({verdict_log}).")


if __name__ == "__main__":
    run()
