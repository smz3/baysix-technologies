# Handover — July 8, 2026 Evening2

## State
- **Session filter FULLY VALIDATED (IS arbiter + OOS), v1.39.0** [fob_baysix.mq5](mt5/Experts/fob_system/fob_baysix.mq5) `InpSessionFilter` (12–23). Both tasks 257 + 258 DONE.
- **Arbiter A/B (task 257):** EA ON run = 185 tr; OFF = 373. OFF-CSV entry-hr-12–23 subset = 187 reproduces result_id 47 to 3dp (+$1.68/tr, meanR +0.256, t+2.20, maxDD −10.4R). EA causal gate (`e.bar_time`) matches the fill-time screen within 2 tr. strategy_log 103.
- **OOS decider (task 258, 2024-07-01→2026-04-29, held-out):** ON = +$3.23/tr, +0.064R, t+0.36, maxDD −5.4R (result_id 50); OFF-all = −$1.29/tr, −0.157R, t−1.23 LOSER (result_id 51); CUT hr00-11 = −$6.15/tr, −0.395R, **t−2.30** WR30 (sig loser). strategy_log 104.
- **Verdict = DEFENSIVE filter, not alpha.** Off-hours are a significant loser across BOTH regimes; on-hours R-edge decayed ~75% OOS (IS +0.256 → OOS +0.065). Robust part = loss-avoidance, NOT on-hours offense.
- **CSV filenames do NOT encode `InpSessionFilter`** → same-window re-runs overwrite. No data lost this session (ON ⊂ OFF).

## Next
1. **(task 239, P1)** Stack D1-dir + W1-bias filter on the H4-CF3 **session(12–23)** trades — the on-hours need an *offense* edge; session alone is only a seatbelt. GUARDED (independence guard, [[fob_storyline_alignment_finding]]).
2. **(task 259, P2)** range_w as POSITION-SIZE on session trades — but frame as **DD-control sizing**, not alpha-compounding (OOS R-edge is ~flat; sizing amplifies a weak signal).
3. **(task 250 / reversal, P2)** the CUT-hours + CF4+ collapse hint at a fade/exhaustion edge — prong B, still untested.

## Blockers
- **None.** task 239 runs on the existing v1.39.0 EA (`InpDirFilterTf` D1/W1 + `InpSessionFilter=true`). Note the enum offers D1/W1/MN1 only — H4 not selectable (unchanged from prior).

## Why
- **Syafiq drove the full IS→OOS→full-span sweep himself on the MT5 arbiter** (real ticks, v1.39.0) rather than trusting the Python screen. All three windows reproduce the DB screen numbers exactly (373 IS / 83 OOS / 456 full), so the EA gate and the analysis layer agree.
- **Full-span (456 tr, 2016→2026) sharpens the filter case on $ + DD:** ON = +$1.97/tr, +$452.7 total, t+2.19, maxDD −10.4R vs OFF +$0.57/tr, +$262, −26R; CUT = −$0.84/tr, −$190, **t−2.10**, maxDD −51.7R (artifact [session_filter_is_oos_full.json](research/outputs/fob_session_fullspan/session_filter_is_oos_full.json) — NOT logged to step4_results; folding OOS back = double-count). Removing off-hours ~doubles total $ AND halves DD over the decade.
- **But the FULL t+2.19 is IS-weighted** (187 of 230 ON trades are IS; per [session_filter_is_oos_full.json](research/outputs/fob_session_fullspan/session_filter_is_oos_full.json)). The honest, transportable claim is **loss-avoidance** (off-hours reliably bad, t−2.10 across the decade), NOT +0.22R on-hours alpha (IS mean_R +0.256 result_id 47 → OOS +0.064 result_id 50).
- **[[er_denominator_illusion]] flipped sign IS→OOS:** on IS the off-hours netted positive-$ on negative-R (fat-SL winners) so filtering was gross-$ neutral; OOS the off-hours were catastrophic so filtering became gross-$ accretive (OOS OFF −$1.29/tr result_id 51 vs ON +$3.23/tr result_id 50). The DD/consistency benefit is the constant across both.

## Ruled-Out
- **Raw H4-cf3-trail WITHOUT the session gate = a LOSER OOS** (result_id 51, −$1.29/tr, t−1.23). FOB H4-cf3 only clears water WITH the filter.
- **Session filter as a source of positive alpha — REJECTED.** OOS ON standalone R-edge = +0.065 t+0.36 (indistinguishable from zero); it's a seatbelt, not an engine (result_id 50, strategy_log 104).

## Live-Threads
- **On-hours offense is the open problem.** Session gate + trail gives positive-$/tiny-DD but not a fundable per-trade edge OOS. task 239 (D1/W1 confluence) is the next attempt to add offense to the *surviving* on-hours cohort — untested on session-filtered trades.
- **Sizing lever is weaker than the IS handover implied.** Because OOS on-hours R is ~flat, task 259 sizing compounds noise, not alpha — reframe it as DD-control (size for smoothness), or defer until an offense edge lands.
- **Reversal/exhaustion reframe (prong B) still parked.** CUT-hours + CF4+ collapse (result_id 41) hint at a fade edge; we remain 100% continuation. Untouched.
- **`InpDirFilterTf` enum lacks H4** ([fob_sequence.mqh:84](mt5/Include/fob_system/fob_sequence.mqh#L84)) — the task-256 H4-align salvage can't be run without extending the enum. Uses D1 LAST-PBO dir (Syafiq-confirmed), not sequence/cycle dir; last-PBO-vs-sequence-dir untested.
