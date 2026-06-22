# Fill Primitive (`research/code/fills.py`) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a venue-aware, idea-agnostic fill primitive that centralizes MT5-faithful bid/ask fill mechanics, so every Gate-3+ backtest pays the same realistic execution cost, guarded by a May-2024 parity regression test.

**Architecture:** A frozen `Venue` dataclass loads JM-Pro mechanics from `brokers/justmarkets.yaml` and exposes pure scalar fill methods (entry/exit fill side, stop quote, PnL, risk). Strategies hand-write their own per-day loop and call these methods — no strategy logic lives in the primitive. The retired idealized mid+tolerance path is marked deprecated (not deleted — it is shared by the abandoned ORB tree the handover forbids retrofitting).

**Tech Stack:** Python 3, pyyaml 6.0.3, numpy, pandas, pytest, ArcticDB (via `research/code/arctic_io.py`).

**Spec:** [docs/superpowers/specs/2026-06-13-fills-primitive-design.md](../specs/2026-06-13-fills-primitive-design.md)

---

## File Structure

| File | Responsibility |
|---|---|
| Create `research/code/fills.py` | `Venue` dataclass + `from_yaml` loader + scalar fill mechanics. No strategy logic, no tick loop. |
| Create `research/tests/test_fills.py` | Unit tests for the loader + each scalar method, plus the May-2024 ORB parity regression test (with the worked-example day loop as the reference consumer). |
| Modify `research/models/orb/orb001/anchor_oos.py` | Add a deprecation banner to `_simulate_day` (the retired idealized path). Do NOT delete its body. |
| Modify `docs/reference/research_protocol.md` | Add the Gate-3 "realistic fills via fills.py mandatory" rule. |

**Reconciliation note (read before Task 4):** spec acceptance criterion 4 says "delete the idealized `_simulate_day` path." After writing the spec we found `_simulate_day` is defined in `anchor_oos.py` and imported by `fork_a_ea_emulation.py` + `reconcile_cache_vs_parquet.py`, and 17 other ORB scripts each call a local copy. ORB-001 is closed, so all of these are dead-tree tombstones the handover explicitly says NOT to retrofit. Physically deleting `_simulate_day` *is* touching the dead tree (breaks their imports). Resolution: **retire in place** — mark it deprecated so no new/live consumer adopts it. The "no toggle" guarantee is met because `fills.py` offers only realistic mechanics, and there are already zero live consumers of the idealized path (its only non-dead caller, fork_a, died with ORB-001). This is a deliberate, surfaced deviation from the literal spec wording.

---

## Task 1: `Venue` dataclass + `from_yaml` loader

**Files:**
- Create: `research/code/fills.py`
- Test: `research/tests/test_fills.py`

- [ ] **Step 1: Write the failing test**

```python
# research/tests/test_fills.py
import pytest
from research.code.fills import Venue


def test_from_yaml_loads_jm_pro_constants():
    v = Venue.from_yaml("justmarkets")
    assert v.venue_id == "just_markets_mt5"
    assert v.half_spread == pytest.approx(0.10)     # 2-pip JM-Pro full $0.20 / 2
    assert v.contract_size == pytest.approx(100.0)  # oz per lot
    assert v.min_lot == pytest.approx(0.01)
    assert v.lot_step == pytest.approx(0.01)
    assert v.commission_per_lot_side == pytest.approx(0.0)
    assert v.swap_long == pytest.approx(0.0)
    assert v.swap_short == pytest.approx(0.0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -X utf8 -m pytest research/tests/test_fills.py::test_from_yaml_loads_jm_pro_constants -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'research.code.fills'`

- [ ] **Step 3: Write minimal implementation**

```python
# research/code/fills.py
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
bid/ask = mid ∓ half_spread via synth_bid_ask(); fill methods take bid/ask as
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -X utf8 -m pytest research/tests/test_fills.py::test_from_yaml_loads_jm_pro_constants -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add research/code/fills.py research/tests/test_fills.py
git commit -m "feat(fills): Venue dataclass + from_yaml JM-Pro loader (task 49)"
```

---

## Task 2: Scalar fill mechanics

**Files:**
- Modify: `research/code/fills.py` (add methods to `Venue`)
- Test: `research/tests/test_fills.py`

- [ ] **Step 1: Write the failing tests**

```python
# append to research/tests/test_fills.py

def _venue():
    return Venue.from_yaml("justmarkets")


def test_synth_bid_ask_flat_overlay():
    bid, ask = _venue().synth_bid_ask(2000.0)
    assert bid == pytest.approx(1999.90)
    assert ask == pytest.approx(2000.10)


def test_entry_fill_long_buys_ask_short_sells_bid():
    v = _venue()
    assert v.entry_fill(+1, bid=1999.90, ask=2000.10) == pytest.approx(2000.10)
    assert v.entry_fill(-1, bid=1999.90, ask=2000.10) == pytest.approx(1999.90)


def test_stop_quote_long_watches_bid_short_watches_ask():
    v = _venue()
    assert v.stop_quote(+1, bid=1999.90, ask=2000.10) == pytest.approx(1999.90)
    assert v.stop_quote(-1, bid=1999.90, ask=2000.10) == pytest.approx(2000.10)


def test_exit_fill_is_the_level():
    assert _venue().exit_fill(+1, level=1995.0) == pytest.approx(1995.0)


def test_pnl_usd_signed_by_side():
    v = _venue()
    # long +$3 move, range_w stop, 0.01 lot -> (2003-2000)*100*0.01 = +3.00
    assert v.pnl_usd(+1, entry=2000.0, exit=2003.0, lot=0.01) == pytest.approx(3.0)
    # short profits when price falls
    assert v.pnl_usd(-1, entry=2000.0, exit=1997.0, lot=0.01) == pytest.approx(3.0)


def test_risk_usd_is_stop_distance_times_contract_times_lot():
    # $3 stop distance, 0.01 lot -> 3*100*0.01 = $3.00
    assert _venue().risk_usd(stop_distance=3.0, lot=0.01) == pytest.approx(3.0)


def test_risk_cap_ok():
    v = _venue()
    # $0.50 risk on $50 equity = 1% <= 5% cap -> ok
    assert v.risk_cap_ok(risk_usd=0.50, equity=50.0, cap_pct=5.0) is True
    # $5 risk on $50 = 10% > 5% -> not ok
    assert v.risk_cap_ok(risk_usd=5.0, equity=50.0, cap_pct=5.0) is False
    # cap disabled (<=0) -> always ok
    assert v.risk_cap_ok(risk_usd=999.0, equity=50.0, cap_pct=0.0) is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -X utf8 -m pytest research/tests/test_fills.py -v -k "synth or entry_fill or stop_quote or exit_fill or pnl_usd or risk"`
Expected: FAIL with `AttributeError: 'Venue' object has no attribute 'synth_bid_ask'`

- [ ] **Step 3: Write minimal implementation**

Append these methods inside the `Venue` dataclass body (after `from_yaml`):

```python
    # --- spread overlay (locked JM-Pro flat 2-pip basis) ---------------------
    def synth_bid_ask(self, mid: float):
        """Flat overlay: derive bid/ask from a mid by the venue half-spread."""
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -X utf8 -m pytest research/tests/test_fills.py -v`
Expected: PASS (all 8 tests)

- [ ] **Step 5: Commit**

```bash
git add research/code/fills.py research/tests/test_fills.py
git commit -m "feat(fills): scalar fill mechanics (entry/exit/stop/pnl/risk) (task 49)"
```

---

## Task 3: May-2024 ORB parity regression test (the permanent guard)

This proves the fill primitive reproduces the EA-faithful Fork A result bit-for-bit
on the same sorted Arctic ticks. The worked-example day loop (a `fills.py` re-port of
`_simulate_day_ea`) lives in the test as the canonical reference consumer.

Pinned target = the stored Fork A single-month output
([research/outputs/orb/fork_a/fork_a_summary.json](../../../research/outputs/orb/fork_a/fork_a_summary.json)):
**n=23, win=17.4%, sum_R=−11.86, net_usd=−9.71** (config 09:00 / N=5 / trail_1R,
synthetic 2-pip on sorted Arctic). Upstream ground truth = MT5 tester run_id 1
(`tester_runs`, fidelity_verdict 'fail') — documented, not asserted bit-identical
(tester ran different synthetic-export ticks).

**Files:**
- Modify: `research/tests/test_fills.py`

- [ ] **Step 1: Write the failing test**

```python
# append to research/tests/test_fills.py
import numpy as np
from research.code.arctic_io import read_tick_month

# frozen ORB-001 live config (strategy_log.get_live_config('ORB-001'))
_ANCHOR_HOUR, _N_MIN, _EOD_HOUR = 9.0, 5, 21
_LOT, _EQUITY, _RISK_CAP_PCT = 0.01, 10_000.0, 5.0
_NS_H, _NS_M, _NS_D = 3_600_000_000_000, 60_000_000_000, 86_400_000_000_000


def _orb_day_ea(venue, ts, bid, ask, day0):
    """Worked example: _simulate_day_ea re-ported onto fills.py. ORB owns this loop;
    the venue owns every fill. Mirrors fork_a_ea_emulation._simulate_day_ea."""
    anchor = day0 + int(_ANCHOR_HOUR * _NS_H)
    or_close = anchor + _N_MIN * _NS_M
    eod = day0 + _EOD_HOUR * _NS_H

    in_or = (ts >= anchor) & (ts < or_close)
    if not in_or.any():
        return None
    or_high = float(bid[in_or].max())
    or_low = float(bid[in_or].min())
    range_w = or_high - or_low
    if range_w <= 0:
        return None

    post = np.where((ts >= or_close) & (ts < eod))[0]
    if len(post) == 0:
        return None

    side, ei = 0, None
    for k in post:
        if bid[k] >= or_high:
            side, ei = 1, k; break
        if bid[k] <= or_low:
            side, ei = -1, k; break
    if side == 0:
        return {"range_w": range_w, "traded": False, "R": 0.0, "pnl": 0.0}

    risk = venue.risk_usd(range_w, _LOT)
    if not venue.risk_cap_ok(risk, _EQUITY, _RISK_CAP_PCT):
        return {"range_w": range_w, "traded": False, "R": 0.0, "pnl": 0.0}

    seg = np.arange(ei, post[-1] + 1)
    B, A = bid[seg], ask[seg]
    entry = venue.entry_fill(side, bid=B[0], ask=A[0])
    peak = entry
    sl = or_low if side > 0 else or_high
    exit_px = venue.stop_quote(side, bid=B[-1], ask=A[-1])  # EOD market close at the watched quote

    for j in range(1, len(seg)):
        q = venue.stop_quote(side, bid=B[j], ask=A[j])
        if side > 0:
            if q > peak:
                peak = q
            want = peak - range_w
            if want > sl:
                sl = want
            if q <= sl:
                exit_px = venue.exit_fill(side, sl); break
        else:
            if q < peak:
                peak = q
            want = peak + range_w
            if want < sl:
                sl = want
            if q >= sl:
                exit_px = venue.exit_fill(side, sl); break

    pnl = venue.pnl_usd(side, entry, exit_px, _LOT)
    return {"range_w": range_w, "traded": True, "R": pnl / risk, "pnl": pnl}


def test_may2024_orb_parity_matches_fork_a():
    venue = Venue.from_yaml("justmarkets")
    df = read_tick_month((2024, 5), columns=["bid", "ask"])
    ts = df["ts_utc"].values.astype("datetime64[ns]").astype(np.int64)
    mid = (df["bid"].values + df["ask"].values) * 0.5
    bid, ask = venue.synth_bid_ask(mid)          # flat 2-pip overlay (vectorized)
    day_key = ts // _NS_D

    rows = []
    for d in np.unique(day_key):
        mk = day_key == d
        r = _orb_day_ea(venue, ts[mk], bid[mk], ask[mk], int(d) * _NS_D)
        if r is not None and r.get("traded"):
            rows.append(r)

    n = len(rows)
    net = sum(r["pnl"] for r in rows)
    sum_r = sum(r["R"] for r in rows)
    win = 100.0 * sum(1 for r in rows if r["R"] > 0) / n

    assert n == 23                              # vs stored fork_a: n=23
    assert net == pytest.approx(-9.71, abs=0.05)
    assert sum_r == pytest.approx(-11.86, abs=0.05)
    assert win == pytest.approx(17.4, abs=0.1)
```

- [ ] **Step 2: Run test to verify it fails (or errors)**

Run: `python -X utf8 -m pytest research/tests/test_fills.py::test_may2024_orb_parity_matches_fork_a -v`
Expected: FAIL — most likely an assertion mismatch if any mechanic diverges, or PASS if the port is already faithful. If it fails on the numbers, debug the day loop against `fork_a_ea_emulation._simulate_day_ea` until bit-identical (do NOT adjust the pinned targets — they are ground truth).

- [ ] **Step 3: Make it pass**

The implementation already exists (Task 2 methods + the worked-example loop above). If numbers mismatch, the bug is in `_orb_day_ea`'s use of the venue methods, not in the targets. Verify against `_simulate_day_ea`: long fills at `A[0]`, short at `B[0]`; long trails on bid, short on ask; EOD close fills at the watched quote.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -X utf8 -m pytest research/tests/test_fills.py -v`
Expected: PASS (all tests). Note: this test reads a full month of ticks (~110k rows) — expect a few seconds.

- [ ] **Step 5: Commit**

```bash
git add research/tests/test_fills.py
git commit -m "test(fills): May-2024 ORB parity guard pinned to Fork A ground truth (task 49)"
```

---

## Task 4: Retire the idealized path + add the Gate-3 protocol rule

**Files:**
- Modify: `research/models/orb/orb001/anchor_oos.py` (deprecation banner on `_simulate_day`)
- Modify: `docs/reference/research_protocol.md`

- [ ] **Step 1: Add the deprecation banner to `_simulate_day`**

Open `research/models/orb/orb001/anchor_oos.py`, find `def _simulate_day(`, and insert this as the first line of its docstring (or a comment directly above the `def` if there is no docstring):

```python
    # DEPRECATED / RETIRED (task 49, 2026-06-13): idealized mid+tolerance fill path.
    # Superseded by research/code/fills.py (realistic bid/ask, MT5-faithful). Kept
    # only because the abandoned ORB-001 tree imports it; do NOT use in new work and
    # do NOT delete (the handover forbids retrofitting the dead ORB scripts).
```

- [ ] **Step 2: Add the protocol rule**

Open `docs/reference/research_protocol.md` and add this line to the Gate-3 (cost / realistic-execution) section (place it where gate rules are listed; if there is no obvious anchor, add under the Gate 3 heading):

```markdown
- **Realistic fills mandatory from Gate 3.** All path-dependent backtests (entries, exits, stops) must fill via `research/code/fills.py` (venue-aware bid/ask, MT5-faithful) — never an idealized mid+tolerance model. Classifier ideas that gate on AUC/IC (e.g. HMM-001) never simulate fills and are exempt. Guarded by `research/tests/test_fills.py::test_may2024_orb_parity_matches_fork_a`.
```

- [ ] **Step 3: Verify nothing live imports the idealized path**

Run: `grep -rn "from research.models.orb.orb001.anchor_oos import" research --include=*.py | grep -v "orb/orb001/"`
Expected: no output (only dead ORB-001 tree files import it; no live/cross-model consumer).

- [ ] **Step 4: Commit**

```bash
git add research/models/orb/orb001/anchor_oos.py docs/reference/research_protocol.md
git commit -m "docs(fills): retire idealized fill path + Gate-3 realistic-fills rule (task 49)"
```

---

## Task 5: Log the architecture decision + close the backlog task

**Files:** none (DB writes via code layer).

- [ ] **Step 1: Log the human methodology decision**

Run (one line, via the code layer per CLAUDE.md rule 10):

```bash
python -X utf8 -c "from research.code.agent_log import log_human_decision; log_human_decision('ORB-001', 7, 'Fill-realism architecture LOCKED + BUILT: research/code/fills.py = venue-aware bid/ask primitive (Venue dataclass from justmarkets.yaml). A=dataclass not YAML-DSL; B=hand-write entry/exit per strategy, extract lib on 2nd reuse; C=realistic fills mandatory Gate3+, classifier ideas exempt. Idealized _simulate_day retired (not deleted; dead ORB tree). May-2024 parity test pinned to Fork A ground truth (n=23,net=-9.71).', 'task 49 built. fills.py + test_fills.py (8 unit + 1 parity). Protocol rule added to research_protocol.md.')"
```

Expected: prints `[agent_log] HUMAN call_id=<N> ORB-001 gate=7`

- [ ] **Step 2: Mark backlog task 49 done**

Run:

```bash
python -X utf8 -c "from research.code.backlog import resolve_task; resolve_task(49, 'Built research/code/fills.py (Venue dataclass + scalar bid/ask fill mechanics from justmarkets.yaml). 8 unit tests + May-2024 ORB parity regression test (pinned to Fork A: n=23, net=-9.71). Idealized path retired. Gate-3 realistic-fills rule added to research_protocol.md.', 'done')"
```

Expected: prints the backlog resolution confirmation.

- [ ] **Step 3: Final full-suite run**

Run: `python -X utf8 -m pytest research/tests/test_fills.py -v`
Expected: PASS (all tests).

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore(fills): log fill-realism decision + close backlog task 49"
```

---

## Self-Review

- **Spec coverage:** Venue dataclass (T1) ✓; scalar mechanics owning broker conventions (T2) ✓; bid/ask as inputs, flat-2pip overlay as caller-side synth (T2/T3) ✓; strategies hand-write loop (T3 worked example) ✓; delete-idealized reconciled to retire-in-place with surfaced deviation (T4) ✓; May-2024 MT5/Fork-A parity guard (T3) ✓; Gate-3 protocol rule (T4) ✓; 18 dead scripts untouched ✓; decision logged (T5) ✓. Acceptance criterion 2 ("bit-identical to Fork A on May-2024") = T3 assertions.
- **Placeholder scan:** none — every step has concrete code/commands and pinned numbers.
- **Type consistency:** `Venue` methods (`synth_bid_ask`, `entry_fill`, `exit_fill`, `stop_quote`, `pnl_usd`, `risk_usd`, `risk_cap_ok`) are defined in T1/T2 and used with identical signatures in T3. `side` is `int` (+1/−1) throughout. `from_yaml("justmarkets")` consistent across all tests.
- **Deviation flagged:** spec criterion 4 (literal "delete") → retire-in-place; rationale documented in the Reconciliation note and Task 4. Surface this to Syafiq at handoff.
