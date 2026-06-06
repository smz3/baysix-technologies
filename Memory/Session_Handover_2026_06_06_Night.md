# Handover — June 6, 2026 Night

## State
**ORB-001 (Opening-Range Breakout, XAUUSD) passed the FULL ladder G0→G6 this session.** Registered in research.db as `category='execution'` (strategies share the model ladder; questions rephrased). Code in [research/models/orb/](research/models/orb/): orb_core, orb_backtest (tick intrabar engine), gate2_sanity, gate3_edge, gate5_cost, exit_study, gate6_oos. All committed+pushed (7aa11a8).

**Frozen config:** London 08:00 UTC anchor (fixed — Dukascopy has a 07–08 UTC daily gap, makes summer BST open unobservable → DST-immune), N=5 min opening range, **3R target / 1R stop**, flat 21:00 UTC, 2-pip JM Pro spread.

**Results:** Gate 3 raw E[R] +0.37R t11 (IS 2016→2024-05-02). Gate 5 net@2pip +0.21R t6.5 — spread modelled correctly as a **win-rate drag, not payoff deduction** (Syafiq's correction; B-book/swap-free → spread is the only cost). Gate 6 OOS (sealed 2024-05-02→2026-05-18, 522 days, one shot): +0.88R t10.2 — **edge HELD, not overfit.**

**Honest caveats:** OOS 281% of IS is INFLATED (verified benign) — gold doubled $1669→$3296 so fixed $0.20 spread drag fell 0.197R→0.065R, plus a strong trend regime flatters the 3R bet. **Forward ≈ IS +0.31R, regime-dependent.** New binding issue: at $3300 gold, min-lot (1oz) risk = range_w$ → median 6% of $50, p90 33% → **$50 survival is the wall now.**

## Next
1. **Regime gate** (Gate 4 attempt 2) — trend/session filter so ORB trades only when regime favors it (addresses regime-dependence). Use `pipeline.open_gate("ORB-001",4,attempt=2)`.
2. **%/ATR-based survival filter** — replace the $-fixed $5 max-range cap (broke at high gold prices); size/skip relative to price for $50.
3. **MQL5 port** into the Sigma EA for live XAUUSD.

## Blockers
None. ORB-001 is research-validated but NOT deploy-ready (needs items 1–3). Forward planning number is IS +0.31R, never the OOS +0.88R.
