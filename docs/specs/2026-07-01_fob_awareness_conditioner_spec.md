# FOB Awareness / Conditioner Model — Phase-2 Feature Spec (v1 checkpoint)

**Date:** 2026-07-01 · **Idea:** FOB-001 · **Status:** v2 (entry/awareness + management layer) · 1 section PENDING (Storyline Sequence)

Source: FOB manual dissection (`research/papers/fob/FOB_breakout_system.dissect.md` + screenshots Img 4.1–4.12, 5.1–5.2).
This spec defines the **conditioner feature set** we screen against FOB own-zone excursion data (run_id 18, M15-M5 / M5-M1 cohorts). It is NOT a trade gate.

---

## Locked decisions

1. **Setup band = intraday, two cohorts:** M15-M5 (VR on M5) **and** M5-M1 (VR on M1). Screen **side-by-side as separate cohorts**, pool only if proven statistically similar. (M5 is the hinge: setup-TF for M5-band, VR-TF for M15-band.)
2. **Awareness = CONDITIONER, never a gate.** Full-stack alignment as a trade gate was REJECTED (result_id 18) and the −33.8pp full-stack finding (result_id 19) is the ghost of that framing. Awareness *informs*, never *vetoes*.
3. **Sizing is later.** Only after a state is proven to shift the edge does it scale size — never permission.
4. **Purpose is decided by LOCAL cross-TF geometry** (setup CF vs its one-higher opposing VR zone + that zone's break/hold state), NOT full-stack simultaneous alignment. Manual 5.2 confirms: each TF pairs with its *closest BO'd neighbour*, propagated up the chain.
5. **Direction derives bottom-up (Axis A); read either order (Axis B).** A TF's direction = the live cycle one TF below it. **Independence guard (task 204):** condition on each higher TF's **own-TF cycle state** (its PBO/VR/CF on its own bars), NOT the propagated-direction that is a mathematical function of the setup's own lower chain — else we re-manufacture the circular full-stack artifact.

Definitions (manual 5.1): **Bias = W1 only** (helicopter/main direction; sets priority; counter-Bias moves are "temporary"). **Direction = D1** (prioritized operative). Below D1 = execution.

---

## Layer 1 — Awareness cascade (context: state per higher TF)

Computed bottom-up, read top-down. For an M15 setup the awareness TFs above = H1, H4, D1, W1 (MN1 as bias-of-bias).

| Feature | Source |
|---|---|
| W1 **Bias**: direction · has-CF? · cycle phase · near-Weekly-barrier | dir/cf HAVE · phase/barrier RE-EMIT |
| D1 **Direction**: direction · sequence state · cycle condition · vr_fresh | DERIVE / RE-EMIT |
| H4, H1: direction · cycle phase · cf_idx | dir/cf HAVE · phase RE-EMIT |
| **Bias↔Direction agreement** (W1 vs D1): aligned=prioritize / counter=temporary | DERIVE |
| **Setup↔Bias**, **Setup↔Direction**: with or against W1 / D1 | DERIVE |

## Layer 2 — Purpose geometry (local: setup CF vs one-higher opposing VR zone) — the classifier

| Feature | Rule | Source |
|---|---|---|
| CF **shape** | structured (internal sub-swing) vs normal — prefer structured (Img 4.1) | RE-EMIT |
| CF **placement** vs own setup zone | in (safe) / above / before (Img 4.2) | DERIVE (confirm_price vs L1/L2) |
| CF **zone width** | vs ~20/30-pip SOP-repeat threshold (Img 4.3) | DERIVE |
| **CF ∈ higher-TF VR zone?** | cross-TF containment (Img 4.4–4.7) | DERIVE (cross-TF join) |
| **HTF VR state** | held/reject vs **strong-break-and-close** = best setup (Img 4.8–4.9) | DERIVE if bars, else RE-EMIT |
| **CF ordinal** | 1st vs 2nd+, sideways ⇒ take 2nd-in-VR-zone (Img 4.10–4.12) | cf_idx HAVE; regime RE-EMIT |
| **Regime** | trending vs sideways (gates CF-ordinal rule) | RE-EMIT |
| **Double-BO** | two adjacent TFs same dir = continuation (Img 4.12 text) | DERIVE |
| **vr_fresh** | fresh=layer-in / structured=ride | HAVE |

Manual note: CFs need **not** be contiguous — a fresh non-adjacent CF still counts in the cycle.

## Layer 3 — Trade management (Barriers = TP/Reversal · RTT = continuation)

**Barrier = a prior BO zone acting as S/R. NOT an entry (rejection risk); ONLY for Take Profit + reversal read** (Img 6.1). Two rules: same-TF barrier (D BO → D barrier, looks for own TF first) + one-TF-below barrier; bonus = overlap barrier.

| Feature | Rule | Source |
|---|---|---|
| **Barrier = prior BO zone** | TP target = next barrier; "monitor first once at barrier" (6.1, 7.1–7.2) | DERIVE (prior-zone lookup) |
| **Barrier break** | body close through required — **shadow ≠ break** (6.2, 6.3) | DERIVE (bar close vs bound) |
| **Overlap barrier** | already-broken barrier = INVALID for entry; wait new CMP/VR BO (6.4) | DERIVE |
| **Reversal cheat-code** | sideways-at-barrier + opposite BO that FAILS to break barrier S/R + same-TF VR ⇒ reversal. **M30 for GOLD** (6.5, 6.6) | RE-EMIT (regime + same-TF VR) |

**RTT — Ride The Trend (continuation management):** purpose = ride a continuation setup while it lasts.

| Feature | Rule | Source |
|---|---|---|
| **Conti = no opposite VR BO yet** | ride while no VR BO breaks; re-eval on VR BO (7.1, 7.2) | DERIVE |
| **VR Fresh** | price went straight to origin, **no close-back** into VR zone ⇒ **layer-in**; 1st entry TP in VR zone, add on 2nd CF (7.5) | HAVE (vr_fresh) |
| **VR Not-Fresh (structured)** | price **closed** back inside VR zone (shadow ≠ count) ⇒ **ride/hold** (7.6) | HAVE (vr_fresh) |
| **Conti-without-CF** | VR straight to BO zone, touch-and-go, VR without structure — distinct entry type; wait CF/HRCF if unsure (7.3) | RE-EMIT (CF-optional path) |
| **BO normal vs structured** | normal = conti; structured = reversal-potential (7.4; ties to CF-shape, Layer 2) | RE-EMIT |

Note: layering/stacking on 2nd CF is a **sizing** mechanic → deferred to the sizing phase (decision 3), captured here only as the trigger.
Special Note (manual): *"When you truly understand direction and storyline, VR and Barrier will be an easy walk. Sir B students make millions on riding Setup Conti."* → the payoff lever is **riding continuation**, consistent with our "payoff asymmetry = THE lever" (task 167).

---

## Build sequence (not started)

1. **Phase-2b outcome fields** (task 202): mfe_r/mae_r rule-free excursion + supersede logic. Prereq for any payoff screen.
2. **DERIVE conditioners** off run_id 18 (cheap, no re-emit) → screen on M15-M5 / M5-M1 cohorts.
3. **Selective RE-EMIT** only for RE-EMIT items the DERIVE screen shows are worth it.

Philosophy anchor (manual Special Note): *"these traders don't trade all the time"* — low trade count is a feature, not a bug. Confirms conditioner-not-gate.

---

## PENDING — to fold into v3 (feeding next)

- **Storyline Sequence (Phase 2 of manual)** — deep sequence/cycle chaining; enriches **Layer 1** (sequence state / cycle condition). Deserves its own pass (fresh session).
