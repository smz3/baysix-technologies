# Handover — June 25, 2026 Evening

## State (FOB-001 — edge-test ladder T1–T6 defined; T1 trader EA BUILT, not yet run)
- **Decision:** skip the Python screen (dropped task 155); build trade logic in the EA so the **MT5 tester is the verdict**. Edge-test ladder = tasks **163(T1)–168(T6)** in `log_tasks` (idea FOB-001). Locked from the FOB manual ([FOB_breakout_system.dissect.md](research/papers/fob/FOB_breakout_system.dissect.md)): **CMP entry, NOT barrier** (barrier = TP only).
- **FOB_VERSION 1.6.0 → 1.7.0.** New [fob_trader.mq5](mt5/Experts/fob_system/fob_trader.mq5) (magic 3001) reuses the emitter's exact classifier; emitter stays pristine. Both EAs + includes compile **0 err** (only cosmetic MQL5-Market version warning). All pushed (latest `59d7196`). Deployed to JM terminal (E7DB) via junction.
- **T1 atom (the coin-flip GATE):** trigger = a **CF** on `InpSetupTf` (4=H1 → CF on M30); entry = **MARKET on CF**, continuation dir; **SL = beyond the CF zone** (CF's broken swing `e.level` ± `InpSlBufferK`); **TP = 1:1 RR** (`InpRMultTP`). Symmetric ±risk = 50% null by construction → win-rate >50% w/ binomial z = CF has directional content. One position at a time. Per-trade ledger (setup_tf/event_tf/cf_idx/seq/realized_R/win) auto-writes to `Common\Files\FOB\fob_trades_*.csv` → T2 input.
- **Per-TF iteration:** EA ingests ONLY `{setup_tf-1, setup_tf}` (byte-identical for that setup's events, fast). Run once per setup TF (8×: `InpSetupTf`=1..8), separate ledger each, combine later.
- **Classifier change (emitter-safe):** `FobSetupState.vr_level` stored on VR lock ([fob_sequence.mqh](mt5/Include/fob_system/fob_sequence.mqh)) — emitter CSV byte-identical; trader no longer uses it (SL is now CF-anchored).
- **Chart cleanup:** native trade-level bands + Ask/Bid price lines (the red/gray bands Syafiq hated) + OHLC disabled in `OnInit`; dropped our own trade markers (MT5 draws deals); added `fob_visual` sequence dots so fills are eyeballable.

## Next
1. **(task 163, P1)** Run `fob_trader` real-ticks 8yr, `InpSetupTf=4` (H1) first — paste the journal `win-rate XX% (w/n)` line. Then ingest the ledger CSV → `pipeline.log_result()` (binomial z vs 0.5). Repeat `InpSetupTf`=1..8 for the per-TF sweep, combine.
2. **(task 169, P2)** ATR-based R variant — Syafiq flagged CF-zone SL is too tight (fast SL/TP hits, min-stop skips). Add `InpRMode = CF_ZONE | ATR`; ATR symmetric bracket = cleaner consistent-R coin-flip. Build next session, not on fumes.
3. **(task 164, P2 / T2)** once T1 passes: split win-rate by `cf_idx` (1 vs 2 vs ≥3) — tests the manual's "2nd CF is best" (conditional) claim.

## Blockers
None. EA compiles + deployed. Re-attach in JM terminal (E7DB) to pull the new `.ex5` (caches old). Open-prices same-bar SL+TP resolves SL-first (slight pessimistic bias) — fine for the gate.
