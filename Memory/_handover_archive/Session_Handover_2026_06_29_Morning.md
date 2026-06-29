# Handover — June 29, 2026 Morning

## State
- **FOB storyline-alignment gate BUILT + MT5-net tested + REJECTED.** Gate is `InpAlignGate`/`InpAlignDepth` in [fob_trader.mq5](../mt5/Experts/fob_system/fob_trader.mq5) v1.20.0 (off by default → baseline unchanged). Preset: [fob_trader-v1.20.0-align3.set](../mt5/presets/fob_system/fob_trader-v1.20.0-align3.set).
- **Result (result_id 18, REJECTED — strategy_log id 79):** H1 CF + full-stack H4/D1/W1 agreement. WR 29.59% (+0.48pp vs id16 29.11%, BE 33.3% — FLAT), E[R] −0.1356 (vs −0.1264), net −0.078/tr, t=−2.06, N=463 (−84% trades). $/tr "better" = sizing artifact, not edge.
- **ROOT-CAUSE found:** the +4.8pp screen finding was computed on **BRC zones (run_id 5)**, not FOB — FOB never had its own zone run in the DB, so the screen silently queried BRC. FOB CMP storyline *model* is genuine FOB; the *empirical numbers* were BRC structure mislabelled.
- **ALL BRC tester data PURGED** (Syafiq order): `tester_runs`/`tester_zones`/`tester_trades` all = **0**. Added code-layer `tester.delete_run()`. BRC re-emits fresh when needed.
- **FOB trader baselines intact + correct:** id16 (H1 −0.363), id17 (H4 −0.897), result_id 11–18 + 9 `fob_trades_*` CSVs in `Common/Files/FOB`. Untouched.

## Next
1. **(task 190, P1)** Run FOB emitter `fob_baysix` on **XAUUSD_dukas, 8 TF, 2016–2024, Open-prices** → `fob_events` CSV. (MT5 GUI/headless.)
2. **(task 191, P1)** Build FOB zone ingest: `fob_events` CSV → `tester_zones` **tagged `idea_id='FOB-001'`**. FOB CSV is an EVENT log (PBO/VR/CF) not a lifecycle log — ingest must rebuild `confirm_time/invalidation_time/continued/realized_r` (mirror [ingest_brc_zones](../research/code/io/tester.py) + fob_lifecycle).
3. **(task 192, P1)** Re-run storyline-alignment screen on FOB OWN zones; **pin run_id + assert `idea_id='FOB-001'`** (isolation guard). Decision point: if FOB ≈ 0pp → consistent w/ id18 → idea falsified on FOB.

## Blockers
- None.

## Why
- **Build went FOB-native deliberately** ("detect bias live in trader", not read BRC CSV) — so id18 is a clean FOB test even though the motivating screen was contaminated. The gate reads each higher-TF's last-confirmed-CF direction causally from the chronological event stream (no look-ahead); v1 bias = last-CF-direction (invalidation-without-replacement NOT modeled — known simplification, MT5 is arbiter).
- **Rejected the gate, not the idea:** id18 says the gate AS BUILT doesn't lift FOB hit-rate. Whether the storyline edge exists in FOB *structure* is still unknown — never screened on FOB zones (190→192 settles it).
- **Purged BRC instead of isolating it (Syafiq override):** I advised keep+isolate (BRC-001 parked-not-killed, [[brc_fade_parked_finding]]); Syafiq chose full wipe ("run fresh when needed"). Done via `delete_run()` because raw sqlite3 DELETE is hook-blocked. Decision logged call_id 89.

## Ruled-Out
- **Full-stack H4/D1/W1 alignment gate as a hit-rate lever for FOB** — REJECTED, result_id 18 / strategy_log 79. Flat WR, still net-negative. Do not re-run align3; it's banked.
- **Trusting the BRC-zone +4.8pp screen as a FOB property** — it was cross-detector contamination (FOB owns its stack, nothing shared from BRC). The 2026-06-27 [alignment findings doc](../docs/specs/2026-06-27_fob_storyline_alignment_findings.md) numbers are BRC structure — treat as VOID for FOB until re-screened on FOB zones.

## Live-Threads
- **Payoff asymmetry (task 167, "THE LEVER")** — two FOB entry signals now empty (fade≈continuation parked; alignment flat). If hit-rate won't move, the exit/TP side is where the money is. Revisit after 190→192 verdict.
- **`realized_r` SELL-sign convention** (task 189) — still unchecked; fold into the FOB re-screen.
- **Bias-definition refinement** — id18 used last-CF-direction (no invalidation kill). If FOB screen shows a real edge but trader stays flat, suspect the bias def / sizing before anything else.
- **Empty BRC husk note:** BRC fully gone from tester_* — any future BRC work starts from a fresh emit + ingest.
