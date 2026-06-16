# Dissection — The Illusion of Breakouts: Empirical Evidence of Institutional Liquidity Capture in Major Currency Pairs

- **Authors:** Costa, R.
- **Year:** 2026
- **paper_id:** 30  ·  **idea:** B2B-001
- **Model:** opus  ·  **Dissected:** 2026-06-16 10:03:53
- **Source:** ssrn  ·  **DOI:** n/a

> Reconstructed from research.db (step2_papers + DISSECT log_agent) by backfill_dissect_md.py. The DB is the source of truth.

## Summary

COMPATIBLE-WITH (and partially SUPPORTIVE of) the B2B retest edge on gold under a continuation-retest reading; CHALLENGES a fade-the-level reading. Gold 66.78% True-Breakout vs FX ~77% False-Breakout is a genuine directional-asymmetry signal: at 20D structural extremes on D1, gold follows through while FX reverts. Confirmation is measured at the SAME daily close, not at a retest, so the paper does NOT directly test B2B retest entry -- it only says gold post-break drift is directional. Reshapes B2B-001 Gate 0/1: frame the gold thesis as continuation-after-pullback (enter retest in break direction), NOT mean-reversion fade. Rigor weak -> treat as HYPOTHESIS GENERATOR, replicate before trusting. Decisive next test on our ticks: after a confirmed close-outside-20D-box on XAUUSD, measure (1) does price retest the broken boundary, (2) retest-depth distribution, (3) continuation win-rate from retest vs fade win-rate.

## Key Equations

[§2 Eq.1] confidence: full-text
20-Day Institutional Range (D1): upper = max(High over 20 preceding sessions), lower = min(Low over 20 preceding sessions). Quote inside box = consolidation regime.

[§2] confidence: full-text
Structural Aggression = intraday High or Low pierces the 20D box limit (the breakout trigger event).

[§2] confidence: full-text
False Breakout (Liquidity Sweep) = price exceeds the limit BUT daily CLOSE returns back INSIDE the box. True Breakout (Directional Flow) = price pierces the limit AND daily CLOSE consolidates OUTSIDE the boundary.

[§2] confidence: full-text
Sweep Depth = distance (pips) from the boundary line to the extreme wick of the false aggression.

[§5 Eq.] confidence: full-text
Break-even Win Rate: W_req = Risk / (Risk + Return). Stop = 1.5xATR, TP band 1.5-2.0xATR. Symmetric R1.5/Ret1.5 -> W_req=50%; asymmetric R1.5/Ret2.0 -> W_req~42.85%. NOTE: no t-stat, p-value, CI, or null-baseline appears anywhere in the paper.

## Empirical Findings

[Table 1] confidence: full-text
Decadal Quant Matrix, Yahoo Finance D1, 2016-01-01 to 2026-04-16. EURUSD n=624 False 77.08% / True 22.92%, sweep 29.9p, ampl 341.6p, consol 76.43%. GBPJPY n=639 False 78.56% / True 21.44%, sweep 65.4p. USDCAD n=664 False 76.81% / True 23.19%, sweep 29.1p. USDJPY n=642 False 75.08% / True 24.92%, sweep 45.9p. AUDUSD n=680 False 80.29% / True 19.71% (most mean-reverting), sweep 25.9p. GOLD n=599 False 33.22% / True 66.78% (INVERTED), sweep 80.5p, ampl 1407.6p, consol 76.52%. Table note: 3,808 total events.

[§3] confidence: full-text
>3,800 breakout attempts total; all assets spend ~74-77% of the decade in consolidation.

[§6] confidence: full-text
Gold True-Breakout 66.78% framed as macro directional flow; gold sweep depth 80.5p is the largest in the sample.

[§7 Appendix] confidence: full-text
Certificate screenshot CONTRADICTS Table 1: claims 15,656 daily sessions processed and per-asset op-counts ~58-65/yr; a second certificate block lists a DIFFERENT checksum/UUID/date than the prose certificate -> internal inconsistency.

## Context Fit

**Paper asset:** 5 FX pairs (EURUSD, GBPJPY, USDCAD, USDJPY, AUDUSD) + GOLD (GC=F futures proxy via Yahoo Finance)
**Paper frequency:** Daily (D1) -- daily close is the sole judge of confirmation
**Target asset:** XAUUSD spot · tick · IS 2016->2024-05-02 sealed, OOS 2024-05-02->2026
**Frequency match:** No
**Key deltas:**
1. Confirmation is measured at the SAME daily candle CLOSE (close outside box), NOT after a retest and NOT at a horizon -- so gold 66.78% means same-day directional follow-through, it says nothing about what price does on a RETEST of the broken level.
2. Gold instrument is GC=F futures via Yahoo, not spot XAUUSD -> basis + data-quality + contract-roll differences.
3. Single D1 timeframe vs our intraday/tick B2B; gold sweep depth 80.5p (largest) implies retests can run deep before continuation.
4. No transaction costs, no OOS split, no statistical significance test in the paper.
**Direct applicability:** MEDIUM
**Reason:** Correct direction-of-asymmetry signal for gold (follow-through, not fade) but wrong frequency and it never measures the retest entry B2B actually trades.
**Parameters to re-validate:** (a) does a confirmed close-outside the 20D box on XAUUSD produce a tradeable retest (b) retest-depth distribution (c) continuation win-rate from retest vs fade win-rate (d) spot-vs-GC=F basis on the asymmetry

## Limitations

[§2] confidence: full-text
Confirmation = a single D1 close relative to the box; ignores intraday path, gaps, and everything AFTER the close (no horizon/retest analysis) -> silent on reversion timing and retest tradeability.

[§7 Appendix] confidence: full-text
Data = Yahoo Finance daily, gold via GC=F futures (NOT spot XAUUSD); data quality / adjustment / roll handling unknown.

[Table 1 / §7] confidence: full-text
Data-volume inconsistency: 3,808 events (Table note) vs 15,656 sessions (certificate) + two mismatched certificate blocks (different UUID / checksum / date) -> the reproducibility/authenticity claim is undercut.

[§3] confidence: full-text
NO statistical test reported anywhere -- no t-stat, p-value, CI, or null/random baseline; claims are raw percentages on a single decade, significance never established.

[§5] confidence: full-text
EV section is generic R:R algebra (W_req=Risk/(Risk+Return)), not derived from the empirical sweep distribution; ATR 1.5x stop is asserted, not fitted. Single 20-day lookback, single D1 TF, no parameter-sensitivity, non-peer-reviewed SSRN, author self-described non-credentialed.
