# Handover — July 9, 2026 Morning

## State
- **Discussion/logic session — no build, no measurement.** Locked the definition of the FOB **VR Fresh/Non-Fresh detector** (a NEW feature, not yet coded). Spec written: [2026-07-09_fob_vr_fresh_detector_spec.md](../docs/specs/2026-07-09_fob_vr_fresh_detector_spec.md). Lineage: strategy_log 105 (PROPOSED, component=exit). Build task: **260 (P1)**.
- **Definition LOCKED (Syafiq):** fresh = **touch-based** (any tick into VR band `[L1,L2]`, wick counts); clock starts at **1st CF birth**; **first post-CF touch → structured**; **born-structured (a)** if already in-band at CF1; **no per-CF re-arm**.
- **Goal shift (noted):** current H4-CF3 entries are fine for **swing on 10k**; Syafiq now wants a **rapid scalp/intraday algo to grow \$50** without blowing up. Fresh/Non-Fresh doubles as the **scalp(fresh)/swing(structured) router**.
- **Confirmed against code:** existing VR touch-ladder (`t1/t2/t3`), RT ladder, invalidation are CORRECT — leave untouched. Legacy `z.vr_fresh` (close-based, from VR birth, [fob_lifecycle.mqh:298](../mt5/Include/fob_system/fob_lifecycle.mqh#L298)) is NOT the concept → rename/replace on build.

## Next
1. **(task 260, P1)** Build the detector: add `vrf_armed`/`vrf` to `FobZone`, rename legacy `vr_fresh`; arm at `cfCount` 0→1 (parent VR `seq` lookup); kill on first band-touch in `FobAccOnTick` ([fob_lifecycle.mqh:239-249](../mt5/Include/fob_system/fob_lifecycle.mqh#L239-L249)).
2. **(task 260 cont.)** EMIT-mode visual FIRST — stamp `[FRESH]`/`[STRUCT]` on VR L2 label (+ optional solid/dashed border) so Syafiq eyeball-verifies detection before any measure. EMIT byte-identical (nicety, not in CSV).
3. **(task 260 cont.)** Then excursion pre-screen (exploratory) → **MT5 arbiter A/B**: fresh→VR-touch TP / structured→trail-ride **vs** trail-everything baseline (v1.39.0, session 12-23, H4 CF3, real ticks).

## Blockers
- **None.** Definition fully locked; build starts cold-clean next session from the spec.

## Why
- **We pivoted off the filter search.** task 239 (D1/W1 confluence) was already tried and is "too restrictive" — and the manual + result_id 18 say alignment is the WRONG layer (bias picks horizon, not side). Syafiq confirmed entries are fine; the deficit is the EXIT.
- **Fresh/Non-Fresh is the payoff-asymmetry lever (task 167 "THE LEVER"), reframed as an EXIT ROUTER** — the concrete answer to the OOS flat-R problem (on-hours OOS +$3.23/tr but R t+0.36, result_id 50, prior handover). Current trailing stop (1.0R/1.5R, result_id 39/42) is structure-blind: it trails identically whether a fresh untested VR wall sits ahead or open space. The router makes the exit structure-aware: fresh→TP at the wall, structured→ride through.
- **Definition corrected 3×** this session before locking: (1) not close-based → **touch**; (2) not from VR birth → **from 1st CF birth**; (3) it is NOT the existing T-touch counter (wrong window) nor RT (post-invalidation phase). This is why the legacy `vr_fresh` field must be renamed — same word, wrong concept.
- **Tracking design = a gated flag, not a new detector** — reuses the tick band-touch primitive already computed in `FobAccOnTick`; only wiring is CF1-birth → parent-VR arm. Keeps existing VR logic byte-identical.

## Ruled-Out
- **task 239 D1/W1 confluence as the offense lever — set aside** (not formally killed): Syafiq reports it's too restrictive; wrong layer per manual + result_id 18. Do not re-surface as "the fix" — offense now comes via the exit router, not an entry gate.
- **Edge-case (b) leave-and-return — REJECTED** in favour of (a) born-structured (simpler, matches "touched after CF born"). See spec §1.
- **Per-CF re-arm — set aside** this session: clock arms once at the 1st CF, does not reset per later CF.

## Live-Threads
- **Fresh/Non-Fresh is a HYPOTHESIS, not proven edge.** Could return flat if the flag doesn't correlate with forward outcome — the arbiter A/B (task 260 step 3) settles it; a flat result cheaply rules out the manual's headline lever.
- **\$50 rapid-scalp mandate is new and unspecified.** Min-lot DD floor at \$50 is structural ([[orb_dd_structural_floor]]) — a scalp algo on \$50 needs its own risk/lot design; not yet scoped. Fresh-VR trades are the natural scalp cohort but sizing/DD for a \$50 account is an open thread.
- **VR-touch TP "which-VR" selector (task 240) still open** — in a nested storyline there are several VR zones (leaf vs parent); the fresh detector gives the TRIGGER (first fresh-VR touch) but which VR's zone is the target in a multi-TF stack is unresolved.
