# Handover — July 6, 2026 Afternoon

## State
- **DISCUSS-only session — no code shipped, no results logged.** Two new tasks opened (240, 241).
- **Exit design reframed:** current FOB exit = fixed-RR target + L2+buffer stop only. Agreed this is an amnesiac exit bolted onto a storyline-aware entry — the asymmetry to fix.
- **Exit taxonomy E1–E4 defined** (combining FOB manual rules + structural-exit thinking) — see ## Why. Split into STOP-side (invalidation) and TARGET-side (structural TP).
- **Flexibility architecture agreed:** STATE (rigid facts) / CONTEXT (few named buckets) / POLICY (one clean rule-set per bucket). "Flexible" = the routing, not more rules.
- **run_19 payload explored** ([data/fob_payload/run_19/](../data/fob_payload/)) — exploratory, mid-price, NOT logged (trust rule). Findings in ## Live-Threads.
- Sorter + smart-exit DEEP design deferred to next session by Syafiq (task 241).

## Next
1. **(task 241, P1 — DISCUSS first)** Sorter + smart-exit design session: horizon buckets (scalp/intraday/swing) + at-wall LOCATION detector + exit taxonomy E1–E4. Open questions listed in the task + ## Live-Threads.
2. **(task 240, P1)** Structural TP: exit on first VR-touch (E4) — resolve the sequence-conditional WHICH-VR selector (leaf VR vs parent VR).
3. **(task 236, P1 — carried)** Structural stop E3: close on opposite PBO of the PARENT timeframe.

## Blockers
- **None hard.** Task 241 is discuss-only and needs Syafiq in the room; the two open design decisions (bucket count/mapping, which-VR selector) are his calls, not code blockers.

## Why
- **The exit is the missing floor, not the entry.** Entry logic (spec v0.2) is storyline-aware; exit collapses to a number. Fix = read the same live state the entry did.
- **Exit taxonomy (manual rules + our discussion), two families:**
  - STOP-side (trade is wrong): **E1** hard SL @ L2+buffer (exists, failsafe) · **E2** CF-invalidated = redundant, just hits E1 (fold in, not separate) · **E3** opposite-direction / opposite-PBO on PARENT TF (task 236, tricky = parent-TF tracking + flip confirmation).
  - TARGET-side (take the money): **E4** first VR-touch — price bounces at VR, so the first profit target is the VR *level*, NOT a fixed RR. Fixed-RR demotes to failsafe. Crux = "which VR" is sequence-conditional (leaf=scalp / parent=swing), but the machine already tracks the chain, so it's picking a node we already hold — reuse the entry leaf-walk engine.
- **Flexibility without a confused robot:** flexibility = COMPOSITION of simple parts, not COMPLICATION of one. STATE = deterministic facts (zero flex, total clarity — the built emitter piece). CONTEXT = small, named, finite bucket set (scalp/intraday/swing; at-wall/open) — the ONLY place flex lives. POLICY = one simple, independently-testable rule-set per bucket (incl. its own exit). At any tick: one (state × context) → one clean policy → never confused.
- **Exit maps into the buckets:** scalp → TP at nearest/leaf VR, tight stop; swing → hold through near VRs, TP at parent VR or bail on E3 parent-flip.
- **Build scoreboard:** sequence-reader (facts) = BUILT (emitter, all 9 TFs). Sorter (scalp/intraday/swing + LOCATION detector) = designed in spec v0.2, NOT built. Smart exit (E3/E4) = discussed, NOT built, NOT tested.

## Ruled-Out
- **Lower-TF for more sample = cost-dominated (do NOT pursue as a sample fix).** Exploratory run_19 screen: cost/R (spread ÷ band) climbs monotonically as TF drops — H4 band is large, M5 band collapses toward the fixed spread, so every faster-TF trade starts a large fraction of an R in the hole. Sample rises but economics detonate. Verdict is cost-geometry (pure arithmetic), robust regardless of entry mechanic. (Source: [data/fob_payload/run_19/](../data/fob_payload/), exploratory.)
- **The k0-immediate-l1 mid-barrier as a proxy for our entry = WRONG, discarded.** The pre-computed `realized_r` (fixed 2R/1R, enter-at-l1, k0) is NOT our L1-limit/k0.5 entry — it contradicted the tester's cf3 = +$304 (result_id 32) and was a bad proxy. Trust its cost axis only, never its P&L sign. (Self-caught; Syafiq flagged.)
- **Confluence framed as "D1-dir aligned with trade dir → better" = the REJECTED alignment gate in disguise.** Spec v0.2 (lines 16/46): trade direction = execution-TF live cycle, NOT HTF bias (worked ex was HTF-bearish, trade BUY). HTF's job = bias/location/horizon (swing-vs-scalp), never a directional filter. Prior kill = result_id 18. Correct reframe: HTF conditions storyline DEPTH (horizon), not side.

## Live-Threads
- **run_19 storyline findings (exploratory, un-logged, mid-price — source [data/fob_payload/run_19/](../data/fob_payload/)):**
  - **Continuation-hazard curve** = P(reach cf k+1 | reached cf k) per TF. It decays fast early then PLATEAUS; plateau height ≈ the TF's trendiness. Stabilises HIGH on D1/M5/H4, collapses on H1/M30 (structurally choppy — storylines die). This *quantifies* "swing has committed" and backs the spec's use of cf_idx as a maturity/strength read. Reframes the TF question from cost → trendiness (D1/M5/H4 are the TFs where storylines actually develop).
  - **`vr_fresh` is the top dormant flag** — populated + ~50/50 balanced on ~192k VR zones but NULL on every CF zone → orphaned from entries. It's a first-class STATE var in spec v0.2 (§1). Highest-value cost-free join: link vr_fresh onto CF events by cycle_id, measure how fresh-vs-structured conditions depth/continuation.
  - **`status` is dead data** — ~99.97% of cycles read `alive`; invalidation fires <70× in ~182k M5 cycles. Cycles terminate by new-PBO (seq++), not invalidation. Either wire real invalidation or drop the column.
  - **`vr_made_first_tf` is deterministic** (always the adjacent lower TF) — confirms the n-1 SOP rule / emitter correctness, but carries no signal.
- **Pre-build validation pass (proposed, not run):** before building the state machine, validate 3 spec assumptions cost-free on run_19 — (1) cf_idx = maturity via the plateau, (2) wire vr_fresh into the sequence, (3) test HTF-stack as a DEPTH/horizon conditioner (NOT a direction gate).
- **cf3 candidate `L1·cf3·k0.5·RR2.0` (result_id 32) still un-OOS'd** — carried from Morning2. Task 238 (OOS) deliberately NOT touched: Syafiq does not want to crack the hold-out until the config is confirmed best. Sorter/exit work happens first.
