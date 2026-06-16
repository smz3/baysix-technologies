"""
zones.py — BRC-001 5-pointer zone construction (STUB — task 107).

SOURCE OF TRUTH: mt5/Include/Sigma_System/V5.0/Docs/5PointB2BDetection.md (FINAL).
This overrides the looser b2b-overview.md. A BRC zone is a 5-SWING-POINT geometry
confirmed by ONE breakout bar (P4) — NOT two consecutive rawbreakouts.

SELL zone, time order (BUY = mirror):
    P5 (old swing LOW)              ← 2nd barrier; closest qualifying low OLDER than P1
    P1 (swing HIGH)   = L2 origin   ← highest before reversal
    P2 (swing LOW)    = L1 entry    ← first LOW after P1
    P3 (swing HIGH)                 ← first HIGH after P2, must be LOWER than P1 (context, REQUIRED)
    P4 (breakout bar)               ← closes BELOW P5 (may break P2 same bar) -> zone confirmed

Level rules:
    L1 = P2 price (deterministic — NOT "tightest"; that was the stale overview).
    L2 = more extreme of P1/P3:  MAX(P1,P3) for SELL, MIN(P1,P3) for BUY.
    Invalidation = CLOSE beyond L2 (not wick).

Maps to STRUCT-001 primitives: P1/P2/P3/P5 = swingpoints; P4 = rawbreakout (close
beyond P5). STRUCT is imported, never forked (see _struct_on_path).

SCOPE for Gate 2 (locked 2026-06-16, task 106): MINIMAL CORE only —
P1-P5 + P4 confirmation + L2-extreme selection. DEFERRED as later variants:
  - V5.1.1 2-pass candidate selection / one-zone-per-P5 / freshest-wins
  - V5.1.2 "No-Interruption" (reject if any swing exists between P3 and P4)
  - retest/entry touch rule (premature — task 108)
D1 only, all zones, no multi-TF russian-doll.

Reference implementations (ground truth, do NOT fork):
  - b2b/sigma_core/b2b/detectors/b2b_engine.py  (legacy Python port)
  - mt5/Include/Sigma_System/.../B2BDetector.mqh (live MQL5 EA)
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
import swingpoints as sp                                             # noqa: E402,F401
from structures import SignalDirection                               # noqa: E402,F401


@dataclass(frozen=True)
class BrcZone:
    """A confirmed 5-pointer zone. Prices/times for all five structural points are
    retained so the geometry is auditable against the live EA."""
    direction: "SignalDirection"
    l1_price: float          # = P2 price (entry level)
    l2_price: float          # = more extreme of P1/P3 (invalidation level)
    p1_time: object          # origin swing (HIGH for SELL / LOW for BUY)
    p2_time: object          # L1 swing
    p3_time: object          # context swing
    p4_time: object          # breakout bar (confirmation)
    p5_time: object          # 2nd-barrier swing (older than P1)
    p5_price: float          # the level P4 must close beyond to confirm

    @property
    def mid(self) -> float:
        return 0.5 * (self.l1_price + self.l2_price)


def detect_zones(tf: str = "D1", swing_window: int = 3) -> list[BrcZone]:
    """Detect minimal-core 5-pointer BRC zones on `tf`.

    TODO(task 107) — implement per 5PointB2BDetection.md, MINIMAL CORE:
      1. Get swings (sp.swings) + breakouts (rb.raw_breakouts) for tf.
      2. Iterate swings oldest->newest. For each P1 (extreme), find P2 (first
         opposite swing after P1), P3 (first same-type-as-P1 swing after P2, less
         extreme than P1), and P5 (closest qualifying barrier OLDER than P1).
      3. Confirm with P4 = a rawbreakout bar closing beyond P5.price.
      4. L1 = P2.price; L2 = MAX/MIN(P1,P3) by direction.
    DEFER: 2-pass dedup, no-interruption, retest. See module docstring.
    """
    raise NotImplementedError("BRC 5-pointer zones — implement in task 107 (next session)")
