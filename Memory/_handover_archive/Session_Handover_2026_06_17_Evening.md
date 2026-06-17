# Handover — June 17, 2026 Evening

## State
- **BRC-001 reframed conceptually (Syafiq's key call this session): "kill" was the wrong frame.** We never built a *strategy* — we ran an **edge atom on a logic primitive**. The 3 prior FALSIFICATIONS (strategy_log #52/#53, see handover Afternoon3) are facts about the *unmanaged directional primitive* (≈ trend beta / outlier mirage), NOT a verdict on every strategy derivable from the logic. So BRC stays `gate_2`, falsified 3/2, kill unblocked but NOT executed.
- **The primitive DOES capture Syafiq's logic faithfully** (verified): 5-point breakout [zones.py] → retest L1/mid/L2 [retest.py] → continuation [continuation.py]. Complete + matches spec. Untested strategy levers (the ceiling): touch-depth selection (T1/T2/T3), managed exit, regime/direction conditioning.
- **THREE-LAYER separation locked (human call_id 78):** L1 Fidelity = detector fires per spec (MT5 oracle). L2 = *does BRC behave* — lifecycle funnel base rates (N confirmed → %retested → %continue vs %invalidate → magnitude) per TF M5..MN1 + unconditional same-direction **random-bar continuation control** (makes "it works" falsifiable). L3 = edge vs trend-beta, ONLY after a real tradeable rule exists. **Trend confound belongs to L3, NOT L2.** Proving the *pattern is real* (L2) comes before any strategy/money.
- **MT5-first zone-emitter decided (human call_id 77).** Build a fresh, self-contained `brc_system` EA; Python = inference-only on the exported CSV. Old Sigma B2BDetector (~3.6k coupled lines, Gemini-authored, welded to live EA) judged MORE expensive to clean than rebuild → **build from scratch**, old detector = read-only reference. Implements **PATH B** (locked spec, strategy_log #48 / call_id 76) — NOT the divergent old B2BDetector (Path B requires P3<P1 + consumes rawbreakout stream).
- **Build progress (tasks 118 build / 119 ingest / 120 funnel):** design spec written [brc_emitter_design.md]; **3 of 6 EA files done** — [brc_types.mqh], [brc_swings.mqh] (close-based pivot port of detectors.py), [brc_breakouts.mqh] (rawbreakout.py trimmed — shared-L2 dropped, unused by Path B + doesn't change which breaks fire). All compile-untested (no MT5 here).
- **Naming convention set:** new MQL5 files = lowercase snake_case ([[mql5_lowercase_filenames]]). mq5 will be `brc_emitter.mq5`. Sigma CamelCase = legacy, leave it.

## Next
1. **Build [brc_zones.mqh]** — Path-B 5-pointer pairing + gates (P3<P1, freshness, gap-validation, one-zone-per-P5 dedup). Port from [zones.py]. Freshness collapses skeleton to most-recent swings → detection stays incremental (no O(n²)). THE intricate core.
2. **Then [brc_lifecycle.mqh]** (retest ladder + invalidation close-only + continuation/MFE/MAE, port retest.py+continuation.py+lifecycle.py) → **[brc_csv.mqh]** (UTF-8 header+comma, NOT old UTF-16/headerless) → **[brc_emitter.mq5]** (per-TF new-bar loop, 8 TFs via CopyRates, "Open prices only" model).
3. **Compile** (MetaEditor64 CLI headless) → short-run sanity → **Phase-3 fidelity-diff EA-D1 vs Python detect_zones('D1')** before the 10-yr run. Then ingest → research.db tester_zones → Python L2 funnel (task 120).

## Blockers
None. Caveat: emitter is the trustworthy oracle — correctness is the whole point, so the Python fidelity-diff (step 3) gates trust before any 10-yr run. Schema + execution model fully specified in [brc_emitter_design.md].
