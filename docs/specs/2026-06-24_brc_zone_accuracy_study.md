# BRC Zone-Accuracy Study — Spec

**Date:** 2026-06-24 · **Idea:** BRC-001 · **Status:** EXECUTING Tier-1 (exploratory)

## Why
Every BRC number to date is a *trade* result (entry/exit/sizing/fade), net of cost. We
never tested the **premise**: does price respect a BRC zone more than a random level?
This is the G2 "Edge" test we skipped by jumping straight to a trader. No entry rule,
no cost, no sizing — just zone predictivity vs a null.

## The metric (and what we reject)
- **Respect = `continued`** (oracle-emitted, [brc_lifecycle.mqh](../../mt5/Include/brc_system/brc_lifecycle.mqh)):
  after the L1 retest fires (`entered`), a bar **CLOSES ≥ +1R in the break direction
  before invalidation**, where entry = L1, **R = |L1 − L2|**, and the zone dies on a
  **close beyond L2 (= entry ∓ 1R)**.
- ⇒ `continued` is *exactly* a **±1R close-based first-passage** from the retest bar:
  first +1R close strictly before first −1R close. This is the clean, TF-comparable,
  horizon-free respect metric.
- **REJECTED — `mfe_r` / `realized_r` as "reaction size":** they accumulate excursion
  over the *entire* zone life until invalidation (mean MFE ≈ 17R, median ≈ 2.6R — heavy
  right tail from long-lived zones). Unbounded-horizon ⇒ contaminated, not a clean
  reaction measure. We use the binary respect rate only.

## The null (the sanity check)
- Real respect = ±1R close first-passage starting at **BRC retest bars**.
- Null respect = the **identical** first-passage starting at **random bars**, with the
  **R sampled from that TF's real |L1−L2| distribution** and direction drawn 50/50.
- Edge = (real respect − null respect) per TF, with bootstrap CIs. Under a driftless
  symmetric model both → 50%; the edge is whether *starting at a BRC level* shifts it up.

## Design axes (strict order)
1. **Per-TF first** (M5/M15/M30/H1/H4/D1, each vs its own null). Establishes which TF —
   if any — carries signal. Confluence is uninterpretable without this baseline.
2. **Confluence second** (TF-stacking / russian-doll), **gated** on Step 1 showing any TF
   beats null. Not built until the foundation justifies it.

## Two tiers (trust discipline — MT5 tester is the arbiter)
- **Tier-1 (this build, EXPLORATORY, NOT a gate verdict):** Python ±1R first-passage on
  ArcticDB-derived bars (`arctic_io.bars(tf, venue='JM_EET')`). Fast go/no-go.
  - **Parity gate:** the same tracker run on the *real* retest bars must reproduce the
    emitter's `continued` within tolerance (target ≥ ~95% agreement). Arctic is a
    different bar source than the Dukascopy the emitter ran on, so a gap is expected —
    parity quantifies how trustworthy the Tier-1 null comparison is.
- **Tier-2 (verdict, only if Tier-1 is promising/ambiguous):** add a placebo random-level
  mode to the MQL5 emitter, re-emit on the same Dukascopy data, compare real vs placebo
  `continued` — apples-to-apples, arbiter-grade.

## Decision rule
- Real respect ≈ null across all TFs (Tier-1) → strong exploratory signal that zones
  carry no standalone edge; motivates the kill-vs-reframe discussion (do **not** kill
  unilaterally — rule 8b needs ≥2 FALSIFIED). Continuation already negative is the 1st.
- Any TF clearly beats null → escalate to Tier-2 for the verdict, then Step-2 confluence.

## Artifacts
- `research/models/brc/zone_accuracy.py` — the study.
- `research/outputs/brc/zone_accuracy_tier1.json` — per-TF real/null/parity numbers.
