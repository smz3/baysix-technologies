"""Tests for the run_and_log harness (P1 task 58).

Covers the four locked design guarantees:
  1. FACT-ONLY        — verdict=None logs the result, touches nothing in the lineage.
  2. VERDICT opt-in   — verdict= writes one log_strategy row attached to the primary result.
  3. CLEAN-TREE gate  — dirty tree blocks; dirty_ok lets it through marked '-dirty'.
  4. CONTRACT guard   — a missing required metric is rejected before anything is written.
  +  COMPENSATING DELETE — a failed verdict write rolls back the orphaned result rows.
"""
import pytest

from core import pipeline, strategy_log, db_init, run_and_log


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    db = tmp_path / "research.db"
    for mod in (db_init, pipeline, strategy_log):
        monkeypatch.setattr(mod, "DB_PATH", db)
    db_init.init()
    import sqlite3
    from core.infra import db_guard
    conn = sqlite3.connect(db)
    # Seeding a fixture IS a legitimate write, so it says so (migration 045).
    db_guard.arm(conn, reason="test fixture")
    conn.execute(
        "INSERT INTO step1_ideas (idea_id, name, created_at, updated_at) "
        "VALUES ('ORB-T','Test ORB','2026-01-01 00:00:00','2026-01-01 00:00:00')"
    )
    conn.commit()
    conn.close()
    # default: a clean committed tree, deterministic sha (no real git in the test)
    monkeypatch.setattr(run_and_log, "_git_dirty", lambda: False)
    monkeypatch.setattr(run_and_log, "_git_sha", lambda: "deadbee")
    return db


def _rr(metrics):
    # stage='montecarlo' keeps these harness-mechanics tests decoupled from the
    # IS/OOS discipline (is_run label + frozen-config), which has its own coverage.
    return {
        "stage": "montecarlo", "period": "per_trade", "cost_adjusted": 1,
        "n_obs": 526, "data_start": "2024-05-02", "data_end": "2026-06-01",
        "metrics": metrics, "notes": "unit test",
    }


# 4. CONTRACT guard ──────────────────────────────────────────────────────────────
def test_contract_rejects_missing_required_metric(tmp_db):
    runner = lambda: _rr({"E_R": -0.08})          # ORB requires E_R AND t_stat
    with pytest.raises(ValueError, match="t_stat"):
        run_and_log.run_and_log("ORB-T", runner, gate_number=7)
    assert pipeline.get_results("ORB-T") == []     # nothing written


def test_unknown_family_rejected(tmp_db):
    with pytest.raises(ValueError, match="no contract"):
        run_and_log.run_and_log("ZZZ-9", lambda: _rr({"x": 1}), gate_number=3)


# 1. FACT-ONLY ───────────────────────────────────────────────────────────────────
def test_fact_only_logs_results_not_lineage(tmp_db):
    runner = lambda: _rr({"E_R": -0.0857, "t_stat": -1.67})
    out = run_and_log.run_and_log("ORB-T", runner, gate_number=7)

    assert out["log_id"] is None
    assert len(out["result_ids"]) == 2
    res = pipeline.get_results("ORB-T")
    assert {r["metric_key"] for r in res} == {"E_R", "t_stat"}
    assert strategy_log.get_lineage("ORB-T") == []   # verdict untouched


# 2. VERDICT opt-in ──────────────────────────────────────────────────────────────
def test_verdict_attaches_to_primary_result(tmp_db):
    runner = lambda: _rr({"E_R": -0.0857, "t_stat": -1.67})
    out = run_and_log.run_and_log(
        "ORB-T", runner, gate_number=7,
        verdict="FALSIFIED", component="config", to_value="look-ahead",
        rationale="EA-faithful fills negative across OOS",
    )
    assert out["log_id"] is not None
    lineage = strategy_log.get_lineage("ORB-T")
    assert len(lineage) == 1
    # the verdict row points at the PRIMARY metric (E_R), logged first
    assert lineage[0]["result_id"] == out["primary_result_id"]
    primary = [r for r in pipeline.get_results("ORB-T")
               if r["result_id"] == out["primary_result_id"]][0]
    assert primary["metric_key"] == "E_R"


# 3. CLEAN-TREE gate ─────────────────────────────────────────────────────────────
def test_dirty_tree_blocks(tmp_db, monkeypatch):
    monkeypatch.setattr(run_and_log, "_git_dirty", lambda: True)
    with pytest.raises(SystemExit, match="dirty"):
        run_and_log.run_and_log("ORB-T", lambda: _rr({"E_R": 1, "t_stat": 3}),
                                gate_number=7)
    assert pipeline.get_results("ORB-T") == []


def test_dirty_ok_marks_sha(tmp_db, monkeypatch):
    monkeypatch.setattr(run_and_log, "_git_dirty", lambda: True)
    out = run_and_log.run_and_log("ORB-T", lambda: _rr({"E_R": 1, "t_stat": 3}),
                                  gate_number=7, dirty_ok=True)
    row = pipeline.get_results("ORB-T")[0]
    assert row["git_sha"].endswith("-dirty")
    assert len(out["result_ids"]) == 2


# + COMPENSATING DELETE ──────────────────────────────────────────────────────────
def test_failed_verdict_rolls_back_results(tmp_db):
    # an invalid verdict makes log_change raise AFTER both result rows are written;
    # the harness must delete the orphans and re-raise.
    runner = lambda: _rr({"E_R": -0.08, "t_stat": -1.67})
    with pytest.raises(ValueError, match="verdict must be one of"):
        run_and_log.run_and_log("ORB-T", runner, gate_number=7, verdict="BOGUS")
    assert pipeline.get_results("ORB-T") == []        # rolled back
    assert strategy_log.get_lineage("ORB-T") == []
