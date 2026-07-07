# Handover — July 7, 2026 Morning

## State
- **SHIPPED: PBO_LIMIT entry mechanic** (v1.34.0, committed 9efaae3) — [fob_baysix.mq5](../mt5/Experts/fob_system/fob_baysix.mq5) `InpEntryMode=PBO_LIMIT` + `InpPboEntryLevel{T1,T2,T3}`. Pending limit into the PARENT PBO zone, armed on VR (pre-CF). Trader-side `g_cur_pbo` cache; EMIT oracle byte-identical.
- **PBO pre-CF entry FALSIFIED** across all 3 depths (H4 8yr net real-tick): result_id 34 (T1 −$4.12/t), 35 (T2 −$0.94/t), 36 (T3 −$0.50/t); lineage change_id 91.
- **FOCUS PIVOT (Syafiq):** build the **State Engine → Sorter → Location Detector**, in that order. Tasks 243 (P1) / 244 (P1) / 245 (P2).
- FOB architecture agreed as 6 truths: State(WHAT) · Selector(WHICH) · Entry(WHERE) · Sorter(HOW FAR) · Exit(WHEN) · Sizing(HOW MUCH).

## Next
1. **(task 243, P1)** FOB **State Engine** — wire cross-TF `htf_state` (EMIT already stamps it; `fob_entry.mqh` reads NONE) into TRADE-mode decisioning. Design-first. The foundation.
2. **(task 244, P1)** FOB **Sorter** — horizon bucketer (scalp/intraday/swing) reading the State Engine. Buckets MEASURED, not guessed. After 243.
3. **(task 245, P2)** FOB **Location Detector** — continuous `room_R` at-wall measure (entry guard + E4 TP). After 243+244.
4. **(task 242, P1 — still open)** cf3 survivorship decomposition (result_id 32 fills) — the confirmed-edge thread PBO_LIMIT redirects back to.

## Blockers
- **None.** 243 is a design session (no build gate). cf3 OOS (task 238) stays untouched until 242 settles edge-vs-survivorship.

## Why
- **PBO_LIMIT built despite the "screen cost-free first" default** because a limit fill at a zone depth is a **tick-path question** (did price actually trade to T2 before continuing?) — only the real-tick tester answers it honestly. So the EA was the right arbiter, not a Python screen.
- **One-level-per-run (not 3-at-once layering)** chosen so the sweep needs **zero CSV format change** — the trades ledger is mode-agnostic (16 generic cols), entry mode/level lives in the FILENAME (`pbot1/2/3`), `entry_px` captures the fill. Layering (3 fills/VR) would need an `entry_level` column + `ingest_fob` migration in lockstep → deferred to sizing (task 168).
- **Ordering State→Sorter→Location (Syafiq):** the State Engine is the substrate the FOB edge is *defined* on (reaction-on-CMP within a nested storyline); Sorter and Location Detector both *consume* it, so it must exist first. Combined design task 241 split into 243/244/245 to encode the sequence.

## Ruled-Out
- **PBO pre-CF entry (all depths) — REJECTED/FALSIFIED**, strategy_log change_id 91, results 34/35/36. Do not retry. Two hypotheses killed: near-edge base AND deeper-filters-traps. Decisive read: all 3 depths significant-negative (t −4.25/−2.20/−3.00); WR *worsens* with depth (31.4→30.5→24.1, all < 33.3 BE); mean R worsens (−0.064→−0.089→−0.299). $/trade "improving" toward 0 (−4.12→−0.50) is **pure denominator illusion** ([[er_denominator_illusion]]) — tighter risk, same bad signal, NOT edge. Deep fills adversely selected (deep pullback = reversal, not retrace).
- **Corollary (not a dead-end, a signpost):** skipping the CF removes the load-bearing filter → **the CF confirmation is what earns** (mirror of cf3 = +$304, result_id 32). Redirects effort to the confirmed-entry path, not more pre-CF variants.

## Live-Threads
- **cf3 survivorship (task 242) still unresolved** — carried from last session. result_id 32 (+$304/373 trades) is IS-only, un-OOS'd; geometry leans survivorship (run_19, exploratory). PBO_LIMIT's failure sharpens the priority: the CF path is the only thing with a positive net, so settling whether cf3 is edge vs survivorship is now the gating question before any OOS spend (task 238).
- **State Engine scope is undecided** — 243 is design-first: which TF fields TRADE reads live, how the htf_state JSON is parsed in-EA (or whether a lighter per-TF struct is passed), and whether it's awareness-only (record) or a soft conditioner (gate). Syafiq's design calls next session.
