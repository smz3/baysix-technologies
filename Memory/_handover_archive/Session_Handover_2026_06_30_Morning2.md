# Handover — June 30, 2026 Morning2

## State
- **FOB emitter v1.24.0 (true-tick accumulator) — DETERMINISM PASS on real ticks, committed `797473d`.** Ran [fob_ticks_determinism.ini](../mt5/tester/fob_ticks_determinism.ini) twice (Model=4, XAUUSD_dukas, 2022.01–04); both captures byte-identical (md5 `21b05f9da8cfc66f1343af44994ddde0`, 13,955,225 bytes).
- **`ingest_fob` BUILT + committed `927d732`** — [tester.py](../research/code/io/tester.py) `ingest_fob()` + CLI [ingest_fob.py](../research/code/io/ingest_fob.py). Capture CSV → fob_cycles/fob_zones/fob_events; cycles reconstructed by (setup_tf,seq); event↔zone 1:1.
- **FOB own zones loaded → run_id 16** (idea_id=FOB-001, run_role=emitter): 9054 cycles / 23914 zones / 23914 events, 0 orphans, counts match raw CSV.
- One-command determinism runner added: [run_determinism.ps1](../mt5/tester/run_determinism.ps1).
- Tasks 191/197/198/199 resolved. 190 wording fixed (Model=4). 200 added (ingest_fob phase-2).

## Next
1. **(task 192, P1)** Re-run storyline-alignment screen on **run_id 16**, asserting `run_id=16 AND idea_id='FOB-001'` + filter `zone_valid=1` (drops pre-VR PBOs). EXPLORATORY mid-price, NOT a tester gate.
2. **(task 190, P1)** Scale the emitter to full history (XAUUSD_dukas 8TF, 2016–2024, real ticks Model=4), then `ingest_fob` each.
3. **(task 200, P2)** ingest_fob phase-2: derive Tier-C values (continued/confirm from next-CF linkage; mfe/mae/realized_r; supersede/is_primary).

## Blockers
- None. Real-tick data for XAUUSD_dukas CONFIRMED present (~2GB .tkc, 201606→202606) — earlier "no tick data" claim was wrong (conflated Arctic store vs MT5 per-symbol tick DB).

## Why
- Emitter rebuilt as a true-tick accumulator (two-clock OnTick) so the CSV resolves intra-bar ORDER — the old OnDeinit closed-bar replay was order-blind by construction; removing the `bool live` gate alone was cosmetic (it gated only the visual). Per Syafiq's real-ticks rule.
- Parity gate redefined: old "tick==closed-bar" is VOID by design (ticks record finer order); new canonical gate = DETERMINISM (run twice = byte-identical).
- `ingest_tester_run` extended with optional run_role/git_sha/git_dirty (all default None, preserves callers) so the emitter run tags run_role='emitter' — that's the isolation handle task-192's screen filters on, so it can never grab BRC's old tester_zones run_id 5 again.
- ingest_fob mirrors retired ingest_brc_zones; risk_class LR/HR→LOW/HIGH; Tier-C cols wired NULL per spec (values deferred to task 200).

## Ruled-Out
- **Removing only the `bool live` gate** (original task-197 framing) — cosmetic, gated the visual not the CSV. Re-scoped to accumulator rebuild (carried from prior handover, now shipped).
- **Committing the `_det_run1.csv` scratch file** — it's out-of-tree (MT5 Common/Files) AND `*.csv` already gitignored; durable proof is the md5+verdict, not the 14MB file.

## Live-Threads
- **PBO `l2=0` is EXPECTED, not a bug** — 1924 PBO zones have l2=0, ALL with zone_valid=0 (perfect match). A PBO's 4-pointer zone is defined by the VR retracement swing; ~1888 of those PBOs never produced a VR → no L2. Screens must filter `zone_valid=1`.
- **Event bar_time predates the test window** (run 16 events back to 2021-01-31 despite FromDate 2022.01.01) — higher-TF (W1/MN1) anchors reference pre-window history bars. Lookback, not look-ahead; faithful to CSV. Confirm it's benign for the screen.
- **Trader divergence** — trader's own touch/RT lifecycle is coarser than the new tick-resolution emitter; out of scope until the trader is meant to consume tick-resolution zones.
- `gen_version` leaves fob_version.mqh DIRTY between commits (gitignored, expected); trader prints DIRTY=exploratory on init.
