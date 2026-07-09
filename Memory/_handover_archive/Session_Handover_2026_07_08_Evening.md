# Handover — July 8, 2026 Evening

## State
- **Session filter BUILT into [fob_baysix.mq5](mt5/Experts/fob_system/fob_baysix.mq5) v1.39.0** — new `InpSessionFilter` (default off) + `InpSessionStartHr=12`/`InpSessionEndHr=23`. Gates a CF entry on the hour of `e.bar_time` (CF signal time, causal), wrap-aware. Compiled clean (0 err; 1 benign MQL5-Market version warning). Default off = baseline byte-identical. **NOT yet arbiter-tested.**
- **IS session screen (the find):** H4 CF3 + session(12–23) = **+$1.68/tr, Sharpe(daily) 2.55, maxDD −10.4R, WR 52.4%, per-year 7/9** (result_id 47) vs CF3 raw +$0.99 / Sharpe 0.73 / maxDD −26R (result_id 42). Wide-range +$2.73 (result_id 48); wide&pm stack +$3.47 (result_id 49). **All IS-only, thresholds in-sample-fit.**
- **Visual check chart:** [research/outputs/fob_session_filter_check.png](research/outputs/fob_session_filter_check.png) — window captures the fat-winner hours but is NOT surgically clean (hour 6 big-+ but n=10 excluded; hour 16 small-− included). Keep the coarse mechanism-block; do NOT tune to individual hours.
- **Nesting thesis FALSIFIED** (result_id 45, strategy_log 100): H1 inside a live H4-CF is WORSE than the −0.45 unconditioned, not better. Fat tail is H4-EXCLUSIVE.

## Next
1. **(task 257, P1)** Arbiter A/B — run MT5 tester H4/CF3/trail matched to result_id 42, `InpSessionFilter` on vs off, real ticks Model=4. Confirm result_id 47 (+$1.68 / Sharpe 2.55) reproduces on arbiter fills. Needs `.set` matched to result_id 42's trail params.
2. **(task 258, P1)** OOS decider — frozen H4 CF3 + session(12–23) on HELD-OUT window. The luck test; supersedes plain task 238.
3. **(task 259, P2)** range_w as POSITION-SIZE (not hard filter) — converts the smoother curve into compounded $ (the filter buys consistency, not gross-$ at fixed lot).

## Blockers
- **None hard.** Arbiter A/B (task 257) needs the EA `.set` matched to result_id 42 (InpTfPair=H4_H1, InpCfIdxFilter=3, trail a1r0/d1r0 — confirm exact trail params from the result_id 42 run) + `InpSessionFilter=true`, `InpSessionStartHr=12`, `InpSessionEndHr=23`.

## Why
- **Syafiq asked to find a real edge on HIS metrics (Sharpe/DD/Sortino/equity) from FOB detection logic — not run the next queued filter.** A feature scan on H4 CF3 tester trades surfaced TWO mechanistically-sound selectors: **SESSION** (London-PM/NY) + **STRUCTURAL SIZE** (range_w). Both monotonic, per-year 7/9, and **CF3-specific** — neither rescues cf2/cf0 (per-year 3–4/9), so they amplify the real CF3 mechanism rather than being a universal session/size overfit (result_id 47/48, strategy_log 102 PROPOSED).
- **Gate uses `e.bar_time`** (CF signal time) = the causal clock. The IS screen used fill-time `entry_ts`; minor divergence expected → the arbiter run is the real test.
- **R-vs-$ honesty ([[er_denominator_illusion]]):** risk-normalized, the session filter clearly wins; at fixed 0.01 lot the cut hours net ~flat because one wide-SL hour dominates the raw dollars. So the filter buys CONSISTENCY (smoother curve, shallower DD), not gross-$ at fixed lot — sizing (task 259) is the companion that compounds it.

## Ruled-Out
- **Nested-TF entry (H1 rides the live H4-CF fat tail) — FALSIFIED** (result_id 45, strategy_log 100). Inside a live H4-CF, H1's per-CF net all sit below the −0.45 unconditioned (late/exhaustion entry). Fat tail non-transportable to lower TF; **H4 stays home base (3rd independent confirmation).**
- **Unconditioned lower-TF as a standalone setup — still dead;** H1 is salvageable only to *breakeven* via H4-direction alignment (result_id 46, strategy_log 101) — the against-cohort bleed is removed but the result is not fundable. Directional context is a real lever (feeds task 239); CF-phase nesting is not.

## Live-Threads
- **`InpDirFilterTf` uses D1 LAST-PBO direction, NOT sequence/cycle direction** ([fob_sequence.mqh:84](mt5/Include/fob_system/fob_sequence.mqh#L84)). Syafiq confirmed last-breakout is what he wants. But the enum only offers D1/W1/MN1 — **H4 is not selectable**, so the task-256 H4-align salvage can't be run by the current EA without extending the enum. Open Q: does sequence-direction (live cycle one-TF-below = model-canonical) beat last-PBO? Untested.
- **Clean D1-filter test never run.** Prior D1-filter A/B (result_id 37/38) is CONFOUNDED (filtered=rr300 vs baseline=rr200) AND on the wrong CF bucket (cf0/cf2). task 252 (NONE-rr300 baseline) still un-run. The real test = D1-filter on H4-CF3-trail vs result_id 42 — deprioritised when Syafiq redirected to the broader edge-hunt.
- **range_w: sizing vs hard filter unresolved.** Hard filter halves n + cuts total-$; the wide&pm stack is highest Sharpe 3.05 / lowest DD but n=72 (9/yr) = over-selection (result_id 49). Lead with session-alone; range_w as sizing (task 259).
- **Reversal reframe (prong B, untested).** We are 100% continuation; the CF4+ collapse (result_id 41) + VR = first-opposite-break hint at a fade/exhaustion edge. Deferred until the session edge is OOS-confirmed.
