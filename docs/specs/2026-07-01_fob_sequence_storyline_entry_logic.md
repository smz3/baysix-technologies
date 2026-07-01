# FOB Sequence-Storyline Entry Logic (Spec v0.1 — LOGIC ONLY)

**Date:** 2026-07-01
**Status:** PROPOSED — logic locked for now; NOT built, NOT measured. Cost/measurement deliberately excluded (discovery is cost-free; logic must be correct before any test).
**Scope:** How FOB *decides where to enter* on a continuation, using the nested Sequence-Storyline MTF model. Sizing, TP magnitude, and cost belong to the trader/tuning layer, not here.

Source: Bonker manual Phase-2 Storyline Sequence (Images 2.1.1–2.1.9) + Phase-1 CF/VR/RTT chapters. See [FOB manual dissection](../../research/papers/fob/FOB_breakout_system.dissect.md) and [CMP storyline model](2026-06-27_fob_cmp_storyline_model.md).

---

## 1. The core reframe

- The storyline is **not a flat list of CFs** — it is a **stack of nested cycles**, one per TF, along the control chain **W ← D ← H4 ← H1 ← M30 ← M15 ← M5 ← M1**. Direction of TF *n* = direction of the live cycle on TF *n*−1 (2.1.2).
- Each cycle = **PBO → VR → CF**. **Every CF of TF *n* is itself a leg that decomposes into a full PBO→VR→CF on TF *n*−1.** A CF is a *container*, not an atom (2.1.2, 2.1.3).
- Therefore **a CF is an *evaluation trigger*, never an auto-entry.** The current trader (one market fill per setup-TF CF) flattens this fractal — that is the defect this spec fixes.

## 2. "Too big" is detected, never measured

- A CF is *too big to enter directly* **iff a complete, direction-aligned PBO→VR→CF has completed one TF below, inside it.** If a qualifying lower cycle fits inside → recurse into it. If none fits → the CF is atomic → it is the entry.
- **No pips, no ratio, no ATR.** The fractal decides. This subsumes both size intuitions (wide |L1–L2| band *and* large P4-from-L1 run are exactly what give a lower cycle the room to complete).
- "Qualifying child" = a lower-TF cycle that passes the **same SOP classifier** ([fob_sequence.mqh](../../mt5/Include/fob_system/fob_sequence.mqh)) — identical rules at every TF, so the test is non-arbitrary by construction.

## 3. The live storyline is a linked stack; you enter at the LEAF

- At runtime the control chain is a **live linked stack**: the live H4 cycle → live H1 cycle building its continuation → M30 → … .
- **Entry = the LEAF**: the deepest TF (floor **M5**; M1 excluded, matching the M1-PBO skip) with a live, direction-aligned, correctly-located cycle that has **no qualifying child below it**.
- A cycle is "too big to be the leaf" **iff it has a child.** Recursion terminates itself; no depth parameter.

## 4. Recursion is TOP-DOWN preference, not time-first

- Lower TF is faster, so "first CF in *time*" would always be M5 and collapse the model. Recursion walks the stack **downward from the parent** (M30 before M15 before M5, 2.1.3) and stops at the first level that is a leaf. M5 wins only if M30 and M15 each still have a child.
- Distinct from the existing *"whichever made the VR first dictates the TF"* rule — that is the **same-instant tie-break for the *setup* TF**, a different question. Both coexist.

## 5. Enter / Skip / Manage — all structural

**ENTER** when:
- A qualifying leaf cycle exists down to M5, **and**
- its CF sits inside the **controlling zone chain** (see §6), **and**
- it is direction-aligned with its parent.

**SKIP** when:
- No in-zone leaf exists down to M5 — price is running with no tradeable sub-structure left inside the zone ("the bus left"), **or**
- Price has **exited the controlling zone** toward target (window closed → any later leaf is a chase). This is the structural *stop-hunting-for-entry* trigger — not a timeout, not a pip count.
- Note: the 2.1.9 "VR-break pullback" trap is respected for free — the emitter only fires CFs on *confirmed continuation breaks*, never on a bare pullback.

**MANAGE** (post-entry, set by `vr_fresh` of the entered cycle — RTT 7.5/7.6):
- **Fresh VR** (price ran straight, no close back into the VR zone) → **TP fast in the VR zone, then layer on the next CF** (scalp/VR-to-VR character).
- **Not-fresh VR** (closed back into the VR zone) → **ride / hold.**
- ⚠️ `vr_fresh` is a **management flag, NOT an entry gate.** (Corrects an earlier draft that treated fresh = skip — the manual keeps fresh tradeable.)

## 6. "Correctly located" is a CHAIN property

- Location is not one test at the leaf. **Every cycle in the stack must sit inside its direct parent's controlling zone** (one-TF-at-a-time control, 2.1.2).
- A valid entry = an **unbroken nested-in-zone chain** from top setup → leaf. Any link drifting outside its parent's zone = broken storyline = skip.
- ⚠️ This is *structural nesting*, deliberately **not** the rejected full-stack directional-alignment gate (result_id 18). Distinguishing the two is Open Question Q7 below.

## 7. Where the numbers live

- **The logic has zero arbitrary FOB-specific parameters** — containment (recurse), nested-in-zone chain (located), CF existence (enter/skip), `vr_fresh` (manage).
- The only numbers are **universal risk knobs** — SL buffer, lot sizing, RR floor — and they live in the **trader/tuning layer**, not this doc. A huge single-bar CF is not a skip; it is just **small lots** (sizing absorbs it) — the correct home for the last remnant of the P4/size intuition.

## 8. Architectural consequence (flag, not build)

- The trader today ingests only `{setup_tf−1, setup_tf}` ([fob_trader.mq5:107-109](../../mt5/Experts/fob_system/fob_trader.mq5#L107-L109)) — under H4 it sees only H1 and **cannot** watch M30/M15/M5. Full recursion needs it to ingest **the whole band below the setup TF (setup↓M5)**. The emitter already classifies all 9 TFs, so the event data exists; only the trader's ingest window is too narrow.

---

## 9. Open Questions (to resolve before build)

- **Q1 — Controlling-zone by setup type.** Conti CF → origin PBO zone; reversal/structured CF → parent VR zone. What picks the type at runtime without circularity (type needs the zone; zone needs the type)?
- **Q2 — Containment window.** A "child inside the CF" — inside *what span*? PBO→CF leg, VR→CF leg, or the continuation *after* the CF (2.1.3 forms the sub-setup in the post-CF rally)?
- **Q3 — "Inside the zone" definition.** Near half, full band, or just not-beyond-the-far-edge? Close-inside (body) or touch/wick? (Manual: body counts, wick doesn't — but for the entry *window* a touch may matter.)
- **Q4 — Direction-alignment timing.** During a pullback the child is counter to the parent and only re-aligns at entry. Do we test alignment on the child's PBO direction or its live CF direction?
- **Q5 — Multi-CF composition.** Does every setup CF spawn its own recursion/entry, or only the first tradeable one? How does the leaf model produce "skip CF1, take CF2" (sideways, 4.10/4.11)?
- **Q6 — Top of the stack.** Is the top a fixed configured setup TF (current InpTfPair), or does it float to the highest live aligned cycle (W/D)?
- **Q7 — Chain vs rejected alignment gate.** Does "every cycle nested in its parent's zone" re-introduce the rejected full-stack-alignment gate (result_id 18), or is structural nesting genuinely distinct from directional alignment? Must be proven distinct.
- **Q8 — Qualifying-child completeness.** To recurse, must the child have *confirmed* (CF fired), or is PBO+VR enough? (Waiting on an unconfirmed child = timing risk.)
- **Q9 — Setaman (2.1.5).** When 3 TFs break the same direction at once (concurrent confirmation), is that an immediate high-conviction direct entry (skip recursion) or still recursed?
- **Q10 — Counter-scalp scope (2.1.6/2.1.7).** VR-to-VR counter-buys while the higher TF still trends — IN scope for this logic or explicitly OUT (continuation-only)?
- **Q11 — TP target level.** "Next HTF zone/barrier" — parent's, grandparent's, or top-setup's zone? (2.1.4 TPs a Daily setup at Weekly.) And the RR floor to decide "enough room to bother."
- **Q12 — Barrier definition.** Manual TPs at barriers; we have no barrier detector. Barrier = prior HTF swing/zone, or something else?
- **Q13 — Layering bounds.** Fresh → layer on next CF: max layers, per-layer sizing, stacking direction (ties to task 168).
