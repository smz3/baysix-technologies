"""
Tests for Protocol 3.2 enforcement (task 80) — pipeline obeys the idea_kind /
output_type metadata, not free assertion:

  - open_gate refuses a gate not applicable to the idea_kind (primitive skips 3-6)
  - _check_previous_gate_passed uses the previous APPLICABLE gate (legal skip)
  - pass_gate(5) refuses unless a step4_results metric_key matches the significance
    test resolved from output_type (pnl_stream->psr/dsr, classifier_score->ic_t/auc)
  - untagged ideas keep 3.1 behaviour (no enforcement)

Single source of truth for the test<->metric mapping lives in protocol.py; this
suite pins both the resolver and the pipeline guard that consumes it.
"""
import sqlite3

import pytest

from research.code import db_init, pipeline, protocol, strategy_log


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    db = tmp_path / "research.db"
    monkeypatch.setattr(db_init, "DB_PATH", db)
    monkeypatch.setattr(pipeline, "DB_PATH", db)
    monkeypatch.setattr(strategy_log, "DB_PATH", db)
    db_init.init()
    return db


def _add(idea_id, kind=None, output_type=None):
    pipeline.add_idea(idea_id, idea_id, "desc", "test")
    if kind or output_type:
        f = {}
        if kind:
            f["idea_kind"] = kind
        if output_type:
            f["output_type"] = output_type
        pipeline.update_idea(idea_id, **f)


def _pass(idea_id, gate, answer="ok"):
    pipeline.open_gate(idea_id, gate, pass_criteria="x")
    pipeline.pass_gate(idea_id, gate, gate_answer=answer)


# ---- protocol resolver (single source of truth) ----

def test_metric_key_matches_sigtest():
    assert protocol.metric_key_matches_sigtest("pnl_stream", "psr_net") is True
    assert protocol.metric_key_matches_sigtest("pnl_stream", "E_R_net_per_trade") is False
    assert protocol.metric_key_matches_sigtest("classifier_score", "regime_change_auc_hmm") is True
    assert protocol.metric_key_matches_sigtest("classifier_score", "ic_t_stat") is True
    assert protocol.metric_key_matches_sigtest("primitive_output", "foundation_check") is False
    assert protocol.metric_key_matches_sigtest(None, "psr") is False


# ---- applicability: legal skip ----

def test_primitive_cannot_open_nonapplicable_gate(tmp_db):
    _add("P-001", kind="primitive", output_type="primitive_output")
    _pass("P-001", 0); _pass("P-001", 1); _pass("P-001", 2)
    with pytest.raises(ValueError, match="not applicable"):
        pipeline.open_gate("P-001", 3, pass_criteria="x")


def test_primitive_gate7_uses_previous_applicable_gate(tmp_db):
    # primitive applies {0,1,2,7}; gate 7's predecessor is gate 2, not gate 6.
    _add("P-002", kind="primitive", output_type="primitive_output")
    _pass("P-002", 0); _pass("P-002", 1); _pass("P-002", 2)
    pipeline.open_gate("P-002", 7, pass_criteria="x")  # must NOT raise on missing 3-6


def test_strategy_keeps_full_ladder_sequencing(tmp_db):
    _add("S-001", kind="strategy", output_type="pnl_stream")
    _pass("S-001", 0); _pass("S-001", 1)
    with pytest.raises(ValueError, match="previous applicable gate 2"):
        pipeline.open_gate("S-001", 3, pass_criteria="x")  # gate 2 not passed


# ---- pass_gate(5) significance-test match ----

def _walk_to_gate5(idea_id):
    for g in (0, 1, 2, 3, 4):
        _pass(idea_id, g)
    pipeline.open_gate(idea_id, 5, pass_criteria="net edge")


def _log5(idea_id, metric_key, value=1.0):
    pipeline.log_result(idea_id, 5, "IS", metric_key, value, cost_adjusted=1,
                        period="per_trade", n_obs=500, data_start="2019-01-01",
                        data_end="2024-01-01", git_sha="deadbeef", code_path="x.py")


def test_pnl_stream_gate5_blocked_without_psr(tmp_db):
    _add("S-002", kind="strategy", output_type="pnl_stream")
    _walk_to_gate5("S-002")
    _log5("S-002", "E_R_net_per_trade")  # wrong test family
    with pytest.raises(ValueError, match="significance test"):
        pipeline.pass_gate("S-002", 5, gate_answer="edge present")


def test_pnl_stream_gate5_passes_with_psr(tmp_db):
    _add("S-003", kind="strategy", output_type="pnl_stream")
    _walk_to_gate5("S-003")
    _log5("S-003", "psr_net")
    pipeline.pass_gate("S-003", 5, gate_answer="PSR>0")  # must NOT raise


def test_classifier_gate5_passes_with_auc(tmp_db):
    _add("C-001", kind="classifier", output_type="classifier_score")
    _walk_to_gate5("C-001")
    _log5("C-001", "regime_change_auc_recal")
    pipeline.pass_gate("C-001", 5, gate_answer="AUC CI clears")


def test_protocol_doc_gate_questions_match_code():
    """Single-source guard (task 84): the gate questions in research_protocol.md must
    mirror pipeline.GATE_QUESTIONS verbatim — code is canonical, the doc is the bug."""
    from pathlib import Path
    doc = (Path(__file__).resolve().parents[2]
           / "docs" / "reference" / "research_protocol.md").read_text(encoding="utf-8")
    for n, q in pipeline.GATE_QUESTIONS.items():
        assert q in doc, f"Gate {n} question drifted from code: {q!r} not in protocol doc"


def test_untagged_gate5_not_enforced(tmp_db):
    _add("U-001")  # no idea_kind / output_type -> 3.1 back-compat
    _walk_to_gate5("U-001")
    _log5("U-001", "anything")
    pipeline.pass_gate("U-001", 5, gate_answer="legacy")  # must NOT raise


def test_gate5_waiver_bypasses(tmp_db):
    _add("S-004", kind="strategy", output_type="pnl_stream")
    _walk_to_gate5("S-004")
    _log5("S-004", "E_R_net_per_trade")
    pipeline.pass_gate("S-004", 5, gate_answer="WAIVER: ...", allow_incomplete=True)


# ---- task 81: spec components + driver advisories ----

def test_conditioning_management_are_first_class_components():
    assert "conditioning" in strategy_log.VALID_COMPONENT
    assert "management" in strategy_log.VALID_COMPONENT
    assert "conditioning" in strategy_log.SPEC_COMPONENTS
    assert "management" in strategy_log.SPEC_COMPONENTS


def test_log_change_accepts_conditioning(tmp_db):
    _add("S-010", kind="strategy", output_type="pnl_stream")
    log_id = strategy_log.log_change(
        "S-010", "born", "CREATED", component="conditioning",
        to_value="trend_up_200d", rationale="mechanism: breakouts persist with HTF trend",
    )
    assert log_id


def test_advisory_warns_undeclared_output_type(tmp_db):
    _add("S-011", kind="strategy")  # no output_type
    _pass("S-011", 0); _pass("S-011", 1)
    warns = protocol.next_step("S-011")["warnings"]
    assert any("output_type UNDECLARED" in w for w in warns)


def test_advisory_warns_gate3_without_conditioning(tmp_db):
    _add("S-012", kind="strategy", output_type="pnl_stream")
    for g in (0, 1, 2):
        _pass("S-012", g)
    pipeline.open_gate("S-012", 3, pass_criteria="edge")  # gate 3 reached, no conditioning
    warns = protocol.next_step("S-012")["warnings"]
    assert any("no conditioning declared" in w.lower() for w in warns)


def test_advisory_silent_once_conditioning_declared(tmp_db):
    _add("S-013", kind="strategy", output_type="pnl_stream")
    for g in (0, 1, 2):
        _pass("S-013", g)
    strategy_log.log_change("S-013", "born", "CREATED", component="conditioning",
                            to_value="asia_range_low_vol")
    pipeline.open_gate("S-013", 3, pass_criteria="edge")
    warns = protocol.next_step("S-013")["warnings"]
    assert not any("conditioning" in w.lower() for w in warns)
