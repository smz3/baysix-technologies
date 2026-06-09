# Handover — June 7, 2026 Morning

## State
**ORB-001 $50 survival is RESOLVED.** Built [research/models/orb/equity_sim.py](research/models/orb/equity_sim.py) (dollar sim, Mode A min-lot + cap sweep) and [research/models/orb/equity_sim_honest.py](research/models/orb/equity_sim_honest.py) (honest-edge MC). Verdict: **$50 survives with 0% ruin even at the honest IS +0.31R edge** (de-rated from inflated OOS +0.88R by flipping excess winners→stops). Honest forward: median **$721** (~14×), p5 $319 / p95 $1025, **median DD 33%**. Inflated run gave $2474–2542. Costs ARE included (2-pip spread as win-rate drag; swap/commission $0); fills idealized, news/open-spread NOT modeled. All committed+pushed. Results logged: step4_results 39/40/41, step5 call_id 15/16/17. Tearsheets in [research/outputs/orb/](research/outputs/orb/).
**New infra:** `step6_backlog` table + [research/code/backlog.py](research/code/backlog.py) (query via `open_backlog` view). git push now auto-allowed; whole-tree `git add -A` adopted. Outputs reorganized into outputs/{orb,hmm,cusum}/.

## Syafiq's explicit concerns (carry forward)
- **Do NOT let real London-open spread be the gating/determining factor** — PARKED (backlog task 11), not a blocker.
- Believes the strategy has lots of **untested upside via variations** — wants these explored before deploy/conclusions. Trader intuition: M15-confirmation entry, retest-pullback entry, etc.
- 33% DD bothers him — wants it <10% if possible (but min-lot forces ≥5%/trade at $50, so sub-10% needs account >~$250 or a better win rate).

## Next (priority order, from `open_backlog`)
1. **ORB M15-confirmation entry** (backlog 8, P1) — M15 prints/confirms bias → trade M5 breakout. NOTE: plain N=15 range already tested & lost (0.24 vs 0.31R); this is a confirmation FILTER, different mechanism.
2. **ORB variation sweep** (backlog 9, P1) — retest-pullback (also sidesteps open-spread), range-width vol filter, trailing stop, partial TP.
3. **Walk-forward edge stability** (backlog 10, P1) — is +0.31R holding or decaying? (existential check).
4. Then: graduated cap for DD, Mode B compounding, ORB-002 NY, MQL5 port.

## Blockers
None. ORB-001 = research-validated + survival-proven, NOT yet deploy-optimized. Forward planning number is honest **median $721 / +0.31R / 33% DD**, never the inflated $2500/+0.88R.
