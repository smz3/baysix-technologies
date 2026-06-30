# Handover — June 29, 2026 Afternoon3

## State
- **FOB EA modularization DONE + compiles 0-err — but UNCOMMITTED on disk, parity NOT yet verified (task 196 P1).**
- Trader [fob_trader.mq5](../mt5/Experts/fob_system/fob_trader.mq5) **741→258 lines**; emitter [fob_baysix.mq5](../mt5/Experts/fob_system/fob_baysix.mq5) **333→198**. 4 new includes: [fob_engine.mqh](../mt5/Include/fob_system/fob_engine.mqh) (shared detection — structs/`FobPeriods`/`FobIngestBar`/`FobIngestTf`/`FobSortPending`/reset helpers), [fob_entry.mqh](../mt5/Include/fob_system/fob_entry.mqh), [fob_ledger.mqh](../mt5/Include/fob_system/fob_ledger.mqh) (`FobTradeBook`), [fob_study.mqh](../mt5/Include/fob_system/fob_study.mqh) (`FobStudyState`).
- **Drift risk fixed:** emitter now `#include`s `fob_engine.mqh`; its copies deleted. Stale-ref grep clean.
- `FOB_VERSION` → **1.23.0** (emitter+trader `#property` lockstep). Both compile **0 errors** (only benign Market `xxx.yyy` warning).
- **Earlier this session (COMMITTED, pushed):** align gate REMOVED → v1.22.0 (strategy_log log_id 81, REJECTED filter, result_id 18); task-195 audit of path-A CSV passed.
- Plan file: [ok-plan-the-trader-deep-quasar.md](../../../.claude/plans/ok-plan-the-trader-deep-quasar.md).

## Next
1. **(task 196, P1)** Parity gate: run emitter (Open-prices) + trader (`FOB_TF_H1_M30`, K=0.25, RR=2.0, real ticks) on a FIXED window, **before (git 1.22.0 HEAD) vs after (1.23.0 working tree)**; diff `fob_capture_*` + `fob_trades_*` CSV **byte-identical**. Any diff = regression → do NOT commit. Clean → `git add -A` + commit + push.
2. **(task 191, P1)** Build `ingest_fob` (wide CSV → `fob_cycles`/`fob_events`/`fob_zones`). Decide `event_id` (EA emits `e+1` vs spec "ingest assigns") + `bar_open` home.
3. **(task 190, P1)** Emitter full-history run 2016–2024 → capture CSV.

## Blockers
- None. (Parity runs need the JM terminal free + a new PowerShell window with live output — rule 12.)

## Why
- **Refactor was pure structural, behaviour-preserving.** MQL5 includes paste ABOVE the `.mq5` globals/inputs, so every extracted fn takes state/inputs as PARAMS (e.g. `FobIngestBar(...,radius,maxAge)`, `FobOpenMarket(...,slBufferK,rMultTP,magic)`) or a by-ref struct (`FobTradeBook`/`FobStudyState`) — it cannot see `g_radius`/`InpSlBufferK` by name.
- **Commit gate is parity, not compile.** Tester is the arbiter; 0-err compile only proves it builds. The plan forbids committing until a before/after CSV diff is byte-identical — that's the only proof the move changed nothing.
- **`FobResetSetup` mirrors the EXACT 9 fields both EAs cleared inline** (not all FobSetupState fields) — adding resets could shift behaviour, so it's deliberately field-for-field identical.
- Version bumped to 1.23.0 despite no behaviour change — git sha changes anyway + stamps the new structure.

## Ruled-Out
- **Sharing detection by leaving it duplicated** — rejected; the whole point was to kill the copy-paste drift, which forced touching the emitter (consume-only, re-verified by re-emit diff).
- **Keeping ledger/study fns in the `.mq5` referencing globals** — impossible across an include boundary (globals declared below the include site); state had to be bundled into structs.

## Live-Threads
- **Parity runs not started** — the before-baseline needs the 1.22.0 binary (git HEAD). Easiest: stash working tree, `git stash`/checkout to get 1.22.0 `.ex5`, run baseline, restore, run 1.23.0, diff. Watch the runid/version token in filenames + any version-stamped column when diffing.
- **Audit notes from task 195 (non-blocking, for ingest task 191):** EA emits `event_id=e+1` though spec §6.1 says ingest assigns it; stale `FOB_N_TF=8` comment in [fob_types.mqh:203](../mt5/Include/fob_system/fob_types.mqh#L203) (array is 9). 4 semantic judgment calls (vr_fresh def, vr_made_first_tf=event_tf, touch hysteresis, body_clears=open-beyond-L1) still want Syafiq confirmation but are not code bugs.
- **`instruments` table** still designed-not-created — needed before the first FOB trader $ run.
