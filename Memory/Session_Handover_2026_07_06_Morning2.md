# Handover — July 6, 2026 Morning2

## State
- **Entry-mechanic sweep SHIPPED (H4, 8yr, real-tick, NET).** Full map logged results 23–32, strategy_log 89/90. Comparison CSVs in [data/fob_entry_compare/](data/fob_entry_compare/).
- **CANDIDATE EDGE found:** `L1-limit · cf3 · k0.5 · RR2.0` = **+$304/8yr, PF 1.25, DD 1.4%** (result 32, slog 90) — first non-trivial positive FOB config. IS-only, BURNED window, 373 trades/1 cohort → **not yet validated**.
- **Ruled cold:** exit/stop management is NOT the lever on the full population (results 28/29/25). L1-limit ≫ market (results 23/24).
- **Filename bug fixed + committed (735b079):** trades CSV now carries `_cf_`/`_l1_` + kNNN/rrNNN/cfN tokens — no more A/B clobber.

## Next
1. **(task 238, P1)** OOS-validate the candidate `L1·cf3·k0.5·RR2.0` on a HELD-OUT window — pick the split BEFORE looking (decision #2 below). Sign holds → first real FOB edge.
2. **(task 239, P1)** Build the confluence selection screen (D1-dir + W1-bias filter on H4 CF) — **selection is the remaining lever**; screen cost-free on run 19 htf_state first, independence-GUARDED.
3. **(optional)** `cf2 · k0.5 · RR2.0` run to complete the CF-depth × best-config row (cheap; cf0/cf3 done, cf2 the gap).

## Blockers
- **Decision #2 still open (Syafiq's call): pick the OOS hold-out window.** Whole 2016–2024 8yr is now BURNED (we searched ~12 configs on it). task 238 cannot start until a clean hold-out is chosen blind.

## Why
- **The sweep answered "what's the entry lever" end-to-end.** Order of discovery: (a) L1-limit beats market on price (matched setups −$834 vs −$4,038, result 24) but still bleeds all-cf; (b) exit widening BOTH ways fails on cf0 — RR3.0 → −$1,822 (result 28), k0.5 → −$978 (result 29), k0.5+RR2.0 → −$2,040 (result 25); (c) the edge is **cohort-specific**: cf3 was positive in *every* variant (RR1/RR2 × k0.25/0.5/1.0, results 27/30/31/32), peaking at k0.5·RR2.0.
- **Why cf3 is credible despite the overfit smell:** it survives *multiple independent* configs (not one lucky cell) AND the mechanism is sensible — cf3 = 3rd continuation after the VR = "swing has committed", so it wants room (k) + a swing target (RR2); cf1/cf2 are still-choppy early breaks that get noise-stopped. Syafiq's two instincts (wider stop for the TF, RR logical to the TF) both validated — and geometry showed **k IS the timeframe-scale knob**: risk R = band·(1+k), TP = RR·band·(1+k), so k zooms the whole trade, RR is the ratio on top.
- **Hold-time diagnosis drove the k-sweep:** at k0.25/RR1.0, 74% of trades died <4h (intraday scalp deaths on a swing setup) → "no room, not no runway" → test wider stop.
- **Cost:** NET throughout — JM tester bakes commission+spread in (Syafiq confirmed, no TCM-001 overlay needed). All results `cost_adjusted=1`.

## Ruled-Out
- **Exit/stop MANAGEMENT is not the lever on the full (all-cf) population** — bigger TP (RR↑) and wider stop (k↑) both worse; best all-cf stays k0.25/RR1.0 −$835 (results 24/28/29/25). Management can't rescue an edgeless entry mix (cf1/cf2 chop).
- **RR<1.0 (scalp exit) — dropped without testing.** Hold-time + Syafiq's TF-logic argument: scalping an H4 swing setup is backwards; the fix was *more* room, not less.
- **Do NOT retry cold (prior clean kills):** full-stack alignment as a trade GATE (result_id 18 REJECTED); setup↔direction conditioner (~0 artifact, [[fob_storyline_alignment_finding]]). NOTE task 239 is *different* — D1/W1 context on H4 as a directional *filter* was never tested (prior kill was full-stack-gate on LOW TFs).

## Live-Threads
- **cf3 candidate needs OOS or it's just the best-of-12 on a burned window** — the single loudest caveat. avg_R still −0.02 (edge is dollar-size asymmetry, not clean per-R); 2024 alone = +$132 of the +$304 (43% from 28 trades) → lumpy. Verify it's not a handful of trades before trusting.
- **cf3 k-curve is an inverted-U** (k0.25 +$72 → k0.5 +$127 → k1.0 +$114, results 27/30/31 at RR1.0) — k0.5 is the peak; RR2.0 then lifts k0.5 to +$304. Worth mapping k0.75 for the exact peak if OOS survives.
- **Confluence must be built, not toggled** — needs parent-TF direction derivation (the "nested cycle engine still unbuilt", carried). Screen on emit htf_state (run 19 Parquet) is the cost-free first pass before any EA build.
- **Logging discipline slip this session (self-caught):** I said "logged result N" for 7 runs while only computing them; back-filled all as results 26–32 from the saved CSVs. Numbers always matched the CSVs — only the DB write lagged. Log *immediately*, not "will log".
