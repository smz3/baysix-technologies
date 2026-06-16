"""
retest.py — BRC-001 pullback re-touch detection (STUB — task 108).

Given a BrcZone, find the first bar after zone formation whose path pulls back and
re-touches L1 (5-pointer P4). This is the trade trigger under H_base. Detection is
close-based to match STRUCT (a wick-touch rule would need tick/intrabar data — record
as a limitation, do not silently approximate from derived bars).
"""
from __future__ import annotations

from dataclasses import dataclass

from zones import BrcZone


@dataclass(frozen=True)
class Retest:
    zone: "BrcZone"
    retest_time: object
    retest_price: float
    bars_to_retest: int


def find_retest(df, zone: "BrcZone", max_bars: int | None = None) -> "Retest | None":
    """Return the first L1 re-touch after the zone forms, else None.

    TODO(task 108): scan df bars after zone.anchor_time for a close (or bar range,
    once a touch rule is chosen) that re-touches zone.l1_price within max_bars.
    """
    raise NotImplementedError("BRC retest — implement with task 108")
