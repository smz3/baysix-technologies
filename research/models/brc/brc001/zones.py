"""
zones.py — BRC-001 5-pointer zone construction (Path B — task 112).

METHOD = PATH B (rawbreakout-derived). LOCKED 2026-06-17 (handover Morning2,
human call_id 76, strategy_log #48). A BRC zone is a 5-point geometry where the
CONFIRMATION is sourced from the STRUCT-001 break primitive (struct.rawbreakout),
NOT from a raw close-scan. Swings seed the skeleton (P1, P3); the break stream
supplies the two same-direction breaks that confirm the zone.

SELL zone, time order (BUY = mirror):
    P5 (old swing LOW)   = 2nd barrier   ← closest qualifying low BELOW P2, OLDER than P1
    P1 (swing HIGH)      = L2 origin     ← extreme high before reversal
    P2 (swing LOW)       = L1 entry      ← first LOW after P1 (the "1st break")
    P3 (swing LOW->HIGH) = context gate  ← first HIGH after P2, MUST be LOWER than P1
    P4 (breakout bar)    = confirmation  ← the bar that BREAKS P5 (the "2nd break")

Two same-direction breaks (the Path-B core — handover Morning2):
    1st break  = bar that closes beyond P2.price  → P2 = L1 (entry)
    2nd break  = bar that closes beyond P5.price  → P4 confirmation; P5 = 2nd barrier
  Because P5 is MORE EXTREME than P2 (P5<P2 for SELL), closing beyond P5 implies
  closing beyond P2 on that bar too — so the 1st break is at-or-before the 2nd.
    same_bar    = one impulse bar breaks P2 AND P5 together.
    sequential  = P2 breaks first, P5 breaks on a later bar.
  This same_bar/sequential flag is the H_alt-2 input for the Gate-3 edge test
  (task 110: is the 2nd break load-bearing?).

Level rules (traced against live EA CreateZoneFrom5Pointer, B2BDetector.mqh:381-425):
    L1 = P2.price          (= zone.first_barrier_price, zone.L1_price)
    L2 = extreme(P1,P3)    (= zone.swing_between_price, zone.L2_price)
         MAX(P1,P3) SELL / MIN(P1,P3) BUY. With the P3<P1 gate RESTORED (Syafiq,
         2026-06-17) the extreme is ALWAYS P1, so L2 == P1.price.
    P5  = zone.second_barrier_price ;  fifty = mid(L1,L2)
    Invalidation = CLOSE beyond L2 (not wick).

P3<P1 gate (RESTORED 2026-06-17): unlike the live EA (line 608 takes the first
HIGH after P2 with NO price gate and absorbs P3>P1 via L2=extreme), Path B
REQUIRES P3 < P1 (SELL) / P3 > P1 (BUY) and rejects the zone otherwise — the
context swing must stay inside the structure. This is a deliberate DEPARTURE: the
EA is no longer a zone-for-zone oracle (it does a swing-scan + plain close<P5 P4
and never consumes rawbreakouts). Validation = eyeball Gate 2 + the edge test.

SCOPE for Gate 2 (locked 2026-06-16, task 106): MINIMAL CORE only —
P1-P5 + two-break confirmation + L2-extreme selection. DEFERRED to task 113:
  - V5.1.1 one-zone-per-P5 / freshest-wins dedup
  - V5.1.2 "No-Interruption" (reject if any swing exists between P3 and P4)
  - gap-validation (L2 closed-through before P4)
  - retest/entry touch rule (task 108)
D1 only, all zones, no multi-TF russian-doll.

Reference implementations (ground truth, do NOT fork):
  - mt5/Include/Sigma_System/.../B2BDetector.mqh (live MQL5 EA — level mapping only)
  - research/models/struct/struct001/rawbreakout.py (the shared break primitive)
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
import pandas as pd                                                  # noqa: E402,F401  (re-exported for visual.py: Z.pd)
import swingpoints as sp                                             # noqa: E402,F401  (re-exported for visual.py: Z.sp)
import rawbreakout as rb                                             # noqa: E402
from structures import SignalDirection, SwingType                    # noqa: E402


@dataclass(frozen=True)
class BrcZone:
    """A confirmed 5-pointer zone. Prices/times for all five structural points are
    retained so the geometry is auditable against the live EA."""
    direction: "SignalDirection"
    l1_price: float          # = P2 price (entry level)        = EA first_barrier_price
    l2_price: float          # = extreme(P1,P3) (invalidation)  = EA swing_between_price
    p1_time: object          # origin swing (HIGH for SELL / LOW for BUY) — L2 source
    p1_price: float          # P1 swing price
    p2_time: object          # L1 swing (the 1st-break target)
    p3_time: object          # context-gate swing
    p3_price: float          # P3 swing price
    p4_time: object          # breakout bar that breaks P5 (the 2nd-break confirmation)
    p4_price: float          # P4 bar CLOSE (beyond p5_price)
    p5_time: object          # 2nd-barrier swing (older than P1)  = EA second_barrier
    p5_price: float          # the level P4 must close beyond to confirm
    break_kind: str          # 'same_bar' | 'sequential'  (H_alt-2 input, task 110)
    p2_break_time: object    # bar that broke P2 (the 1st break) — for sequencing audit

    @property
    def mid(self) -> float:
        return 0.5 * (self.l1_price + self.l2_price)


def _scan_one_direction(swings, breakouts, sell: bool) -> list[BrcZone]:
    """One pass of the Path-B 5-pointer scan. SELL: P1=HIGH, P2=LOW, P3=HIGH
    (<P1), P5=older LOW < P2. Confirmation = the two same-direction breaks from
    the struct.rawbreakout stream (P2 break = entry, P5 break = P4). BUY = mirror.

    Swings seed P1/P2/P3/P5; the break primitive supplies P4 + the same_bar /
    sequential label. A zone is emitted only once P5 has actually been broken."""
    p1_type = SwingType.HIGH if sell else SwingType.LOW    # P1 / P3 type
    p2_type = SwingType.LOW if sell else SwingType.HIGH    # P2 / P5 type
    direction = SignalDirection.BEARISH if sell else SignalDirection.BULLISH

    # struct.rawbreakout stream, keyed by the swing it broke (a swing breaks once,
    # so broken_swing_time is a unique key). Only same-direction breaks matter.
    brk_by_swing_time = {
        b.broken_swing_time: b for b in breakouts if b.direction == direction
    }

    out: list[BrcZone] = []

    for i in range(len(swings) - 2):
        p1 = swings[i]
        if p1.type != p1_type:
            continue

        # P2 = first opposite swing after P1 (by time) — the 1st-break target / L1
        p2 = next((s for s in swings[i + 1:]
                   if s.time > p1.time and s.type == p2_type), None)
        if p2 is None:
            continue

        # P3 = first P1-type swing after P2, with the RESTORED context gate:
        #   SELL -> P3 < P1 ;  BUY -> P3 > P1.  Reject the zone otherwise.
        p3 = next((s for s in swings
                   if s.time > p2.time and s.type == p1_type), None)
        if p3 is None:
            continue
        if (p3.price >= p1.price) if sell else (p3.price <= p1.price):
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

        # CONFIRMATION via the break stream (Path B): P4 = the bar that broke P5
        # (the 2nd break). No P5 break -> zone is not yet confirmed -> skip.
        b_p5 = brk_by_swing_time.get(p5.time)
        if b_p5 is None:
            continue
        p4_time = b_p5.breakout_bar_time
        p4_close = b_p5.breakout_bar_close_price

        # 1st break = the bar that broke P2 (L1 entry). Because P5 is more extreme
        # than P2, breaking P5 implies P2 broke at-or-before. If P2 has its own
        # break event we compare bars; if not (P2 absorbed on the same impulse
        # bar, or already consumed), treat as same_bar.
        b_p2 = brk_by_swing_time.get(p2.time)
        if b_p2 is not None:
            same = b_p2.breakout_bar_index == b_p5.breakout_bar_index
            p2_break_time = b_p2.breakout_bar_time
        else:
            same = True
            p2_break_time = p4_time
        break_kind = "same_bar" if same else "sequential"

        # Levels (traced vs EA CreateZoneFrom5Pointer): L1 = P2; L2 = extreme(P1,P3)
        # — which, under the restored P3<P1 gate, is always P1.
        l1 = p2.price
        l2 = max(p1.price, p3.price) if sell else min(p1.price, p3.price)

        out.append(BrcZone(
            direction=direction, l1_price=l1, l2_price=l2,
            p1_time=p1.time, p1_price=p1.price, p2_time=p2.time,
            p3_time=p3.time, p3_price=p3.price,
            p4_time=p4_time, p4_price=p4_close,
            p5_time=p5.time, p5_price=p5.price,
            break_kind=break_kind, p2_break_time=p2_break_time,
        ))
    return out


def detect_zones(tf: str = "D1", swing_window: int = 3) -> list[BrcZone]:
    """Detect Path-B 5-pointer BRC zones on `tf` (D1 atom for Gate 2).

    PATH B (task 112, locked 2026-06-17): swing-seeded skeleton (P1/P2/P3/P5) +
    two-break confirmation sourced from struct.rawbreakout + L1=P2 / L2=extreme(P1,P3)
    with the P3<P1 gate restored. Both directions, every valid pattern (no dedup).
    DEFERRED to task 113 — see module docstring:
      - V5.1.1 freshest-pattern-per-P5 / swing-reuse dedup
      - V5.1.2 no-interruption (reject new swing between P3 and P4)
      - gap-validation (L2 broken before P4)
      - retest / entry touch rule (task 108)
    """
    _df, swings, breakouts = rb.raw_breakouts(tf, swing_window=swing_window)
    zones = _scan_one_direction(swings, breakouts, sell=True)
    zones += _scan_one_direction(swings, breakouts, sell=False)
    zones.sort(key=lambda z: z.p4_time)
    return zones


def _main(argv: list[str]) -> None:
    tf = argv[argv.index("--tf") + 1].upper() if "--tf" in argv else "D1"
    window = int(argv[argv.index("--window") + 1]) if "--window" in argv else 3
    zones = detect_zones(tf, swing_window=window)
    sell = sum(1 for z in zones if z.direction == SignalDirection.BEARISH)
    seq = sum(1 for z in zones if z.break_kind == "sequential")
    print(f"{tf} window={window}  BRC zones={len(zones)}  "
          f"(sell={sell} buy={len(zones) - sell})  "
          f"(same_bar={len(zones) - seq} sequential={seq})")
    for z in zones[:5]:
        d = "SELL" if z.direction == SignalDirection.BEARISH else "BUY"
        print(f"  {d}  P4={str(z.p4_time)[:10]}  L1={z.l1_price:.2f} "
              f"L2={z.l2_price:.2f}  P5={z.p5_price:.2f}  {z.break_kind}")


if __name__ == "__main__":
    import sys as _sys
    _main(_sys.argv[1:])
