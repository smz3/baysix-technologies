# FOB Awareness / Conditioner Model — Phase-2 Feature Spec (v1 checkpoint)

**Date:** 2026-07-01 · **Idea:** FOB-001 · **Status:** v3 (awareness + Storyline Sequence + management — complete)

Source: FOB manual dissection (`research/papers/fob/FOB_breakout_system.dissect.md` + screenshots Img 4.1–4.12, 5.1–5.2, 6.1–6.6, 7.1–7.6, Special Note) + **Storyline Sequence** screenshots (`research/papers/fob/2.1.1_sequence.JPG` … `2.1.9_sequence`, Phase-2 video 2h38m).
This spec defines the **conditioner feature set** we screen against FOB own-zone excursion data (run_id 18, M15-M5 / M5-M1 cohorts). It is NOT a trade gate.

> **North Star (manual Special Note):** *"When you truly understand direction and storyline, VR and Barrier will be an easy walk. Sir B students make millions on riding Setup Conti."*
> Reading: **direction + storyline are the foundation**; VR/Barrier are downstream consequences, not independent signals. The edge (the money) is in **riding continuation** — so our modelling priority is (1) get direction/storyline awareness right, then (2) let VR/Barrier fall out of it, and (3) put the payoff weight on continuation-ride, not on entry-picking. Aligns with task 167 (payoff asymmetry = THE lever).

---

## Locked decisions

1. **Setup band = intraday, two cohorts:** M15-M5 (VR on M5) **and** M5-M1 (VR on M1). Screen **side-by-side as separate cohorts**, pool only if proven statistically similar. (M5 is the hinge: setup-TF for M5-band, VR-TF for M15-band.)
2. **Awareness = CONDITIONER, never a gate.** Full-stack alignment as a trade gate was REJECTED (result_id 18) and the −33.8pp full-stack finding (result_id 19) is the ghost of that framing. Awareness *informs*, never *vetoes*.
3. **Sizing is later.** Only after a state is proven to shift the edge does it scale size — never permission.
4. **Purpose is decided by LOCAL cross-TF geometry** (setup CF vs its one-higher opposing VR zone + that zone's break/hold state), NOT full-stack simultaneous alignment. Manual 5.2 confirms: each TF pairs with its *closest BO'd neighbour*, propagated up the chain.
5. **Direction derives bottom-up (Axis A); read either order (Axis B).** A TF's direction = the live cycle one TF below it. **Independence guard (task 204):** condition on each higher TF's **own-TF cycle state** (its PBO/VR/CF on its own bars), NOT the propagated-direction that is a mathematical function of the setup's own lower chain — else we re-manufacture the circular full-stack artifact.
6. **VR / cycle event vocabulary is LOCKED (no "confirmation" term):**
   - **Cycle birth = new PBO** — `seq` (cycle id) is set by PBO only, once per cycle. VR-break is **never** a second cycle-id source. (Manual 2.1.8 "break VR → new cycle" was a wording typo, corrected by Syafiq: a new VR *confirms* the cycle the PBO already started; PBO leads, VR-break lags.)
   - **VR detected** = first opposite break exactly one TF below the PBO → **births the VR zone**, sets which TF you trade, fires **once**/cycle. (This is the event previously muddled as "VR confirmation" — that term is retired.)
   - **VR break** = price clears the VR zone in the **continuation/PBO direction** (L2 / far-origin edge broken). This is the *already-coded* logic and arms **`[RT0]`** ([fob_visual.mqh:444-450](../../mt5/Include/fob_system/fob_visual.mqh#L444-L450)).
   - **RT (retest)** = retouch of the **broken** VR level. `[RT0]` = broke, not yet retested; `[RT1]+` = break-and-retest entries (`rt_count`, VR-row only). Feeds entry tasks 181/182.

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

## Layer 1b — Storyline Sequence (control-chain / cycle state)

Source: Sequence screenshots 2.1.1–2.1.9. **Core thesis:** every move is driven by **Trade Control** = *the one-TF-lower cycle controlling the TF above it* (2.1.2, "lower TF controls the bigger TF": M1‑M5‑M15‑M30‑H1‑H4‑D‑W). "Sequence" = **reading which lower TF is actually driving an HTF move** — the gears inside the HTF candle. This is the same bottom-up propagation as Layer 1 decision 5, made into an explicit *chain* + a set of named multi-TF patterns. Same independence guard applies: condition on **own-TF cycle state**, never the propagated direction.

| # | Img | Feature (measurable) | Source |
|---|-----|----------------------|--------|
| **S1** | 2.1.2 | **Control-chain** — walk down from a live HTF cycle to its driving child cycle (W→…→M1); the *lowest live VR* is who's moving price. State = depth + TF of the live controller. | DERIVE (cross-TF child link) |
| **S2** | 2.1.3 | **Sequence-on** — HTF candle trending (HTF BO, no pullback) **while** an LTF VR is present. The state that says "find the LTF that's driving." | DERIVE |
| **S3** | 2.1.3 | **"Price that doesn't come back"** — HTF BO trends with **no CMP retest**; waiting for the pullback fails → controlling TF descends a level. (= vr_fresh "straight-to-origin" at sequence scale.) Flags **setups NOT to trade**. | DERIVE / vr_fresh HAVE |
| **S4** | 2.1.1 | **CF-in-PBO / no-pullback path** — CF forms *inside* the PBO zone, price moves without a pullback. Structural sample. (Extends L2 "CF placement vs own zone".) | DERIVE (confirm_price ∈ PBO L1/L2) |
| **S5** | 2.1.5 | **"Setaman"** — ≥3 adjacent TFs BO **same direction concurrently** = time-frame-in-a-time-frame, concurrent confirmation → strong continuation. Count concurrent same-dir BOs across adjacent TFs in a window. | DERIVE |
| **S6** | 2.1.4 | **"Swing" direction / TP-reach** — TP target = the **controlling parent's barrier** (trade H4 → TP at Weekly; "H4 controls Daily"). Collective adjacent-TF BO ⇒ max TP distance. Feeds **L3 Barriers**. | DERIVE (parent-barrier lookup) |
| **S7** | 2.1.6 | **Counter / "False Breakout"** — opposite-dir LTF BO **while the higher-sequence TF is unchanged** = counter/fade, **partial-TP only, NOT a reversal**. ("Higher sequence TF still a buy.") | DERIVE (HTF cycle-dir unchanged + LTF opp VR) |
| **S8** | 2.1.7 | **Scalp / entry-risk class** — **VR-to-VR** entry = **high risk**; **CF** entry = **low risk**. Valid only while higher-seq TF not turning. Tags entry type for sweeps 165/171/181. | DERIVE / RE-EMIT |
| **S9** | 2.1.8 | **Market Cycle** — cycle = repetition of CMP **BO‑VR‑CF**; confirms the existing cycle model (`seq` = cycle id). | HAVE (seq) |
| **S10** | 2.1.9 | **Cycle-VR-Breakout rule** — on VR break, **do NOT enter the pullback** (VR = high risk); wait for the **new cycle's BO** (new PBO). Enter at NEW BO, not at BO-VR. Ties to `[RT0]` arming + L3 "overlap barrier invalid". | DERIVE (uses RT state) |

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

## Resolved in v3

- **Storyline Sequence (Phase 2, 2.1.1–2.1.9)** — folded into **Layer 1b** (control-chain + named multi-TF patterns S1–S10) and **locked decision 6** (VR/cycle event vocabulary). No sections pending.
- Sequence items route: S1–S3/S9 = Layer-1b state · S4 → Layer 2 (CF placement) · S5/S8/S10 = new conditioner states · S6 → Layer 3 (Barrier TP) · S7 = new counter/fade state.
