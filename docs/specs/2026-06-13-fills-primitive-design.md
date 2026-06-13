# Fill Primitive (`research/code/fills.py`) — Design Spec

**Task:** backlog #49 — "bake fill-realism in EARLY (MT5 fidelity gap)."
**Date:** 2026-06-13
**Status:** locked in [Session_Handover_2026_06_13_Morning.md](../../../memory/Session_Handover_2026_06_13_Morning.md); this spec records the build contract.

---

## Why this exists

Realistic bid/ask fill mechanics are currently **hardcoded and duplicated** across the
codebase: `HALF_SPREAD = 0.10` appears in [export_ticks_mt5.py](../../../research/code/export_ticks_mt5.py),
[fork_a_ea_emulation.py](../../../research/models/orb/orb001/fork_a_ea_emulation.py), and
[d0_parity.py](../../../research/models/orb/orb001/d0_parity.py). The fill *conventions*
(long fills at ask, short at bid, stop on the opposite quote, PnL math) live inline inside
`_simulate_day_ea`. Every new strategy re-derives them, and any one of them can silently
diverge from what the MT5 EA actually does — the exact class of fidelity gap that produced
the ORB-001 Gate-7 contradiction.

This primitive centralizes the **broker fill mechanics** behind one venue-aware object so
that every Gate-3+ backtest pays the same, MT5-faithful execution cost, verified against the
MT5 Strategy Tester as ground truth.

## Scope boundary (locked decision B)

The primitive owns **broker mechanics only** — it is idea-agnostic and contains **no strategy
logic**. Strategies hand-write their own OR/breakout/trail/EOD loop and *call* the primitive
for fills. A reusable strategy library is extracted only on the 2nd genuine reuse, not now.

| In scope (broker mechanics) | Out of scope (strategy owns) |
|---|---|
| bid/ask the order fills against | opening-range / signal computation |
| long→ask, short→bid entry fill | breakout / entry-trigger detection |
| stop watches opposite quote (long stop on bid, short stop on ask) | trailing-stop logic |
| PnL = (exit−entry)·contract·lot (sign by side) | EOD close decision |
| risk_usd = stop_distance·contract·lot | position sizing / risk-cap policy |
| risk-cap **arithmetic** (given equity, pct, risk_usd) | *whether* to apply the cap |
| venue constants from `justmarkets.yaml` (half_spread, contract, lot defaults) | — |

## Venue source of truth

Reads **JM-Pro** from [brokers/justmarkets.yaml](../../../brokers/justmarkets.yaml):
- `costs.model: spread_only` → **no commission, no swap** (swap-free).
- half-spread = **$0.10/oz** (2-pip JM-Pro spread; `tcm.spread.pip_usd_per_lot` × 1 pip).
- `contract_size_oz: 100`, `min_lot: 0.01`, `lot_step: 0.01`.

The yaml is loaded once and cached. Adding a second venue later = a second yaml + a venue id
argument; no code change to the mechanics.

## Spread basis (locked — NOT reopened here)

The locked basis is the **JM-Pro flat 2-pip overlay**: the caller synthesizes
`bid = mid − 0.10`, `ask = mid + 0.10` from the Dukascopy mid, because the Arctic store's
*native* Dukascopy spread (~3.5-pip median) is Dukascopy's cost, not JM's. The real floating
JM spread is measured later at the FORWARD gate. This spec does **not** change that basis.

Mechanical consequence only: because the store *does* hold real bid/ask, the primitive's fill
methods take **bid and ask as explicit inputs** (correct MT5 mechanics) rather than deriving
them from a mid internally. The flat-2-pip synthesis stays in the caller, where it is visible.
A `native`-spread path (fill on the source's real bid/ask) is reachable as a non-default knob
for future sensitivity work, but flat-$0.10 remains the default/locked behavior.

## Public surface (dataclass — locked decision A)

A lightweight `@dataclass` (NOT a YAML DSL), constructed once per backtest:

```
Venue.from_yaml("justmarkets") -> Venue          # half_spread, contract, lot defaults, costs
```

Scalar mechanics (pure, no tick loop inside):
```
synth_bid_ask(mid)            -> (bid, ask)       # flat overlay: mid ∓ half_spread  (the locked basis)
entry_fill(side, bid, ask)    -> fill_px          # long->ask, short->bid
exit_fill(side, level)        -> fill_px          # stop/market exit fills at the level (market close fills at quote)
stop_quote(side, bid, ask)    -> px               # which quote a stop watches: long->bid, short->ask
pnl_usd(side, entry, exit, lot)-> usd             # (exit-entry)*contract*lot, signed by side
risk_usd(stop_distance, lot)  -> usd              # stop_distance*contract*lot
risk_cap_ok(risk_usd, equity, cap_pct) -> bool    # arithmetic only; caller decides to call it
```

The strategy's per-day loop is unchanged in shape — it just replaces inline arithmetic with
these calls. `_simulate_day_ea` becomes the worked example / first consumer.

## What gets deleted

The **idealized** mid+tolerance fill path (`anchor_oos._simulate_day`) is removed — **no
toggle**. From Gate-3 onward there is one fill model: realistic bid/ask. Classifier ideas that
gate on AUC/IC (e.g. HMM-001) never simulate fills and are exempt.

The 18 dead ORB exploratory scripts are **not** retrofitted.

## Parity regression test (the permanent guard)

A pytest pinned to the **MT5 Strategy Tester ground truth** for May-2024 ORB
(09:00 / N=5 / trail_1R, synthetic 2-pip): the EA-faithful Python path rebuilt on
`fills.py` must reproduce the tester within tolerance (≈22 trades, ~13.6% win, ~−$11).
This test fails loudly if anyone changes the fill conventions out from under the EA — it is
the structural lock that the ORB saga's root cause (silent fill-convention drift) cannot
recur. Lives in `research/tests/` (or alongside fork_a); runs in the normal test sweep.

## Acceptance criteria

1. `Venue.from_yaml("justmarkets")` returns JM-Pro constants matching the yaml (half_spread
   0.10, contract 100, lot 0.01, zero commission/swap).
2. `_simulate_day_ea` (or a thin re-port of it) calls `fills.py` and produces **bit-identical**
   per-trade results to the current Fork A output on May-2024.
3. The May-2024 MT5-tester parity test passes.
4. The idealized `_simulate_day` path is deleted and no caller references it.
5. A one-line protocol rule is added to [docs/reference/research_protocol.md](../../../docs/reference/research_protocol.md):
   realistic bid/ask fills via `fills.py` are mandatory from Gate 3 (classifier ideas exempt).

## Out of scope (this task)

- Strategy-spec workflow / `params_json` (task 57 — next).
- Arctic backup (task 56).
- Multi-venue / IBKR cost model (task 30).
- Floating/measured JM spread (FORWARD gate).
