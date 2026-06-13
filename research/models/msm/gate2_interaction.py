"""
gate2_interaction.py — MSM-001 Gate 2 EXISTENCE test (H4 trial, 1 of n_trials=4).

QUESTION (Gate 1 null): does a cross-scale INTERACTION (sign-alignment across the
9-rung close-only return ladder) carry MARGINAL forward predictive power OVER a
separable straddle-ladder benchmark, on sealed XAUUSD IS, leak-free?

  H0: interaction adds nothing beyond the separable per-rung blend (coef t < 2).
  Reject only if interaction t >= 2-3 (the Gate-0 bar).

LOOK-AHEAD GUARDS (the whole point — see [[orb_unsorted_tick_lookahead]]):
  G1  M5 closes built from SORTED Arctic ticks (arctic_io); index asserted monotonic.
  G2  Every feature at decision time t uses ONLY returns ending <= t (past shifts).
  G3  z-standardisation is CAUSAL: expanding mean/std up to t-1 (.shift(1)),
      NEVER full-sample stats.
  G4  Forward H4 return is the LABEL (t -> t+H); decisions sampled on the H4 grid
      so forward windows are NON-OVERLAPPING + contiguous.
  G5  IS only — is_ticks() enforces the 2024-05-02 seal; OOS cannot leak in.

The ladder: 9 geometric rungs L_k = 2^k M5-bars, k=0..8  ->  5,10,20,40,80,160,
320,640,1280 minutes (~M5 .. ~D1). Close-to-close return per rung.

Benchmark B(t)  = sum_k [2*Phi(z_k) - 1]            (separable, odd, per-rung squash)
Interaction I(t)= sign(S) * meanPairwiseCoSign       (S = sum of rung signs)
                = sign(S) * (S^2 - K) / (K*(K-1))     (non-additive across rungs)

Primary metric: HAC t-stat of I in  y ~ const + B + I.  Reject H0 if |t|>=2-3 and
sign positive (alignment -> continuation). Secondary: delta-R^2, marginal IC, and a
net-of-spread directional Sharpe on the benchmark-orthogonalised interaction.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm
from tqdm import tqdm

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "research" / "code"))
import arctic_io as aio          # noqa: E402
import pipeline                  # noqa: E402
import strategy_log              # noqa: E402

# ---- pre-registered config (n_trials family) -----------------------------------
K_RUNGS      = 9
LADDER_BARS  = [2 ** k for k in range(K_RUNGS)]     # 1..256 M5 bars
M5_PER_H4    = 48                                    # 240 min / 5
HORIZON_BARS = M5_PER_H4                             # H4 forward label
WARMUP_H4    = 250                                   # expanding-stat warmup (H4 obs)
HAC_LAGS     = 5
SPREAD_USD   = 0.20                                  # JM Pro round-trip (TCM-001)
CODE_PATH    = "research/models/msm/gate2_interaction.py"


def _git_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).decode().strip()


def build_m5_closes() -> pd.Series:
    """SORTED M5 mid-close series over the IS span (G1, G5). Built month-by-month
    from ticks, clipped strictly below the seal."""
    seal = aio.seal_date()
    frames = []
    for ym in tqdm(aio.tick_months(), desc="M5 closes (IS)"):
        # skip months entirely at/after the seal
        if pd.Timestamp(year=int(ym[0]), month=int(ym[1]), day=1) >= seal:
            continue
        df = aio.read_tick_month(ym, columns=["bid", "ask"], as_column=False)
        df = df[df.index < seal]
        if df.empty:
            continue
        mid = (df["bid"] + df["ask"]) * 0.5
        frames.append(mid.resample("5min").last().dropna())
    m5 = pd.concat(frames).sort_index()
    m5 = m5[~m5.index.duplicated(keep="first")]
    assert m5.index.is_monotonic_increasing, "M5 index non-monotonic — look-ahead risk"
    return m5.rename("close")


def build_features(m5: pd.Series) -> pd.DataFrame:
    """Per-rung close-to-close returns on the M5 grid (G2), sampled at H4 closes,
    plus the causal benchmark B, interaction I, and the forward H4 label (G4)."""
    # rung returns over L_k bars, ending at each M5 bar (all PAST shifts => causal)
    rr = {f"r{k}": m5 / m5.shift(L) - 1.0 for k, L in enumerate(LADDER_BARS)}
    feat = pd.DataFrame(rr, index=m5.index)

    # forward H4 return (LABEL — uses the future; only ever the y, never an x)
    feat["fwd"] = m5.shift(-HORIZON_BARS) / m5 - 1.0

    # sample the H4 decision grid (top of hours 0,4,8,..; minute 0)
    h4 = feat[(feat.index.minute == 0) & (feat.index.hour % 4 == 0)].copy()
    rcols = [f"r{k}" for k in range(K_RUNGS)]
    h4 = h4.dropna(subset=rcols + ["fwd"])

    # G3: CAUSAL standardisation — expanding mean/std up to t-1
    z = pd.DataFrame(index=h4.index)
    for c in rcols:
        mu = h4[c].expanding(min_periods=WARMUP_H4).mean().shift(1)
        sd = h4[c].expanding(min_periods=WARMUP_H4).std().shift(1)
        z[c] = (h4[c] - mu) / sd
    z = z.dropna()
    h4 = h4.loc[z.index]

    # benchmark: separable per-rung squash, summed
    h4["B"] = (2.0 * norm.cdf(z[rcols].values) - 1.0).sum(axis=1)

    # interaction: signed consensus * mean pairwise co-sign (non-additive)
    s = np.sign(h4[rcols].values)
    S = s.sum(axis=1)
    mean_pair_cosign = (S ** 2 - K_RUNGS) / (K_RUNGS * (K_RUNGS - 1))
    h4["I"] = np.sign(S) * mean_pair_cosign

    h4["price"] = m5.loc[h4.index].values
    return h4[["B", "I", "fwd", "price"]].dropna()


def run():
    import statsmodels.api as sm

    m5 = build_m5_closes()
    feat = build_features(m5)
    # cache the H4 feature frame (gitignored outputs) so post-hoc stats never re-read ticks
    cache = REPO / "research" / "outputs" / "msm_g2_features.pkl"
    cache.parent.mkdir(parents=True, exist_ok=True)
    feat.to_pickle(cache)
    n = len(feat)
    y = feat["fwd"].values

    # ---- sanity block (protocol rule 5) ----
    print("\n=== MSM-001 Gate 2 — sanity ===")
    print(f"M5 bars: {len(m5):,}   span {m5.index[0]} -> {m5.index[-1]}")
    print(f"H4 decision obs (post-warmup): {n:,}")
    print(f"fwd H4 return: mean {y.mean():+.5f}  std {y.std():.5f}")
    print(f"B  range [{feat['B'].min():.2f}, {feat['B'].max():.2f}]")
    print(f"I  range [{feat['I'].min():.2f}, {feat['I'].max():.2f}]  corr(B,I)={np.corrcoef(feat['B'],feat['I'])[0,1]:+.3f}")
    if n < 500:
        print("ABORT: n < 500 — insufficient H4 obs"); return

    # ---- benchmark-only vs benchmark+interaction (HAC) ----
    Xb  = sm.add_constant(feat[["B"]])
    Xbi = sm.add_constant(feat[["B", "I"]])
    mb  = sm.OLS(y, Xb ).fit(cov_type="HAC", cov_kwds={"maxlags": HAC_LAGS})
    mbi = sm.OLS(y, Xbi).fit(cov_type="HAC", cov_kwds={"maxlags": HAC_LAGS})

    t_I   = mbi.tvalues["I"]
    coef_I = mbi.params["I"]
    t_B   = mb.tvalues["B"]          # does the SEPARABLE benchmark itself predict at H4?
    coef_B = mb.params["B"]
    dR2   = mbi.rsquared - mb.rsquared

    # marginal IC: I residualised on [const,B], corr with y
    I_resid = sm.OLS(feat["I"], Xb).fit().resid
    ic = np.corrcoef(I_resid, y)[0, 1]

    # ---- net-of-spread directional Sharpe on the orthogonalised interaction ----
    d = np.sign(I_resid.values)
    pnl_raw = d * y
    cost_ret = SPREAD_USD / feat["price"].values          # round-trip drag per H4 trade
    pnl_net = pnl_raw - cost_ret
    def _sharpe_t(x):
        x = x[np.isfinite(x)]
        if x.std() == 0: return 0.0, 0.0
        sh = x.mean() / x.std()
        return sh, sh * np.sqrt(len(x))
    sh_raw, t_raw = _sharpe_t(pnl_raw)
    sh_net, t_net = _sharpe_t(pnl_net)

    print("\n=== RESULT (H4 trial, IS) ===")
    print(f"benchmark B own t-stat : {t_B:+.3f}  coef={coef_B:+.6f}  <-- does separable momentum predict H4 at all?")
    print(f"benchmark R^2          : {mb.rsquared:.5f}")
    print(f"+interaction R^2       : {mbi.rsquared:.5f}   dR2={dR2:+.5f}")
    print(f"interaction coef       : {coef_I:+.6f}")
    print(f"interaction HAC t-stat : {t_I:+.3f}   <-- PRIMARY (reject H0 if >=+2..3)")
    print(f"marginal IC (resid)    : {ic:+.4f}")
    print(f"dir Sharpe/trade raw   : {sh_raw:+.4f}  (t {t_raw:+.2f})")
    print(f"dir Sharpe/trade NET   : {sh_net:+.4f}  (t {t_net:+.2f})  spread drag={cost_ret.mean():.6f}/trade")
    verdict = "REJECT H0 (interaction edge)" if (t_I >= 2 and coef_I > 0) else "FAIL TO REJECT H0 (no marginal edge)"
    print(f"\nVERDICT: {verdict}")

    # ---- log (protocol rule 9: only after sanity) ----
    sha = _git_sha()
    ds, de = str(feat.index[0]), str(feat.index[-1])
    params = (f"ladder={LADDER_BARS}; horizon=H4({HORIZON_BARS}m5); benchmark=sum(2Phi(z)-1) "
              f"causal-expanding-z warmup={WARMUP_H4}; interaction=sign(S)*meanPairCoSign; HAC={HAC_LAGS}")
    rid = pipeline.log_result(
        idea_id="MSM-001", gate_number=2, stage="IS",
        metric_key="h4_interaction_marginal_t", metric_value=float(t_I),
        cost_adjusted=0, period="per_trade", n_obs=int(n),
        data_start=ds, data_end=de, git_sha=sha, code_path=CODE_PATH,
        n_trials=4, instrument="XAUUSD", parameters=params,
        notes=(f"Gate-2 existence test H4 trial. coef_I={coef_I:+.6f} dR2={dR2:+.5f} "
               f"IC={ic:+.4f} dirSharpe_net={sh_net:+.4f}(t{t_net:+.2f}) spread${SPREAD_USD}rt. "
               f"{verdict}. Guards: sorted M5, causal-z, non-overlap H4, IS-sealed."))
    pipeline.log_result(
        idea_id="MSM-001", gate_number=2, stage="IS",
        metric_key="h4_interaction_dir_sharpe_net", metric_value=float(sh_net),
        cost_adjusted=1, period="per_trade", n_obs=int(n),
        data_start=ds, data_end=de, git_sha=sha, code_path=CODE_PATH,
        n_trials=4, instrument="XAUUSD", parameters=params,
        notes=f"net of $0.20 rt spread; t={t_net:+.2f}; paired with result for marginal-t.")

    verdict_log = "VALIDATED" if (t_I >= 2 and coef_I > 0) else "FALSIFIED"
    strategy_log.log_change(
        "MSM-001", event="gate2_existence_test", verdict=verdict_log, component="entry",
        from_value="alignment-threshold H4 continuation (untested)",
        to_value=f"interaction marginal t={t_I:+.2f} over separable ladder",
        rationale=(f"Gate-2 IS existence test (H4, leak-free): interaction HAC t={t_I:+.3f}, "
                   f"coef={coef_I:+.6f}, dR2={dR2:+.5f}, IC={ic:+.4f}, net dir Sharpe={sh_net:+.4f}. "
                   f"{verdict}."),
        result_id=rid, git_sha=sha)
    print(f"\nlogged result_id={rid}; strategy_log updated ({verdict_log}).")


if __name__ == "__main__":
    run()
