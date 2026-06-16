"""
continuation.py — BRC-001 continuation labelling (STUB — task 108).

After a retest of L1, measure the H-bar forward return in the break direction
(5-pointer P5). This is the dependent variable for the Gate-3 edge test:
  H_base : forward return > 0 (continuation / "memory")
  H_alt-1: forward return <= 0 (fade-the-level / no memory)

Returns are signed by direction (BULLISH = +fwd, BEARISH = -fwd) so a positive
label always means "continued in the break direction". $/trade conversion and cost
deduction live in the Gate-3 harness, not here.
"""
from __future__ import annotations

from retest import Retest


def label_continuation(df, retest: "Retest", horizon: int = 5) -> float:
    """Signed forward return over `horizon` bars past the retest, in break direction.

    TODO(task 108): from the retest bar, take close[t+horizon] - close[t], signed by
    retest.zone.direction. Caller aggregates to E[return] / E[$/trade].
    """
    raise NotImplementedError("BRC continuation — implement with task 108")
