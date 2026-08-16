"""
Tests for the strategy-spec workflow (task 57):
  - log_change(params_json=...) round-trips structured knobs
  - get_spec(idea_id) assembles per-component spec cards (live/proposed/dead)
"""
import json

import pytest

from research.code import strategy_log, db_init


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    db = tmp_path / "research.db"
    monkeypatch.setattr(db_init, "DB_PATH", db)
    monkeypatch.setattr(strategy_log, "DB_PATH", db)
    db_init.init()
    # spec requires a parent idea (FK)
    import sqlite3
    from research.code.infra import db_guard
    conn = sqlite3.connect(db)
    # Seeding a fixture IS a legitimate write, so it says so (migration 045).
    db_guard.arm(conn, reason="test fixture")
    conn.execute(
        "INSERT INTO step1_ideas (idea_id, name, created_at, updated_at) "
        "VALUES ('T-001','Test idea','2026-01-01 00:00:00','2026-01-01 00:00:00')"
    )
    conn.commit()
    conn.close()
    return db


# ---- log_change params_json ----

def test_params_json_roundtrips(tmp_db):
    strategy_log.log_change(
        "T-001", "born", "CREATED", component="exit", to_value="fixed_3R",
        params_json={"target_R": 3.0, "stop": "OR_opposite"},
    )
    row = strategy_log.get_lineage("T-001")[0]
    assert json.loads(row["params_json"]) == {"target_R": 3.0, "stop": "OR_opposite"}


def test_params_json_must_be_dict(tmp_db):
    with pytest.raises(ValueError):
        strategy_log.log_change(
            "T-001", "bad", "CREATED", component="exit", params_json=[1, 2, 3]
        )


def test_params_json_defaults_null(tmp_db):
    strategy_log.log_change("T-001", "born", "CREATED", component="exit", to_value="x")
    assert strategy_log.get_lineage("T-001")[0]["params_json"] is None


def test_set_params_attaches_to_existing_row(tmp_db):
    log_id = strategy_log.log_change("T-001", "live", "VALIDATED",
                                     component="anchor", to_value="09:00/N5")
    strategy_log.set_params(log_id, {"open": "09:00", "N": 5})
    spec = strategy_log.get_spec("T-001")
    assert spec["anchor"]["params"] == {"open": "09:00", "N": 5}


def test_set_params_requires_dict(tmp_db):
    log_id = strategy_log.log_change("T-001", "x", "VALIDATED", component="exit", to_value="y")
    with pytest.raises(ValueError):
        strategy_log.set_params(log_id, "not a dict")


# ---- get_spec ----

def test_spec_proposed_component(tmp_db):
    strategy_log.log_change(
        "T-001", "spec-birth", "CREATED", component="entry",
        to_value="immediate_breakout", params_json={"confirm": False},
    )
    spec = strategy_log.get_spec("T-001")
    assert spec["entry"]["status"] == "proposed"
    assert spec["entry"]["value"] == "immediate_breakout"
    assert spec["entry"]["params"] == {"confirm": False}


def test_spec_live_overrides_proposed(tmp_db):
    strategy_log.log_change("T-001", "birth", "CREATED", component="exit",
                            to_value="fixed_3R", params_json={"target_R": 3.0})
    strategy_log.log_change("T-001", "adopt", "ADOPTED", component="exit",
                            to_value="trail_1R", params_json={"trail_R": 1.0})
    spec = strategy_log.get_spec("T-001")
    assert spec["exit"]["status"] == "live"
    assert spec["exit"]["value"] == "trail_1R"
    assert spec["exit"]["params"] == {"trail_R": 1.0}


def test_spec_dead_component(tmp_db):
    strategy_log.log_change("T-001", "kill", "FALSIFIED", component="filter",
                            to_value="trend_gate")
    spec = strategy_log.get_spec("T-001")
    assert spec["filter"]["status"] == "dead"


def test_spec_counts_dead_variants(tmp_db):
    strategy_log.log_change("T-001", "live", "VALIDATED", component="exit", to_value="fixed_3R")
    strategy_log.log_change("T-001", "v1", "FALSIFIED", component="exit", to_value="fixedpip_2p0")
    strategy_log.log_change("T-001", "v2", "REJECTED", component="exit", to_value="atr_stop")
    spec = strategy_log.get_spec("T-001")
    assert spec["exit"]["status"] == "live"
    assert spec["exit"]["value"] == "fixed_3R"
    assert spec["exit"]["dead_variants"] == 2


def test_spec_excludes_config_and_birth(tmp_db):
    strategy_log.log_change("T-001", "born", "CREATED", to_value="strategy born")  # component=None
    strategy_log.log_change("T-001", "falsify", "FALSIFIED", component="config", to_value="look-ahead")
    spec = strategy_log.get_spec("T-001")
    assert "config" not in spec
    assert spec == {} or set(spec).issubset({"entry", "exit", "sizing", "anchor", "filter"})
