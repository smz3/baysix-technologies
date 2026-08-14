"""Tests for the parts that stop the factory grading its own homework.

Provenance, the strategy spec, the restricted rule evaluator, and pre-registration
immutability. Each test names the failure it prevents.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from factory.adjudicate import (
    ADJUDICATION_VARS,
    RuleError,
    Ruling,
    adjudicate,
    eval_rule,
)
from factory.prereg import PreregError, load, prereg_sha, register
from factory.provenance import (
    Claim,
    Provenance,
    assumed,
    cited,
    derived,
    measured,
    require_evidence,
)
from factory.spec import SpecError, StrategySpec
from factory.venue import Window


# --------------------------------------------------------------------------- #
#  provenance
# --------------------------------------------------------------------------- #


def test_recalled_is_a_banned_provenance_class():
    """Recall produces errors; execution catches them. The class exists in the enum
    only as a named rejection, so it fails loudly rather than being spelled some
    other way and slipping through."""
    with pytest.raises(ValueError, match="banned"):
        Provenance("RECALLED")


def test_a_claim_cannot_be_made_without_a_source():
    with pytest.raises(ValueError, match="no source"):
        Claim("n_trades", 412, Provenance.MEASURED, source="")


def test_an_assumption_must_name_its_falsifier():
    """An assumption with no falsifier is a belief, and beliefs do not go in a ledger."""
    with pytest.raises(ValueError, match="falsify"):
        Claim("fill_slippage", 0.5, Provenance.ASSUMED, source="   ")
    ok = assumed("fill_slippage", 0.5, falsified_by="measured fills from mbp-1 quotes")
    assert "falsified by" in ok.cite()


def test_assumed_values_are_not_evidence_and_block_a_decision():
    good = measured("net_usd", 812.40, command="pytest -k smoke")
    bad = assumed("commission", 1.29, falsified_by="the broker's own fee schedule")
    assert good.is_evidence and not bad.is_evidence
    require_evidence(good)  # does not raise
    with pytest.raises(ValueError, match="ASSUMED"):
        require_evidence(good, bad)


def test_claim_round_trips_to_a_ledger_row():
    c = derived("p_hat", 0.58, formula="14 / 24")
    row = c.to_row()
    assert row["provenance"] == "DERIVED"
    assert row["source"] == "14 / 24"
    assert cited("tick_value", 1.0, "config/costs/cme.yaml").provenance is Provenance.CITED


# --------------------------------------------------------------------------- #
#  strategy spec
# --------------------------------------------------------------------------- #


def _spec(**over) -> StrategySpec:
    base = dict(
        family="mgc-breakout",
        instrument="MGC",
        signal_tf="M5",
        entry={"type": "DONCHIAN_BREAK", "lookback": 20},
        exit={"type": "FIXED_RR", "rr": 2.0},
        risk={"mode": "CONTRACTS_FIXED", "n": 1},
        filters=("SESSION_RTH",),
        mechanism=(
            "Liquidity resting beyond the overnight extreme is swept by index "
            "rebalancing flow at the RTH open, so the first break carries."
        ),
    )
    base.update(over)
    return StrategySpec(**base)


def test_a_valid_spec_hashes_stably():
    a, b = _spec(), _spec()
    assert a.config_hash == b.config_hash
    assert len(a.config_hash) == 16


def test_rewording_the_mechanism_does_not_mint_a_new_config():
    """Prose is excluded from identity on purpose: two specs differing only in
    wording must COLLIDE, or the trial counter silently inflates."""
    a = _spec()
    b = _spec(mechanism="A completely different sentence explaining the same edge.")
    assert a.config_hash == b.config_hash


def test_changing_a_parameter_does_mint_a_new_config():
    a = _spec()
    b = _spec(entry={"type": "DONCHIAN_BREAK", "lookback": 30})
    assert a.config_hash != b.config_hash


def test_filter_order_does_not_change_identity():
    a = _spec(filters=("SESSION_RTH", "VOL_FLOOR"))
    b = _spec(filters=("VOL_FLOOR", "SESSION_RTH"))
    assert a.config_hash == b.config_hash


def test_duplicate_filters_are_rejected():
    with pytest.raises(SpecError, match="duplicate"):
        _spec(filters=("VOL_FLOOR", "VOL_FLOOR"))


def test_unknown_primitives_are_rejected():
    """An unknown primitive is skipped by one engine and honoured by the other,
    which produces two different strategies wearing the same config hash."""
    with pytest.raises(SpecError, match="entry type"):
        _spec(entry={"type": "MAGIC_CROSSOVER"})
    with pytest.raises(SpecError, match="exit type"):
        _spec(exit={"type": "VIBES"})
    with pytest.raises(SpecError, match="filters"):
        _spec(filters=("MOON_PHASE",))
    with pytest.raises(SpecError, match="timeframes"):
        _spec(signal_tf="M7")


def test_a_spec_without_a_mechanism_is_rejected():
    with pytest.raises(SpecError, match="lottery ticket"):
        _spec(mechanism="")
    with pytest.raises(SpecError, match="lottery ticket"):
        _spec(mechanism="looks good")


def test_a_mechanism_that_cites_evidence_instead_of_a_mechanism_is_rejected():
    """'The backtest is profitable' is not a reason the edge should exist."""
    with pytest.raises(SpecError, match="not a mechanism"):
        _spec(mechanism="The backtest shows it works across every year we tested.")


def test_a_hand_edited_spec_file_is_rejected_on_load(tmp_path):
    """Breaking the link between a result and the strategy that produced it is the
    quietest way to make a whole batch meaningless."""
    p = _spec().write(tmp_path / "s.json")
    payload = json.loads(p.read_text())
    payload["entry"]["lookback"] = 99
    p.write_text(json.dumps(payload))
    with pytest.raises(SpecError, match="config_hash mismatch"):
        StrategySpec.load(p)


def test_spec_round_trips():
    a = _spec()
    b = StrategySpec.from_dict(json.loads(a.to_json()))
    assert b.config_hash == a.config_hash
    assert b.mechanism == a.mechanism


# --------------------------------------------------------------------------- #
#  the restricted rule evaluator
# --------------------------------------------------------------------------- #


VALUES = {k: 1.0 for k in ADJUDICATION_VARS} | {
    "is_p_hat": 0.62, "oos_p_hat": 0.55, "oos_n_resolved": 40.0, "n_trials": 18.0,
}


def test_a_normal_rule_evaluates():
    assert eval_rule("oos_p_hat >= 0.5 AND oos_n_resolved >= 20", VALUES) is True
    assert eval_rule("oos_p_hat >= 0.9", VALUES) is False


def test_a_typo_raises_instead_of_quietly_failing_open():
    """A rule that silently fails open promotes on a typo, and a typo'd threshold
    that returns False is indistinguishable from a clean falsification."""
    with pytest.raises(RuleError, match="unknown variable"):
        eval_rule("oos_phat >= 0.5", VALUES)


def test_a_null_input_raises_instead_of_comparing_as_zero():
    """A missing holdout leg must STOP the adjudication, not read as a failure."""
    with pytest.raises(RuleError, match="NULL"):
        eval_rule("oos_p_hat >= 0.5", VALUES | {"oos_p_hat": None})


def test_calls_and_attributes_are_illegal():
    for bad in (
        "max(oos_p_hat, 0.5) > 0.4",
        "oos_p_hat.real > 0.4",
        "[oos_p_hat][0] > 0.4",
        "(lambda: 1)() > 0",
        "__import__('os').system('echo hi') > 0",
    ):
        with pytest.raises(RuleError):
            eval_rule(bad, VALUES)


def test_an_empty_rule_raises():
    with pytest.raises(RuleError, match="empty"):
        eval_rule("   ", VALUES)


def test_arithmetic_and_the_trial_counter_are_allowed():
    """The bar should be able to rise as the search widens."""
    assert eval_rule("oos_p_hat >= 0.5 + n_trials / 1000", VALUES) is True


def test_adjudication_returns_the_inputs_it_actually_read():
    v = adjudicate("oos_p_hat >= 0.5", "oos_p_hat <= 0.2", VALUES)
    assert v.ruling is Ruling.PROMOTE
    assert set(v.inputs_used) == {"oos_p_hat"}
    assert v.inputs_used["oos_p_hat"] == 0.55


def test_adjudication_can_falsify_and_can_do_nothing():
    low = VALUES | {"oos_p_hat": 0.1}
    assert adjudicate("oos_p_hat >= 0.5", "oos_p_hat <= 0.2", low).ruling is Ruling.FALSIFIED
    mid = VALUES | {"oos_p_hat": 0.35}
    assert adjudicate("oos_p_hat >= 0.5", "oos_p_hat <= 0.2", mid).ruling is Ruling.NO_ACTION


def test_a_self_contradictory_prereg_raises_rather_than_picking_a_winner():
    with pytest.raises(RuleError, match="self-contradictory"):
        adjudicate("oos_p_hat >= 0.1", "oos_p_hat >= 0.1", VALUES)


# --------------------------------------------------------------------------- #
#  pre-registration
# --------------------------------------------------------------------------- #


GOOD = dict(
    batch_id="mgc-2026-08-13-001",
    family="mgc-breakout",
    instrument="MGC",
    hypothesis="RTH-open breaks of the overnight range clear cost on MGC.",
    mechanism=(
        "Overnight liquidity rests beyond the Globex extreme and is swept by "
        "index-rebalance flow at the cash open, so the first break carries."
    ),
    objective_ref="barrier_prop_topstep50k_v1.0.0.json@abc123",
    is_window=["2016-01-01", "2023-12-31"],
    oos_window=["2024-01-01", "2026-06-30"],
    n_trials_budget=20,
    promote_if="oos_p_hat >= 0.5 AND oos_n_resolved >= 20",
    kill_if="oos_p_hat <= 0.2",
)


def test_registering_writes_a_hashed_prereg(tmp_path):
    pre = register(tmp_path, **GOOD)
    assert pre.path.exists()
    assert pre.sha == prereg_sha(pre.payload)
    assert pre.payload["oos_spent"] is False
    load(pre.path).verify()


def test_a_prereg_cannot_be_overwritten(tmp_path):
    """Changing a threshold opens a NEW batch. The old one stays on the record,
    including its failure — that is what keeps the trial count honest."""
    register(tmp_path, **GOOD)
    with pytest.raises(PreregError, match="immutable"):
        register(tmp_path, **(GOOD | {"promote_if": "oos_p_hat >= 0.3 AND oos_n_resolved >= 5"}))


def test_a_hand_edited_prereg_is_rejected_on_load(tmp_path):
    pre = register(tmp_path, **GOOD)
    payload = json.loads(pre.path.read_text())
    payload["promote_if"] = "oos_p_hat >= 0.05"
    pre.path.write_text(json.dumps(payload))
    with pytest.raises(PreregError, match="edited since registration"):
        load(pre.path)


def test_overlapping_windows_are_rejected(tmp_path):
    """A holdout the search has already seen is not a holdout."""
    with pytest.raises(PreregError, match="overlapping"):
        register(tmp_path, **(GOOD | {"oos_window": ["2023-06-01", "2026-06-30"]}))


def test_a_promotion_rule_that_never_reads_the_holdout_is_rejected(tmp_path):
    """Decided entirely in-sample, that is a ranking, not a test."""
    with pytest.raises(PreregError, match="ranking, not a test"):
        register(tmp_path, **(GOOD | {"promote_if": "is_p_hat >= 0.6"}))


def test_a_rule_naming_an_undeclared_variable_is_caught_at_registration(tmp_path):
    """Catch it now, not hours later with results waiting."""
    with pytest.raises(PreregError, match="undeclared"):
        register(tmp_path, **(GOOD | {"promote_if": "oos_sharpe >= 1.0"}))


def test_a_batch_without_a_mechanism_is_rejected(tmp_path):
    with pytest.raises(PreregError, match="lottery ticket"):
        register(tmp_path, **(GOOD | {"mechanism": "should work"}))


def test_missing_required_fields_are_named(tmp_path):
    with pytest.raises(PreregError, match="hypothesis"):
        register(tmp_path, **(GOOD | {"hypothesis": ""}))


def test_prereg_sha_ignores_key_order_and_whitespace():
    a = {"b": 2, "a": 1, "prereg_sha": "x"}
    b = {"a": 1, "b": 2, "prereg_sha": "y"}
    assert prereg_sha(a) == prereg_sha(b)


# --------------------------------------------------------------------------- #
#  windows
# --------------------------------------------------------------------------- #


def test_a_backwards_window_is_rejected():
    with pytest.raises(ValueError, match="ends before it starts"):
        Window(datetime(2026, 6, 1), datetime(2026, 1, 1))


def test_holdout_flag_travels_with_the_window():
    """Looking is spending, so the flag lives on the window rather than in a
    caller's head."""
    assert Window(datetime(2024, 1, 1), datetime(2026, 6, 30), is_holdout=True).is_holdout
    assert not Window(datetime(2016, 1, 1), datetime(2023, 12, 31)).is_holdout
