"""
Geometry-primitive unit tests for the recovered B2B engine.

These lock the EXACT behaviour confirmed against the live MQL5 source
(SwingPointDetector.mqh / RawBreakoutDetector.mqh, InpSwingWindow=3):

  - swings    = 3-bar STRICT local extrema on CLOSE prices, endpoints excluded
  - breakouts = left-to-right scan; close STRICTLY beyond an unbroken swing,
                strictly AFTER the swing's bar; each swing breaks at most once;
                detection MUTATES swing.has_been_broken (stateful footgun).

Scope: D1 + H4 + H1 only (these primitives are timeframe-agnostic).
"""
import pandas as pd
import pytest

from sigma_core.b2b.models.structures import (
    SwingPointInfo, SwingType, SignalDirection, DetectionConfig,
)
from sigma_core.b2b.detectors.swing_points import detect_swings
from sigma_core.b2b.detectors.breakouts import detect_breakouts


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def mkdf(closes):
    """Build a minimal time+close frame (the only columns the engine reads)."""
    t = pd.date_range("2020-01-01", periods=len(closes), freq="D")
    return pd.DataFrame({"time": t, "close": [float(c) for c in closes]})


def times_of(df):
    """df bar times as python datetimes (matches breakouts.py internal type)."""
    return [pd.Timestamp(t).to_pydatetime() for t in df["time"].values]


def mkswing(price, t, typ, bar_index):
    return SwingPointInfo(price=float(price), time=t, close_price=float(price),
                          type=typ, bar_index=bar_index)


# --------------------------------------------------------------------------- #
# detect_swings — 3-bar strict local extrema on closes
# --------------------------------------------------------------------------- #
def test_single_high():
    swings = detect_swings(mkdf([1, 2, 3, 2, 1]))
    assert len(swings) == 1
    assert swings[0].type == SwingType.HIGH
    assert swings[0].bar_index == 2
    assert swings[0].price == 3.0


def test_single_low():
    swings = detect_swings(mkdf([3, 2, 1, 2, 3]))
    assert len(swings) == 1
    assert swings[0].type == SwingType.LOW
    assert swings[0].bar_index == 2
    assert swings[0].price == 1.0


def test_monotonic_up_has_no_swings():
    assert detect_swings(mkdf([1, 2, 3, 4, 5])) == []


def test_monotonic_down_has_no_swings():
    assert detect_swings(mkdf([5, 4, 3, 2, 1])) == []


def test_flat_line_has_no_swings():
    assert detect_swings(mkdf([2, 2, 2, 2])) == []


def test_plateau_is_not_a_swing_strict_inequality():
    # 2 is NOT strictly greater than its equal neighbour -> no swing.
    assert detect_swings(mkdf([1, 2, 2, 1])) == []


def test_endpoints_are_never_swings():
    # idx0=5 is the global max and idx4=4 near-max, but both are endpoints.
    # Only interior idx1 (=1) qualifies, as a LOW.
    swings = detect_swings(mkdf([5, 1, 2, 3, 4]))
    assert len(swings) == 1
    assert swings[0].type == SwingType.LOW
    assert swings[0].bar_index == 1


def test_zigzag_alternates_high_low():
    swings = detect_swings(mkdf([1, 3, 2, 4, 2, 5, 1]))
    assert [(s.type, s.bar_index, s.price) for s in swings] == [
        (SwingType.HIGH, 1, 3.0),
        (SwingType.LOW, 2, 2.0),
        (SwingType.HIGH, 3, 4.0),
        (SwingType.LOW, 4, 2.0),
        (SwingType.HIGH, 5, 5.0),
    ]


@pytest.mark.parametrize("closes", [[], [1], [1, 2]])
def test_too_short_has_no_swings(closes):
    assert detect_swings(mkdf(closes)) == []


# --------------------------------------------------------------------------- #
# detect_breakouts — close strictly beyond an unbroken, earlier swing
# --------------------------------------------------------------------------- #
def test_bullish_break_recorded_once():
    df = mkdf([3, 1, 1, 4, 5])
    t = times_of(df)
    swing = mkswing(3.0, t[0], SwingType.HIGH, 0)
    bos = detect_breakouts(df, [swing])
    assert len(bos) == 1
    assert bos[0].direction == SignalDirection.BULLISH
    assert bos[0].breakout_bar_index == 3          # first bar to close > 3
    assert bos[0].broken_swing_price == 3.0
    assert swing.has_been_broken is True


def test_bearish_break_recorded():
    df = mkdf([2, 3, 1])
    t = times_of(df)
    swing = mkswing(2.0, t[0], SwingType.LOW, 0)
    bos = detect_breakouts(df, [swing])
    assert len(bos) == 1
    assert bos[0].direction == SignalDirection.BEARISH
    assert bos[0].breakout_bar_index == 2


def test_equal_close_is_not_a_break_strict():
    # close == swing price must NOT break (strict > / <).
    df = mkdf([3, 3, 3])
    t = times_of(df)
    swing = mkswing(3.0, t[0], SwingType.HIGH, 0)
    assert detect_breakouts(df, [swing]) == []


def test_swing_only_broken_by_later_bars():
    # A high-close bar BEFORE the swing formed must not break it; only the
    # bar after the swing's time does.
    df = mkdf([5, 5, 1, 5])
    t = times_of(df)
    swing = mkswing(1.0, t[2], SwingType.HIGH, 2)   # swing forms at bar 2
    bos = detect_breakouts(df, [swing])
    assert len(bos) == 1
    assert bos[0].breakout_bar_index == 3


def test_max_breakout_age_filters_old_swings():
    df = mkdf([1, 1, 1, 1, 1, 5])                   # break candidate at bar 5
    t = times_of(df)

    # age = 5 - 0 = 5; with a cap of 3 the breakout is filtered out.
    swing_old = mkswing(1.0, t[0], SwingType.HIGH, 0)
    capped = DetectionConfig(max_breakout_age=3)
    assert detect_breakouts(df, [swing_old], capped) == []

    # default config (max_breakout_age=0) disables the age filter -> it breaks.
    swing_fresh = mkswing(1.0, t[0], SwingType.HIGH, 0)
    assert len(detect_breakouts(df, [swing_fresh])) == 1


def test_detect_breakouts_mutates_swing_state():
    # Documents the stateful footgun: re-running on the SAME swing list yields
    # nothing the second time because has_been_broken was set in place.
    df = mkdf([3, 1, 4])
    t = times_of(df)
    swings = [mkswing(3.0, t[0], SwingType.HIGH, 0)]

    first = detect_breakouts(df, swings)
    second = detect_breakouts(df, swings)
    assert len(first) == 1
    assert second == []
    assert swings[0].has_been_broken is True
