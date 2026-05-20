# ADR-006: Vectorized vs Event-Driven Validation

**Date:** 2026-05-20
**Status:** Active
**Component:** `core/measurement/*` (vectorized Engine) + `sigma-lean/` (event-driven, B2BZoneStrategy)

---

## Decision

Two validation tools, two distinct jobs. They are sequenced cheap → expensive, not treated as duplicates.

| Tool | Job | Question it answers |
|------|-----|---------------------|
| **Vectorized Engine** (`core/measurement`) | Alpha **discovery** | "Is the signal predictive?" — IC, ICIR, decay, factor decomp, regime conditioning |
| **Event-driven** (`sigma-lean`, LEAN CLI) | Alpha **capture** | "Does the edge survive execution?" — fills, slippage, intrabar path, sizing, financing |

**The rule:** Use the vectorized Engine for all signal research. Escalate to `sigma-lean` only when **(a)** the signal clears the falsification gate (§2 of `ENGINE_BLUEPRINT.md`) **AND (b)** the strategy has path-dependent execution the vectorized stage assumed away. The event-driven run is **Gate B** in the build order (§4) — it runs the moment Slice 2 passes, before any mechanism upgrade (Slice 3) is funded with effort.

`sigma-lean` is **NOT** a higher-resolution rerun of the vectorized IC number. It is a different falsification — it can kill a signal that has genuine IC but dies on execution friction.

---

## Why

**Vectorized is valid only for path-independent signals.**
- A vectorized backtest assumes position at time *t* depends only on information at *t*, and that the period return is realised cleanly. That holds for cross-sectional rank signals and most factor research.
- It is fast (seconds), so it is the right tool for IC, decay profiles, parameter sweeps, and the regime-conditioning kill test.

**Event-driven is required when execution is path-dependent.**
- Stops, take-profits, trailing stops, partial fills, intrabar sequencing, margin and financing over time — none of these survive a vectorized assumption. They need a bar-by-bar simulator.
- It is expensive (minutes-to-hours), so it is wasted on a signal that has not first cleared the cheap predictiveness bar.

**The B2B-specific trigger (the reason this ADR exists).**
- The 1,084 H1 B2B trade records are **already path-resolved** — each carries a frozen entry/exit/R produced by a zone backtest. So the vectorized Slice 1–2 work is *analysis on top of event-resolved outcomes*, not pure signal research.
- Consequence: the measured edge may live partly in the **trade management** (SL/TP placement, trailing), not only in the entry regime. Vectorized IC on the entry conditioner can therefore be an artifact of one frozen exit rule.
- Therefore `sigma-lean` runs the **moment Slice 2 passes** — specifically to confirm the entry-regime edge is not an exit-logic artifact. Deferring it further than that is a governance violation.

---

## Alternatives Considered

| Alternative | Description | Why not chosen |
|-------------|-------------|----------------|
| **Vectorized only** | Trust the IC tearsheet, skip event-driven, go straight to live | Ignores execution friction and the frozen-exit artifact; the single most common way a "validated" intraday signal dies live |
| **Event-driven only** | Run everything through LEAN from the start | Wastes the expensive tool on signals that fail the cheap predictiveness bar; cripples parameter sweeps and IC research |
| **LEAN as a higher-res rerun** | Treat the LEAN result as a more accurate version of the vectorized IC | Category error — they answer different questions; a signal can pass one and fail the other. This ADR exists to prevent exactly this misreading |
| **Tick-level simulator** | Sub-bar fill modelling beyond LEAN's bar resolution | Justified only at live capital with measured slippage sensitivity — deferred, see below |

---

## Deferred Upgrades

### Upgrade 1: Bar-resolution → tick/sub-bar fill modelling

**What it is:** Model fills at sub-bar resolution (tick data) rather than LEAN's bar-level fill assumptions.

**Trigger condition:** Gate B passes, live capital is committed, AND a slippage-sensitivity sweep shows net edge is materially sensitive to fill assumptions (edge halves under a 1-tick adverse fill).

**How to implement:** Ingest Dukascopy tick data for the traded sessions; re-run the confirmed strategy with tick-level fill logic; compare net R distribution vs bar-level.

---

## Interview Defence

> "We separate validation by question, not by fidelity. The vectorized engine answers whether the signal is predictive — IC, ICIR, decay — cheaply, so it's where all the research happens. Event-driven LEAN answers a different question: does the edge survive execution, with realistic fills and intrabar path? We escalate to it only after the signal clears the falsification gate, and specifically early for B2B because our trade records have the exits baked in — so we have to rule out that the edge is an artifact of a frozen exit rule rather than the entry regime."

---

## Relationship to other ADRs

- **ADR-004 (IC method)** governs the vectorized side of this decision (how IC/ICIR/t-stat are computed).
- **ADR-005 (cost model)** feeds both tools: the vectorized net-IC and the LEAN cost assumptions must agree on spread/impact/financing.
- This ADR is referenced by `ENGINE_BLUEPRINT.md` §3 ("Vectorized vs event-driven — sigma-lean's home") and §4 ("Gate B").
