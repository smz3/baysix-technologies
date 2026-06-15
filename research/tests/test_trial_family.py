"""Task 87 — trial-family ledger feeds a TRUE DSR (not silent PSR)."""
import numpy as np
import pytest

from research.code import db_init, pipeline, trial_family, gate5_report


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    db = tmp_path / "research.db"
    for mod in (db_init, pipeline, trial_family):
        monkeypatch.setattr(mod, "DB_PATH", db)
    db_init.init()
    pipeline.add_idea("TF-001", "trial family test", "desc", "test")
    return db


def _log_family(n, base_sr=1.0, spread=0.3):
    fam = "TF-001_sweep"
    trial_family.open_family(fam, "TF-001", description="sweep")
    for i in range(n):
        trial_family.log_trial(
            fam, "TF-001", config_hash=f"cfg{i}",
            sharpe=base_sr + spread * i, n_obs=200,
            git_sha="deadbeef", code_path="test",
        )
    return fam


def test_ledger_computes_n_and_var(tmp_db):
    fam = _log_family(4, base_sr=1.0, spread=0.5)  # sharpes 1.0,1.5,2.0,2.5
    row = trial_family.read_family(fam)
    assert row["n_configs"] == 4
    expected_var = float(np.var([1.0, 1.5, 2.0, 2.5], ddof=1))
    assert row["var_sr"] == pytest.approx(expected_var)
    nt, var = trial_family.deflation_inputs(fam)
    assert nt == 4 and var == pytest.approx(expected_var)


def test_single_config_no_variance(tmp_db):
    fam = _log_family(1)
    nt, var = trial_family.deflation_inputs(fam)
    assert nt == 1 and var is None


def test_missing_family_is_psr_inputs(tmp_db):
    nt, var = trial_family.deflation_inputs("nope")
    assert nt == 0 and var is None


def test_select_config(tmp_db):
    fam = _log_family(3)
    trial_family.select_config(fam, "cfg1")
    assert trial_family.read_family(fam)["selected_config_hash"] == "cfg1"


def test_gate5_auto_dsr_from_family(tmp_db):
    fam = _log_family(8, base_sr=0.5, spread=0.2)
    rng = np.random.default_rng(0)
    returns = rng.normal(0.02, 0.1, 500)  # positive-edge pnl stream
    rep = gate5_report.Gate5Report("TF-001", "pnl_stream")
    rep.commit_bars(psr=0.5, sharpe_t=1.0, net_mean=0.0)
    rep.evaluate_pnl(returns, family_id=fam)
    # DSR ran: deflated benchmark > 0, so DSR < PSR (penalised for 8 trials)
    assert "dsr" in rep.metrics
    assert rep.metrics["sr_benchmark"] > 0
    assert rep.metrics["dsr"] < rep.metrics["psr"]
    assert "DSR ran" in rep.report()


def test_gate5_psr_when_no_family(tmp_db):
    rng = np.random.default_rng(1)
    returns = rng.normal(0.02, 0.1, 500)
    rep = gate5_report.Gate5Report("TF-001", "pnl_stream")
    rep.commit_bars(psr=0.5, sharpe_t=1.0, net_mean=0.0)
    rep.evaluate_pnl(returns)  # no family
    assert "dsr" not in rep.metrics
    assert "PSR only" in rep.report()
