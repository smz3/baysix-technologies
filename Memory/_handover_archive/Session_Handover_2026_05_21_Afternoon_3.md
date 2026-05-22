# Session Handover — May 21, 2026 (Afternoon #3 — Pipeline restructured 8-step; Step 4 dissected, built & scaffolded)

## Context for this session

Continued the first-principles QR pipeline build. Previous session locked Steps 1–3 and seeded Step 4 (then called "OOS Rigor Gate"). This session: deep-dived Step 4 from first principles, restructured the pipeline to 8 steps, dissected Step 4 IS Validation, built its HTML panel, and scaffolded its folders.

**Canonical map:** [quant_pipeline_flow.html](../Braindump/quant_pipeline_flow.html) — click Step 4 to see the full panel with flow diagram, metrics glossary, and three gate deep-dives.

**STYLE RULES (enforced — do not drift):**
- Global CLAUDE.md #3 brevity: lead with the answer, fewer words, no padding.
- [feedback_doc_abbreviations.md]: spell out every abbreviation + what/why/mental-model in research docs.
- [feedback_multi_asset_framing.md]: do NOT anchor examples to XAUUSD. Frame all pipeline work as multi-asset.
- Working method: discuss + deep-dive FIRST (Socratic, why-why-why), THEN touch artifacts.

---

## What Was Accomplished This Session

### 1. Pipeline restructured: 7 steps → 8 steps

**The problem:** Step 4 (OOS Rigor Gate) was doing both IS correction work (DSR, factor decomp, regime) AND the OOS seal break in one step. This conflated IS and OOS work.

**The fix:** Split Step 4 into two distinct steps:

| Old | New |
|-----|-----|
| Step 4 — OOS Rigor Gate (IS corrections + OOS) | Step 4 — IS Validation (IS corrections only) |
| — | Step 5 — OOS Rigor Gate (one-shot OOS break) |
| Step 5 — Lean Engine | Step 6 — Lean Engine |
| Step 6 — Research Note | Step 7 — Research Note |
| Step 7 — Risk + Deploy | Step 8 — Risk + Deploy |

**Also renamed:**
- `step3-rapid-fire` → `step3-is-rapid-fire`
- `step4-rigor-gate` → now `step4-is-validation` + `step5-oos-rigor-gate`
- HTML display names updated to "IS Rapid Fire", "IS Validation", "OOS Rigor Gate"

**Full pipeline:**
```
step1-idea-bank
step2-dataset
step3-is-rapid-fire       ← IS coarse screen (IC t-stat gate)
step4-is-validation       ← IS honest accounting (DSR, factor decomp, regime)
step5-oos-rigor-gate      ← one-shot OOS IC break
step6-lean-engine         ← costs, slippage, fills
step7-research-note
step8-risk-deploy
```

### 2. Key conceptual clarity from deep-dive

**"Where do you play around with parameters?"** → Step 3, not Step 4. Step 3 is explicitly cheap and many-variant. Step 4 receives the best survivor and judges it. If Step 4 rejects, it gives a diagnosis (trial inflation / factor exposure / regime collapse) — you revise the hypothesis at Step 1 and re-run through Step 3. Max 3× loops. Never tune inside Step 4.

**Why no tuning in Step 4:** adjusting parameters after seeing a DSR or factor result adds hidden trials that corrupt the Ledger count N, making SR* artificially low and PSR overstated.

**Step 4 IS Validation has two internal layers:**
- Layer 1 (IS housekeeping): DSR → Factor Decomp → Regime Diagnostic
- Layer 2: output to Step 5 for OOS seal

They stay in one step because Layer 1 decides whether you've earned the right to break the OOS seal.

### 3. Step 4 IS Validation — dissected from first principles

Three sequential kill gates, each catching a different lie in the IS result:

**Gate 1 — DSR (Deflated Sharpe Ratio):**
- Why: multiple testing — test 100 signals at 5%, ~5 pass by luck. The winner's SR is inflated.
- What: compute SR* (expected best SR from N trials), test if observed SR̂ beats it.
- Output: PSR = P(true SR > 0). Gate: PSR > 0.95.
- Why DSR over alternatives: cheaper than bootstrap, accounts for non-normality via skew/kurt, produces an interpretable probability, industry-standard language at pod shops.
- Limitation: N is almost always understated (mental iterations don't get logged).

**Gate 2 — Factor Decomposition:**
- Why: the signal might just be momentum or carry in disguise. A PM can buy those cheaper via ETFs.
- What: OLS regression of signal returns against known factors → residual α must have t(α) > 2.
- Factor set is universe-specific (built from Step 2), not globally pre-specified.
- OLS default; Huber alongside for fat-tailed universes (outlier events distort OLS betas).

**Gate 3 — Regime Diagnostic:**
- Why: if the IS sample was mostly trending, the IC estimate is regime-specific, not general.
- What: compute IC per regime using past-data-only labels (vol-pct, Hurst, HMM).
- Three outcomes: IC stable → clean. IC collapses in one regime → revise hypothesis (add regime filter at Step 1). IC negative in a regime → investigate before OOS.
- This is diagnostic, not design. Not building a regime engine here.

**The Rule (enforced):** Any gate fails → back to Step 1. Never tune parameters here.

### 4. Step 4 HTML panel built

[quant_pipeline_flow.html](../Braindump/quant_pipeline_flow.html) Step 4 now includes:
- SVG flow diagram — 3 sequential kill gates with yes/no paths, The Rule box, output
- Metrics table — SR̂, SR*, PSR, N, T, skew, kurt, α, βₖ, Fₖ, ICⱼ — each with what/why/mental-model
- Gate 1 deep-dive — DSR math, why not plain t-stat, alternatives compared
- Gate 2 deep-dive — factor table (market, momentum, carry, value, VRP, universe-specific), OLS vs Huber
- Gate 3 deep-dive — Hurst / vol-pct / HMM regime methods, three outcome types

### 5. step4-is-validation/ scaffolded

```
step4-is-validation/
├── IS_VALIDATION_SCOREBOARD.md       ← root artifact: notation, 8 locked decisions, scoreboard, run template, IV-001 seeded
├── dsr-engine/
│   └── dsr.py                        ← observed_sharpe, benchmark_sharpe, psr, dsr_gate (fully implemented)
├── factor-model/
│   └── factor_model.py               ← run_ols (implemented), run_huber (NotImplementedError stub), factor_gate
├── regime-diagnostic/
│   └── regime_diagnostic.py          ← label_regimes_vol_pct (implemented), rolling_hurst (stub), ic_by_regime, regime_diagnostic_gate
└── runs/
    └── IB-001-b2b/
        └── README.md                 ← IV-001 seeded, queued, blocked on RF-001 passing first
```

---

## What Is NOT Done / Still Open

- **Step 5 OOS Rigor Gate** — not started. Next session's main task. Discuss-first, first principles.
- **Steps 5–8 HTML panels** — not built. Step 5 especially needs the abbreviation-spell-out treatment.
- **CS-GOLD-JM-H1 honesty audit** — still outstanding. Blocks RF-001 (Step 3) → IV-001 (Step 4).
- **step3 ic-engine stubs** — effective_n (Newey-West), decile_spread, decay_profile all still NotImplementedError.
- **factor-model/run_huber** — NotImplementedError stub. OLS works; flag if single event drives >10% of R².
- **regime-diagnostic/rolling_hurst** — NotImplementedError stub. vol-pct is the working alternative.
- **CLAUDE.md lean-engine path fix** — stale path still outstanding from two sessions ago.
- **Step 3 SVG still references XAUUSD** — `timing skill — e.g. XAUUSD` at line ~421. Should be generic.

---

## Running Processes

None.

---

## Priority for Next Session

1. **Deep-dive Step 5 OOS Rigor Gate — discuss first, first principles.** One job: *is the edge real on data the signal has never seen?* Key atoms: one-shot OOS seal (break it once, no re-tuning), IC stability IS→OOS, decay profile confirms holding period, PSR on OOS result. Spell out every abbreviation; give what/why/mental-model per metric.
2. After dissection: build Step 5 HTML panel (flow diagram + metrics + gate deep-dives).
3. Scaffold step5-oos-rigor-gate/ folder (same pattern: root artifact + function subfolders).
4. Quick wins (any session): fix CLAUDE.md lean-engine path, fix Step 3 SVG XAUUSD reference.

---

## Key Decisions Made

- **Pipeline is now 8 steps.** IS corrections (Step 4) are fully separated from OOS break (Step 5). Clean boundary.
- **Step 4 name: IS Validation** (not "IS Tuning" — "tuning" implies parameter search which is forbidden here).
- **Tuning happens in Step 3, judging happens in Step 4.** Step 3 → Step 4 → Step 1 loop max 3×.
- **Gate 3 is a flag, not a kill.** Regime collapse → revise hypothesis. It does not kill the hypothesis class.
- **Multi-asset framing mandatory.** Do not anchor pipeline examples to XAUUSD. Use generic instrument/signal/universe language.

---

## Blockers

None for Step 5 discussion. IV-001 execution blocked on RF-001 (CS-GOLD-JM-H1 audit), but that does not block Step 5 design work.
