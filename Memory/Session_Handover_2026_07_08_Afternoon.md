# Handover — July 8, 2026 Afternoon

## State
- **Trailing-stop exit BUILT + compiled clean (0 errors), default OFF** — v1.38.0 ([fob_baysix.mq5](mt5/Experts/fob_system/fob_baysix.mq5)). First RIGHT-tail / payoff-asymmetry lever (C).
  - `InpTrailStop` = ONE toggle: disables the fixed RR TP (`no_tp` on all 3 entry funcs) **and** ratchets SL toward profit. `InpTrailActivateR`=1.0, `InpTrailDistR`=1.5. Peak captured implicitly (SL never loosens). New helpers `RiskForPos`+`FobModifySL` ([fob_ledger.mqh](mt5/Include/fob_system/fob_ledger.mqh)); `TrailStops()` each tick in TRADE.
- **A/B RAN (H4/l1/k050, real ticks, IS 2016→2024):** trail beat no-trail on CF3 (+$1.001 vs +$0.814 /trade, result_id 39/40) — via right tail (maxR 11.24 vs 2.43), NOT win-rate.
- **BUT CF-decomposition KILLS the excitement:** trail on ALL CFs (CF0) = **−$0.516/trade, t=−3.27** (result_id 41). Per-CF: CF1 −0.618(t−3.07), CF2 −0.726(t−0.97), **CF3 +1.002 (t+0.91, ONLY positive bucket)**, CF4+ −1.422(t−3.47). CF3 = lone best-of-5, sub-1 t → likely CF-selection noise.

## Next
1. **(task 238, P1)** OOS DECIDER: run **CF3 + trail** (H4/l1/k050/activate1.0R/trail1.5R, Model=4) on the HELD-OUT window. If +$1/trade survives at real t → edge; if it collapses → CF-selection luck. This settles the trail.
2. **(task 255, P1)** Trail A/B is logged for IS (result_id 39/40/41); extend to the rr300 baseline config once task 252 settles RR, so trail shares one baseline with the other exit A/Bs.
3. **(task 252, P1)** STILL OPEN + still gates the B-verdict + the exit-A/B RR: run NONE baseline at rr300 (H4/l1/k050/cf0+cf2, real ticks) to de-confound D1 filter (result_id 37/38).

## Blockers
- **None hard.** Note: `InpTrailStop=true` must be set in the tester Inputs tab to fire; default off = byte-identical baseline.

## Why
- **Trail = the simplest right-tail test before structural E4 VR-touch TP** (tasks 240/248). The two prior exits (CfInval/OppPbo v1.36/1.37) are LEFT-tail loss-cutters — they can only shrink losers; trail UNCAPS winners. Syafiq's call: try the dumb trail first; if it can't beat fixed-RR, the fancy VR-touch TP probably won't either.
- **ONE toggle does both (TP off + trail on)** on purpose — the chosen config was "trail-only" (Syafiq picked: TP off / `InpTrailActivateR`=1.0 / `InpTrailDistR`=1.5 in risk units), so a single bool is the clean A/B unit. Additive + default off, same discipline as every prior exit; broker SL stays catastrophic backstop.
- **The mechanism is confirmed real** — maxR 11.24 vs 2.43 on identical entries proves uncapping the TP captures the fat tail. That part is not in doubt. What's in doubt is whether ANY population-level edge exists (see below).

## Ruled-Out
- **"Trail makes FOB profitable" — REJECTED as stated.** The CF0 (all-CF, honest) population is solidly negative (−$0.516/tr, t=−3.27, result_id 41). Trail does NOT rescue the strategy population-wide. Only CF3 nets positive and only at t=+0.91.
- **CF3 fat tail is NOT structurally unique** — CF1 (maxR 9.46) and CF2 (10.72) have equally big winners yet still net negative. CF3 wins because THIS window's CF3 losers were fewer/smaller, not because its tails are fatter → fragile, not a mechanism.

## Live-Threads
- **CF3-trail edge is unresolved (t=+0.91 per result_id 41 decomposition, IS-only, lone bucket of 5).** Weight of evidence = likely multiple-comparisons noise, but not yet falsified. OOS (task 238) is the clean decider — do NOT declare trail dead OR alive until it runs. If OOS collapses → strategy_log FALSIFIED for the trail (log_id 97 is currently PROPOSED). If it holds → first real FOB edge.
- **B-verdict (D1 direction filter) STILL carried** from Morning2 — task 252 (NONE-rr300 baseline) still un-run; still gates both the B-retire decision AND the RR that tasks 253/254/255 must share.
- **Exit A/B RR-coupling** — trail IS run was on rr200; the other pending exit A/Bs (CfInval 253 / OppPbo 254) + the trail rr300 extension must all share whatever RR task 252 settles, or they re-confound against each other.
