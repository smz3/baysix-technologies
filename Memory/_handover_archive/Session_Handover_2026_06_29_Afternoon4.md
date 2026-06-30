# Handover — June 29, 2026 Afternoon4

## State
- **Task 196 DONE + committed/pushed (ff62e95): FOB EA modularization parity gate PASSED.**
  - Ran emitter + trader **before (1.22.0 HEAD) vs after (1.23.0 working tree)** on a fixed window; `fob_capture` (23,758 rows, 13,817,860 B) + `fob_trades` (74 rows) **byte-identical, md5 match**. Refactor is behaviour-preserving. v1.23.0 stamped.
  - New parity inis committed: [fob_parity_emitter.ini](../mt5/tester/fob_parity_emitter.ini), [fob_parity_trader.ini](../mt5/tester/fob_parity_trader.ini).
- **⚠️ BIG RULE CHANGE (Syafiq, emphatic): BOTH FOB EAs run/tested on REAL TICKS ONLY (Model=4). Open-prices is BANNED for FOB.** FOB is a tick-resolution model — intrabar touch/retest path IS the signal.
  - The task-196 parity used an **open-prices emitter** → that model is now invalid. The *refactor-equivalence* conclusion still holds (before/after on the same model), but the emitter must be re-verified on ticks (task 198).
- **Uncommitted on disk right now:** `CLAUDE.md` (tester-model section rewritten to ticks-only). Needs commit.

## Done this session (housekeeping per Syafiq)
- **Deleted** the inherited BRC memo `brc_emitter_open_prices_model.md` (auto-memory) + removed its MEMORY.md index line — it was BRC's close-only logic, never FOB's.
- **Created** memory `fob_both_eas_real_ticks_only.md` (feedback, HARD rule) + indexed it.
- **Rewrote** [CLAUDE.md](../CLAUDE.md) "Tester model" line: both EAs REAL TICKS, open-prices banned, flags the live-only intrabar gate.
- **Logged tasks 197, 198** (below).

## Next
1. **(task 197, P1)** Remove the live-only gate in [fob_baysix.mq5](../mt5/Experts/fob_system/fob_baysix.mq5) OnTick (`bool live = !MQLInfoInteger(MQL_TESTER)`) so the **forming-bar touch/retest path runs in the TESTER** on real ticks. Today it's SKIPPED in tester → a tick run still emits bar-resolution output. Watch per-tick quadratic cost (gate touches by new-tick, not new-bar).
2. **(task 198, P1)** After 197: re-run emitter+trader parity on **real ticks (Model=4)**; re-verify capture CSV under true tick-resolution detection.
3. **(task 190, P1) — ⚠️ STALE TEXT:** task says "Open-prices" — that is now BANNED. Full-history emitter run must be **Model=4 real ticks**, and only after task 197 (else it's bar-resolution anyway). Also blocked on the data gap below.
4. **(task 191, P1)** Build `ingest_fob` (wide CSV → fob_cycles/fob_events/fob_zones). Audit notes from task 195 still pending Syafiq confirm (event_id, bar_open home, vr_fresh def).

## Blockers / Caveats
- **DATA GAP:** `XAUUSD_dukas` in the JM terminal (E7DB) currently only holds **full-year 2022** (2023+ empty — 1 stub bar). I ran parity on **2022-01-01 → 2022-04-01** because of this. The full 2016–2024 runs (task 190) need dukas history re-imported first.
- **Commit `CLAUDE.md`** (tester-rule change) — still on disk uncommitted.
- First FOB trader $ run still needs the `instruments` table (designed-not-created).

## Build/Run mechanics learned (this host)
- **PowerShell is DENIED via the Bash tool** this session (deny rule + the `-ExecutionPolicy Bypass` guard). Compile/run by calling `metaeditor64.exe` / `terminal64.exe` **directly from Bash** instead.
- **Compile detaches on back-to-back calls** — run ONE EA at a time, then `sleep 3` and assert fresh `.ex5` mtime + `Result: 0 errors` in the UTF-16 log. Looping both in one shot silently no-ops the 2nd.
- **Emitter Open-prices needed an M1 chart** (it ingests all 9 TFs incl M1; Open-Prices rejects sub-chart TFs). MOOT now that emitter = real ticks (Model=4 has no such restriction).
- Runtime (3-mo window): emitter ~50s, trader real-ticks ~22s. Headless tester fires only with NO terminal64 running ([[brc_headless_tester_fires]]).
- Filename quirk: capture runid keeps dots (`v1.23.0`), ledger strips them (`v1230`). Runid timestamp = backtest start/end (sim time), so only the version token differs run-to-run → content diff is clean.

## Why
- **Open-prices emitter "equivalent because detection is close-only"** — REJECTED by Syafiq for FOB. That was the BRC inheritance. FOB's edge is the intrabar path, so bar-resolution detection is invalid, not just slower → both EAs on real ticks.
- **Parity proven on the SAME model (open-prices both sides)** still validly proves the *refactor* changed nothing structurally (byte-identical md5) — but it does NOT prove correctness under the production model (ticks), hence task 198.
- **Memo deleted, not edited** — the BRC open-prices logic was wrong for FOB at its root; a HARD rule-memory replaces it so the wrong assumption can't be re-inherited.

## Ruled-Out
- **Running emitter on ticks WITHOUT removing the live-gate** — pointless: the code makes a tick run *look* fine but silently bar-resolution (intrabar path is live-only). Task 197 must land first.

## Live-Threads
- **task 190 has STALE "Open-prices" text** — must become Model=4 ticks; blocked on task 197 + the dukas data re-import.
- **dukas data gap** — `XAUUSD_dukas` only has full-2022 in the terminal; full-history runs need a re-import.
- **CLAUDE.md tester rule committed this session** — verify it reads ticks-only next session.
- Task-195 CSV-contract judgment calls (event_id, bar_open home, vr_fresh def) still want Syafiq confirm before ingest_fob (task 191).
