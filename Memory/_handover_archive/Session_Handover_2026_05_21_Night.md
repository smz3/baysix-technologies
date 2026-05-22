# Session Handover — May 21, 2026 (Night — Steps 5–8 built; Step 4 math bugs found & fixed; pipeline HTML walk complete)

## Context for this session

Continued the first-principles QR pipeline build. Previous session locked Steps 1–4 (Step 4 IS Validation dissected, built, scaffolded). This session: dissected & built **Step 5 (OOS Rigor Gate)**, **audited and fixed critical math bugs in Step 4**, then built **Steps 6 (LEAN), 7 (Research Note), 8 (Risk + Deploy)** — HTML panels + scaffolded folders. **All 8 pipeline steps now have full HTML panels and scaffolded folders.**

**Canonical map:** [quant_pipeline_flow.html](../Braindump/quant_pipeline_flow.html) — click any step 1–8 for the full panel (flow SVG, metrics glossary, gate deep-dives).

**STYLE RULES (enforced — do not drift):**
- Global CLAUDE.md #3 brevity: lead with the answer, fewer words, no padding.
- [feedback_doc_abbreviations.md]: spell out every abbreviation + what/why/mental-model in research docs.
- [feedback_multi_asset_framing.md]: do NOT anchor examples to XAUUSD. Frame all pipeline work as multi-asset.
- Working method: discuss + deep-dive FIRST (Socratic, why-why-why), THEN touch artifacts.

---

## What Was Accomplished This Session

### 1. Step 5 — OOS Rigor Gate: dissected, built, scaffolded

One job: **is the edge real on data the signal has never seen?** Key design locked via discussion before building:
- **Archetype branch** (the core fix): cross-sectional signals use `t = ICIR·√T`; time-series use `t = IC·√N_eff`. Declared at Step 1. The original Sonnet draft conflated these (described cross-sectional IC but used the time-series `IC·√T` formula) — that wrongly implied "4–12 years OOS needed." For cross-sectional with ICIR≈0.5 you need ~11 periods, not years.
- **OOS budget**: the one-shot seal rule holds per-signal, but Step 4 allows a 3× revise-loop. Each loop back through OOS spends a test → Šidák-corrected critical t. Otherwise "N=1" is a lie by loop 3.
- **Power audit**: report min-detectable IC = 1.65/√N_eff. If it exceeds signal IC → **QUALIFIED PASS** (underpowered), not a kill — Lean (Step 6) becomes load-bearing.
- 4 gates: OOS IC t-stat · IS→OOS degradation · decay-profile match · PSR on OOS curve. Three outcomes: PASS / QUALIFIED PASS / REJECT.

Scaffold: [step5-oos-rigor-gate/](../workspace/baysix-engine/sigma-are/research-engine/step5-oos-rigor-gate/) — OOS_RIGOR_SCOREBOARD.md + oos-ic-engine/ + degradation/ + decay-match/ + psr-oos/ + runs/IB-001-b2b (OG-001 seeded).

### 2. Step 4 — IS Validation: CRITICAL math bugs found & fixed (re-audit after user concern)

User asked to double-check Sonnet's Step 4 work. Found and fixed (all verified numerically):

**dsr.py (Gate 1 — DSR) — was effectively broken:**
- **Units bug (critical):** `observed_sharpe` returned ANNUALISED Sharpe but `psr()` expects PER-PERIOD with T=obs count. The `√(T−1)` already carries frequency → PSR pinned at 0.0 or 1.0 (a step function, never a real probability). Fixed: per-period internally, annualised only for display.
- **var_sr=1.0 hard-coded:** SR* was in arbitrary units. Fixed: default to null `1/(T−1)`, accept empirical trial variance.
- **kurt term:** used `(kurt−3)/4`; canonical Bailey–LdP is `(kurt−1)/4`. Fixed.
- **SR\*:** upgraded to two-term Euler–Mascheroni expected-max (was single-term Φ⁻¹(1−1/N)).
- Verified: PSR now moves smoothly — N=5→0.94, N=50→0.70, N=200→0.51.

**factor_model.py (Gate 2):**
- **`abs(t_alpha)` bug:** a significantly NEGATIVE alpha (loses money after factors) would PASS. Fixed to signed `t_alpha >= +2`. Verified: t=−4.32 now correctly kills.
- Added **Newey-West HAC** standard errors (auto lag, default on) — plain OLS understated SE on autocorrelated returns. Verified: t=3.52 (OLS) → 2.17 (HAC).

**regime_diagnostic.py (Gate 3):**
- **Lookahead leak:** vol percentile thresholds used the full sample. Fixed to expanding past-only window (honors locked decision #4).
- **NaN ≠ collapse:** thin-data regimes now reported as `insufficient`, no longer forcing a needless `revise`.

Also synced the Step-4 HTML SR\* formula line to the corrected two-term form.

### 3. Step 5 self-audit — SAME bug class found in MY OWN code

After fixing Step 4, re-audited Step 5 (which I built this session). Found I'd repeated the exact bugs:
- **psr_oos.py:** same units bug + `(kurt−3)/4`. With SR\*=0 it pinned PSR at ~1.0 → Gate 4 always passed. **Fixed + verified** (now varies 0.92–0.99).
- **oos_ic.py:** underpowered check compared raw mean-IC to the floor, but cross-sectional t-stat runs on ICIR. **Fixed** — power floor now in the test metric's own units.

→ Saved feedback memory [[per-period-sharpe-units-rule]]: the units bug recurred **3×**. Now a mandatory checklist item for every Sharpe/PSR touchpoint.

### 4. Step 6 — LEAN Execution Gate: panel + scaffold

Resolved a key confusion with the user: **LEAN is the engine; we do NOT write a cost simulator.** LEAN is event-driven (prevents lookahead by construction) and ships cost/slippage/fill models. We add only: (1) custom Just Markets CFD FeeModel (spread + **swap** — LEAN has no Just Markets model, swap dominates multi-day CFD holds), (2) the gate evaluator (judges LEAN output), (3) capacity sweep.

LEAN CLI **is installed** (`lean 1.0.225`); Docker runtime + XAUUSD data UNVERIFIED. Per user instruction: algorithm/model files are **API stubs**; gate evaluator is real/runnable.

Scaffold: [step6-lean-engine/](../workspace/baysix-engine/sigma-are/research-engine/step6-lean-engine/) — LEAN_EXECUTION_SCOREBOARD.md + models/ (justmarkets_cfd_model.py stub) + algorithms/ (b2b_gold_algo.py stub) + gate/execution_gate.py (verified: all 4 verdicts fire — pass/revise/kill-cost/kill-capacity) + runs/IB-001-b2b (LE-001).

### 5. Step 7 — Research Note: panel + scaffold (flat folder system)

Synthesis step — pulls evidence from each upstream scoreboard (single-source, never recompute) into one publishable note + explicit GO/NO-GO in pod-shop language. **Deliberately flat to avoid mess:** no function sub-folders, one self-contained `.md` per signal.

Scaffold: [step7-research-note/](../workspace/baysix-engine/sigma-are/research-engine/step7-research-note/) — RESEARCH_NOTE_INDEX.md + NOTE_TEMPLATE.md + notes/RN-001-IB-001-b2b.md.

Also **relocated 3 misplaced notebooks** out of step7 (it's write-only) to their owning steps under `notebooks/b2b-xauusd/`: `00_data_audit` → step2, `02_b2b_ic_measurement_v2` → step3, `03_b2b_cost_adjusted` → step6.

### 6. Step 8 — Risk + Deploy: panel + scaffold (closes the loop ↻)

Final step. Key concept: **Risk runs twice** — Pass 1 sizes each signal to its vol target (+ fractional Kelly ¼–½); Pass 2 scales the whole book by `min(1, target_vol/√(wᵀΣw))` after combination (correlated signals stack risk). Pre-committed kill switch. Live attribution (realised IC vs expected → drift) feeds back to Step 1.

Scaffold: [step8-risk-deploy/](../workspace/baysix-engine/sigma-are/research-engine/step8-risk-deploy/) — RISK_DEPLOY_SCOREBOARD.md + sizing/vol_target.py + limits/risk_limits.py + attribution/live_attribution.py + runs/IB-001-b2b (RD-001). All 3 modules verified numerically (Pass 2 scaled 0.8-corr book to 0.42×; kill switch trips at −12% vs −10%; all 3 attribution routes fire). Applied per-period units rule to drift t-stat; ASCII arrows in action strings for Windows-console safety.

---

## What Is NOT Done / Still Open

- **LEAN end-to-end run** — deferred by user to the very end, after all HTML steps done. Need to verify Docker + LEAN runtime image launch, and XAUUSD CFD data loads via [parquet_to_lean.py](../workspace/baysix-engine/sigma-are/research-engine/step6-lean-engine/scripts/parquet_to_lean.py). See [[lean-cli-runnability-status]].
- **Step 6 algorithm/model stubs** — `b2b_gold_algo.py` and `justmarkets_cfd_model.py` are API stubs; fill from the Just Markets contract spec (spread, commission, swap long/short) when running for real.
- **CS-GOLD-JM-H1 honesty audit** — STILL outstanding. Blocks the entire IB-001 chain: RF-001 → IV-001 → OG-001 → LE-001 → RN-001 → RD-001. Nothing runs until this resolves.
- **step3 ic-engine stubs** — effective_n (Newey-West), decile_spread, decay_profile still NotImplementedError.
- **step4 factor-model/run_huber** — NotImplementedError stub. OLS+HAC works; flag if single event drives >10% R².
- **step5 regime rolling_hurst, decay-match** edge cases — vol-pct is the working alternative.
- **CLAUDE.md lean-engine path** — note: lean-engine now lives at `research-engine/step6-lean-engine/` (user moved it from baysix-engine for easier tracking). CLAUDE.md workspace layout still shows old `sigma-are/lean-engine/` path — should be updated.
- **Step 3 SVG XAUUSD reference** — `timing skill — e.g. XAUUSD` still present, should be generic.

---

## Running Processes

None.

---

## Priority for Next Session

1. **Resolve the CS-GOLD-JM-H1 honesty audit** — this is the single blocker for the whole IB-001 chain. Until it passes, no signal can flow through Steps 3–8. This is the highest-leverage next action.
2. **Verify LEAN runs end-to-end** (when ready): `lean backtest` a trivial sample to confirm Docker + engine, then build XAUUSD data via parquet_to_lean.py. See [[lean-cli-runnability-status]].
3. **Quick wins:** update CLAUDE.md lean-engine path (now `research-engine/step6-lean-engine/`); fix Step 3 SVG XAUUSD reference to generic.
4. **Optional polish:** implement the remaining stubs (step3 effective_n/decile_spread/decay_profile, step4 run_huber, step5 rolling_hurst).

---

## Key Decisions Made

- **Per-period units rule is now law** — every PSR/Sharpe→t-stat uses per-period Sharpe with T=obs count, never annualised. Recurred 3× → checklist item. Kurt term = (kurt−1)/4. [[per-period-sharpe-units-rule]].
- **Step 5 OOS gate branches on archetype** — cross-sectional ICIR·√T vs time-series IC·√N_eff. Wrong formula lies about power by an order of magnitude.
- **OOS budget** — the 3× revise-loop reuses OOS data; tighten the gate with Šidák correction per loop.
- **LEAN is the engine; we don't reimplement costs** — we add custom venue models + gate evaluator + capacity sweep only.
- **lean-engine moved** to `research-engine/step6-lean-engine/` (sibling step folder), not under baysix-engine, for easier tracking.
- **Step 7 is write-only, flat folders** — one self-contained note per signal, no compute, no notebooks. Single-source rule (links upstream, never recomputes).
- **Risk runs twice** in Step 8 — per-signal vol target, then portfolio aggregate cap after combination.
- **Run ID chain convention:** IB-XXX → RF-XXX → IV-XXX → OG-XXX → LE-XXX → RN-XXX → RD-XXX threads one signal through all steps.

---

## Blockers

- **CS-GOLD-JM-H1 honesty audit outstanding** — blocks the entire IB-001 execution chain (Steps 3–8). What's needed: complete the audit on the CS-GOLD-JM-H1 signal so RF-001 can pass Step 3. The +0.309 R/trade prior result is naive until this resolves.
