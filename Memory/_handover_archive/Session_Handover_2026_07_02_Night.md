# Handover — July 2, 2026 Night

## State
- **FOB v1.31.0 SHIPPED** (commit 4e6df6d, compiles 0 err / 1 benign Market version-warn): killed the dual display engine. Deleted all 4 live-only bar-wick backfills (`FobBackfillLadderTimes`/`FobBackfillRtTimes` + `CFobVisual::BackfillChartLadder`/`BackfillChartRt`); replaced with a real historical-tick warm-up — [FobWarmupReplay](mt5/Experts/fob_system/fob_baysix.mq5) (EA) → [FobWarmFillTick](mt5/Include/fob_system/fob_lifecycle.mqh) (lifecycle), gated by new input `InpTickWarmDays=30`.
- **NOT confirmed working** — Syafiq eyeball: **RT dots STILL stray to the current timestamp** for pre-attach retouches (task 225). T-dots not confirmed either. So the warm-up isn't fully fixing the RT ladder.
- Tester untouched (`if(live)` gate) → EMIT CSV byte-identical by construction. Spec: [2026-07-02_fob_tick_warmup_single_engine.md](docs/specs/2026-07-02_fob_tick_warmup_single_engine.md).

## Next
1. **(task 225, P1)** Debug why RT dots still land at `now` for pre-attach retouches: check (a) `CopyTicksRange` actually returns pre-attach ticks (not empty/retry), (b) `inval_close` boundary routing, (c) whether RT is stamped by the live tick (OnTick section 4) at `now` instead of the warm-up. Print rt1/rt2/rt3_time vs bar on M5/M15.
2. **(task 227, P1)** CF+VR co-firing on ONE bar — CF must be strictly AFTER VR confirm. Sibling of the 1.30.0 VR-before-PBO fix; inspect the CF gate in `FobClassifyBreak` (require VR locked at a STRICTLY earlier bar_time).
3. **(task 226, P2)** Cache the historical scan across chart TF switches — each period switch re-inits + re-warms = few-sec lag. Persist g_events/ladders (globals survive OnInit on period-switch) behind a build-signature guard so a real recompile/param-change still rebuilds.

## Blockers
- None. But do NOT declare 223 fixed — the visual symptom (stray RT dots) persists; task 225 is the real gate.

## Why
- Chose **Option T** (keep FOB's timestamped touch-dots) over **Option S** (Sigma's count-only depth model) — logged human decision call_id 95. Sigma's [B2BZoneStatus](mt5/Include/Sigma_System/V5.0/Detection/B2BZoneStatus.mqh) only tracks boolean depth `T0–T3` as a label, stamps touch_time=`TimeCurrent()` (bar-res), never a time-anchored dot → it *avoids* the bug by asking an easier question but loses WHEN. FOB needs truthful WHEN+WHERE (program-critical for RT entry timing, tasks 181/182), so we keep dots and fix the engine.
- Root cause of the funky dots (confirmed in code): on live attach the close-path replays all 64 bars (invalidation correct) but the tick-path only ever sees the ONE current tick → historical touch ladders empty → bars can't recover intrabar TIME (right day/week, wrong minute on low TFs). The tester is already single-engine tick-exact; the fix makes live do what the tester does.
- `InpTickWarmDays=30` chosen because M5×64≈5h … H4×64≈11d all ≪ 30d (the bug band), while W1/MN1 (bar-accurate already) truncate at the edge; keeps attach cheap. `0`=unbounded.

## Ruled-Out
- **Sigma count-only touch model (Option S)** — rejected as the FOB approach: no time-anchored dots means it structurally cannot give the WHEN the program needs. Kept only as the conceptual lesson (depth is lossless from bars; time is not). Syafiq: "I prefer our FOB method."
- Bar-wick backfill (v1.27.1/1.29.1 family) — DELETED this session as the wrong tool; do not revive it. Bars can't time intrabar touches; that ceiling is physical, not a tuning bug.

## Live-Threads
- **v1.31.0 warm-up is unverified/partly-wrong** — the T-vs-RT boundary (`inval_close = invalidation_time + PeriodSeconds(tf)`) is my best guess at the tester ordering; the stray RT dots suggest RT stamping is still off. Prime suspect for task 225. May be that RT for a still-in-`g_watch` VR gets its first RT stamp from the live tick (section 4) before/instead of the warm-up, since warm-up skips already-`rdone` zones but a partially-stamped RT is not skipped.
- Caching (task 226) and the CF/VR co-fire (task 227) were both surfaced by Syafiq at session end — neither investigated yet; captured cold as tasks only.
