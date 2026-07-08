# Handover — July 8, 2026 Afternoon2

## State
- **Trail-distance A/B settled: a WASH.** H4/CF3/l1/k050, trail dist 1.0 vs 1.5, real ticks IS 2016→2024:
  - Trail **1.0** = +$0.990/tr (t+1.86, WR 47.5%, maxR 7.45) — result_id 42
  - Trail **1.5** = +$1.001/tr (t+1.61, WR 34.0%, maxR 11.24) — result_id 39
  - Identical net; 1.0 = tighter (breakeven stop → higher WR, clipped tail), 1.5 = looser (fatter tail). **Distance is not a lever.**
- **H4-CF3 edge decomposed → REAL, not survivorship** (strategy_log log_id 98, resolves task 242). Loser size FLAT across CF depth (−0.91/−0.87/−0.86/−0.87R) ⇒ not a pre-cleaned survivor cohort. CF3 wins via higher WR (34% vs 30%) + **fatter winners (+1.91R)**. Hump-shaped: CF1→CF2→CF3 climbs, **CF4+ collapses** (−0.251, result_id 41 decomposition) = maturity/exhaustion mechanism.
- **H1 as setup TF = net-negative, unconditioned** (strategy_log log_id 99). H1 CF0 all = −$0.450/tr, t−3.87 (result_id 43); H1 CF3 = −$0.006/tr breakeven (result_id 44). Hump SURVIVES on H1 (CF3 best) but whole curve sits ~$0.5–1 lower. **CRUX: H1 winners only ~+1.05R vs H4-CF3 +1.91R — the fat-tail asymmetry is H4-specific, dies at lower TF (cost floor).**

## Next
1. **(task 256, P1)** FOB nested-TF inner-wave test: temporal-join the 2039 H1 trades (result_id 43) to run_19 H4 events → tag each by concurrent H4 CF-phase + H4 dir → partition H1 $/tr by H4-CF1/CF2/CF3/none & aligned-vs-against. Win = H1 goes positive INSIDE H4-CF1/CF2 while unconditioned stays neg. Post-hoc tag first (no EA build).
2. **(task 238, P1)** OOS DECIDER on H4-CF3-trail (frozen config, held-out window, Model=4). Now justified — edge is post-entry + hump-mechanistic, not best-of-5 noise. Shoot ONCE.
3. **(task 240/248, P1)** Structural VR-touch TP (E4) — the real payoff-asymmetry exit (trail was the dumb version + a wash). Amplifies the fat tail that IS the edge.

## Blockers
- **None hard.** Task 256 join needs the run_19 H4-event timeline (fob_payload.read_fob_payload, table 'events', event_tf='H4'); H1 trade CSVs are in the JM terminal Common/Files/FOB (fob_trades_*_H1_*_cf{0,2,3}_*.csv).

## Why
- **Focus order set with Syafiq (squeeze-every-edge map):** (1) prove H4-CF3 real on OOS → (2) SELECTION: take fewer/better CF3 trades via context filters (H4-wave/nesting, VR-fresh, location-at-wall, W1/D1 bias) — biggest lever since population is negative but CF3 subset positive → (3) structural exit (VR-touch TP) to let the tail run → (4) sizing (VR-fresh layering) to multiply proven edge. 3/4 only after 1/2.
- **FOB's edge = payoff asymmetry (fat right tail), not win-rate.** Every decision now judged by "does it protect/amplify the big winners." This is why trail-distance (a tail-reshuffler) was a wash and why the structural TP (task 240) is the real exit lever.
- **H4 is home base.** Not because lower TFs lack structure (the CF-hump survives to H1) but because only H4 legs run far enough in R to beat the gold spread. Established this session — don't re-explore M15/M5 as setup TFs.

## Ruled-Out
- **Trail DISTANCE tuning as a lever — REJECTED.** 1.0 ≈ 1.5 on $/tr (result_id 42 vs 39). Only reshuffles WR-vs-tail texture, doesn't change the edge.
- **H1 (and lower) as a STANDALONE setup TF — REJECTED** (strategy_log log_id 99, result_id 43/44). Winner asymmetry doesn't survive; symmetric ~1R payoff + cost = net loser. NOTE: this rejects *unconditioned* H1 only — the H4-phase-CONDITIONED version (task 256) is the live bet, NOT killed.
- **CF3 = survivorship illusion — REJECTED** (log_id 98). Post-entry edge, confirmed via flat loser-size across depth.

## Live-Threads
- **Task 256 is the open bet:** does H1 conditioned on H4-phase pull positive out of the −$0.45 noise? Honest prior = thin — H1 winners only ~1.05R give conditioning little raw material; it'd need a big WR lift to overcome symmetric payoffs. But untested and directly tests the FOB nesting thesis. Run it before spending OOS.
- **CF3-trail edge still IS-only** (result_id 39/42), strategy_log log_id 97 still PROPOSED. OOS (task 238) is the clean decider — don't declare alive/dead until it runs. Sequencing: task 256 first (may yield a stronger nested config worth OOS-ing instead of H4-CF3-alone).
- **B-verdict (D1 filter) + task 252 (NONE-rr300 baseline) STILL carried** from prior sessions — un-run, still gates the RR that exit A/Bs (253/254/255) must share. Not touched this session.
