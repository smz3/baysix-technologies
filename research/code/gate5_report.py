"""Gate-5 reporting layer (Protocol 3.2, task 83).

Gate 5 asks "is there a tradeable signal with positive NET edge?" 3.2 changes two
things:

  1. The significance test BRANCHES on output_type (resolved by `protocol`, never
     chosen here): pnl_stream -> PSR/DSR, classifier_score -> IC t-stat / AUC CI.
  2. Pass metrics are PRE-COMMITTED before the tearsheet is viewed — no
     eyeball-gating. You declare 3-4 numeric bars up front; the report computes,
     scores pass/fail, and only THEN may you render the QuantStats tearsheet.

The hard wall stays in pipeline.pass_gate(5) (task 80) — it requires a logged
step4_results metric_key matching the resolved test. This module is the producer
of those metrics + the human-facing tearsheet.

PSR/DSR follow the per-period convention (memory: per_period_sharpe_units_rule —
recurred 3×): per-period Sharpe + T = observation count, NEVER annualised; the
kurtosis term is (kurt − 1)/4 with Pearson (non-excess) kurtosis (normal = 3).

Usage (pnl_stream):
    rep = Gate5Report("BRK-001", "pnl_stream")
    rep.commit_bars(psr=0.95, sharpe_t=2.0, net_mean=0.0)   # BEFORE looking
    rep.evaluate_pnl(returns)                                # compute + score
    print(rep.report())
    if rep.verdict():
        rep.tearsheet(returns, "research/outputs/brk001_gate5.html")  # view LAST
"""
from __future__ import annotations

import numpy as np
from scipy import stats

_EULER = 0.5772156649015329  # Euler–Mascheroni, for the DSR expected-max-SR deflation


# ── PSR / DSR (per-period convention) ───────────────────────────────────────────

def _clean(returns) -> np.ndarray:
    r = np.asarray(returns, dtype=float)
    return r[np.isfinite(r)]


def sharpe_per_period(returns) -> float:
    """Per-period Sharpe (mean/std, ddof=1). NOT annualised — annualising then
    feeding into PSR/t-stat is the recurring units bug (per_period_sharpe_units_rule)."""
    r = _clean(returns)
    sd = r.std(ddof=1)
    return float("nan") if sd == 0 else r.mean() / sd


def sharpe_t(returns) -> float:
    """t-stat of the per-period Sharpe = SR * sqrt(T). T = observation count."""
    r = _clean(returns)
    return sharpe_per_period(r) * np.sqrt(len(r))


def psr(returns, sr_benchmark: float = 0.0) -> float:
    """Probabilistic Sharpe Ratio: P(true SR > sr_benchmark) given skew/kurtosis.
    Bailey & López de Prado. Per-period SR, T = obs, Pearson (non-excess) kurtosis."""
    r = _clean(returns)
    T = len(r)
    if T < 3 or r.std(ddof=1) == 0:
        return float("nan")
    sr = sharpe_per_period(r)
    skew = float(stats.skew(r, bias=False))
    kurt = float(stats.kurtosis(r, fisher=False, bias=False))  # Pearson: normal = 3
    denom = np.sqrt(1.0 - skew * sr + ((kurt - 1.0) / 4.0) * sr**2)
    if not np.isfinite(denom) or denom == 0:
        return float("nan")
    z = (sr - sr_benchmark) * np.sqrt(T - 1) / denom
    return float(stats.norm.cdf(z))


def deflated_sr_benchmark(var_sr: float, n_trials: int) -> float:
    """The SR* a strategy must beat after deflating for N trials (the expected
    maximum of N independent SR estimates). var_sr = variance of SR across trials."""
    if n_trials < 2 or var_sr <= 0:
        return 0.0
    sd = np.sqrt(var_sr)
    z1 = stats.norm.ppf(1.0 - 1.0 / n_trials)
    z2 = stats.norm.ppf(1.0 - 1.0 / (n_trials * np.e))
    return float(sd * ((1.0 - _EULER) * z1 + _EULER * z2))


def dsr(returns, var_sr: float, n_trials: int) -> float:
    """Deflated Sharpe Ratio = PSR against the trial-deflated benchmark SR.
    var_sr = variance of the per-period SR across the n_trials you compared."""
    return psr(returns, sr_benchmark=deflated_sr_benchmark(var_sr, n_trials))


# ── classifier metrics (classifier_score branch) ────────────────────────────────

def ic_t(ic_series) -> float:
    """t-stat of an information-coefficient series: mean(IC)/se(IC) * sqrt(T)."""
    ic = _clean(ic_series)
    sd = ic.std(ddof=1)
    return float("nan") if sd == 0 else float(ic.mean() / sd * np.sqrt(len(ic)))


def auc_ci(y_true, scores, n_boot: int = 2000, seed: int = 0) -> tuple[float, float, float]:
    """ROC-AUC with a bootstrap 95% CI. Returns (auc, lo, hi). The lower bound is
    the pass object (AUC CI clears 0.5)."""
    from sklearn.metrics import roc_auc_score
    y = np.asarray(y_true); s = np.asarray(scores, dtype=float)
    auc = float(roc_auc_score(y, s))
    rng = np.random.default_rng(seed)
    n = len(y)
    boots = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        if len(np.unique(y[idx])) < 2:
            continue
        boots.append(roc_auc_score(y[idx], s[idx]))
    lo, hi = np.percentile(boots, [2.5, 97.5]) if boots else (float("nan"), float("nan"))
    return auc, float(lo), float(hi)


# ── pre-committed gate report ───────────────────────────────────────────────────

class Gate5Report:
    """Pre-commit the pass bars, THEN compute, THEN (only on a pass) view the
    tearsheet. The significance test must match the idea's output_type."""

    def __init__(self, idea_id: str, output_type: str):
        self.idea_id = idea_id
        self.output_type = output_type
        self.bars: dict[str, float] = {}
        self.metrics: dict[str, float] = {}
        self._evaluated = False

    def commit_bars(self, **bars) -> "Gate5Report":
        """Declare numeric pass thresholds BEFORE looking at results. 3-4 expected.
        Names map to computed metrics (psr, sharpe_t, net_mean, dsr, ic_t, auc_lo)."""
        if self._evaluated:
            raise RuntimeError("bars must be committed BEFORE evaluate (no eyeball-gating)")
        if not 2 <= len(bars) <= 6:
            raise ValueError("pre-commit 3-4 pass metrics (2-6 allowed) — not just one")
        self.bars = {k: float(v) for k, v in bars.items()}
        return self

    def evaluate_pnl(self, returns, var_sr: float | None = None, n_trials: int | None = None) -> dict:
        """Compute the pnl_stream metric panel and score against committed bars."""
        if self.output_type != "pnl_stream":
            raise ValueError(f"evaluate_pnl is for pnl_stream, not {self.output_type!r}")
        r = _clean(returns)
        self.metrics = {
            "psr": psr(r),
            "sharpe_t": sharpe_t(r),
            "sharpe_per_period": sharpe_per_period(r),
            "net_mean": float(r.mean()),
            "n_obs": float(len(r)),
        }
        if var_sr is not None and n_trials is not None:
            self.metrics["dsr"] = dsr(r, var_sr, n_trials)
        self._evaluated = True
        return self.metrics

    def evaluate_classifier(self, ic_series=None, y_true=None, scores=None) -> dict:
        """Compute the classifier_score metric panel (IC t-stat and/or AUC CI)."""
        if self.output_type != "classifier_score":
            raise ValueError(f"evaluate_classifier is for classifier_score, not {self.output_type!r}")
        m: dict[str, float] = {}
        if ic_series is not None:
            m["ic_t"] = ic_t(ic_series)
        if y_true is not None and scores is not None:
            auc, lo, hi = auc_ci(y_true, scores)
            m.update({"auc": auc, "auc_lo": lo, "auc_hi": hi})
        if not m:
            raise ValueError("provide ic_series and/or (y_true, scores)")
        self.metrics = m
        self._evaluated = True
        return m

    def _scored(self) -> list[tuple[str, float, float, bool]]:
        """(bar_name, threshold, actual, pass?) — a bar passes if metric >= threshold."""
        out = []
        for name, thr in self.bars.items():
            actual = self.metrics.get(name, float("nan"))
            out.append((name, thr, actual, bool(np.isfinite(actual) and actual >= thr)))
        return out

    def verdict(self) -> bool:
        """PASS only if evaluated and EVERY committed bar is met."""
        return self._evaluated and bool(self.bars) and all(ok for *_, ok in self._scored())

    def report(self) -> str:
        try:                                # resolved test for the header (single source)
            from research.code import protocol
        except ImportError:
            import protocol
        # idea_kind unknown here; resolve from output_type only.
        kind = {"pnl_stream": "strategy", "classifier_score": "classifier"}.get(self.output_type)
        lines = [f"== Gate 5 · {self.idea_id} · output_type={self.output_type}",
                 f"   sig test: {protocol.significance_test_for(kind, self.output_type)}"]
        if not self._evaluated:
            lines.append("   (NOT evaluated — commit bars then evaluate before viewing)")
            return "\n".join(lines)
        lines.append("   metrics: " + ", ".join(f"{k}={v:.4g}" for k, v in self.metrics.items()))
        lines.append("   bars (metric >= threshold):")
        for name, thr, actual, ok in self._scored():
            lines.append(f"     [{'PASS' if ok else 'FAIL'}] {name} >= {thr:.4g}  (got {actual:.4g})")
        lines.append("   -> " + ("PASS — log the matching metric, then pass_gate(5)"
                                 if self.verdict() else "FAIL — do NOT pass Gate 5"))
        return "\n".join(lines)

    def tearsheet(self, returns, output_html: str, title: str | None = None) -> str:
        """Render the QuantStats HTML tearsheet — only AFTER evaluate (pnl_stream).
        Viewing is the LAST step; the verdict is already decided by committed bars."""
        if self.output_type != "pnl_stream":
            raise ValueError("QuantStats tearsheet is for pnl_stream returns only")
        if not self._evaluated:
            raise RuntimeError("evaluate before rendering the tearsheet (no eyeball-gating)")
        import pandas as pd
        import quantstats as qs
        s = pd.Series(_clean(returns))
        qs.reports.html(s, output=output_html, title=title or f"{self.idea_id} Gate 5")
        return output_html
