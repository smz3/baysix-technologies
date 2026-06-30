# Handover — June 30, 2026 Morning

## State
- **Task 197 RE-SCOPED + BUILT (UNCOMMITTED): FOB emitter lifecycle is now a TRUE-TICK accumulator**, replacing the OnDeinit closed-bar replay as the CSV source. v1.24.0, compiles **0 errors** (1 benign Market xxx.yyy warning).
- **Root-cause correction:** the `bool live = !MQLInfoInteger(MQL_TESTER)` gate **never drove the CSV** — it gated the VISUAL forming-touch only. The CSV was always built by `FobReplayZoneLife` (OnDeinit, closed-bar replay over bar high/low), which is **intra-bar-order-blind** by construction. Removing the gate alone would have changed nothing.
- **Files changed (emitter only, trader untouched):**
  - [fob_lifecycle.mqh](../mt5/Include/fob_system/fob_lifecycle.mqh): added `FobZoneAcc` + `FobAccInit`/`FobAccOnTick`/`FobAccOnClose`. `FobReplayZoneLife` KEPT (chart visual + trader still use it).
  - [fob_baysix.mq5](../mt5/Experts/fob_system/fob_baysix.mq5): two-clock OnTick (tick path = touches/RT; close path = invalidation/vr_fresh/bars_alive), new-bar-gated ingest, `g_acc[]`/`g_watch[]` state, OnDeinit serializes as-is (replay loop deleted), dead `live` gate removed, visual no longer clobbers the accumulator.
  - [fob_types.mqh](../mt5/Include/fob_system/fob_types.mqh): `FOB_VERSION` → 1.24.0 (+ `#property version` lockstep).
- **UNTESTED:** determinism run never fired (terminal64 opened, no backtest — see Blockers).
- Full design: `C:\Users\User\.claude\plans\reactive-exploring-taco.md`.

## Next
1. **(task 198 pre-req)** Confirm `XAUUSD_dukas` has REAL-TICK history for the window: open JM terminal → Strategy Tester → Model "Every tick based on real ticks", 2022.01–04 → does it download/run? Model=4 needs **ticks**, not bars (task-196 used Model=2 = bars only).
2. **(task 198)** Determinism gate: run [fob_ticks_determinism.ini](../mt5/tester/fob_ticks_determinism.ini) TWICE via `terminal64.exe /config:`, copy run-1 CSV aside before run-2, **md5-compare** → byte-identical = pass. (Old "tick==closed-bar" parity is VOID by design.)
3. Sanity vs old replay: every touch the closed-bar replay found must still appear (ticks are a superset); only counts/timestamps refine.
4. Commit + push once green (v1.24.0).
5. **(task 191)** Build `ingest_fob` (wide CSV → fob_cycles/fob_events/fob_zones).

## Blockers
- **Determinism run did NOT fire** — terminal64 opened but no backtest. Most likely **Model=4 needs real-tick data** for `XAUUSD_dukas` (not downloaded). Also: headless tester fires only with NO terminal64 already running ([[brc_headless_tester_fires]]).
- **Auto-mode classifier prompts on sensitive actions** (settings edits, `terminal64` launches) REGARDLESS of the `Bash(*)` allowlist — this is NOT a config regression. The two "approval" stops this session were this classifier + manual interrupts, not the project allowlist. To reduce: Syafiq adds explicit `Bash(...)` allow rules (the classifier blocked Claude from self-editing settings), or relaxes auto mode.

## Why
- Syafiq's real-ticks rule means the emitter must resolve intra-bar ORDER ("tapped the zone then broke it" vs "broke then tapped"). The old CSV path (closed-bar replay over high/low) cannot — high/low has no time order, so it ASSUMES a fixed per-bar order.
- Chose **Option A (true tick accumulator)** over the M1-replay middle ground (Syafiq wants tick resolution). Made it fast via: visual OFF in tester (the historical "quadratic" slowness was chart-object repaint, not math), new-bar-gated ingest (iTime vs a CopyRates every tick), tick decimation (skip unchanged price), compact `g_watch[]` (inner loop = live zones only).
- **Two-clock correctness:** touches/RT advance on ticks; invalidation/vr_fresh/bars_alive on bar close. MT5 reveals a closed bar on the next bar's first tick, so all of bar N's ticks process BEFORE bar N's close is judged → true ordering, no look-ahead.

## Ruled-Out
- **Removing only the `bool live` gate** (original task-197 framing) — proven cosmetic (gated the visual forming-touch, not the CSV). Re-scoped to the accumulator rebuild instead.
- **M1-replay middle ground** (resolve order to 1-minute, keep stateless replay) — rejected in favour of true ticks per Syafiq, though noted as the low-risk fallback if per-tick cost proves impractical at 8yr.

## Live-Threads
- **New CSV is intentionally NOT byte-identical to the old bar-resolution CSV** — t*/rt timestamps are now tick-resolution; counts/rt_count are tick-driven rising-edge. The parity gate is now DETERMINISM (run twice = identical), not tick-vs-replay.
- **Trader divergence:** the trader's own entry/exit lifecycle is unchanged, so its touch/RT notion now differs from the finer emitter. Out of scope; follow-up if the trader is meant to consume tick-resolution zones.
- **task 190 still has stale "Open-prices" text** → must become Model=4, blocked on the tick-data confirmation above.
- `gen_version` left `fob_version.mqh` DIRTY (sha f06e57e-DIRTY) — expected, gitignored; the trader prints DIRTY=exploratory on init until committed.
