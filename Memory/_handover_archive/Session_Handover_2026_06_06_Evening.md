# Handover — June 6, 2026 Evening

## State
Pure discussion session — **no code written, nothing committed.** Two threads:

**(A) B2B parity — paused, not abandoned.** Diagnosed that the CSV-diff approach is poisoned at the source: the 13 `QUANT_ZONES_*.csv` in MT5 Common are a **junk drawer** — keyed by date only, so multiple symbols/runs blend (prices 1059→122006, BTC-like 70k values, mixed M5/M30/D1, 8 of 13 headerless). 373,973 CREATED rows; D1 dedups to 1,136 unique. **Don't delete them** (live folder, not our ground truth). Also surfaced: bridge bars (live JustMarkets `copy_rates`) are the WRONG parity source vs CSVs (which came from Dukascopy-in-Strategy-Tester). Syafiq's verdict: **B2B "can be worked around."**

**(B) New direction — Intraday ORB strategy, $50/1:3000.** Long quant discussion. Established: leverage is a red herring (margin trivial); $50 forces ~6–16% risk/trade (over-Kelly) → with a real edge, **smaller bets win** (doubling-to-$100 odds: $5→88%, $10→73%, $25→60%). $50 is irrelevant to *edge existence* (R-space unit-free), decisive for *survival*. I proposed **Opening-Range Breakout + regime gate** as the only intraday shape that clears the cost/sizing/edge walls. Agreed: **one DB, formal pipeline from step 0, no side-channel.**

## Next
1. **Answer Syafiq's two open questions** (he asked, then called handover): (a) *How* to fit an intraday strategy like ORB into the single research.db (built for foundational models HMM/CUSUM — step1_ideas→step5). Strategies are Downstream/Trading; need a clean way to gate+log them in the same DB. (b) *Why ORB* — justify the choice (vs VWAP-fade, momentum, time-of-day) on structural-edge + cost-survival grounds.
2. If ORB proceeds: register as idea in `step1_ideas`, pass Gate 0 (prior plausibility) + Gate 1 (falsifiable hypothesis: "ORB London-open E[R]>0 net of TCM-001, IS") per CLAUDE.md rule 13 — **before any code**.
3. Then build sequence: Python ORB → vectorized IS scan (cost-adj, kill cheap) → **tick/M1-resolved event backtest** (resolve intrabar stop-vs-target — our data edge) → OOS (break 2024-05-02 seal ONCE) → only if passes, port to MQH + MT5 ST.

## Blockers
Decision pending from Syafiq: schema for housing a *trading strategy* in research.db (same gates as models, or a strategy-specific path within the one DB). Nothing built until that + Gate 0/1 are settled.
