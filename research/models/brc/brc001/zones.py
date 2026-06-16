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

Maps to STRUCT-001 primitives: P1/P2/P3/P5 = swingpoints (the shared break
primitive BRC imports, never forks — see _struct_on_path). P4 = plain first bar
that CLOSES beyond P5.price after P3 — the live-EA rule (B2BDetector.mqh), NOT
routed through struct.rawbreakout, which would add confirmation/min_age/impulse
gating the EA's P4 does not have and so would diverge from ground truth.

Faithful to the EA: P3 has NO "lower than P1" constraint (the 5-pointer doc table
says it does, but the same doc's L2 section says "P3 can > P1" and both the live
EA (line 608) and the python port take the FIRST opposite swing after P2 with no
price gate — P3 >= P1 is absorbed by L2 = extreme(P1,P3)).

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
import pandas as pd                                                  # noqa: E402
import swingpoints as sp                                             # noqa: E402
from structures import SignalDirection, SwingType                    # noqa: E402


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


def _scan_one_direction(df, swings, sell: bool) -> list[BrcZone]:
    """One pass of the minimal-core 5-pointer scan. SELL: P1=HIGH, P2=LOW,
    P3=HIGH, P5=older LOW < P2, P4 closes below P5. BUY = mirror."""
    p1_type = SwingType.HIGH if sell else SwingType.LOW    # P1 / P3 type
    p2_type = SwingType.LOW if sell else SwingType.HIGH    # P2 type
    direction = SignalDirection.BEARISH if sell else SignalDirection.BULLISH

    closes = df["close"].values
    times = df["time"].values
    out: list[BrcZone] = []

    for i in range(len(swings) - 2):
        p1 = swings[i]
        if p1.type != p1_type:
            continue

        # P2 = first opposite swing after P1 (by time)
        p2 = next((s for s in swings[i + 1:]
                   if s.time > p1.time and s.type == p2_type), None)
        if p2 is None:
            continue

        # P3 = first P1-type swing after P2 (no price gate — EA-faithful)
        p3 = next((s for s in swings
                   if s.time > p2.time and s.type == p1_type), None)
        if p3 is None:
            continue

        # P5 = closest qualifying barrier OLDER than P1 (scan backwards from P1):
        #   SELL -> LOW with price < P2;  BUY -> HIGH with price > P2
        p5 = None
        for j in range(i - 1, -1, -1):
            s = swings[j]
            if s.time < p1.time and s.type == p2_type and \
               (s.price < p2.price if sell else s.price > p2.price):
                p5 = s
                break
        if p5 is None:
            continue

        # P4 = first bar after P3 that CLOSES beyond P5.price (EA close-rule)
        start = p3.bar_index + 1
        seg = closes[start:]
        hits = (seg < p5.price) if sell else (seg > p5.price)
        idx = hits.argmax() if hits.any() else -1
        if idx < 0:
            continue
        p4_bar = start + int(idx)
        p4_time = pd.Timestamp(times[p4_bar]).to_pydatetime()

        # Levels: L1 = P2; L2 = more extreme of (P1, P3)
        l1 = p2.price
        l2 = max(p1.price, p3.price) if sell else min(p1.price, p3.price)

        out.append(BrcZone(
            direction=direction, l1_price=l1, l2_price=l2,
            p1_time=p1.time, p2_time=p2.time, p3_time=p3.time,
            p4_time=p4_time, p5_time=p5.time, p5_price=p5.price,
        ))
    return out


def detect_zones(tf: str = "D1", swing_window: int = 3) -> list[BrcZone]:
    """Detect minimal-core 5-pointer BRC zones on `tf` (D1 atom for Gate 2).

    MINIMAL CORE (task 107, locked 2026-06-16): P1->P2->P3->P5 selection + P4
    close-confirmation + L1=P2 / L2=extreme(P1,P3). Both directions, every valid
    pattern (no dedup). DEFERRED as variants — see module docstring:
      - V5.1.1 freshest-pattern-per-P5 (Pass 2) + swing-reuse dedup (Pass 3)
      - V5.1.2 no-interruption (reject new swing between P3 and P4)
      - early-fade gap validation (L2 broken before P4)
      - retest / entry touch rule (task 108)
    Ground truth for the full filtered engine: b2b/sigma_core/.../b2b_engine.py.
    """
    df, swings = sp.swings(tf, swing_window=swing_window)
    zones = _scan_one_direction(df, swings, sell=True)
    zones += _scan_one_direction(df, swings, sell=False)
    zones.sort(key=lambda z: z.p4_time)
    return zones


def _main(argv: list[str]) -> None:
    tf = argv[argv.index("--tf") + 1].upper() if "--tf" in argv else "D1"
    window = int(argv[argv.index("--window") + 1]) if "--window" in argv else 3
    zones = detect_zones(tf, swing_window=window)
    sell = sum(1 for z in zones if z.direction == SignalDirection.BEARISH)
    print(f"{tf} window={window}  BRC zones={len(zones)}  "
          f"(sell={sell} buy={len(zones) - sell})")
    for z in zones[:5]:
        d = "SELL" if z.direction == SignalDirection.BEARISH else "BUY"
        print(f"  {d}  P4={str(z.p4_time)[:10]}  L1={z.l1_price:.2f} "
              f"L2={z.l2_price:.2f}  P5={z.p5_price:.2f}")


if __name__ == "__main__":
    import sys as _sys
    _main(_sys.argv[1:])
