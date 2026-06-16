"""
zones.py — BRC-001 two-barrier zone construction (STUB — task 107).

Pairs consecutive same-direction STRUCT-001 rawbreakouts into a Break-Retest zone:
  L1 = the swing broken by the 1st breakout (entry level; tightest when ambiguous)
  L2 = the most extreme swing within the pattern window (invalidation level)
  mid = 50% midpoint (touch-depth reference)

Ports ONLY the 5-pointer L1/L2 *selection geometry* from the legacy b2b docs — the
"institutional/trapped-trader" narrative is dropped. Open spec to lock first
(task 106): "two consecutive breakouts" vs "one break + impulse swing".

STRUCT is imported, never forked (see _struct_on_path).
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]


def _struct_on_path() -> None:
    """Put STRUCT-001 + the shared code layer on sys.path so BRC depends on the
    single source-of-truth break detector instead of copying it."""
    for p in (REPO / "research" / "models" / "struct" / "struct001",
              REPO / "research" / "code"):
        sp = str(p)
        if sp not in sys.path:
            sys.path.insert(0, sp)


_struct_on_path()
import rawbreakout as rb                                              # noqa: E402,F401
from structures import SignalDirection                               # noqa: E402,F401


@dataclass(frozen=True)
class BrcZone:
    direction: "SignalDirection"
    l1_price: float          # entry level — swing broken by the 1st breakout
    l2_price: float          # invalidation level — most extreme swing in window
    l1_time: object
    l2_time: object
    anchor_time: object      # zone anchored at L2's swing time

    @property
    def mid(self) -> float:
        return 0.5 * (self.l1_price + self.l2_price)


def detect_zones(tf: str = "D1", swing_window: int = 3) -> list[BrcZone]:
    """Pair consecutive same-direction struct rawbreakouts -> BrcZone list.

    TODO(task 107): implement after the task-106 definition lock. Source breaks via
    rb.raw_breakouts(tf, swing_window=swing_window); group same-direction runs; apply
    L1 (tightest) / L2 (extreme) selection; prune redundant zones.
    """
    raise NotImplementedError("BRC zones — implement after task 106 spec lock")
