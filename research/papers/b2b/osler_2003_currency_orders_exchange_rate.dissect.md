# Dissection — Currency Orders and Exchange-Rate Dynamics: An Explanation for the Predictive Success of Technical Analysis

- **Authors:** Osler, C.L.
- **Year:** 2003
- **paper_id:** 28  ·  **idea:** B2B-001
- **Model:** opus  ·  **Dissected:** 2026-06-16 09:51:54
- **Source:** ssrn  ·  **DOI:** n/a

> Reconstructed from research.db (step2_papers + DISSECT log_agent) by backfill_dissect_md.py. The DB is the source of truth.

## Summary

Osler 2003 gives the microstructure mechanism behind decisive level breaks + reflective levels: SL/TP orders cluster at round numbers (uniform-null rejected, A-D 63-138 vs crit 8); TP cluster AT the figure (9.3pct vs 4.4pct SL, sig 1.1pct) making levels partial reflectors, while SL cluster JUST BEYOND (SL-buy 14.4pct above vs 7.4pct below 00, sig 0.029; +11.0 around 50, sig 0.002) so a cross triggers a same-direction stop cascade -> strong trend. Simulation: round-# bounce-freq +3.4pp and post-cross trend larger, all 20 cases sig. Underwrites B2B: real break = stop cascade (decisive), level = partial reflector (retest edge), consecutive same-direction breaks = stacked cascades (institutional imbalance). BUT evidence is FX dealer order-book (not observable for XAUUSD spot) and silent on net profitability; gold transfer rests on documented gold round-# PRICE clustering (note14, Ball 1985). Applicability MEDIUM. Next: Osler2001-style bounce-freq + post-break trend tests on XAUUSD ticks for Gate 0/1.

## Key Equations

[§3.A Eq.2]  confidence: full-text
Order-flow -> exchange-rate map: x(t+1)-x(t) = b*O(t), b>0. x=log exchange rate; O=net order flow (value buy-initiated minus sell-initiated). Linear approx to true F() with F(0)=0, F prime()>0.

[§3.A Eq.1]  confidence: full-text
Total order flow: O(t) = lambda*C(t) + m*v(F,t) + delta*(xbar - x(t)). C=conditional(SL/TP), m*v=fundamental random-walk shock, delta*(xbar-x)=arbitrage/mean-reversion to long-run xbar.

[§3.A]  confidence: full-text
Conditional orders: C(t+1) = d*[sb(t)-ts(t)] + (1-d)*[tb(t)-ss(t)], d=1 if rate rose t-1->t else 0. On an up-move only SL-buy and TP-sell trigger; on a down-move only TP-buy and SL-sell.

[§3.A]  confidence: full-text
Order value of type i: i(t)=sum over j in J(t) of Theta(i,j)*v(i,j). Theta(i,j)=fraction of executed type-i orders ending in 2-digit level j (e.g. Theta(sb,00)=0.0284); J(t)=set of 2-digit levels crossed t-1->t; v(i,j)~N(0,1).

[§3.A Eq.2 + 3.C]  confidence: full-text
Price built via preliminary x-prime(t+1), then X-prime=exp(x-prime), ROUND to 5 sig digits -> X(t+1), then x=ln(X). Rounding manufactures round-number clustering. Calibrated: lambda=m=0.5, delta=3.0, b=0.00015; 250k periods (~15min each, ~13yr); conditional share ~74-75pct.

## Empirical Findings

[§1.B]  confidence: full-text
Dataset: 9,667 stop-loss + take-profit conditional orders, single large FX dealing bank, 1 Sep 1999 - 11 Apr 2000. USDJPY 43pct, EURUSD 33pct, GBPUSD 24pct. Avg order 5.8M USD, median 3.0M; ~92 new orders/day; median life 0.4d, mean 3.4d; conditional ~5-10pct of deal flow.

[§2.C / Fig.1A / note13]  confidence: full-text
Execution rates strongly cluster at round numbers; uniform-null REJECTED far better than 0.01pct (Anderson-Darling 65.8 JPY / 137.6 GBP / 63.5 EUR vs critical 8.0). ~8.7pct of all orders end in 00.

[§2.D / Table 1]  confidence: full-text
PREDICTION 1 (reflect AT level): TP cluster at 00 stronger than SL -- 9.3pct TP vs 4.4pct SL execute exactly at 00; bootstrap marginal sig 1.1pct. On a hit of a round number ~2.8pct SL-buy vs 10.5pct TP-sell trigger -> reflecting TP flow dominates -> price reverses.

[§2.D / Table 1]  confidence: full-text
PREDICTION 2 (trend AFTER cross): SL-buy cluster JUST ABOVE 00 (14.4pct in 01-10 vs 7.4pct in 90-99; diff +7.0, sig 0.029) and just above 50 (40-49=17.3 vs 51-60=6.3; diff +11.0, sig 0.002). SL-sell mirror just below (90-99=10.0 vs 01-10=5.1; diff -4.9, sig 0.064). TP symmetric (all marg sig >0.35, NS). 3 of 4 SL asymmetries sig<5pct. At level ending 10 ~4.5pct SL-buy vs ~2.7pct TP-sell -> trend-intensifying SL flow dominates -> price trends.

[§3.D / Table 3 and 4]  confidence: full-text
SIMULATION (calibrated to actual book): round-# bounce-freq > arbitrary-# in all 20 cases, sig 0.01pct; avg bounce-freq lift +3.4pp (sim) vs +4.6pp actual FX (Osler2001). Post-cross trend: move at round# > arbitrary in all 20 cases, sig <=1pct; 2-period move ~0.0037pct larger at round numbers.

[note14]  confidence: full-text
Actual PRICE clustering at round numbers also documented in the London GOLD market (Ball, Torous and Tschoegl 1985) and corn/soybean futures (Stevenson and Bear 1970) -- the direct gold-relevant footnote (prices, not orders).

## Context Fit

**Paper asset:** USDJPY, GBPUSD, EURUSD spot FX (dealer conditional order book).
**Paper frequency:** Order-book cross-section + minute/15-min intraday (companions Osler 2000/2001).
**Target asset:** XAUUSD spot - tick/intraday - IS sealed 2024-05-02.
**Frequency match:** Partial (both high-frequency/intraday; paper adds private dealer-book micro data we LACK for gold).
**Key deltas:**
1. Paper observes ORDER placement (cause); for XAUUSD spot OTC there is no consolidated tape/order book, so we can only observe PRICE behavior (effect) - mechanism is inferential for gold.
2. FX SL/TP placement habits (a few pips beyond the figure) may differ in pip/tick magnitude for gold (USD/oz, ~10-100x larger nominal).
3. Round-number leg plausibly transfers - note14 documents gold round-# PRICE clustering - but B2B swing-structure zones are not always round numbers.
**Direct applicability:** MEDIUM.
**Reason:** Mechanism (TP reflect at level + SL stop-cascade just beyond = decisive break) is theoretically transferable and gold round-# clustering is documented, but the order-book proof is FX-only and not directly observable for our instrument.
**Parameters to re-validate:** (a) XAUUSD round-#/level bounce-freq lift vs arbitrary levels (Osler2001-style on ticks); (b) post-break trend continuation vs post-arbitrary-cross moves; (c) is the B2B double-break edge concentrated near psychological round numbers (00/50 in USD/oz); (d) retest-bounce win-rate at flipped levels net of spread.
SUPPORTS B2B on two fronts: (a) DECISIVE DOUBLE-BREAK -- asymmetric SL placement just beyond levels means a cross triggers a self-reinforcing same-direction stop cascade (buy-stops above resistance, sell-stops below support); a real break is decisive because stops STACK beyond it, and B2B two consecutive same-direction breaks = two cascades in series = institutional-imbalance signature. (b) RETEST/ZONE FORMATION -- TP clustering AT the level makes it a partial reflector; after a cascade clears the stops the level flips (resistance->support) as residual TP + fresh positioning concentrate there, giving a mechanistic basis for a tradeable retest bounce.

## Limitations

[§2 intro / p6]  confidence: full-text
Single dealing bank, 7.5-month window. Author concedes cannot PROVE representativeness of all FX conditional orders (plausibility argued from full client spectrum, no formal proof).

[§3 intro p22-23]  confidence: full-text
Simulations are ILLUSTRATIVE not realistic -- intentionally structured so the conditional-order effect EXCEEDS reality (cond share ~74pct); inference is only that a weaker version persists in real rates.

[§3.A / note18]  confidence: full-text
F() functional form unknown; linear x(t+1)-x(t)=b*O(t) is an admitted first-approximation; order book modeled as refreshed each period (no resting-order aging). 1-period = 15min equivalence asserted from author experience, explicitly NOT empirically justified.

[§5 Conclusion p32]  confidence: full-text
Paper is SILENT on market efficiency / risk-adjusted PROFITABILITY -- documents the dynamic, makes NO claim a trader can extract net-of-cost profit.

[note14]  confidence: full-text
London-gold / commodity clustering results concern PRICES not ORDERS and those markets differ structurally from FX -- author explicitly says not directly applicable. Transfer to non-round B2B structural zones is unproven by this paper.
