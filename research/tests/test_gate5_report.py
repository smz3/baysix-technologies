"""Tests for the Gate-5 reporting layer (Protocol 3.2, task 83)."""
import numpy as np
import pytest

from research.code import gate5_report as g5


def _pos_returns(n=500, mu=0.05, sd=1.0, seed=0):
    return np.random.default_rng(seed).normal(mu, sd, n)


# ---- PSR / DSR / per-period convention ----

def test_psr_in_unit_interval_and_directional():
    pos = _pos_returns(mu=0.10)
    neg = _pos_returns(mu=-0.10)
    p_pos, p_neg = g5.psr(pos), g5.psr(neg)
    assert 0.0 <= p_pos <= 1.0 and 0.0 <= p_neg <= 1.0
    assert p_pos > 0.5 > p_neg


def test_sharpe_t_is_per_period_times_sqrt_T():
    r = _pos_returns(n=400, mu=0.1)
    assert np.isclose(g5.sharpe_t(r), g5.sharpe_per_period(r) * np.sqrt(len(r)))


def test_dsr_deflates_below_psr():
    r = _pos_returns(mu=0.08)
    plain = g5.psr(r)
    deflated = g5.dsr(r, var_sr=0.02, n_trials=50)
    assert deflated <= plain  # beating a higher benchmark is harder


def test_psr_handles_zero_variance():
    assert np.isnan(g5.psr(np.ones(100)))


# ---- pre-commit gate flow ----

def test_bars_must_precede_evaluate():
    rep = g5.Gate5Report("X", "pnl_stream")
    rep.evaluate_pnl(_pos_returns())
    with pytest.raises(RuntimeError):
        rep.commit_bars(psr=0.9, sharpe_t=2.0)


def test_commit_requires_multiple_bars():
    rep = g5.Gate5Report("X", "pnl_stream")
    with pytest.raises(ValueError):
        rep.commit_bars(psr=0.9)  # only one — eyeball-gating risk


def test_verdict_pass_when_all_bars_met():
    rep = g5.Gate5Report("X", "pnl_stream")
    rep.commit_bars(psr=0.5, sharpe_t=0.0, net_mean=-1.0)  # lax bars
    rep.evaluate_pnl(_pos_returns(mu=0.1))
    assert rep.verdict() is True


def test_verdict_fail_when_a_bar_missed():
    rep = g5.Gate5Report("X", "pnl_stream")
    rep.commit_bars(psr=0.999, sharpe_t=99.0, net_mean=0.0)  # unmeetable
    rep.evaluate_pnl(_pos_returns(mu=0.05))
    assert rep.verdict() is False


def test_tearsheet_blocked_before_evaluate(tmp_path):
    rep = g5.Gate5Report("X", "pnl_stream")
    rep.commit_bars(psr=0.5, sharpe_t=0.0)
    with pytest.raises(RuntimeError):
        rep.tearsheet(_pos_returns(), str(tmp_path / "x.html"))


def test_evaluate_pnl_rejects_wrong_output_type():
    rep = g5.Gate5Report("X", "classifier_score")
    with pytest.raises(ValueError):
        rep.evaluate_pnl(_pos_returns())


# ---- classifier branch ----

def test_classifier_auc_ci():
    rng = np.random.default_rng(1)
    y = rng.integers(0, 2, 400)
    scores = y + rng.normal(0, 0.5, 400)  # informative
    rep = g5.Gate5Report("C", "classifier_score")
    rep.commit_bars(auc_lo=0.5, ic_t=0.0)
    m = rep.evaluate_classifier(y_true=y, scores=scores, ic_series=rng.normal(0.1, 1, 50))
    assert 0.5 < m["auc"] <= 1.0
    assert m["auc_lo"] <= m["auc"] <= m["auc_hi"]


def test_report_renders():
    rep = g5.Gate5Report("X", "pnl_stream")
    rep.commit_bars(psr=0.5, sharpe_t=0.0, net_mean=-1.0)
    rep.evaluate_pnl(_pos_returns(mu=0.1))
    txt = rep.report()
    assert "Gate 5" in txt and "PSR" in txt
