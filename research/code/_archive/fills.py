"""
fills.py — the ONE canonical bid/ask fill model. Venue-aware, idea-agnostic.

WHY THIS EXISTS
---------------
Realistic fill mechanics (long fills at ask, short at bid, stop on the opposite
quote, PnL/risk math) and the venue half-spread were hardcoded + duplicated across
export_ticks_mt5.py, fork_a_ea_emulation.py and d0_parity.py. Any one of them could
silently drift from what the MT5 EA actually does — the fidelity gap that produced
the ORB-001 Gate-7 contradiction. This centralizes the broker mechanics behind one
venue object, pinned to the MT5 Strategy Tester as ground truth.

SCOPE: broker mechanics only. NO strategy logic (opening range, breakout, trail,
EOD) — strategies hand-write their own loop and call these methods. See
docs/superpowers/specs/2026-06-13-fills-primitive-design.md.

SPREAD BASIS (locked): JM-Pro flat 2-pip overlay. The caller synthesizes
bid/ask = mid -/+ half_spread via synth_bid_ask(); fill methods take bid/ask as
explicit inputs (correct MT5 mechanics). A native-spread path (fill on the source's
real bid/ask) is reachable simply by NOT calling synth_bid_ask — pass real bid/ask.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
BROKERS = REPO / "brokers"


@dataclass(frozen=True)
class Venue:
    """Immutable venue fill mechanics, loaded from brokers/<id>.yaml."""
    venue_id: str
    half_spread: float              # $/oz, one side of the spread (mid -> quote)
    contract_size: float            # oz per 1.0 lot
    min_lot: float
    lot_step: float
    commission_per_lot_side: float  # $/lot/side (0 for JM-Pro spread-only)
    swap_long: float                # $/lot/night (0 for swap-free JM)
    swap_short: float

    @classmethod
    @lru_cache(maxsize=None)
    def from_yaml(cls, venue_id: str = "justmarkets", instrument: str = "XAUUSD.s") -> "Venue":
        spec = yaml.safe_load((BROKERS / f"{venue_id}.yaml").read_text(encoding="utf-8"))
        inst = spec["instruments"][instrument]
        full_spread = float(spec["costs"]["spread"]["pro_typical_full_usd_per_oz"])
        return cls(
            venue_id=spec["venue_id"],
            half_spread=full_spread / 2.0,
            contract_size=float(inst["contract_size_oz"]),
            min_lot=float(inst["min_lot"]),
            lot_step=float(inst["lot_step"]),
            commission_per_lot_side=float(spec["costs"]["commission"]["pro_per_lot_usd"]),
            swap_long=float(spec["costs"]["swap"]["long_per_lot_per_night_usd"]),
            swap_short=float(spec["costs"]["swap"]["short_per_lot_per_night_usd"]),
        )

    # --- spread overlay (locked JM-Pro flat 2-pip basis) ---------------------
    def synth_bid_ask(self, mid):
        """Flat overlay: derive bid/ask from a mid by the venue half-spread.
        Scalar or numpy-array `mid` both work (returns a (bid, ask) pair)."""
        return mid - self.half_spread, mid + self.half_spread

    # --- fill mechanics (exactly what the MT5 market order does) -------------
    def entry_fill(self, side: int, bid: float, ask: float) -> float:
        """Market entry: long buys at ask, short sells at bid."""
        return ask if side > 0 else bid

    def exit_fill(self, side: int, level: float) -> float:
        """Stop / market exit fills at the level price (already in the right quote)."""
        return level

    def stop_quote(self, side: int, bid: float, ask: float) -> float:
        """Which live quote a stop watches: long stop on bid, short stop on ask."""
        return bid if side > 0 else ask

    # --- money math ----------------------------------------------------------
    def pnl_usd(self, side: int, entry: float, exit: float, lot: float) -> float:
        raw = (exit - entry) if side > 0 else (entry - exit)
        return raw * self.contract_size * lot

    def risk_usd(self, stop_distance: float, lot: float) -> float:
        return stop_distance * self.contract_size * lot

    def risk_cap_ok(self, risk_usd: float, equity: float, cap_pct: float) -> bool:
        if cap_pct <= 0 or equity <= 0:
            return True
        return (risk_usd / equity) * 100.0 <= cap_pct
