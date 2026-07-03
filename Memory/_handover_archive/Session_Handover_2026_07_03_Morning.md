# Handover — July 3, 2026 Morning

## State
- **FOB v1.32.0 SHIPPED** ([fob_baysix.mq5](mt5/Experts/fob_system/fob_baysix.mq5)), compiles 0 err / 1 benign Market version-warn. Three commits this session on top of v1.31.0.
- **Task 225 FIXED + VERIFIED** (Syafiq eyeball) — live-chart stray dots gone; both T- and RT-ladders on historical zones now match the tester tick-for-tick.
- **Task 226 SHIPPED + approved** — timeframe switch no longer re-warms (reuses cached ladder); near-instant.
- **Task 227 closed** — not a bug (CF gate already enforces `bt > vr_time`; VR & CF share the same TF so same-bar CF is structurally impossible).
- `InpDebugRt` input still present (default off, harmless) — verify-only, can be stripped.
- Tester + EMIT CSV **untouched** by all three fixes (live-chart only) → OOS re-emits still byte-identical.

## Next
1. **(task 220, P1)** Re-emit + re-test BOTH modes on current v1.32.0 build → clean RT-ladder capture. (Tester-affecting change was v1.30.0 VR-causality; v1.31.x/1.32.0 are live-only so CSV is byte-identical to a clean ≥v1.30.0 emit.)
2. **(task 222, P1)** VR contamination audit: diff old-CSV VRs vs the fresh re-emit — confirm the causality fixes changed the VR set as expected.
3. **(task 182, P1)** RT statistical study: export rt1/rt2/rt3 per VR, measure the RT-entry edge by setup-TF (the actual program goal; entry tasks 181/185/209 sit downstream).
4. Strip `InpDebugRt` once 225/226 fully settled (housekeeping).

## Blockers
- None.

## Why
- **225 was a two-part ordering bug, not a warm-up bug.** (1) v1.31.1: on a fresh live attach, OnTick §4 (live-tick path) ran on the FIRST tick and stamped every historical zone's `t*/rt*` slot at NOW (current price already satisfies the level), BEFORE the §5 warm-up replayed real ticks; warm-up is fill-only (`if slot==0`) so it could never overwrite the NOW value. Fix = defer §4 while `live && InpVisualize && !g_warmed`. (2) v1.31.2: with §4 deferred, historical T became warm-up-sourced only, exposing that `FobWarmFillTick` started the T-phase at the break-bar OPEN — the tester seeds its accumulator at the break-bar CLOSE, so it never counts that bar's own impulse plunge as touches. Fix = start T-phase at `bar_time + tf_sec`. RT was already correct (its `inval_close` boundary = bar CLOSE).
- **226 is safe because `g_events` is chart-period-INDEPENDENT** (EMIT ingests all 9 TFs; TRADE/STUDY key off `InpTfPair`, an input — never the chart period). So on a pure period switch the rebuild is redundant work → reuse the cached, warmed state. Guarded on `REASON_CHARTCHANGE` + unchanged symbol + `g_warmed` (recompile/param/template/symbol-swap all fall through to the full clean rebuild — the [[mt5_oninit_full_reset]] footgun stays closed for every non-CHARTCHANGE path). OnDeinit also skips the redundant ledger dump on CHARTCHANGE (the other half of the lag).
- Sequencing choice: did 225 → 226 → (next) 220 measurement thread. 226 was deliberately held until 225 was green so we weren't caching a buggy ladder.

## Ruled-Out
- **227 "CF+VR co-fire on one bar"** — investigated, not a bug. VR and every CF of a setup fire on the SAME TF (`etf`), the CF gate at [fob_sequence.mqh:156](mt5/Include/fob_system/fob_sequence.mqh#L156) requires `bt > vr_time`, and a confirmation-time mirror of the 221 fix is a mathematical no-op (same period cancels). Original report was a misread. No code change.
- **Bar-wick backfill family** (v1.27–v1.29.1) — already deleted in v1.31.0; do not revive. Bars can't time intrabar touches; the warm-up (real ticks) is the only truthful source.

## Live-Threads
- **Chart TYPE toggle (candles↔line) was NOT addressed by 226** — it never re-inits the EA (only fires OnChartEvent → repaint), so it never paid the re-warm cost. If Syafiq still sees lag there, it's pure DrawZones redraw perf (ClearAll + redraw all zones), a separate optimization — not yet a task.
- **226 reuse relies on globals surviving OnDeinit→OnInit.** Verified-by-design + Syafiq eyeball, but if a future MT5 build ever full-unloads on a period switch, reuse silently falls back to full rebuild (safe, just slower) — worth remembering if the "CHART-SWITCH reuse" log line ever stops appearing.
- **task 184** (RT not firing on D1 VR, fires on M30) — untouched this session; may or may not interact with the warm-up path. Left cold.
