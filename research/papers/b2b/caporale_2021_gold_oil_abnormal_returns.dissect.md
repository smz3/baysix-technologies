# Dissection — Gold and Oil Prices: Abnormal Returns, Momentum and Contrarian Effects

- **Authors:** Caporale, G.M.; Plastun, A.
- **Year:** 2021
- **paper_id:** 8  ·  **idea:** BRK-001
- **Model:** opus  ·  **Dissected:** 2026-06-16
- **Source:** ssrn (Financial Markets and Portfolio Management)  ·  **DOI:** n/a

> Dissected on Opus (separate-room sub-agent). Source = Docling `.md` (research/papers/b2b/caporale_2021_gold_oil_abnormal_returns.md). DB is source of truth (log_dissect_result).

## Summary

HYPOTHESIS-GENERATOR (leaning OFF-THESIS for the day-after edge). Decisive number: **Strategy 2 on Gold (the day-after contrarian trade) is NOT statistically distinguishable from random — t=1.36 (positive abnormal) / 0.73 (negative abnormal), null NOT rejected** [Table 4/5]. The "~70% continuation win-rate" in our backlog note maps to **Strategy 1 (same-day intraday continuation): Gold 86%/72% WR, t=5.61/8.17** — but that is a *same-day intraday momentum* trade exiting at the daily close, NOT a next-session prior-range breakout. The paper's day-*after* Gold pattern is contrarian (reversion), weak, and fails its own significance test. The genuinely tradeable next-day continuation in this paper is in **Oil, not Gold**.

## Key Equations

[§3 Eq.1] confidence: full-text
Return R_i = (Close_i − Open_i)/Open_i × 100%, open-to-close per day/hour. Open_i used instead of Close_{i-1} deliberately to avoid gap distortion.

[§3 Eq.2-3] confidence: full-text
Abnormal-day definition (dynamic k-sigma trigger): positive abnormal day when R_i > (R̄_n + k·σ_n); negative when R_i < (R̄_n − k·σ_n); **k=2** SD, R̄_n = mean daily return over period n. This is a RETURN-MAGNITUDE threshold, NOT a range/high-low breakout.

[§3 Eq.4-6] confidence: full-text
CAR: AR_t = R_t − E(R_t), E(R_t) = full-sample mean hourly return; CAR_i = Σ AR over hours i=1..24. Locates the intraday hour by which the anomaly is detectable.

[§3 Eq.7-8] confidence: full-text
Trade result = (P_close − P_open)/P_open (long) per deal; %successful = successful/total. Strategy vs random-trading t-test at 5%.

## Empirical Findings

[Abstract / §3] confidence: full-text
Data: daily + hourly Gold and Oil, MetaQuotes (MetaTrader) feed, GMT+3, 01.01.2009–31.03.2020. Abnormal days by k=2σ dynamic trigger.

[Table 2 / Table 3] confidence: full-text
Day-OF abnormal returns = momentum (continuation) for BOTH Gold and Oil. Detectable: Gold 19:00 (positive) / 17:00 (negative) GMT+3; continuation runs to the daily close.

[Table 2 / Table 3] confidence: full-text
Day-AFTER abnormal returns, Gold = CONTRARIAN ("No*" for momentum). Reversion most pronounced 06:00 (positive), lasts till end of day (negative). Oil day-after = momentum (peak 9:00/10:00). Headline split: **Gold reverts next day, Oil continues.**

[Table 4 — positive abnormal, Strategy 1 same-day] confidence: full-text
Gold: 59 trades, 51 wins = 86%, total +41.44%, +0.70%/trade, t=5.61, null REJECTED. Oil: 96 trades, 56%, +2.22%/trade, t=12.23 rejected.

[Table 5 — negative abnormal, Strategy 1 same-day] confidence: full-text
Gold: 74 trades, 53 wins = 72%, total +77.79%, +1.05%/trade, t=8.17, null REJECTED. Oil: 89 trades, 66%, +4.15%/trade, t=8.60 rejected.

[Table 4 — positive abnormal, Strategy 2 day-after] confidence: full-text
Gold: 59 trades, 35 wins = 59%, total +4.26%, +0.07%/trade, t=1.36, null NOT REJECTED (= random). Oil: 81 trades, 62%, +0.70%/trade, t=3.89 rejected.

[Table 5 — negative abnormal, Strategy 2 day-after] confidence: full-text
Gold: 74 trades, 43 wins = 58.1%, total +11.3%, +0.15%/trade, t=0.73, null NOT REJECTED (= random). Oil: 83 trades, 59%, +0.60%/trade, t=2.12 rejected.

[Table A.2 / A.3 — Gold hour-level t, day-of] confidence: full-text
Strongest same-day continuation hours: pos day 17:00 t=4.29, 20:00 t=4.14, 18:00 t=3.78; neg day 16:00 t=−5.44, 19:00 t=−4.05, 17:00 t=−3.44. Same-day momentum concentrated in US afternoon (GMT+3).

[Table B.1 / B.2 — Gold hour-level t, day-AFTER] confidence: full-text
Day-after Gold signal sparse + sign-mixed; most hours |t|<2; isolated sig hours (pos-day 06:00 t=−2.41, 14:00 t=−3.07; neg-day 06:00 t=−4.80, 10:00 t=+2.60). No coherent tradeable drift — consistent with failed Strategy-2 t-test. n≈59 (pos)/75 (neg).

[§3] confidence: full-text
Results are GROSS — no transaction costs. Justified by "typical Gold spread 0.02%." Same-day edge (+0.70%/+1.05%/trade) dwarfs that; the day-after Gold edge (+0.07%/+0.15% gross) is same order as costs → likely negative net.

## Context Fit

**Paper asset:** Gold (and Oil) — MetaQuotes/MT spot-CFD feed, GMT+3.
**Paper frequency:** Daily abnormal-day classification + hourly intraday returns/CAR. Trades held intraday (open→daily close), not multi-day.
**Target asset:** XAUUSD spot, tick (2016–2026), IS sealed 2024-05-02; BRK-001 = prior-session high/low breakout anchored to 17:00 ET CME settlement.
**Frequency match:** Partial. Same asset (gold spot, MT-style feed — high overlap with JM XAUUSD) + overlapping period (2016–2020 ⊂ 2009–2020). But mechanism differs: trigger = k=2σ return magnitude, not a range/high-low breakout; profitable trade is intraday same-day, not next-session.
**Key deltas:**
1. Trigger: k=2σ daily return ≠ prior-session high/low break. An abnormal-return day and a range-break day overlap but are not identical (a wide-range inside day can be 2σ without breaking the prior range).
2. Edge horizon: the strong, significant edge is same-day continuation to close (Strategy 1). BRK-001 trades the NEXT session — exactly the Gold leg the paper finds contrarian AND insignificant.
3. Timing clock: paper GMT+3 (MetaQuotes); negative-day anomaly fires 17:00 GMT+3, offset from BRK-001's 17:00 ET anchor — re-derive on our timezone.
4. Costs: gross; JM B-book spread (~$0.20–0.30 ≈ 0.01–0.015%) is a win-rate drag, relevant given sub-0.2%/trade day-after edge.
5. Sample: only ~59–74 Gold abnormal days over 11 years — thin; high overfit/regime risk on single asset.
**Direct applicability:** LOW for BRK-001's core thesis (next-session breakout continuation on gold).
**Reason:** The "70% continuation" figure belongs to a same-day exit-at-close trade, not the prior-session breakout BRK-001 trades; the next-day gold leg the thesis maps to fails its own significance test.
**Parameters to re-validate:** (a) abnormal-day def — test BOTH k=2σ return AND true prior-range break, same days? (b) does same-day continuation survive on our 2016–2024 IS ticks net of JM spread? (c) does next-session gold direction show continuation or reversion on our data (decisive BRK-001 test) (d) detectability timing under 17:00-ET anchor vs GMT+3 17:00/19:00 (e) win-rate after removing half-spread barrier shift.

## Limitations

[§3] confidence: full-text
No transaction costs — explicitly gross, justified only by "0.02% typical gold spread." Fatal for the small day-after Gold edge (+0.07–0.15%/trade ~ cost scale).

[Table 4 / Table 5] confidence: full-text
Gold day-after strategy fails its own significance test (t=1.36 and 0.73, null not rejected). Authors concede gold results "not so [significant]." The exploitable claim rests on Oil, not Gold.

[§3] confidence: full-text
Single feed/vendor (MetaQuotes); k=2 chosen "to generate a sufficient number of detected abnormal returns" — parameter picked for sample size, a mild data-snooping flag.

[Table 4/5] confidence: full-text
Small n (59–74 abnormal Gold days). Strategy-2 Gold totals over 11yr +4.26%/+11.3% — tiny; sensitive to few trades + regime (2009–2020 = QE gold bull + 2013 crash + COVID spike).

[§3 / Tables] confidence: full-text
Strategy 1 is forward-looking-adjacent: requires knowing the day is abnormal "when it becomes clear" then trading the residual move to close. Detectability timing (17:00/19:00) is in-sample; real-time fill must be re-tested — the idealized-fill trap that killed ORB-001.

[Figures A.1–D.3] confidence: unavailable
Average-return comparison plots are figure-only; not extractable — recorded as a gap, not vision-read.
