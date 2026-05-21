# Session Handover — May 21, 2026 (Afternoon — QR research pipeline: Step 1 locked, Step 2 next)

## Context for this session

Syafiq asked for a fresh, first-principles design of a world-class quant research pipeline (he explicitly set aside the older B2B-locked engine architecture for this exercise). We designed it Elon-Musk style — strip to atoms, add back only what earns its place. The output is a **visual blueprint + a folder structure that mirrors it 1:1**. Next session: deep-dive **Step 2 (Dataset)**.

**STYLE RULE (enforced this session — do not forget):** Global CLAUDE.md #3 is now a hard rule. Lead with the answer, fewer words, no padding, no decorative tables/headers to look thorough. Depth of topic ≠ license for length. See memory [feedback_brevity_delivery.md]. Syafiq will call it out if you drift.

---

## What Was Accomplished This Session

### 1. Designed the QR pipeline as a kill-gate funnel (the "Alpha Funnel")
Canonical blueprint = [quant_pipeline_flow.html](../Braindump/quant_pipeline_flow.html) — interactive monochrome flowchart. Click any step/foundation block → panel shows Input→Output, What's inside, Metrics/math, Kill gate. (We trialed a Sankey first, then moved to this flowchart — flowchart is the one we use.)

**Design principle:** one job per engine, measured at its boundary, in strict order. Each step is a kill-gate — die cheaply before the next, more expensive step. ~100 ideas in → ~2 deployed.

**The 7 steps (final order):**
1. Idea Bank + Triage
2. Load Dataset
3. Rapid Fire (vectorized, IS) — does edge EXIST?
4. Rigor Gate (deflated Sharpe, decay, regime IC, factor decomposition, OOS) — is edge REAL?
5. LEAN (event-driven, full costs) — does edge SURVIVE execution?
6. **Research Note** — write up evidence = the go/no-go decision (evidence before capital)
7. **Risk + Deploy** — size (vol target, fractional Kelly), limits, kill switch, paper→live; live attribution loops back to Step 1

**FOUNDATION (built once, feeds every step — NOT per-idea flow):** Data Machinery · Volatility Estimators · Research Ledger · Context/State Engine.

### 2. Step 1 fully fleshed out (this is locked)
- **Organize the bank by RETURN DRIVER, not asset class.** Two buckets: risk premia (ballast) vs inefficiencies (independent's hunting ground).
- **Core 5 families** (cut down from 8): 1 Trend · 2 Mean Reversion/RV · 3 Carry · 4 Volatility (VRP) · 5 Value. Folded in: stat-arb + slow flow (B2B) → #2; event/catalyst → an overlay; HFT microstructure dropped (inaccessible to independent).
- **Macro & HMM-regime are CONDITIONS, not families.** A condition = a state variable that modulates a signal, doesn't generate one. Conditions live in the **Context/State Engine (Foundation)**: regime, macro state, vol regime, session/liquidity, trend-vs-range, correlation, event-proximity. Caveat: conditioning is an overfitting magnet → default UNCONDITIONED; a condition earns its place only if conditional IC > unconditional IC out-of-sample (validated at Step 4).
- **Plug-and-play = one contract, not one universal strategy.** Every strategy is a plugin: DECLARE (the Idea Bank entry schema) + COMPUTE(PIT_data)→standardized forecast (centered 0, |avg|~10, capped ±20). Same pattern as pysystemtrade rules / LEAN Alpha Models.
- **Triage decision flow:** New idea → Specify (family·asset·venue·frequency — free, not a gate) → Has economic story? (no→graveyard) → Data available for this asset/venue? (no→park) → Triage score ≥ threshold? (no→backlog) → write kill condition → QUEUE to Step 2.
- **Venue is part of the hypothesis** (3 venues: Just Markets MT5 / Darwinex Zero / IBKR — different costs, leverage, capacity, data).

### 3. Created the fillable Idea Bank
[IDEA_BANK_TEMPLATE.md](../workspace/baysix-engine/sigma-are/research-engine/step1-idea-bank/IDEA_BANK_TEMPLATE.md) (Syafiq renamed from IDEA_BANK.md). Markdown: a Queue dashboard table + a copy-paste Template block + 4 worked seed entries:
- IB-001 Gold B2B flow reversion (family 2, Just Markets, status=testing, real evidence: +0.309 R/trade, n=1,084, z=+7.19 — next: cost-adjusted check)
- IB-002 Gold VRP (family 4, IBKR, queued)
- IB-003 Regime-gated trend (family 1, Darwinex, queued)
- IB-004 Macro-conditioned carry (family 3, Darwinex, backlog)
Triage = avg of 4 scores (plausibility, capacity-fit, data-availability, edge-in-understanding), 1–5 each; ≥3.5 queued, 2.5–3.5 backlog, <2.5 reconsider.

### 4. Folder structure now mirrors the pipeline 1:1
Syafiq reorganized `workspace/baysix-engine/sigma-are/research-engine/` into step-numbered folders:
`step1-idea-bank · step2-dataset · step3-rapid-fire · step4-rigor-gate · step5-lean-engine · step6-research-note · step7-risk-deploy`.
(`lean-engine` was moved in and renamed `step5-lean-engine`. Steps 6/7 were swapped — folders already renamed by Syafiq, HTML already updated to match.)

---

## What Is NOT Done / Still Open

- **Step 2 (Dataset) deep-dive** — not started. This is the next session's main task.
- The step2–step7 folders are empty scaffolding (only step1 has content).
- CLAUDE.md still references the OLD lean-engine path (`sigma-are/lean-engine`) — now stale; should point to `research-engine/step5-lean-engine`.

---

## Running Processes

None.

---

## Priority for Next Session

1. **Deep-dive Step 2 (Load Dataset)** — same method as Step 1: define what's inside, then enrich the Step 2 panel in [quant_pipeline_flow.html](../Braindump/quant_pipeline_flow.html). Key topics to cover: instrument-specific fetch driven by Step 1 tags (CFD gold ≠ GC futures ≠ QQQ); point-in-time alignment; cleaning (gaps/ticks/outliers); adjustment PER ASSET CLASS (futures rolls / equity corporate actions / CFD none); IS/OOS split + sealed OOS vault; the capability-vs-instance rule (build the connector once per asset class, instantiate per idea). Remember the distinction: Data Machinery (capability) = Foundation; the actual dataset fetch = the Step 2 flow.
2. Optionally produce a Step 2 working artifact in `research-engine/step2-dataset/` (e.g., a data-source registry / schema), analogous to the Idea Bank template.
3. Quick win: fix the stale lean-engine path in CLAUDE.md.

---

## Key Decisions Made

- **Flowchart over Sankey** as the canonical visualization (interactive, click-to-expand).
- **Core 5 families**, organized by return driver not asset class.
- **Conditions (macro, regime, vol regime, session…) belong in a Foundation Context/State Engine**, referenced by a `conditioned_by` field in Step 1, validated at Step 4 — not a strategy family.
- **Steps 6 & 7 swapped**: Research Note (evidence/go-no-go) comes BEFORE Risk+Deploy. Rationale: evidence before capital; the research note is the QR deliverable and the deploy decision input.
- **Plug-and-play via a signal contract** (DECLARE + COMPUTE), not a universal strategy.
- Monochrome / no-AI-slop design for all HTML (paper bg, charcoal ink, serif headings, hairline rules).

---

## Blockers

None.
