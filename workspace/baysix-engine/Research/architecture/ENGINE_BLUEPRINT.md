# Sigma Engine Blueprint — Authoritative

**Date:** 2026-05-20
**Owner:** Syafiq M. Zin — Quant Researcher (Deployable)
**Status:** AUTHORITATIVE — supersedes `engine-design-v1.md` and reconciles the Co-Work `engine-architecture/` docs
**Target:** Balyasny Asset Management + Millennium Management (Tier C) + Malaysia buyside (Kenanga, Affin Hwang, KL systematic shops)

---

## 0. Why this document exists

There were two competing engine designs:

1. **`engine-design-v1.md`** (May 13) — an asset-agnostic, cross-sectional IC tearsheet lab (US + ASEAN ETFs, 5 equity signals, 6 layers). Strong on statistical rigor and governance; generic and disconnected from Syafiq's real edge.
2. **Co-Work `engine-architecture/` docs** (May 20) — the Sigma Gold System: Data → Context (Kalman/PCA) → Regime (HMM/BOCPD) → Signal/Execution (SAMTC + MT5/Darwinex). Architecturally world-class and grounded in Syafiq's real edge; lighter on statistical hygiene and governance, and welded to one instrument.

**Decision: the Sigma Gold System is the canonical architecture.** We transplant v1's statistical rigor and ADR governance into it, and we add one structural idea neither had — a hard separation between the **Engine** (universal measurement instrument) and the **Strategy** (instrument-specific content). This document is set in stone. Every build step references it.

This blueprint also rejects **both frameworks' build order**. Both build horizontally (finish each layer before the next). We build **vertically** — validate-first, thinnest slice end-to-end — because the underlying signal has not yet earned a cathedral.

---

## 1. The single sentence

> Build an **instrument-agnostic measurement instrument** that turns any `(signal, returns, costs, factors, regimes)` into an institutional tearsheet (IC, ICIR, IC-decay, net IC, residual alpha, regime-conditioned IC), and run the **regime-conditioned gold B2B signal** through it as the first adapter.

The engine is the career asset. Gold is the first thing we measure with it. Neither framework stated this; it is the most important decision in this document.

---

## 2. The falsification gate (top of the funnel — read before building anything)

A world-class researcher writes down what would prove them wrong **first**. This is also exactly what a Balyasny interviewer probes for.

> **KILL CRITERION:** If the regime-conditioned B2B signal shows **IC < 0.02 with t-stat < 1.5 on out-of-sample data**, the B2B signal is abandoned as a QR artifact. We do not build the Context Engine, the Regime Engine, or the EA around it.

The unconditional signal is already known to be net ≈ −0.008 R after costs (Notebook 03). The entire project rests on the hypothesis that regime-conditioning rescues it. We test that hypothesis with the **crudest possible proxies first**, before any sophisticated machinery is built.

---

## 3. Architecture — Engine vs Strategy

```
┌──────────────────────────────────────────────────────────────────┐
│  ENGINE  (universal, instrument-agnostic — the portfolio piece)    │
│                                                                    │
│  measurement/                                                      │
│    ic_engine        IC, ICIR, IC-decay, Newey-West t-stat,         │
│                     Benjamini-Hochberg, bootstrap CI, subsample    │
│    factor_decomp    residual alpha after factor model, R²          │
│    regime_ic        IC conditioned on regime state                 │
│    cost_model       spread + impact + financing (cost_registry)    │
│    capacity         AUM-before-decay estimate                      │
│    tearsheet        all of the above → one Tier C artifact         │
│                                                                    │
│  mechanisms/   (added only when a measured IC gain justifies it)   │
│    pit_loader       point-in-time data load (FRED ALFRED vintages) │
│    kalman           continuous-state noise filter                  │
│    pca              redundancy / orthogonalization                 │
│    regime           HMM + BOCPD probabilistic regime inference     │
└──────────────────────────────────────────────────────────────────┘
              ▲ consumes a uniform interface
┌──────────────────────────────────────────────────────────────────┐
│  STRATEGY ADAPTERS  (instrument-specific content — swappable)      │
│                                                                    │
│    gold/         B2B/SAMTC signal + DFII10 / GEX / realized-vol    │
│                  inputs.  ← FIRST ADAPTER (time-series IC story)    │
│    commodities/  cross-sectional momentum (gold/silver/oil/copper/ │
│                  natgas) + gold-silver ratio stat-arb              │
│                  ← cross-sectional IC story (pod-shop-native)      │
│    (future)      equities, FX — each is just config + 4 functions  │
└──────────────────────────────────────────────────────────────────┘
              ▲ same target-state contract
┌──────────────────────────────────────────────────────────────────┐
│  EXECUTION  (deferred — separate engine, separate build)           │
│    target-state → order diff → broker adapter (MT5 / Darwinex /    │
│    IBKR) → fills → reconcile.  NOT built until signal validated.   │
└──────────────────────────────────────────────────────────────────┘
```

**Adapter contract:** every strategy adapter implements exactly four functions — `load_data()`, `build_signal()`, `factor_model()`, `cost_assumptions()`. The engine's measurement core never changes when a new adapter is added. This is v1's adapter philosophy carried by Co-Work's mathematics.

### The dual-IC narrative (how a single-asset engine speaks pod-shop language)

Balyasny/Millennium are equity-heavy pod shops whose native metric is **cross-sectional** IC. A single-gold time-series engine doesn't naturally produce that. The adapter split solves it:

| Adapter | IC paradigm | Interview narrative |
|---|---|---|
| `gold/` | Time-series | "My live-traded B2B signal, regime-conditioned — IC X in trending regimes vs Y unconditional." Authentic edge. |
| `commodities/` | Cross-sectional | "Same engine, cross-sectional commodity momentum + gold-silver stat-arb — IC across the rank, pod-shop-native." |

Authentic edge backed by systematic measurement beats generic competence. Gold is the authentic edge; commodities supply the cross-sectional vocabulary.

---

## 4. Build order — VERTICAL, validate-first

Reject horizontal layer-completion. Build the thinnest end-to-end slice, prove it, then thicken only what a measured IC gain justifies.

### Slice 1 — The kill test (no sophisticated machinery)
- `ic_engine.py`: implement `compute_ic`, `compute_icir`, `compute_ic_decay`, `ic_tstat` (these are universal — both paradigms need them). Crystallize the logic currently scattered in Notebook 03.
- `gold/` adapter, crude regime proxy only: FRED **DFII10** real-yields 3-month-change z-score + 30-day realized-vol rank from existing H1 data. **No Kalman. No HMM. No PCA.**
- Re-filter the existing 1,084 H1 trades to `ry_zscore < 0` AND `rv_rank < 0.4`; re-run cost-adjusted EV and measure IC on the conditioned subset.
- **Gate:** does conditioned IC clear the falsification bar (§2)? Build `notebooks/04_b2b_regime_conditioned.ipynb`.
- **If FAIL → stop. The B2B signal is not the QR artifact.** Pivot to a different signal or adapter.
- **If PASS → license granted to build the rest.**

### Slice 2 — Rigor + tearsheet (turn the slice into an artifact)
- Add Newey-West t-stat, Benjamini-Hochberg, bootstrap CI, subsample stability to `ic_engine`.
- `factor_decomp.py`: regress residual alpha against momentum, DXY, vol regime. Report residual alpha + t-stat.
- `tearsheet.py`: implement the stubbed generator → first Tier C artifact to `strategies/b2b-gold/tearsheet_<date>.md`.
- Walk-forward OOS (IS 2016–2020, OOS 2021–2026, no refit). IS-IC vs OOS-IC.

### Slice 3 — Upgrade mechanisms ONLY where IC improves
- Swap realized-vol proxy → **HMM + BOCPD** regime engine. Keep the upgrade only if regime-conditioned IC improves measurably vs the proxy.
- Swap raw z-score → **Kalman**-filtered inputs. Keep only if IC improves.
- Add **PCA** when ≥3 context inputs exist and correlation > 0.6.
- Each upgrade is justified by a measured number, recorded in its ADR.

### Slice 4 — Second adapter (proves the engine is universal)
- Build `commodities/` adapter (cross-sectional momentum + gold-silver stat-arb). One session, because the engine already exists. Produces the cross-sectional IC narrative.

### Deferred — Execution engine, TimescaleDB, alt-data
- All behind ADRs with explicit triggers. **Not built until a signal passes §2 and live capital is committed.** Point-in-time correctness comes from FRED ALFRED vintages in parquet — **no database required** for the memo.

---

## 5. Statistical standard (transplanted from v1 — non-negotiable)

Every IC number in a tearsheet carries:
- Spearman rank IC, ICIR = mean(IC)/std(IC)
- **Newey-West** corrected t-stat (lags=5 daily) — corrects IC autocorrelation
- **Benjamini-Hochberg** correction whenever >1 signal is tested — prevents false discovery
- **Bootstrap 95% CI** on mean IC
- **Subsample stability** — split IS into thirds, all three must show positive IC
- **Point-in-time correctness** — FRED revises DFII10; join on release vintage, never on calendar date. This is the single most common lookahead bug in macro-conditioned strategies and a guaranteed Balyasny question.

Pass gate (per signal): IC > 0.03 AND ICIR > 1.0 AND NW t-stat > 2.0 AND subsample-stable AND net IC > 0 after costs.

---

## 6. Governance (transplanted from v1 — non-negotiable)

Any agent modifying an engine component MUST:
1. Read the relevant ADR before touching the component.
2. Check whether the ADR's trigger condition has been met.
3. Trigger met → follow the documented upgrade path. Not met → implement within the current decision.
4. Proposing a deviation not covered by an ADR → write a new ADR first, get Syafiq's approval.

ADR status under this blueprint:
- ADR-001 (factor model), ADR-003 (signal combination), ADR-004 (IC method), ADR-005 (cost model) — **active**.
- ADR-002 (regime detection) — **active, extension pending**. ADR-002 already chose HMM 3-state (correct). The Co-Work Regime Engine extends it with **BOCPD** transition detection and **four regime dimensions** (trend/vol/correlation/liquidity). ADR-002 to be amended to record that extension when Slice 3 begins. The crude SPY/VIX/yield-curve `if/else` in the `regimes.py` stub docstring is NOT the chosen method and must be discarded.

---

## 7. What changed from each prior design

| | v1 | Co-Work | This blueprint |
|---|---|---|---|
| Architecture | Cross-sectional equity lab | Gold-welded 4-engine system | Co-Work mechanisms, **un-welded** into a universal engine + adapters |
| Build order | Horizontal, 10 sessions | Horizontal, 4 months | **Vertical, validate-first slices** |
| Infrastructure | None | TimescaleDB + Kafka up front | **Deferred behind ADR; parquet + ALFRED vintages for the memo** |
| Statistical rigor | Strong (NW, BH, bootstrap) | Light | **v1's rigor, kept** |
| Governance | ADRs | None | **v1's ADRs, kept** |
| Falsification gate | Implicit | Absent | **Explicit kill criterion (§2)** |
| Career framing | Generic ETF lab | Gold bot | **Instrument-agnostic measurement instrument** |

---

## 8. Source documents

- Architecture (canonical): `engine-architecture/{Context,Regime,Signal_Execution,Data_Layer}_Architecture.md`, `XAUUSD_Options_Flow_Research.md`
- Diagrams: `engine-diagram/*.svg`
- Superseded: `_superseded/engine-design-v1.md`
- Methodology standard: `Research/RESEARCH_FRAMEWORK.md`
- First adapter spec: `strategies/b2b-gold/B2B_STRATEGY_MASTER.md`
