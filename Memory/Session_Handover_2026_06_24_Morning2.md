# Handover — June 24, 2026 Morning2

> Read this fully before proposing work. This session pivoted BRC's whole framing — don't re-surface the old "filter the bulldozed cohort" plan; it was tested and reframed today.

## TL;DR (one breath)
BRC-continuation loses on average **every way we've sliced it** (entry timing, zone-quality filters, HTF alignment, dollar-risk caps). Per-trade expectancy is **E[R] ≈ −0.28, $/trade ≈ −0.49** (result_id 7). Today proved the "instant-loss cohort = our bleed" belief was an **R-multiple illusion** — in *dollars* those are the cheapest losses. The one untested direction left is the **mirror trade (FADE, #131)**. That is the next experiment.

## What I did this session
1. **IS-03 full 8.5yr re-run scored + logged** (task 148 done). v1.2.1 binary, no 2018 freeze. **result_id 7**: net −0.492/trade, E[R]=−0.282, t=−4.31, n=1557, span 2016.06.20–2024.06.28. Ledger: `Common/Files/BRC/brc_trades_XAUUSD_dukas_v121_M15CONF_L1_CONTINUATION_k020_20240628_2359.csv` → ingested as **tester run #15**.
2. **Verdict held (NOT logged as FALSIFIED — Syafiq said hold):** the M15-confirmation's pre-registered job was to kill the never-green cohort. It **failed** — never-green 43.5% vs IS-01 ~42% (result_id 7 vs result_id 3). Confluence-as-confirmation does not separate good zones.
3. **Closed two provenance gaps:** saved [brc_trader-v1.2.1-IS03-M15CONF.set](../mt5/presets/brc_system/brc_trader-v1.2.1-IS03-M15CONF.set); ingested the v121 ledger into `tester_trades`. (IS-02's raw ledger was already lost — only run #12 summary survives. New habit: ingest every ledger before moving on.)
4. **Wrote DRAFT spec** [docs/specs/2026-06-24_brc_zone_quality_features.md](../docs/specs/2026-06-24_brc_zone_quality_features.md) (task #144) — then the exploratory pass below made me recommend NOT building it yet.
5. **EXPLORATORY separation screens** (query-layer on existing emit run #5 + ledger v121 — labelled exploratory, NOT tester verdicts). Findings:
   - **Cheap zone-geometry features (zone width, break impulse |p4−p5|, distance-to-fill) do NOT separate the bulldozed cohort** once the *complete* cohort is used. AUCs ≈ 0.46–0.49. (Earlier "they separate" was an artifact: run-10 IS-01 ledger silently **dropped zone_key on 100% of bulldozed trades** — biased sample. IS-03/run #15 is clean: 0 blank keys.)
   - **R-DENOMINATOR ILLUSION confirmed ([[er_denominator_illusion]]):** sort trades by M15-zone width → bulldozed *rate* falls monotonically (narrow 68% → wide 23%) **but $/trade gets WORSE** (narrow −0.28 → wide −1.04), because wide zone = 10× bigger stop ($0.52 → $5.30 per 1R). **The instant-loss cohort is our CHEAPEST loss in dollars; the dollar bleed is the wide-stop trades.** "Filter the bulldozed" optimizes the wrong number.
   - **HTF alignment (your H4+D1 idea):** H4-aligned trades have better payoff (−0.43 vs −0.60 $/trade) at the *same* bulldozed rate — small but real. D1 = no help / wrong sign. Keep H4-align as a minor feature, not a main lever.
6. **Dollar-risk-cap simulation** on the v121 ledger (exploratory): capping/skipping wide-stop trades cuts the bleed hugely — at a ~$1.0–1.5 cap, $/trade −0.49→~−0.13 and max DD $817→~$95–155 — **but E[R] stays −0.28 at every cap level.** Sizing smooths/slows the loss; it cannot turn negative expectancy positive. Not an edge fix.

## Next
1. **TEST THE FADE (task #131, P1):** reverse the entry direction (sell the retest instead of buy), same H1/M15 atom, **net of double-spread cost**. Core question: if continuation is reliably negative (E[R]=−0.28, result_id 7), is the mirror +edge after costs? This is THE experiment. Run on the MT5 trader (flip `InpEntrySide=BRC_REVERSAL`) or first cheap-screen the existing v121 ledger by negating realized_r minus 2× cost as a go/no-go.
2. **Decision gate after #131:** if fade also fails → that's the 2nd clean falsification → BRC-continuation is **kill-eligible** (rule 8b needs ≥2 FALSIFIED). Bring kill vs final-reframe to Syafiq; do NOT kill unilaterally.
3. **#144 zone-quality emitter = DEPRIORITISED (now P2):** cheap geometric features are an R-illusion (above). Only worth building if fade fails AND we want the *fill-time* features the screen couldn't test (momentum-into-zone / approach-velocity) — those are the only untested causal story.

## Blockers
- None. OOS #126 stays blocked (no IS variant with a positive frozen edge yet).
- ⚠️ Note for next agent: a Bash guard ([protocol_guard.py](../.claude/hooks/scripts/protocol_guard.py)) blocks any script containing the word `REPLACE` (incl. Python `.replace()`) when a DB name is present — use `.removeprefix()` / slicing, and open research.db read-only (`file:...?mode=ro`).
