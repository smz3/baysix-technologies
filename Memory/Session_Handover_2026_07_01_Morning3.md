# Handover — July 1, 2026 Morning3

## State
- **Pure design/dissection session** — no code, no model runs, no new pipeline results.
- **FOB awareness/conditioner spec built + pushed** — [docs/specs/2026-07-01_fob_awareness_conditioner_spec.md](docs/specs/2026-07-01_fob_awareness_conditioner_spec.md), commit `d2cf1e8`, status **v2**.
- Spec captures the full FOB manual as a **measurable conditioner checklist**, 3 layers: L1 awareness cascade (Bias=W1 / Direction=D1), L2 purpose geometry (CF/VR local cross-TF), L3 management (Barriers=TP/reversal, RTT=continuation). Every feature tagged **HAVE / DERIVE / RE-EMIT**.
- **Storyline Sequence (Phase 2 manual) still PENDING** → spec v3; Syafiq uploads next session (task 205).
- run_id 18 (8yr FOB emit) is the data all screening runs against; research.db local-only (untracked, task 203 prior session).

## Next
1. **(task 205 P1)** Fold Storyline Sequence (Phase 2 manual, Syafiq uploading) into spec **v3** — enriches L1 sequence/cycle state. Then commit v3.
2. **(task 206 P1)** Build the **DERIVE-conditioner screen** on run_id 18, cohorts M15-M5 / M5-M1 **separate** — compute DERIVE-tagged features, measure reaction/continuation shift. Guard task-204 circularity.
3. **(task 202 P2)** ingest_fob phase-2b: mfe_r/mae_r rule-free excursion + supersede — prereq for any payoff-magnitude screen.

## Blockers
- None. Waiting on Syafiq's Storyline Sequence screenshots to start task 205.

## Why
- **Awareness = CONDITIONER, never a gate** — full-stack alignment gate was REJECTED (result_id 18); the −33.8pp full-stack finding (result_id 19) is that framing's ghost. Manual confirms (5.2): TFs pair with the *closest BO'd neighbour*, propagated up — awareness is **local/adjacent**, not full-stack simultaneous.
- **Setup band = M15-M5 + M5-M1, screened as SEPARATE cohorts** — M5 is the hinge; pooling immediately re-creates the multi-population attribution trap. Both have power (M5 182k, M15 62k cycles).
- **Purpose decided by local geometry** — setup CF vs its one-higher opposing VR zone + that zone's break/hold state (manual Img 4.4–4.9). This sidesteps the task-204 circularity: a higher-TF *propagated direction* partly contains the setup's own lower chain, so condition on each higher TF's **own-cycle state**, not propagated dir.
- **Raw excursion stored rule-free** (price/ATR), NOT baked to one entry rule — so entry sweeps (tasks 171/165/181) re-score cheaply instead of re-mining ticks. R = excursion ÷ risk-unit(entry,SL) is a re-projection; always carry $/trade + survival alongside R (denominator illusion).
- **North Star (manual Special Note):** direction+storyline are foundation; VR/Barrier fall out of them; **payoff weight goes on riding continuation** (matches task 167 = payoff asymmetry is THE lever).

## Ruled-Out
- **Option 1 (code auto-selects which TF to trade)** — deferred, not rejected: it's an ensemble of proven per-TF models + a selector, so it's strictly downstream of Option 2 (fixed intraday band). Premature to build now.
- **Awareness as a hard alignment gate / filter** — stays rejected (result_id 18). Enters as conditioner first, sizer only later once a state is proven to shift the edge.

## Live-Threads
- **task 204 (full_cont=0.06 interrogation) still open + now better understood** — the extreme full-stack reversal number is most likely the *circularity artifact* (higher-TF propagated direction contains the setup's own chain). The spec's independence guard is the intended fix; 204 should be closed/reframed once the DERIVE screen (task 206) is built with the guard in place.
- **RE-EMIT-tagged features not yet scoped** — CF-shape (structured vs normal), regime (trending/sideways), enriched htf_state cycle-phase, conti-without-CF path. Only build the emitter pass for the ones the DERIVE screen shows are worth it.
- **Layering/stacking (VR-fresh) parked to sizing phase** — captured in spec L3 as a trigger only; do not build sizing until a conditioner state is proven (decision 3).
