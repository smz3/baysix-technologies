"""Tests for the generic Gate-2 sanity checker (Protocol 3.2, task 82)."""
import numpy as np
import pytest

from research.code import gate2_sanity as g2


def _full_pass(idea="X-001"):
    g = g2.Gate2Sanity(idea)
    g.assert_finite([1.0, 2.0, 3.0])
    g.assert_not_constant([1, 2, 3])
    g.assert_monotonic_time([1, 2, 3])
    return g


def test_verdict_requires_all_three_categories():
    g = g2.Gate2Sanity("X-001")
    g.validity("ok", True)
    assert g.verdict() is False        # only 1 category covered
    g.non_degeneracy("ok", True)
    g.causal("ok", True)
    assert g.verdict() is True


def test_any_failure_fails_verdict():
    g = _full_pass()
    assert g.verdict() is True
    g.validity("bad", False)
    assert g.verdict() is False


def test_monotonic_time_catches_unsorted():
    # THE ORB unsorted-tick lesson — backward step must FAIL causal cleanliness.
    g = g2.Gate2Sanity("ORB-x")
    assert g.assert_monotonic_time([1, 2, 1, 3]) is False
    assert g.assert_monotonic_time([1, 2, 3, 4]) is True


def test_entry_after_signal():
    g = g2.Gate2Sanity("ORB-x")
    assert g.assert_entry_after_signal([10, 20], [11, 21]) is True
    assert g.assert_entry_after_signal([10, 20], [10, 21]) is False  # entry == signal


def test_finite_and_constant():
    g = g2.Gate2Sanity("X")
    assert g.assert_finite([1.0, np.nan]) is False
    assert g.assert_not_constant([5, 5, 5]) is False
    assert g.assert_not_constant([5, 6]) is True


def test_both_directions():
    g = g2.Gate2Sanity("X")
    assert g.assert_both_directions(["long", "long", "short"]) is True
    assert g.assert_both_directions(["long", "none"]) is False


def test_in_range():
    g = g2.Gate2Sanity("X")
    assert g.assert_in_range(5.0, 0.5, 30, "range") is True
    assert g.assert_in_range(0.1, 0.5, 30, "range") is False


def test_report_renders_without_error():
    txt = _full_pass().report()
    assert "ALL SANE" in txt
    for cat in g2.CATEGORIES:
        assert cat in txt


# ---- classifier-only Markov-4 instance ----

def test_markov4_passes_on_sane_hmm():
    P = np.array([[0.8, 0.2], [0.3, 0.7]])
    states = np.array([0, 0, 1, 1, 0, 1, 0, 1, 1, 0])
    g = g2.markov4(states, P)
    assert g.verdict() is True


def test_markov4_fails_non_stochastic_matrix():
    P = np.array([[0.8, 0.3], [0.3, 0.7]])  # row 0 sums to 1.1
    states = np.array([0, 1, 0, 1, 0, 1])
    assert g2.markov4(states, P).verdict() is False


def test_markov4_fails_dead_state():
    P = np.array([[0.9, 0.1], [0.1, 0.9]])
    states = np.zeros(10, dtype=int)          # state 1 never occupied
    assert g2.markov4(states, P).verdict() is False
