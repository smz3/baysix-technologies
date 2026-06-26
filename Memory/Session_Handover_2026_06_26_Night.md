# Handover — June 26, 2026 Night

## State
- **FOB visual layer now v1.18.1** (was v1.16.2 at session start). 4 commits, all pushed: `95fa595` (dim v1.17.0), `e5842ef` (dim full-geom fix v1.17.1), `892bd9c` (RT v1.18.0), `e30f8f6` (RT live v1.18.1). Both EAs compile clean (0 errors).
- **Dimmed-failure retention:** an invalidated parent VR/CF no longer vanishes — it stays drawn in a FADED role colour (CF green / VR yellow, ~45%), FULL geometry (ray right), until its cycle supersedes (then wiped). Dead PBO-only bands still drop. Files: [fob_visual.mqh](mt5/Include/fob_system/fob_visual.mqh).
- **RT (Retouch) — new VR-only lifecycle field.** After a VR invalidates (close through L2), counts DISTINCT returns to the broken L2 edge (`rt_count`, hysteresis) + stamps first (`rt_time`). L2 label carries `[RTn]` next to `[Tn]` (e.g. `L2 VR W1 #16 SELL [T3] [RT0]`); orange dot at first retouch. New `FobZone.rt_count/rt_time` ([fob_types.mqh](mt5/Include/fob_system/fob_types.mqh)); `FobReplayZoneLife`+`FobLiveTouch` gained `track_rt` ([fob_lifecycle.mqh](mt5/Include/fob_system/fob_lifecycle.mqh)). Classifier UNTOUCHED throughout — all visual/lifecycle only.
- **KNOWN BUG (task 183):** RT not updating — a broken/dimmed D1 VR shows `[RT0]` though price re-touched L2. `rt_count` stuck at 0. Computation bug, not draw (label prints rt_count).

## Next
1. **(task 183, P1)** FIX RT not updating — invalidated VR shows `[RT0]` after price touched L2. Check L2-vs-L1 probe in `FobReplayZoneLife` RT phase + `FobLiveTouch` track_rt branch ([fob_lifecycle.mqh](mt5/Include/fob_system/fob_lifecycle.mqh)); verify `LiveTouchForming` fires for dead zones. Repro on the exact D1 VR.
2. **(task 181, P1)** Wire trader entry on RT: enter on first L2 retouch of a broken VR, setup-direction, conditioned on setup-TF ([fob_trader.mq5](mt5/Experts/fob_system/fob_trader.mq5)). DO AFTER 183.
3. **(task 182, P1)** RT stat study: export `rt_count/rt_time` to emitter CSV/tester_zones, measure RT-entry edge vs CF by setup-TF — prove or kill.

## Blockers
- None. (Pre-existing FOB tasks 179/175/171 still open but DEPRIORITISED behind the RT thread — RT is now the active line of work.)

## Why
- **RT exists because it's Syafiq's discretionary edge, now instrumented.** Break-and-retest of a broken VR: price breaks the VR (continuation resumes), returns to the broken L2 edge → enter in setup direction. Higher setup-TF = bigger move ("physics"). Powerful by feel, statistically UNPROVEN — so we built the measurement (RT stamp + visual) before any auto-trading.
- **L2 (not L1) is the RT level** — Syafiq's explicit call: RT = retest of the broken edge it closed through (classic break-and-retest, earliest/tightest entry).
- **Dimming, not wiping, was the prerequisite** — RT needs the broken VR to stay on-chart as the reference. That's why the dim work came first and feeds directly into RT.
- **Dim = faded role hue, full geometry.** First cut (v1.17.0) truncated dead bands at the invalidation bar → looked "half broken" next to live full-width zones. v1.17.1 draws full ray-right geometry, only the colour fades.
- **Everything this session is classifier-safe** — cf_count/last_conf_swing/seq untouched; the picture stays a pure projection of (event log × bar buffer).

## Ruled-Out
- **Grey dimmed bands — rejected.** Syafiq wants role-coloured dim (VR dim-yellow / CF dim-green), not neutral grey, so failed zones keep their identity.
- **Truncating dead bands at the invalidation bar — rejected** (v1.17.0 → v1.17.1). Read as "half broken." Dead zones now draw full geometry, colour-faded only.
- **Dimming PBO-only bands — rejected.** A PBO's death = the start of a new cycle, so a dead PBO-only band still drops (only parent VR/CF dim).
- **"First retouch only" for RT — superseded.** Went with a COUNT (`[RT0]`→`[RT1]`→…, distinct retouches with hysteresis) so the stat study can see repeat retests; the entry layer can still pick RT1.

## Live-Threads
- **RT live-tick (task 183) is the open thread.** I wired live intrabar RT into `FobLiveTouch` (v1.18.1) for [Tn]-parity, but Syafiq observes it NOT firing — `[RT0]` persists after an L2 touch on a dimmed D1 VR. His hunch: the live RT path may be probing L1 (the T-touch level) instead of L2. Unconfirmed — could equally be the closed-bar hysteresis (armed/re-arm), or `LiveTouchForming` not running for invalidated zones. Next session: reproduce on his exact D1 VR before changing code.
- **RT not yet in the emitter CSV** — visual-only so far; the stat study (182) needs `rt_count/rt_time` exported to tester_zones. Not started.
- **Trader has zero RT awareness** — entering on RT (181) is unbuilt; this session only made RT *visible/measurable*.
- **`/handover` filename snippet still only scans `memory/` root, not `_handover_archive/`** (carried from Evening3, still unticketed minor).
