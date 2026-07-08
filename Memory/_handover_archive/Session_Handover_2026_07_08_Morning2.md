# Handover — July 8, 2026 Morning2

## State
- **Two NEW exit mechanics built + compiled clean (0 errors), both default OFF** ([fob_baysix.mq5](mt5/Experts/fob_system/fob_baysix.mq5)):
  - **v1.36.0 `InpExitOnCfInval`** (task 236 slice) — close-only CF-invalidation exit: close a position when a CLOSED bar on its CF's own TF (`event_tf`) closes beyond the CF zone far edge L2 (long: close<L2, short: close>L2). Same rule the accumulator invalidates a zone with. Fires at L2, earlier than the L2±k·band broker-SL touch → cuts losses shorter.
  - **v1.37.0 `InpExitOnOppPbo`** (task 236 proper) — close positions whose dir FIGHTS a NEW PBO on the setup TF (opposite cycle anchored); same-dir hedges kept.
- Both are **independent toggles**, share `FobMarketClose` helper ([fob_ledger.mqh](mt5/Include/fob_system/fob_ledger.mqh)); broker SL/TP stay as gap backstop. `L2` now stashed per-position in both trade-book (market) + pending-book (CF_L1_LIMIT); mapped by `POSITION_IDENTIFIER` via `InvalCtxForPos`.
- **NEITHER is A/B-tested yet** — no tester result exists for either. Default off = baseline byte-identical.

## Next
1. **(task 252, P1)** Still open + still gates the B-verdict: run **NONE baseline at rr300** (H4/CF_L1_LIMIT/k0.50/RR3.0/cf0+cf2, Model=4 real ticks) to de-confound the D1 direction filter (result_id 37/38).
2. **(task 253, P1)** A/B **`InpExitOnCfInval`** on vs off, matched config, real ticks. Metrics: net $/trade, WR, avg loss, left tail.
3. **(task 254, P1)** A/B **`InpExitOnOppPbo`** on vs off (and combined with CfInval), real ticks, same config.

## Blockers
- **None hard.** Note: both exit toggles must be set `=true` in the tester Inputs tab to fire — Syafiq's live-visual SELL "didn't close on opposite PBO" was two things: (a) toggle default-off, and (b) CfInval ≠ opposite-PBO (different triggers). Resolved by adding OppPbo (v1.37.0).

## Why
- **Exit reframed from "arbitrary buffered price" → "structural failure event."** Current SL = L2 + k·band (touch); k·band scales with CF zone size → the stop is decoupled from the real failure BOTH ways: fires early on a wick to L2+buffer with no close, AND holds a dead CF when price closes past L2 but hasn't wicked to L2+buffer. CF-invalidation (close beyond L2, wick≠count) is the exact structural edge, already computed by the accumulator ([fob_lifecycle.mqh:91](mt5/Include/fob_system/fob_lifecycle.mqh#L91)) — we bind to an event the oracle already emits, no new detection, no drift.
- **Kept ADDITIVE + toggled (default off), not a replacement** — same discipline as the v1.35.0 direction filter: broker SL/TP stay as catastrophic/gap backstop, CF-inval fires earlier so it "only ever cuts a loss shorter" (Syafiq's "minimize losses further"). Clean A/B on the arbiter; rips out if null.
- **Two separate toggles on purpose** — CfInval = fine (this trade's own CF zone failed); OppPbo = coarse (a whole new opposite cycle anchored on the setup TF). Different triggers, different tails; Syafiq wanted both after seeing a SELL survive an opposite PBO.
- **This is C-adjacent (exit lever)** — the handover-flagged "real untested lever." These are LEFT-tail (loss-control) cutters; the RIGHT-tail prize (E4 VR-touch TP / let winners run, tasks 240/248) is still separate + untested.
- Lineage: strategy_log **log_id 95** (CfInval CREATED/PROPOSED), **log_id 96** (OppPbo CREATED/PROPOSED).

## Ruled-Out
- **Parent-TF opposite-PBO exit — chosen AGAINST for now** (discussed, not built). Parent (D1 for H4) is slow: by the time it confirms, price often already hit SL or ran to TP; and a single opposite break on the parent may just be the parent's own VR (healthy retrace), not a regime death. Went with setup-TF opposite PBO (what Syafiq was actually watching). Parent variant = one-line extension later if setup-TF shows life.
- **Counterfactual-on-past-trades pre-screen — skipped by Syafiq's call** ("no need to test from past trades, just code it"). Went straight to the EA toggle + tester A/B.

## Live-Threads
- **B-verdict (D1 direction filter) still unresolved** — carried from Morning1: weight of evidence (clean mid null + confounded-negative tester pass) points to H4-CF-at-cost dead regardless of D1 alignment, but task 252 (NONE-rr300 baseline) is the clean de-confound and hasn't run. If confirmed null → `strategy_log.log_change` FALSIFIED for the D1 filter, retire B, pivot to C.
- **Exit A/B design coupling** — tasks 253/254 should reuse whatever config task 252 settles (RR especially), so all three share one baseline. Don't run the exit A/Bs on a different RR than the de-confound or we re-confound.
- **Both exits are unproven** — "it will definitely help" is Syafiq's prior, not a result. The tester is the arbiter; possible failure mode = OppPbo/CfInval chops out trades that later resume (a parent/own VR mislabeled as death). A/B decides.
