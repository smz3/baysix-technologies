# Handover — July 1, 2026 Afternoon

## State
- **Discussion session — no code/results logged.** Output = a locked *design* for the VR-quality → CF-entry classifier, plus a new P1 task (208).
- **Spec unchanged on disk** — [docs/specs/2026-07-01_fob_awareness_conditioner_spec.md](docs/specs/2026-07-01_fob_awareness_conditioner_spec.md) still v3; the classifier design below is NOT yet written into it.
- **Grounded the VR logic in real code** — VR detection lives in [fob_sequence.mqh:97-134](mt5/Include/fob_system/fob_sequence.mqh#L97-L134); the 5 coded conditions confirmed (live PBO · one-TF-below · opposite-dir · after-PBO · first/once). Detection + T/RT touches already solid (Syafiq confirmed).
- **Gap identified:** VR *quality/state* flags are NOT coded — placement (3.4), clean/messy (3.7), CF break-state A/B/C (4.4-4.9).

## Next
1. **(task 208 P1)** Build the DERIVE screen off run_id 18: **placement** (in-zone binary + retracement-frac low/mid) × **clean/messy** co-rider × **CF break-state A/B/C**. Report cont-lift + **net $/oz per bucket**. Reuse `setup_direction_screen.py` pattern.
2. **Hand Syafiq a 15-row VR audit sample** (time · TF · vr_level · zone · computed frac + placement tag) so he sets `T_LOW`/`T_MID` thresholds by eye vs MT5 — verification is visual on chart, never a Python number.
3. **(task 207 P1)** vr_fresh screen still open — fold into the same 208 pass (both are cheap DERIVE co-variates).

## Blockers
- None.

## Why
- **VR must be fully conditioned BEFORE CF** (Syafiq's insight, confirmed): every CF condition is defined *relative to* the VR gate, so placement/state come first.
- **Placement (3.4) = the load-bearing quality flag** — mechanical, non-circular, cheap: `in_zone` = `vr_level` inside PBO 4-pointer (binary, no tuning); else `frac=(vr_level-origin)/(pbo_zone_edge-origin)` → low/mid. Anchors (PBO zone · vr_level · leg-extreme) all already in run_id 18 data → DERIVE, no re-emit.
- **CF break-state A/B/C (4.4-4.9) is the real "context = drastic" lever** — the *same* CF is a trap (A, VR not broken), a best-entry (B, strong-break-and-close), or an opposite reversal (C, rejected). Our dead baseline (result_id 22) likely pools all three → cancels to ~zero. Passes independence guard because "did the setup-TF body-close through its own VR zone" is a raw bar event, NOT the circular full-stack propagation that made the −33.8pp ghost (result_id 19).
- **Verification loop = the emitter DRAWS each flag (colour/label) → Syafiq eyeballs on MT5** ([[feedback_verify_against_live_ea]]). His corrections set the thresholds. This was his explicit blocker ("I can't verify what you're doing").

## Ruled-Out
- **Clean/messy (3.7) as a headline lever — DEMOTED to cheap co-rider.** Its manual purpose is gating VR-*riding* ("messy → wait for low-risk CF"), but we enter on CF anyway and VR-riding is parked (tasks 181/182). Cheap to compute (swing/T-touch density in PBO→VR window) so track it, but don't expect the edge there.
- **RT / VR-break-and-retest entry — Syafiq queued for LATER** ("VR is a trade on its own, needs dedicated handling"). Tasks 181/182 stay P1-open but deprioritized behind CF. Note S10 (cycle-VR-BO: don't enter the pullback, wait new BO) *contradicts* RT-entry — reconcile when RT is picked up.

## Live-Threads
- **CF entry mechanics (#1) vs context awareness (#2) ranking** — agreed: context/selection (VR-break-state) ≈ payoff-asymmetry (task 167) > entry mechanics (structured/placement/20-pip/limit). The one mechanic that matters most = **SL-per-TF (task 185)** — wrong-TF stop kills you before you can ride. Not yet actioned.
- **Baseline dead at cost in BOTH cohorts** (result_id 22: M5-M1 −$0.19/oz, M15-M5 −$0.25/oz gross) — every 208 bucket judged by whether it flips this net-positive, not by pp shift.
- **20-pip rule (Img 4.3) + "price that doesn't come back" (2.1.4)** = the same *descend-a-TF* entry-availability mechanic (wide CF zone OR no HTF pullback → drop to controlling LTF's fresh BO-VR-CF). Captured, not yet a task — it's fill-availability, not a selection edge.
- **`mfe_r`/`mae_r` NULL on run_id 18** (task 202) — blocks any payoff-magnitude bucket; fix before payoff screens.
