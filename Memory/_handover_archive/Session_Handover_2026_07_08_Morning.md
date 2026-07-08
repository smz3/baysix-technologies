# Handover — July 8, 2026 Morning

## State
- **v1.35.0 shipped + compiled clean** ([fob_baysix.mq5](mt5/Experts/fob_system/fob_baysix.mq5)): new `InpDirFilterTf` {NONE,D1,W1,MN1} — optional ALIGN gate on TRADE-mode CF entries (fire only if setup-TF CF dir == aligner TF's last-PBO dir). State-Engine slice 1 (task 251, human dec call_id 96).
- Filter reads causal `g_setup[fi].pbo_dir` (persists between cycles) — SAME state EMIT stamps into `htf_state`, no Python/no drift. TRADE ingest appends the aligner TF.
- **Gate wiring CONFIRMED firing** — D1 filter cut trades ~36% (cf0 1670/2594, cf2 419/661), matching the run_19 screen's aligned/not split.
- **First A/B pass NET-NEGATIVE + CONFOUNDED** — filtered runs used RR=3.0 but only no-filter baseline on disk is RR=2.0 (result_id 37 cf0 −$1.148/trade, result_id 38 cf2 −$1.511/trade).

## Next
1. **(task 252, P1)** Run **NONE baseline at rr300** — identical settings (H4_H1 / CF_L1_LIMIT / k0.50 / RR3.0 / cf0 AND cf2), real ticks Model=4. De-confounds vs result_id 37/38. Filename won't tag filter → note timestamp.
2. **(task 167, P1)** If B closes null (expected): pivot to **C = exit / payoff-asymmetry (THE LEVER)** — let rare winners run vs fixed RR cap. The one lever still untested.
3. Log the NONE-rr300 result + `strategy_log.log_change` FALSIFIED for the D1 filter if confirmed null.

## Blockers
- **252 gates the B verdict.** Can't declare the D1 filter dead-or-alive on net until the matched NONE-rr300 baseline exists — current A/B mixes RR3.0 (filtered) vs RR2.0 (baseline).

## Why
- **Reopened B (direction filter), prior null was VOID** — the −33.8pp "aligned=reversal" was circularity, and results 20/21 ran on BRC-contaminated tester_zones. Never cleanly tested on FOB's own zones ([[fob_storyline_alignment_finding]], [[reopen_falsified_on_new_data]]).
- **D1 PBO chosen as the aligner** because it's independent: "direction of any TF = that TF's most recent PBO", a D1-bar event independent of both W1 above and the H4 setup below → breaks the circularity that faked the old result. `htf_state.D1.dir` = `pbo_dir` ([fob_types.mqh:283](mt5/Include/fob_system/fob_types.mqh#L283)), causal, non-circular.
- **Built into the EA (not trusted from Python)** — Syafiq's standing rule: MT5 tester is the arbiter, query-layer is a FIND only. Wired as a toggle so it rips out cleanly if null.
- **v1 scope frozen to ALIGN-only, one aligner TF** — maturity (`cf_count` band) + multi-TF stack are phase-2 knobs, default-off, so we don't build the full State Engine cold.

## Ruled-Out
- **D1-alignment on H4 CFs — NULL on the clean mid screen** (aligned ≈ not-aligned, diff-t~1.2; D1 cf_count maturity buckets all flat-negative; human dec call_id 96). Syafiq distrusted the Python layer → escalated to the tester anyway (didn't take the mid null as the verdict).
- **Tester first pass: D1 filter does NOT rescue H4 to profitability** — every cell net-negative, cf0 and cf2, filtered or not (result_id 37/38 + closest baseline). The filter removes a third of trades without turning the edge positive. NOT yet a formal kill (confounded by RR — task 252 closes it).
- **RR=8 corner (prior session) stays dead** — sparsest-win, bleeds worst; never eyeball a single high-RR corner.

## Live-Threads
- **The de-confound (task 252) is the ONLY thing between us and a clean B verdict.** Weight of evidence (clean mid null + confounded tester pass, both negative) strongly points to: H4-CF-at-cost is dead regardless of D1 alignment → B retires properly, pivot to C.
- **C (exit / payoff-asymmetry) is the real untested lever** — strategy_log 94: M5 cf1 winners run median MFE ~8.8–14× band vs the 2R cap (artifact research/outputs/fob_m5_screen_run19/m5_cfidx_payoff.csv). Rule 16's escape from cost-death. Every entry-side lever (A entry, B direction) has now come back null/negative; C is where FOB lives or dies.
- **Filter is generic** — `InpDirFilterTf` also accepts W1/MN1 with no rebuild. If B shows ANY life at cf2 after de-confounding, sweep the aligner TF before abandoning.
