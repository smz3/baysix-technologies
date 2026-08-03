"""
Task 290 acceptance: the adjudicator must be mechanical and un-negotiable.

These tests assert the FAILURE modes, not the happy path. The happy path was never the
risk — the risk is the agent talking itself into a promotion. Each test below is one
route by which that could happen, closed.
"""
import json
import sqlite3
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from research.code.gates import grw


# ─── rule evaluator ──────────────────────────────────────────────────────────

def test_rule_evaluates_mechanically():
    v = {k: None for k in grw.ADJUDICATION_VARS}
    v.update(is_growth=1.0, oos_growth=0.6, oos_n_trades=150)
    assert grw.eval_rule("oos_growth >= 0.5 * is_growth AND oos_n_trades >= 100", v)
    v.update(oos_growth=0.4)
    assert not grw.eval_rule("oos_growth >= 0.5 * is_growth AND oos_n_trades >= 100", v)


def test_unknown_variable_raises_rather_than_failing_open():
    """A typo'd threshold must STOP the adjudication. Returning False would look like a
    clean falsification; returning True would promote noise. Both are worse than a crash."""
    v = {k: 1.0 for k in grw.ADJUDICATION_VARS}
    with pytest.raises(ValueError, match="unknown variable"):
        grw.eval_rule("oos_growht >= 0.5", v)          # transposed letters
    with pytest.raises(ValueError, match="unknown variable"):
        grw.eval_rule("sharpe > 1.0", v)               # plausible but undeclared


def test_null_input_raises_rather_than_comparing_as_zero():
    v = {k: 1.0 for k in grw.ADJUDICATION_VARS}
    v["oos_growth"] = None
    with pytest.raises(ValueError, match="NULL"):
        grw.eval_rule("oos_growth > 0", v)


@pytest.mark.parametrize("evil", [
    "__import__('os').system('echo pwned')",
    "open('/etc/passwd').read()",
    "oos_growth.__class__",
    "[x for x in range(10)]",
    "(lambda: True)()",
])
def test_rule_is_not_eval(evil):
    v = {k: 1.0 for k in grw.ADJUDICATION_VARS}
    with pytest.raises(ValueError):
        grw.eval_rule(evil, v)


def test_sql_style_and_or_accepted():
    v = {k: 1.0 for k in grw.ADJUDICATION_VARS}
    assert grw.eval_rule("oos_growth > 0 AND is_growth > 0", v)
    assert grw.eval_rule("oos_growth > 99 OR is_growth > 0", v)


# ─── pre-registration ────────────────────────────────────────────────────────

def test_prereg_sha_is_order_and_whitespace_invariant():
    a = {"batch_id": "b", "hypothesis": "h", "promote_if": "oos_growth > 0"}
    b = {"promote_if": "oos_growth > 0", "hypothesis": "h", "batch_id": "b"}
    assert grw.prereg_sha(a) == grw.prereg_sha(b)


def test_prereg_sha_changes_when_threshold_moves():
    a = {"batch_id": "b", "promote_if": "oos_growth >= 0.5 * is_growth"}
    b = {"batch_id": "b", "promote_if": "oos_growth >= 0.2 * is_growth"}
    assert grw.prereg_sha(a) != grw.prereg_sha(b)


def test_sha_excludes_the_sha_field_itself():
    a = {"batch_id": "b", "promote_if": "oos_growth > 0"}
    sha = grw.prereg_sha(a)
    assert grw.prereg_sha({**a, "prereg_sha": sha}) == sha


def test_overlapping_is_oos_windows_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(grw, "RUNS_DIR", tmp_path)
    with pytest.raises(ValueError, match="OVERLAP|AFTER OOS starts"):
        grw.register_batch(
            batch_id="x", idea_id="GRW-001", trial_family_id="f", hypothesis="h",
            mechanism="m", is_window=["2016-01-01", "2025-01-01"],
            oos_window=["2024-01-01", "2026-01-01"], n_trials_budget=10,
            promote_if="oos_growth > 0")


def test_missing_mechanism_rejected(tmp_path, monkeypatch):
    """Spec 3.0: a config with no stated mechanism is a lottery ticket."""
    monkeypatch.setattr(grw, "RUNS_DIR", tmp_path)
    with pytest.raises(ValueError, match="mechanism"):
        grw.register_batch(
            batch_id="x", idea_id="GRW-001", trial_family_id="f", hypothesis="h",
            mechanism="  ", is_window=["2016-01-01", "2023-12-31"],
            oos_window=["2024-01-01", "2026-06-30"], n_trials_budget=10,
            promote_if="oos_growth > 0")


def test_unparseable_rule_rejected_at_registration_not_after_the_compute(tmp_path, monkeypatch):
    monkeypatch.setattr(grw, "RUNS_DIR", tmp_path)
    with pytest.raises(ValueError, match="unknown variable"):
        grw.register_batch(
            batch_id="x", idea_id="GRW-001", trial_family_id="f", hypothesis="h",
            mechanism="m", is_window=["2016-01-01", "2023-12-31"],
            oos_window=["2024-01-01", "2026-06-30"], n_trials_budget=10,
            promote_if="sharpe_ratio > 1.0")


# ─── tamper detection (the load-bearing test) ────────────────────────────────

def _fake_batch(tmp_path, monkeypatch, promote_if="oos_growth >= 0.5 * is_growth"):
    """Build a registered batch against a throwaway DB + prereg dir."""
    db = tmp_path / "t.db"
    conn = sqlite3.connect(db)
    # grw_passes FKs into tester_runs (the IS/OOS legs are real MT5 runs), so the
    # fixture needs the ledger spine too — same shape as the live DB.
    from research.code.infra.schema_ledger import SCHEMA_MT5, SCHEMA_GRW
    conn.executescript(SCHEMA_MT5)
    conn.executescript(SCHEMA_GRW)
    conn.commit()
    conn.close()
    monkeypatch.setattr(grw, "DB_PATH", db)
    monkeypatch.setattr(grw, "RUNS_DIR", tmp_path / "runs")
    monkeypatch.setattr(grw, "REPO", tmp_path)
    grw.register_batch(
        batch_id="b1", idea_id="GRW-001", trial_family_id="fam1", hypothesis="h",
        mechanism="m", is_window=["2016-01-01", "2023-12-31"],
        oos_window=["2024-01-01", "2026-06-30"], n_trials_budget=5,
        promote_if=promote_if, kill_if="oos_growth <= 0")
    return db


def test_editing_prereg_after_registration_aborts_adjudication(tmp_path, monkeypatch):
    """THE test. Moving the goalpost after seeing results must be impossible, not
    merely discouraged."""
    _fake_batch(tmp_path, monkeypatch)
    path = tmp_path / "runs" / "b1" / "prereg.json"
    prereg = json.loads(path.read_text())
    prereg["promote_if"] = "oos_growth >= 0.01 * is_growth"     # lower the bar
    path.write_text(json.dumps(prereg, indent=2))

    with pytest.raises(ValueError, match="PREREG TAMPERED"):
        grw.adjudicate("b1")


def test_clean_prereg_loads(tmp_path, monkeypatch):
    _fake_batch(tmp_path, monkeypatch)
    assert grw.load_prereg("b1")["batch_id"] == "b1"


def test_prereg_never_overwritten(tmp_path, monkeypatch):
    _fake_batch(tmp_path, monkeypatch)
    with pytest.raises(FileExistsError):
        grw.register_batch(
            batch_id="b1", idea_id="GRW-001", trial_family_id="fam1", hypothesis="h2",
            mechanism="m2", is_window=["2016-01-01", "2023-12-31"],
            oos_window=["2024-01-01", "2026-06-30"], n_trials_budget=5,
            promote_if="oos_growth > 0")


# ─── ladder discipline ───────────────────────────────────────────────────────

def test_trial_budget_is_enforced(tmp_path, monkeypatch):
    """Widening the budget after seeing results is never automated (spec 3.4)."""
    _fake_batch(tmp_path, monkeypatch)
    for i in range(5):
        grw.log_pass("b1", {"i": i}, is_fitness=float(i), is_growth=float(i),
                     is_n_trades=100)
    with pytest.raises(ValueError, match="n_trials_budget"):
        grw.log_pass("b1", {"i": 99}, is_fitness=9.0)


def test_oos_leg_requires_an_is_leg(tmp_path, monkeypatch):
    _fake_batch(tmp_path, monkeypatch)
    pid = grw.log_pass("b1", {"i": 0})            # no IS numbers attached
    with pytest.raises(ValueError, match="no in-sample leg"):
        grw.record_oos(pid, oos_growth=1.0, oos_n_trades=100)


def test_looking_at_oos_latches_oos_spent(tmp_path, monkeypatch):
    db = _fake_batch(tmp_path, monkeypatch)
    pid = grw.log_pass("b1", {"i": 0}, is_fitness=1.0, is_growth=1.0, is_n_trades=100)
    grw.record_oos(pid, oos_growth=0.9, oos_n_trades=120, oos_fitness=0.9)
    conn = sqlite3.connect(db)
    assert conn.execute("SELECT oos_spent FROM grw_batches WHERE batch_id='b1'"
                        ).fetchone()[0] == 1


def test_adjudication_assigns_one_verdict_per_held_out_pass(tmp_path, monkeypatch):
    db = _fake_batch(tmp_path, monkeypatch)
    winner = grw.log_pass("b1", {"i": 1}, is_fitness=2.0, is_growth=1.0, is_n_trades=200)
    loser  = grw.log_pass("b1", {"i": 2}, is_fitness=1.5, is_growth=1.0, is_n_trades=200)
    dead   = grw.log_pass("b1", {"i": 3}, is_fitness=1.2, is_growth=1.0, is_n_trades=200)
    never  = grw.log_pass("b1", {"i": 4}, is_fitness=0.5, is_growth=1.0, is_n_trades=200)

    grw.record_oos(winner, oos_growth=0.9, oos_n_trades=150, oos_fitness=0.9)
    grw.record_oos(loser,  oos_growth=0.2, oos_n_trades=150, oos_fitness=0.2)
    grw.record_oos(dead,   oos_growth=-0.3, oos_n_trades=150, oos_fitness=-0.3)
    # `never` is deliberately not held out

    counts = grw.adjudicate("b1")
    assert counts == {"PROMOTED": 1, "FALSIFIED": 1, "KILLED": 1, "SKIPPED": 1}

    conn = sqlite3.connect(db)
    verdicts = dict(conn.execute("SELECT pass_id, verdict FROM grw_passes").fetchall())
    assert verdicts[winner] == "PROMOTED"
    assert verdicts[loser] == "FALSIFIED"
    assert verdicts[dead] == "KILLED"
    assert verdicts[never] == "PENDING"


def test_promote_refuses_a_pass_the_adjudicator_did_not_promote(tmp_path, monkeypatch):
    """The agent does not get to override a verdict."""
    _fake_batch(tmp_path, monkeypatch)
    loser = grw.log_pass("b1", {"i": 2}, is_fitness=1.0, is_growth=1.0, is_n_trades=200)
    grw.record_oos(loser, oos_growth=0.2, oos_n_trades=150, oos_fitness=0.2)
    grw.adjudicate("b1")
    with pytest.raises(ValueError, match="not PROMOTED"):
        grw.promote(loser)


def test_trial_count_accumulates_across_batches(tmp_path, monkeypatch):
    """The reason GRW shares research.db: one family, one denominator."""
    _fake_batch(tmp_path, monkeypatch)
    for i in range(3):
        grw.log_pass("b1", {"i": i}, is_fitness=float(i))
    grw.register_batch(
        batch_id="b2", idea_id="GRW-001", trial_family_id="fam1", hypothesis="h2",
        mechanism="m2", is_window=["2016-01-01", "2023-12-31"],
        oos_window=["2024-01-01", "2026-06-30"], n_trials_budget=5,
        promote_if="oos_growth > 0")
    for i in range(2):
        grw.log_pass("b2", {"i": i}, is_fitness=float(i))

    fam = grw.family_trials("fam1")
    assert fam["n_trials_cum"] == 5, "trials must pool across batches, not reset"
    assert fam["n_batches"] == 2


def test_no_promotion_streak_counts_consecutive_barren_batches(tmp_path, monkeypatch):
    db = _fake_batch(tmp_path, monkeypatch)
    conn = sqlite3.connect(db)
    conn.execute("UPDATE grw_batches SET stage='S3', n_promoted=0 WHERE batch_id='b1'")
    conn.commit()
    conn.close()
    assert grw.no_promotion_streak("fam1") == 1
