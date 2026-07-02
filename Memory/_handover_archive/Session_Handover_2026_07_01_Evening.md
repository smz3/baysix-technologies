# Handover — July 1, 2026 Evening

## State
- **Pure LOGIC session — no code, no measurement, no cost** (Syafiq: nail FOB logic before measuring).
- **New spec LOCKED:** [2026-07-01_fob_sequence_storyline_entry_logic.md](../docs/specs/2026-07-01_fob_sequence_storyline_entry_logic.md) — sequence-storyline MTF entry model, logic-only.
- **Core model:** a CF is a *container, not an atom*; "too big" is **detected structurally** (contains a complete lower-TF PBO→VR→CF), never measured in pips; enter at the **LEAF** of the live nested-cycle stack (floor M5); recursion is **top-down preference** (M30→M15→M5); enter/skip = existence of an **in-zone-chain leaf**; `vr_fresh` = **management flag, NOT entry gate**; located = **unbroken nested-in-zone chain**; window closes when price exits the controlling zone.
- **Cross-referenced with** [awareness/conditioner spec v3](../docs/specs/2026-07-01_fob_awareness_conditioner_spec.md): it already answers **9 of my 13 open Qs** (S1–S10 + dec 4/5/6). Reconciliation banner added to the entry-logic spec.
- **Logged:** human decision `call_id 91`; tasks 213 (13 Qs), 214 (ruling), 215 (v0.2).

## Next
1. **(task 214, P1) — RULING NEEDED from Syafiq:** gate-vs-conditioner framing. Entry-logic spec = active enter/skip (skip=veto); awareness spec dec 2 = conditioner-never-gate. Which governs? **Blocks all build.**
2. **(task 215, P1)** After ruling: write entry-logic **spec v0.2** — fold awareness dec 4/5/6, resolve the only 2 genuinely-open Qs: **Q2** (containment-window endpoint) + **Q11 RR-floor**.
3. **(task 213, P1)** Umbrella: the 13 Qs (9 now resolved by cross-ref; recommendations in this session's final report).

## Blockers
- **Task 214 (the ruling) blocks build** — but this is a logic phase, so it blocks nothing until we choose to build. No technical blocker.

## Why
- **Cost/measurement excluded on purpose.** Syafiq hard-corrected mid-session: do NOT factor cost (or even measure buckets) until FOB logic is understood as intended — "big mistake to factor in cost" now. Overrides the awareness spec's measure-first ordering *for this phase*.
- **"Too big" reframed to structural, not pips** — Syafiq asked "how do we track it without an arbitrary rule?" Answer: a CF is too-big iff a complete lower-TF SOP fits inside it (the fractal decides). Kills every arbitrary threshold; the only numbers left are universal risk knobs (SL buffer, sizing, RR-floor) that live in the trader layer, not the logic.
- **`vr_fresh` corrected to a management flag** — an earlier draft treated fresh=skip; the manual (RTT 7.5/7.6) keeps fresh tradeable (TP-fast+layer) vs not-fresh (ride). Fresh is HOW you manage, not WHETHER you enter.
- **Q7 is the existential guard** — "every cycle nested in its parent's zone" is safe ONLY if built from each TF's own-TF cycle state + local one-higher geometry (awareness dec 5 independence guard), never full-stack propagated direction — else the result_id-19 −33.8pp artifact returns. This keeps the chain distinct from the rejected full-stack alignment gate (result_id 18).

## Ruled-Out
- **Pip/ratio/ATR threshold for "too big CF"** — rejected in favour of structural containment (no arbitrary number). Syafiq explicitly wanted no arbitrary rule.
- **`vr_fresh` as an entry gate** — rejected; it's management-only (manual RTT 7.5/7.6).
- **"Enter directly on any setup-TF CF" (current trader behaviour)** — rejected as the defect being fixed: it flattens the fractal (enters mis-located + oversized CFs).
- **My original Q1 split (conti→PBO zone / reversal→VR zone)** — superseded by awareness dec 4: the one-higher VR zone's held/reject-vs-break state *defines* the type; no upfront type choice, no circularity.

## Live-Threads
- **Gate-vs-conditioner philosophy clash (task 214)** — the two FOB specs now genuinely disagree on framing; unresolved until Syafiq rules. This is the single most important loose end.
- **Q2 — containment window endpoint** — is a child "inside the CF" measured over the VR→CF leg, or the post-CF continuation (2.1.3 forms the sub-setup in the rally)? Materially changes detection. Lean: VR-detected → current CF.
- **Q11 — RR-floor** — "enough room to bother" to the next structural barrier; a tuning knob, deferred but named.
- **Trader ingest window too narrow for recursion** — trader ingests only {setup_tf−1, setup_tf} ([fob_trader.mq5:107-109](../mt5/Experts/fob_system/fob_trader.mq5#L107-L109)); full recursion needs the whole band below setup (setup↓M5). Emitter already classifies all 9 TFs, so data exists — only the trader's ingest is the gap. Architectural, for the build phase.
- **Prior P1 plumbing still open** (pre-this-session): task 211 (re-emit v1.26.0 on run_id-18 window), task 212 (re-test trader on re-emitted zones), task 209 (CF break-state A/B/C DERIVE). These wait until the entry-logic direction is settled — don't run them cold.
