# Handover — June 26, 2026 Morning2

## State (FOB T-170 forward-excursion built + run COST-FREE; CF1 direction EDGELESS)
- **T-170 done (task 170 resolved).** Built `InpStudyMode` on [fob_trader.mq5](mt5/Experts/fob_system/fob_trader.mq5) (Route B, real ticks, XAUUSD_dukas): per CF, no orders — tracks MFE/MAE/terminal until the next CF (cap 48 H1 bars), ATR(14)/M30 unit. Emits `fob_excursion_*.csv`. FOB_VERSION → **1.10.1**, both EAs compile 0 err. Tester cfg [fob_excursion.ini](mt5/tester/fob_excursion.ini).
- **HARD LESSON (Syafiq, "for the last time"): discovery = COST-FREE.** First run measured MFE/MAE on exit-side Bid/Ask → spread baked in → manufactured a fake fade. Fixed to **mid price**; re-ran. New memory [[discovery_phase_cost_free]] (cost enters ONLY at G2). result_id 13 + strategy_log 74 = SPREAD-CONTAMINATED, superseded.
- **Cost-free verdict (result_id 14, supersedes 13; strategy_log 75 supersedes 74):** CF1 n=2284, continuation terminal **−0.053 ATR (median 0.000, t=−0.54) = ZERO directional edge**. MFE-first 36.4% ≈ MAE-first 38.7% (near-symmetric); MFE 2.60 ≈ MAE 2.78 ATR. The earlier −0.226 ATR "fade lean" was entirely spread. **CF1 direction alone is edgeless** — fade and continuation both dead. CSV: research/models/fob/excursion/ (v1101).
- Pushed sha 5a4bb4c. Task 173 (VR visual-verify) confirmed accurate by Syafiq → resolved.

## Next
1. **(task 174, P1) CF1 conditioning sweep on the cost-free CSV** — does ANY subset (session, ATR regime, VR depth, bars_to_next_cf, setup-TF) tip terminal off zero / create MFE>MAE asymmetry? Pure Python on research/models/fob/excursion/ (cost-free, mid). If none → CF direction is dead.
2. **(task 167, P1-ish) Payoff-asymmetry lever** — MFE mean 2.60 ATR is large despite zero net; test if a fat-tail/runner exit extracts $ even with edgeless direction (result_id 14).
3. **(task 171, P1) Retest entry** — reframe: now a CONDITIONING test (does pullback-into-PBO entry tip direction), not an execution fix; direction edge must exist first (do after 174).

## Blockers
None. Real-tick run needs JM terminal CLOSED + PowerShell Start-Process (bash-direct no-ops). Decision pending: if 174 finds no conditioning, CF direction is dead → pivot signal or payoff-only.
