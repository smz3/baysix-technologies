"""Objective tests — one per rule, every expected number computed by hand.

The rule these exist to enforce: a prop evaluation encoded from a *summary* of a
rulebook produces equity paths that look completely normal and are wrong. So each
test below states the arithmetic in its docstring and asserts against that, not
against whatever the implementation happens to return.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from research.code.factory.objective import (
    EquityPoint,
    FixedBarrierRules,
    PHat,
    PropRules,
    UNRANKABLE,
    UnverifiedObjective,
    Verdict,
    aggregate,
    evaluate_fixed,
    evaluate_prop,
    load_rules,
)

CONFIG = Path(__file__).resolve().parents[1] / "config" / "objective"


def pt(day: int, hour: int, equity: float, balance: float | None = None) -> EquityPoint:
    """One observation. Hours stay in 9..16 so the 17:00 day roll never fires."""
    return EquityPoint(
        datetime(2026, 1, day, hour), equity, equity if balance is None else balance
    )


TOPSTEP_50K = PropRules(
    firm="test_50k",
    account_size=50_000.0,
    profit_target=3_000.0,
    mll_offset=2_000.0,
    consistency_frac=0.50,
    min_trading_days=2,
    max_contracts=5,
)


# --------------------------------------------------------------------------- #
#  barrier_fixed
# --------------------------------------------------------------------------- #


def test_fixed_target_first_is_pass():
    """stake 20, target_mult 2 -> target 40. Path touches 40 without seeing 2."""
    rules = FixedBarrierRules(stake=20.0, target_mult=2.0, floor_frac=0.10)
    out = evaluate_fixed([pt(1, 9, 20), pt(1, 10, 31), pt(1, 11, 40)], rules)
    assert out.verdict is Verdict.PASS
    assert out.fitness == 1.0
    assert out.resolved_at == datetime(2026, 1, 1, 11)


def test_fixed_floor_first_is_fail():
    """floor_frac 0.10 on a 20 stake -> floor 2.00. Touching it resolves the episode."""
    rules = FixedBarrierRules(stake=20.0, target_mult=2.0, floor_frac=0.10)
    out = evaluate_fixed([pt(1, 9, 20), pt(1, 10, 8), pt(1, 11, 2.0)], rules)
    assert out.verdict is Verdict.FAIL
    assert out.fitness == 0.0


def test_fixed_floor_wins_when_it_comes_first():
    """Both barriers are reachable; the EARLIER one resolves. Floor at 10:00 beats
    target at 11:00, so a later 40 must not rescue the episode."""
    rules = FixedBarrierRules(stake=20.0, target_mult=2.0, floor_frac=0.10)
    out = evaluate_fixed([pt(1, 9, 20), pt(1, 10, 1.5), pt(1, 11, 40)], rules)
    assert out.verdict is Verdict.FAIL


def test_fixed_unresolved_is_censored_not_failed():
    """Neither 40 nor 2 is touched. This is UNRANKABLE, never 0.0 — the whole
    point of the sentinel is that 'we ran out of window' must not be rankable
    alongside 'the method died'."""
    rules = FixedBarrierRules(stake=20.0, target_mult=2.0, floor_frac=0.10)
    out = evaluate_fixed([pt(1, 9, 20), pt(1, 10, 25), pt(1, 11, 18)], rules)
    assert out.verdict is Verdict.CENSORED
    assert out.fitness == UNRANKABLE


def test_fixed_empty_path_raises():
    rules = FixedBarrierRules(stake=20.0, target_mult=2.0, floor_frac=0.10)
    with pytest.raises(ValueError):
        evaluate_fixed([], rules)


# --------------------------------------------------------------------------- #
#  barrier_prop — the floor
# --------------------------------------------------------------------------- #


def test_mll_starts_offset_below_account_size():
    """50,000 - 2,000 = 48,000."""
    assert TOPSTEP_50K.initial_mll == 48_000.0


def test_mll_ratchets_on_end_of_day_balance():
    """Day 1 closes at 51,000 -> MLL rises to 51,000 - 2,000 = 49,000.
    Day 2 equity of 48,900 is therefore a breach, even though it is comfortably
    above the ORIGINAL 48,000 floor."""
    path = [
        pt(1, 9, 50_000), pt(1, 16, 51_000),
        pt(2, 9, 50_500), pt(2, 12, 48_900),
    ]
    out = evaluate_prop(path, TOPSTEP_50K)
    assert out.verdict is Verdict.FAIL
    assert out.floor_at_end == 49_000.0
    assert out.resolved_at == datetime(2026, 1, 2, 12)


def test_mll_never_moves_down():
    """Day 1 closes 51,000 -> MLL 49,000. Day 2 closes back at 50,000, which would
    imply 48,000 — the floor must STAY at 49,000. Day 3 at 48,950 then breaches."""
    path = [
        pt(1, 9, 50_000), pt(1, 16, 51_000),
        pt(2, 9, 51_000), pt(2, 16, 50_000),
        pt(3, 9, 50_000), pt(3, 12, 48_950),
    ]
    out = evaluate_prop(path, TOPSTEP_50K)
    assert out.verdict is Verdict.FAIL
    assert out.floor_at_end == 49_000.0


def test_mll_locks_permanently_at_starting_balance():
    """Day 1 closes 52,000 -> MLL would be 50,000, which IS the starting balance,
    so it locks there. Day 2 closes 55,000 — an unlocked floor would climb to
    53,000. It must not. Day 3 equity 50,500 therefore survives."""
    path = [
        pt(1, 9, 50_000), pt(1, 16, 52_000),
        pt(2, 9, 52_000), pt(2, 16, 55_000),
        pt(3, 9, 55_000), pt(3, 12, 50_500), pt(3, 16, 50_600),
    ]
    out = evaluate_prop(path, TOPSTEP_50K)
    assert out.floor_at_end == 50_000.0
    assert out.verdict is not Verdict.FAIL


def test_floor_is_tested_intraday_on_equity_not_on_closing_balance():
    """Unrealized P&L counts. Equity dips to 47,900 at midday — below the 48,000
    floor — then the day closes at a healthy 50,500 balance. The account is already
    liquidated; the good close is irrelevant."""
    path = [
        pt(1, 9, 50_000),
        EquityPoint(datetime(2026, 1, 1, 12), equity=47_900, balance=50_000),
        pt(1, 16, 50_500),
    ]
    out = evaluate_prop(path, TOPSTEP_50K)
    assert out.verdict is Verdict.FAIL
    assert out.resolved_at == datetime(2026, 1, 1, 12)
    assert "intraday" in out.detail


# --------------------------------------------------------------------------- #
#  barrier_prop — the consistency rule, i.e. the endogenous target
# --------------------------------------------------------------------------- #


def test_effective_target_is_unchanged_by_a_small_best_day():
    """best_day 1,000 / 0.50 = 2,000, which is below the 3,000 base target."""
    assert TOPSTEP_50K.effective_target(1_000.0) == 3_000.0


def test_effective_target_is_raised_by_a_large_best_day():
    """best_day 2,500 / 0.50 = 5,000 > 3,000, so the bar moves to 5,000."""
    assert TOPSTEP_50K.effective_target(2_500.0) == 5_000.0


def test_a_losing_best_day_does_not_move_the_target():
    assert TOPSTEP_50K.effective_target(-800.0) == 3_000.0


def test_one_big_day_does_not_pass_the_evaluation():
    """The headline case. Day 1 makes +2,500 (balance 52,500), which alone clears
    the 3,000 base target on day 2 with a further +600 (total 3,100). But best_day
    2,500 raises the effective target to 5,000, so 3,100 is not a pass. Only after
    day 3's +2,000 (total 5,100 >= 5,000) does it resolve."""
    path = [
        pt(1, 9, 50_000), pt(1, 16, 52_500),
        pt(2, 9, 52_500), pt(2, 16, 53_100),
        pt(3, 9, 53_100), pt(3, 16, 55_100),
    ]
    out = evaluate_prop(path, TOPSTEP_50K)
    assert out.verdict is Verdict.PASS
    assert out.best_day_profit == 2_500.0
    assert out.effective_target == 5_000.0
    assert out.days_traded == 3
    assert out.resolved_at == datetime(2026, 1, 3, 16)


def test_evenly_earned_target_passes_on_the_boundary():
    """Two days of +1,500. best_day 1,500 / 0.50 = 3,000, exactly the base target,
    and total profit is exactly 3,000. Boundary is inclusive, so this passes."""
    path = [
        pt(1, 9, 50_000), pt(1, 16, 51_500),
        pt(2, 9, 51_500), pt(2, 16, 53_000),
    ]
    out = evaluate_prop(path, TOPSTEP_50K)
    assert out.verdict is Verdict.PASS
    assert out.effective_target == 3_000.0
    assert out.days_traded == 2


def test_lopsided_days_miss_the_target_they_would_otherwise_hit():
    """+1,400 then +1,600 reaches 3,000 total — the base target — but best_day
    1,600 / 0.50 = 3,200, so it falls 200 short and the window ends CENSORED."""
    path = [
        pt(1, 9, 50_000), pt(1, 16, 51_400),
        pt(2, 9, 51_400), pt(2, 16, 53_000),
    ]
    out = evaluate_prop(path, TOPSTEP_50K)
    assert out.verdict is Verdict.CENSORED
    assert out.effective_target == 3_200.0
    assert out.final_balance == 53_000.0


def test_minimum_trading_days_blocks_a_one_day_pass():
    """consistency_frac 1.0 removes the consistency term so the day count is the
    only thing under test: +4,000 in one day clears a 3,000 target outright, and
    must still not pass with min_trading_days = 2."""
    rules = PropRules(
        firm="t", account_size=50_000, profit_target=3_000, mll_offset=2_000,
        consistency_frac=1.0, min_trading_days=2, max_contracts=5,
    )
    path = [pt(1, 9, 50_000), pt(1, 16, 54_000)]
    out = evaluate_prop(path, rules)
    assert out.verdict is Verdict.CENSORED
    assert out.days_traded == 1


def test_flat_account_is_censored_and_trades_no_days():
    path = [pt(1, 9, 50_000), pt(1, 16, 50_000), pt(2, 9, 50_000), pt(2, 16, 50_000)]
    out = evaluate_prop(path, TOPSTEP_50K)
    assert out.verdict is Verdict.CENSORED
    assert out.days_traded == 0
    assert out.fitness == UNRANKABLE


def test_final_partial_day_still_settles():
    """The window ending must not discard the last session — a pass earned on the
    final observation is a pass."""
    path = [
        pt(1, 9, 50_000), pt(1, 16, 51_500),
        pt(2, 9, 51_500), pt(2, 14, 53_000),
    ]
    out = evaluate_prop(path, TOPSTEP_50K)
    assert out.verdict is Verdict.PASS


def test_prop_empty_path_raises():
    with pytest.raises(ValueError):
        evaluate_prop([], TOPSTEP_50K)


# --------------------------------------------------------------------------- #
#  aggregation — one pass is one draw
# --------------------------------------------------------------------------- #


def _outcome(verdict: Verdict):
    return evaluate_fixed(
        {
            Verdict.PASS: [pt(1, 9, 20), pt(1, 10, 40)],
            Verdict.FAIL: [pt(1, 9, 20), pt(1, 10, 1)],
            Verdict.CENSORED: [pt(1, 9, 20), pt(1, 10, 21)],
        }[verdict],
        FixedBarrierRules(20.0, 2.0, 0.10),
    )


def test_aggregate_refuses_below_the_minimum_resolved_count():
    """19 resolved draws is an anecdote with a decimal point. UNJUDGED, not
    rejected — the distinction matters because a rejected config is dead and an
    unjudged one just needs more windows."""
    outs = [_outcome(Verdict.PASS)] * 10 + [_outcome(Verdict.FAIL)] * 9
    got = aggregate(outs, min_resolved=20)
    assert got.p_hat is None
    assert got.reportable is False
    assert "UNJUDGED" in got.why


def test_aggregate_refuses_when_mostly_censored():
    """12 of 22 censored = 0.545 > 0.50. Reporting p_hat off the 10 that resolved
    would be selection on the outcome."""
    outs = (
        [_outcome(Verdict.PASS)] * 5
        + [_outcome(Verdict.FAIL)] * 5
        + [_outcome(Verdict.CENSORED)] * 12
    )
    got = aggregate(outs, min_resolved=5)
    assert got.p_hat is None
    assert "censored" in got.why


def test_aggregate_reports_p_hat_with_a_wilson_interval():
    """14 pass / 10 fail over 24 resolved -> p_hat = 14/24 = 0.58333..."""
    outs = [_outcome(Verdict.PASS)] * 14 + [_outcome(Verdict.FAIL)] * 10
    got = aggregate(outs, min_resolved=20)
    assert got.reportable
    assert got.p_hat == pytest.approx(14 / 24)
    assert got.n_resolved == 24
    assert got.ci_low < got.p_hat < got.ci_high
    # n=24 near p=0.58 is a wide interval, and it should say so out loud.
    assert (got.ci_high - got.ci_low) > 0.3


def test_aggregate_of_nothing_is_not_an_error():
    got = aggregate([])
    assert isinstance(got, PHat)
    assert got.reportable is False


# --------------------------------------------------------------------------- #
#  loading — an unverified rulebook may not drive a decision
# --------------------------------------------------------------------------- #


def test_fixed_objective_loads_and_fingerprints():
    rules, fp = load_rules(CONFIG / "barrier_fixed_v1.0.0.json")
    assert isinstance(rules, FixedBarrierRules)
    assert rules.target == 40.0
    assert rules.floor == 2.0
    assert len(fp) == 64


def test_unverified_prop_objective_is_refused():
    """profit_target came off a review site and has not been read from Topstep.
    The loader must refuse rather than quietly return a plausible number."""
    with pytest.raises(UnverifiedObjective) as excinfo:
        load_rules(CONFIG / "barrier_prop_topstep50k_v1.0.0.json")
    assert "profit_target" in str(excinfo.value)


def test_unverified_prop_objective_loads_only_under_an_explicit_override():
    rules, fp = load_rules(
        CONFIG / "barrier_prop_topstep50k_v1.0.0.json", allow_unverified=True
    )
    assert isinstance(rules, PropRules)
    assert rules.initial_mll == 48_000.0
    assert rules.consistency_frac == 0.50
    assert len(fp) == 64


def test_fingerprint_changes_when_a_parameter_changes(tmp_path):
    """Two results carrying different fingerprints were judged against different
    questions and must never be pooled. Prove the fingerprint actually moves."""
    import json

    src = CONFIG / "barrier_fixed_v1.0.0.json"
    payload = json.loads(src.read_text(encoding="utf-8"))
    _, fp_a = load_rules(src)

    payload["parameters"]["target_mult"] = 3.0
    edited = tmp_path / "edited.json"
    edited.write_text(json.dumps(payload), encoding="utf-8")
    _, fp_b = load_rules(edited)

    assert fp_a != fp_b
