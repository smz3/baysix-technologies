# FOB VR Fresh / Non-Fresh Detector (Spec v1.0 — LOGIC LOCKED, NOT BUILT)

**Date:** 2026-07-09
**Status:** PROPOSED — logic locked with Syafiq this session; NOT built, NOT measured.
**Cross-refs:** [FOB manual dissection §RTT VR Fresh/Not-Fresh, Images 7.5/7.6](../../research/papers/fob/FOB_breakout_system.dissect.md) · [sequence-storyline entry logic v0.2](2026-07-02_fob_sequence_storyline_entry_logic_v0.2.md) · CLAUDE.md FOB canonical.

---

## 0. Why this exists (the edge thesis)

- **The problem (from OOS, handover 2026-07-08 Evening2):** on-hours OOS is **positive-$ but flat-R (t+0.36)**. Entries are fine; the **exit leaves the payoff asymmetry on the table**.
- **Current exit = a single, structure-blind trailing stop** (`InpTrailStop`, activate 1.0R / trail 1.5R, result_id 39/42). It trails the same way on every trade regardless of what structure sits ahead of it. It reacts to *price giving back*, never to *what's in front of the trade*.
- **Fresh/Non-Fresh is an EXIT ROUTER, not an entry filter.** It decides, trade-by-trade:
  - **Fresh VR** (untested barrier dead ahead) → **TP at the first VR touch** (manual 7.5: "must TP in the VR zone"). Don't let the trail give it back through a live wall.
  - **Structured VR** (barrier already worn) → **let the trail ride through / hold** for the extension (manual 7.6).
- **Why it's the right lever:** (1) preserves n — it's an exit overlay, not a gate, so no D1/W1 trade-count collapse; (2) it IS the scalp-vs-swing router Syafiq asked for (fresh = rapid defined-target scalp for the $50 account; structured = swing ride); (3) it's the manual's actual headline offense.
- **Quant-honest:** this is a HYPOTHESIS. It settles only on the MT5 arbiter (§4). Could come back flat if fresh/non-fresh doesn't correlate with forward outcome — in which case we've cheaply ruled out the manual's headline lever.

---

## 1. The definition (LOCKED with Syafiq, 2026-07-09)

Corrected against Syafiq's actual trading definition — **differs from both the manual's literal wording and the legacy code:**

- **Primitive = TOUCH, not close.** Any tick reaching the VR band `[L1,L2]` counts. **Wick counts.** (The manual's "shadow doesn't count" applied to the *close-based* reading; Syafiq's operational rule is touch-based.)
- **Clock starts at the 1st CF birth**, NOT at VR birth. At the moment CF1 confirms, the VR is **fresh**.
- **First touch of the VR band after the 1st-CF clock starts → NON-FRESH (structured).** One-way latch.
- **Re-arm:** clock starts at the **1st CF** of the cycle and does **not** re-arm per later CF (per this session; per-CF re-arm was considered and set aside — freshness is a property of the cycle's first confirmation).
- **Edge case (a), born-structured — CONFIRMED:** if price is *already* inside the VR band at the moment CF1 fires, the very next in-band tick kills it → it is effectively born structured. (Option (b) leave-and-return was rejected.)

---

## 2. What this is NOT (leave untouched)

- **Existing VR logic is CORRECT and stays untouched:** the touch ladder (`t1/t2/t3`, `n_l1/mid/l2_touches`), the RT ladder (`rt1/rt2/rt3`, post-invalidation break-and-retest), and invalidation. Do NOT modify these.
- **The T-touch counter is NOT this.** It counts touches from **VR birth** (during the setup's own formation) — the wrong window. Fresh/Non-Fresh clocks from **CF1 birth**.
- **The RT ladder is NOT this.** RT fires only *after* the zone is invalidated (a different phase).
- **Legacy naming collision:** there is already a field `z.vr_fresh` in [fob_lifecycle.mqh](../../mt5/Include/fob_system/fob_lifecycle.mqh) that flips on **close-inside-band from VR birth** — this is NOT Syafiq's Fresh/Non-Fresh concept. On build, **rename/replace that stale field** so exactly one "fresh" exists in the codebase meaning the §1 definition.

---

## 3. Tracking mechanism (reuses existing primitives — a gated flag, no new detector)

1. **Two new fields on `FobZone`:** `vrf_armed` (bool — has the CF1 clock started?) and `vrf` (bool — still fresh?). Both start `false`.
2. **Arm at CF1 birth:** the EA already knows the moment CF1 fires — the `cfCount[E]` transition **0 → 1** for the setup TF (same signal `LifecycleBadge` reads in [fob_visual_draw.mqh](../../mt5/Include/fob_system/fob_visual_draw.mqh)). At that transition, look up the parent VR zone of that cycle (`seq`) and set `vrf_armed = true`, `vrf = true`.
3. **Kill on first touch after arming:** inside the existing per-tick loop `FobAccOnTick` ([fob_lifecycle.mqh:239-249](../../mt5/Include/fob_system/fob_lifecycle.mqh#L239-L249)) the band-touch test (`h1/h2/h3` = px in `[L1,L2]`) is *already computed*. Add one line: `if(vrf_armed && vrf && (h1||h2||h3)) vrf = false;`. Born-structured (a) falls out naturally — if price is already in-band at arm, the next tick kills it.

Existing T-ladder/RT logic is completely untouched; `vrf` is a parallel flag reading the same `px` test. The only wiring is linking "CF1 fired for cycle `seq`" → "arm the VR zone of cycle `seq`" (a `seq` lookup, not new state).

---

## 4. The test (how the edge settles — MT5 arbiter, real ticks)

The real A/B is **NOT** fresh-vs-RR. It is:

- **Baseline:** trail-everything (current v1.39.0: session 12-23 + H4 CF3 + trail 1.0R/1.5R).
- **Treatment:** fresh → **VR-touch TP** (exit at first VR touch); structured → **trail-and-ride** (current trail).

Measure on the arbiter, split by the flag:
- fresh-TP-at-touch cohort: $/trade + t vs the same trades under blind trail.
- structured-ride cohort: $/trade + t vs blind trail.
- **Offense confirmed if** fresh-touch-TP beats blind trail on fresh trades AND ride beats blind trail on structured trades. Report net (§ cost enters at G2, the arbiter).

Cost-free logic/excursion pre-screen is allowed as exploratory (label it) before the arbiter run.

---

## 5. Build priority (next session)

1. Add `vrf_armed`/`vrf` + rename legacy `vr_fresh` (§2/§3).
2. Wire the CF1-birth arm (`cfCount` 0→1 → parent VR lookup).
3. **Visual first (EMIT mode):** stamp `[FRESH]`/`[STRUCT]` on the VR L2 label (+ optional solid=fresh / dashed=structured border) so Syafiq eyeball-verifies detection before any measurement. EMIT stays byte-identical (chart nicety, never in the CSV).
4. Excursion pre-screen (exploratory) → then the §4 arbiter A/B.
