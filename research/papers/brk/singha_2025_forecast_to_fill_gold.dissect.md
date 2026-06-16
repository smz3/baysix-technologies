# Dissection — Singha 2025, "Forecast-to-Fill: Benchmark-Neutral Alpha and Billion-Dollar Capacity in Gold Futures (2015-2025)"

- paper_id=10 · idea_id=BRK-001 · arXiv:2511.08571
- Dissected on Opus (separate-room sub-agent), 2026-06-16. Source = Docling `.md` (79,642 chars).

#### Paper
- Title: Forecast-to-Fill: Benchmark-Neutral Alpha and Billion-Dollar Capacity in Gold Futures (2015-2025)
- URL: https://arxiv.org/abs/2511.08571
- Source: research/papers/brk/singha_2025_forecast_to_fill_gold.md (Docling)
- Full text available: YES

#### Key Equations
Note: Docling rendered nearly all display equations as `<!-- formula-not-decoded -->`. Reconstructed from surrounding prose; symbols verified, LaTeX form not.

- [§3.2 / §6.1] confidence: full-text → EMA smooth of log-price: ỹ_t = EMA_λ(log P_t); slope Δỹ_t = ỹ_t − ỹ_{t-1}; standardized z_t = (Δỹ_t − µ_train)/σ_train. µ/σ computed on the 10yr train window only, frozen for OOS.
- [§3.3 / §6.2] confidence: full-text → trend confidence: clip z_t to [−3,3], affine-map to p_trend ∈ [0,1]; p_trend=0.5 = neutral, →1 strong up, →0 strong down.
- [§3.4 / §6.2] confidence: full-text → momentum term mom_t = 1 if P_t > P_{t-50} else 0 (K=50). Blended regime: p_bull(t) = ω·p_trend + (1−ω)·mom_t, with ω=0.6 (slope) / 0.4 (momentum), frozen from train. p_bear = 1 − p_bull.
- [§4.1 / §7.1] confidence: full-text → vol forecast: σ̂²_{t+1} = θ·σ̂²_t + (1−θ)·r_t² (EWMA / RiskMetrics, 20-day per §15.3). Target σ*_ann=15%, daily σ* = 0.15/√252. Vol-target weight w^(vol)_t = min(σ*/σ̂_{t+1}, W_max), W_max=2.0.
- [§4.3 / §7 / App.E] confidence: full-text → friction-adjusted Kelly growth: g(f) ≈ µf − ½σ²f² − nkf − γ(nf)^{3/2}. Sub x=√f → 2σ²x² + 3γn^{3/2}x − 2(µ−nk) = 0; take nonneg root x*, f*=x*². Reduces to classic f*=µ/σ² when γ=k=0,n=1. Tempered: f̃ = λ_Kelly·f*, λ_Kelly=0.40. Baseline 0.25× vol-budget when f* ≈ 0.
- [§4.5 / §10 / App.C] confidence: full-text → capacity curve: g(L) = µ_u·L − ½(σ_u·L)² − nkL − γ(nL)^{3/2}, L = participation (frac of daily ADV). Concave; zero-growth root = practical capacity.
- [§9.1] confidence: full-text → CAPM: r_strat_t = α_d + β·r_gold_t + ε_t; annualized α = 252·α_d. Newey-West HAC SEs.
- [§3.5 / §6.3] confidence: full-text → exits: hard stop = P_ent − 2·ATR14; trailing = peak − 1.5·ATR14; max age 30 trading days; de-risk (halve/close) if p_bear > 0.50. ATR14 = 14-day avg of TR. Entry (long-only) when p_bull ≥ 0.52 AND slope > 0.

#### Empirical Findings
- [Abstract / §8.1 / §16] confidence: full-text → OOS 2015–2025, 2,793 trading days (~11yr OOS; walk-forward: 10yr train → 6mo test, monthly-advanced). Net of k=0.7bps round-trip + sqrt-impact γ=0.02.
- [§8.1 / Table 1] confidence: full-text → Sharpe 2.88, Ann.Ret 2.62%, Ann.Vol 0.91% (realized, far below 15% cap), MaxDD 0.52%, Calmar 5.11, CAGR 2.65%. Bootstrap 95% CI Sharpe [2.49, 3.27] (1,000 block bootstraps, block=20d).
- [§8.1] confidence: full-text → Entries 1,282; non-zero-exposure days 1,132 (~40%); mean |w_t| = 0.0326; mean f* on train (non-zero) = 0.0029; share days p_bull≥0.52 = 59.5%; up-months 79.1%.
- [§8.3] confidence: full-text → Active-day (|w|>1e-3, n=1,132): hit rate 65.81%, avg gain +6.00bps, avg loss −4.01bps, payoff 1.49×, EV +2.58bps/active-day → annualizes to 2.63% (matches CAGR).
- [§8.2] confidence: full-text → returns highly right-skewed; ~58% of days ~zero (flat); high kurtosis by design. Distribution stats equation Docling-mangled → moments not reported numerically.
- [§9.1 / §9.3] confidence: full-text → α = 2.25%/yr (t=9.53, p<0.001), β = 0.03 (t=31.01), R²=0.001, IR=2.09. (§9 reports α at realized 0.91% vol.)
- [§10 / §16] confidence: full-text → scaled to 15% vol budget: implied return 43.2%/yr, CAPM-alpha ~43%/yr, IR-based alpha 37.1%/yr (abstract uses 37%). Two alpha conventions reconciled in §10 — same performance, CAPM-annualization vs IR×TE.
- [§10 / App.C] confidence: full-text → capacity params µ_u=1.0e−4, σ_u=5.7e−4, k=0.7bps, γ=0.02, n=1. Zero-growth point maps to $0.8–1.0bn USD on CME gold (ADV ~$50bn/day, |Δw_t|≈0.066), i.e. ~0.07% of daily volume.
- [Table 1] confidence: full-text → sub-period stability: 2015–2025 Sharpe 2.88 / MaxDD 0.52; 2019+ Sharpe 2.93 / DD 0.47; 2022+ Sharpe 2.91 / DD 0.47. Sharpe ~2.9 throughout.
- [Table 2] confidence: full-text → regime attribution: Bull (n=1,628) Ann.Ret 4.49%, Sharpe 3.82; Chop (n=49) ~0.02%, Sharpe 2.03; Bear (n=1,116) ~0.00%, Sharpe −0.02. Essentially ALL profit in self-identified bull regime; long-only.
- [Table 3] confidence: abstract (figures suspect) → cost stress (k scaled): 0.5× Sharpe 1.907; 1.0× 0.937; 1.5× −0.033; 2.0× −1.004. ⚠️ These contradict §8.1 baseline 2.88 at 1.0× — Table 3 appears to be a different (unscaled/non-vol-targeted?) series or Docling-mangled. §12.1 prose says "at 1.0× Sharpe remains well above 2.5." Treat exact figures as suspect; qualitative takeaway = 2.0× cost → Sharpe~0, linear decay.
- [Table 4] confidence: full-text → latency: T+0 Sharpe 2.88; T+1 2.28; T+2 2.24. Moderate proportional decay. Baseline trading fill stated as T+1 (minor internal labeling inconsistency vs Table 4).
- [§13.2] confidence: full-text → reversed signal Sharpe −2.95 (clean falsification); ablating either slope or momentum substantially cuts Sharpe (exact numbers not reported).
- [§13.3] confidence: full-text → SPA test p=0.000 over 64-config grid (EMA decay, momentum K, threshold), B=800 stationary block bootstraps, block=20, studentized stat. White Reality-Check also applied.
- [§13.4] confidence: full-text → multifactor check (spot gold, DXY, rate level/changes, Newey-West) preserves alpha, near-zero betas. Tails: worst month −0.20%, daily VaR95 0.04%, CVaR95 0.09%.

#### Limitations
- [§15.1] confidence: full-text → static friction model (k=0.7bps, γ=0.02 fixed); does not adapt to spread/volume/vol clustering. Stress only spans 0.5–2×.
- [§15.2] confidence: full-text → single-asset (gold only); cross-asset generalization untested.
- [§15.3] confidence: full-text → vol forecast is a plain 20-day EWMA; suboptimal vs HAR-RV/GARCH; can over-de-risk on short vol spikes.
- [§15.4] confidence: full-text → unmodeled execution frictions: micro-latency, partial fills, overnight funding ignored; assumes ≤1 round-trip/day (n≤1) — daily-roll level, not HFT.
- [§15.5] confidence: full-text → directionality verified but no formal causal test (Granger/permutation) yet; driver (behavioral inertia vs inventory flow) unconfirmed.
- [§15.6] confidence: full-text → no live/streaming validation; no drift detection; backtest-only.
- [Figures 1,2,3] confidence: unavailable → all three figures are figure-only images, not extractable from Docling (rolling hit-rate, rolling beta, $1M growth curve).
- [§2.1] confidence: full-text → uses daily settlement prices only (LBMA/COMEX); explicitly rejects intraday/tick. Holiday gaps carried forward (price, not return).

#### Context Fit
- **Paper asset:** CME Gold (GC) futures, continuous front-month, rolled 2 business days before first notice; close-to-close total returns incl. roll P&L. LBMA PM fix used only as benchmark regressor.
- **Paper frequency:** DAILY settlement (close-to-close). Explicitly avoids intraday/tick.
- **Target asset:** XAUUSD spot · tick (511M ticks 2016–2026, IS sealed 2024-05-02).
- **Frequency match:** NO — paper is daily-bar, target store is tick. Signal fully derivable from daily/M1 closes; tick is overkill for this signal (resample to daily).
- **Key deltas:**
  1. **Spot vs futures** — no roll P&L on XAUUSD spot; paper's returns include roll yield (possible persistent contango/backwardation component spot won't see).
  2. **Cost mismatch** — paper k=0.7bps RT is GC-futures liquidity; JM XAUUSD spot B-book spread ≈ 2–3bps RT, ~3–4× the paper's cost. Spread = win-rate drag ([[spread_winrate_drag]]). Since edge dies near 2× cost, **JM spread alone may sit at/near the death boundary.**
  3. **Market-impact/capacity term irrelevant at $50–$250 size** — billion-$ capacity is academic for us.
  4. **NOT a prior-session range breakout.** This is a trend/momentum regime follower (EMA slope + 50d momentum + vol-targeted Kelly), long-only, daily-rebalanced. No "breakout of prior session range" anywhere — it does not test BRK-001's hypothesis.
- **Direct applicability:** LOW (for BRK-001 as briefed).
- **Reason:** wrong signal family (trend-regime, not range-breakout), wrong frequency (daily, not tick/session), wrong cost regime (3–4× cheaper than JM spot), edge dies at 2× cost. Strong *methodology* template, not a breakout reference.
- **Parameters to re-validate (IF adapted as a trend sleeve, not breakout):** EMA λ; z-score train window vs IS≤2024-05-02; momentum K=50; activation threshold 0.52; ATR14 stops (2×/1.5×); 30-day max-age; 20d EWMA vol target 15%; λ_Kelly 0.40; and critically **re-derive net edge under JM spot (2–3bps RT), long-only, on XAUUSD daily bars** first.

#### Verdict
Needs full replication before trusting, and is mis-matched to BRK-001 as briefed. Headline numbers (Sharpe 2.88, MaxDD 0.52%, α 2.25%/yr, SPA p=0.000, reversal Sharpe −2.95) are methodologically clean — strict walk-forward, frozen params, ablation + reversal + SPA falsification, HAC SEs — a textbook validation template worth copying. But three gates: (1) it is a **trend/momentum regime follower, not a prior-session range breakout** — does not address BRK-001's hypothesis; (2) it trades **daily GC futures**, while we hold **XAUUSD spot tick** — signal resamples to daily and loses roll-P&L; (3) edge is **fragile to cost** — Sharpe collapses to ~0 at 2× the assumed 0.7bps, and JM spot is already ~3–4× that, so live net edge on our venue is the whole question and is left untested. Realized vol 0.91% vs the "implied 43%" headline means the eye-catching CAGR is a leverage-scaling artifact, not realized performance. Use: borrow the engineering scaffold (walk-forward freeze, friction-adjusted Kelly, ATR exits, ablation/SPA suite); do NOT treat its 43%/billion-$ claims as transferable to XAUUSD spot.
